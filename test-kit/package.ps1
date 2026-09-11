[CmdletBinding()]
param([string]$Version = (Get-Date -Format 'yyyyMMdd'))

$ErrorActionPreference = 'Stop'
$kitRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$engineRoot = Split-Path -Parent $kitRoot
$distRoot = Join-Path $engineRoot 'dist'
$packageName = "GroundMap-Internal-Test-$Version"
$stagingRoot = Join-Path $distRoot $packageName
$zipPath = Join-Path $distRoot ($packageName + '.zip')

if (Test-Path -LiteralPath $stagingRoot) { Remove-Item -LiteralPath $stagingRoot -Recurse -Force }
if (Test-Path -LiteralPath $zipPath) { Remove-Item -LiteralPath $zipPath -Force }
New-Item -ItemType Directory -Force -Path $stagingRoot | Out-Null

$rootFiles = @(
    'README.md','README.zh-CN.md','LICENSE','NOTICE','SECURITY.md','SUPPORT.md',
    'requirements.txt','requirements-ocr.txt','requirements-audio.txt'
)
foreach ($file in $rootFiles) {
    Copy-Item -LiteralPath (Join-Path $engineRoot $file) -Destination $stagingRoot
}
Copy-Item -LiteralPath (Join-Path $kitRoot 'README.md') -Destination (Join-Path $stagingRoot 'START-HERE.md')
Copy-Item -LiteralPath (Join-Path $kitRoot 'USER-GUIDE.zh-CN.md') -Destination (Join-Path $stagingRoot 'USER-GUIDE.zh-CN.md')
Copy-Item -LiteralPath (Join-Path $kitRoot 'PROJECT-INGEST-OPERATIONS.zh-CN.md') -Destination (Join-Path $stagingRoot 'PROJECT-INGEST-OPERATIONS.zh-CN.md')
@(
    '@echo off',
    'call "%~dp0test-kit\00-INSTALL-AND-START.cmd"',
    'exit /b %errorlevel%'
) | Set-Content -LiteralPath (Join-Path $stagingRoot 'GroundMap.cmd') -Encoding ASCII

$excludeDirs = @('.git','node_modules','.next','__pycache__','.pytest_cache','.runtime','_build','derived','dist')
$excludeFiles = @('.env','.env.local','.setup-complete','*.pyc','*.pyo','tsconfig.tsbuildinfo')
foreach ($relative in @('scripts','web','tools\debug-console','test-kit')) {
    $source = Join-Path $engineRoot $relative
    $destination = Join-Path $stagingRoot $relative
    New-Item -ItemType Directory -Force -Path $destination | Out-Null
    $arguments = @($source, $destination, '/E', '/NFL', '/NDL', '/NJH', '/NJS', '/NP', '/XD') + $excludeDirs + @('/XF') + $excludeFiles
    & robocopy.exe @arguments | Out-Null
    if ($LASTEXITCODE -ge 8) { throw "Packaging failed while copying $relative (robocopy exit $LASTEXITCODE)." }
}

$forbiddenNames = Get-ChildItem -LiteralPath $stagingRoot -Recurse -Force | Where-Object {
    $_.Name -in @('.env.local','.env','.git','node_modules','.next')
}
if ($forbiddenNames) { throw 'Package contains a forbidden secret, history, cache, or dependency path.' }

$textFiles = Get-ChildItem -LiteralPath $stagingRoot -Recurse -File | Where-Object { $_.Extension -in @('.md','.txt','.json','.js','.mjs','.ts','.tsx','.ps1','.cmd','.example') }
$markerFile = Join-Path $PSScriptRoot '.sensitive-markers.local'
if (-not (Test-Path -LiteralPath $markerFile)) {
    throw 'Create test-kit/.sensitive-markers.local from .sensitive-markers.example before packaging.'
}
$sensitiveMarkers = @(Get-Content -LiteralPath $markerFile | Where-Object { $_.Trim() -and -not $_.Trim().StartsWith('#') })
if (-not $sensitiveMarkers) { throw 'The local sensitive marker list must not be empty.' }
foreach ($file in $textFiles) {
    foreach ($marker in $sensitiveMarkers) {
        $match = Select-String -LiteralPath $file.FullName -Pattern $marker -SimpleMatch -ErrorAction SilentlyContinue
        if ($match) { throw "Sensitive marker found in package staging: $($file.FullName)" }
    }
    $keyMatch = Select-String -LiteralPath $file.FullName -Pattern 'DEEPSEEK_API_KEY=sk-[A-Za-z0-9_-]{12,}' -ErrorAction SilentlyContinue
    if ($keyMatch) { throw "Provider key found in package staging: $($file.FullName)" }
}

$manifestPath = Join-Path $stagingRoot 'PACKAGE-SHA256.txt'
Get-ChildItem -LiteralPath $stagingRoot -Recurse -File | Sort-Object FullName | ForEach-Object {
    $relative = $_.FullName.Substring($stagingRoot.Length + 1)
    $hash = (Get-FileHash -LiteralPath $_.FullName -Algorithm SHA256).Hash
    "$hash  $relative"
} | Set-Content -LiteralPath $manifestPath -Encoding UTF8

Compress-Archive -LiteralPath $stagingRoot -DestinationPath $zipPath -CompressionLevel Optimal
Write-Host "Created $zipPath" -ForegroundColor Green
