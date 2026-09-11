[CmdletBinding()]
param(
    [switch]$AutoInstallSystemTools,
    [switch]$SkipInstall,
    [switch]$SkipTests,
    [switch]$SkipAudioModelDownload,
    [switch]$SkipShortcut,
    [ValidatePattern('^[A-Za-z0-9._/-]+$')]
    [string]$AudioModel = 'small'
)

$ErrorActionPreference = 'Stop'
$kitRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$engineRoot = Split-Path -Parent $kitRoot
$demoRoot = Join-Path $kitRoot 'demo-data'
$workspace = 'groundmap-demo'

function Refresh-ProcessPath {
    $machinePath = [Environment]::GetEnvironmentVariable('Path', 'Machine')
    $userPath = [Environment]::GetEnvironmentVariable('Path', 'User')
    $env:Path = "$machinePath;$userPath"
}

function Require-Command([string]$Name, [string]$WingetId, [string]$InstallHint) {
    $command = Get-Command $Name -ErrorAction SilentlyContinue
    if ($command) { return $command.Source }

    if (-not $AutoInstallSystemTools) {
        throw "Missing $Name. $InstallHint"
    }

    $winget = Get-Command 'winget.exe' -ErrorAction SilentlyContinue
    if (-not $winget) {
        throw "Missing $Name and Windows Package Manager (winget) is unavailable. $InstallHint"
    }

    Write-Host "Installing $Name with Windows Package Manager..."
    & $winget.Source install --exact --id $WingetId --silent --accept-package-agreements --accept-source-agreements
    if ($LASTEXITCODE -ne 0) { throw "Automatic installation of $Name failed (exit $LASTEXITCODE). $InstallHint" }
    Refresh-ProcessPath

    $command = Get-Command $Name -ErrorAction SilentlyContinue
    if (-not $command) { throw "$Name was installed but is not available in this terminal. Restart Windows, then run this launcher again." }
    return $command.Source
}

function Invoke-Checked([string]$FilePath, [string[]]$Arguments, [string]$FailureMessage) {
    & $FilePath @Arguments
    if ($LASTEXITCODE -ne 0) { throw "$FailureMessage (exit $LASTEXITCODE)." }
}

Write-Host '[1/7] Checking local tools...'
$python = Require-Command 'python' 'Python.Python.3.13' 'Install Python 3.11-3.13 and enable Add Python to PATH.'
$node = Require-Command 'node' 'OpenJS.NodeJS.LTS' 'Install Node.js 20 or newer LTS.'
$npm = Require-Command 'npm.cmd' 'OpenJS.NodeJS.LTS' 'Install Node.js with npm.'
$git = Require-Command 'git' 'Git.Git' 'Install Git for Windows.'

$pythonVersion = & $python -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')"
$nodeMajor = [int]((& $node -p "process.versions.node.split('.')[0]").Trim())
if ([version]$pythonVersion -lt [version]'3.11' -or [version]$pythonVersion -ge [version]'3.14') {
    throw "Python $pythonVersion is unsupported. Use Python 3.11-3.13."
}
if ($nodeMajor -lt 20) {
    throw "Node.js $nodeMajor is unsupported. Use Node.js 20 or 22 LTS."
}

if (-not $SkipInstall) {
    Write-Host '[2/7] Installing Python, OCR, and audio dependencies...'
    Invoke-Checked -FilePath $python -Arguments @('-m','pip','install','-r',(Join-Path $engineRoot 'requirements.txt')) -FailureMessage 'Base Python dependency installation failed'
    Invoke-Checked -FilePath $python -Arguments @('-m','pip','install','-r',(Join-Path $engineRoot 'requirements-ocr.txt')) -FailureMessage 'OCR dependency installation failed'
    Invoke-Checked -FilePath $python -Arguments @('-m','pip','install','-r',(Join-Path $engineRoot 'requirements-audio.txt')) -FailureMessage 'Audio transcription dependency installation failed'

    Write-Host '[3/7] Installing Web dependencies...'
    Invoke-Checked -FilePath $npm -Arguments @('--prefix',(Join-Path $engineRoot 'web'),'ci') -FailureMessage 'Knowledge-console dependency installation failed'
    Invoke-Checked -FilePath $npm -Arguments @('--prefix',(Join-Path $engineRoot 'tools\debug-console'),'ci') -FailureMessage 'Query-console dependency installation failed'
} else {
    Write-Host '[2/7] Dependency installation skipped.'
    Write-Host '[3/7] Web dependency installation skipped.'
}

$audioModelStatus = 'skipped'
if (-not $SkipAudioModelDownload) {
    Write-Host "[4/7] Preparing faster-whisper audio model '$AudioModel'..."
    & $python -c "from faster_whisper.utils import download_model; print(download_model('$AudioModel'))"
    if ($LASTEXITCODE -eq 0) {
        $audioModelStatus = 'ready'
    } else {
        $audioModelStatus = 'download_failed'
        Write-Warning 'The audio model could not be downloaded. Core setup will continue; retry setup on a network that can reach the model repository before testing audio transcription.'
    }
} else {
    Write-Host '[4/7] Audio model download skipped.'
}

$localEnv = Join-Path $kitRoot '.env.local'
if (-not (Test-Path -LiteralPath $localEnv)) {
    Copy-Item -LiteralPath (Join-Path $kitRoot '.env.example') -Destination $localEnv
    Write-Host 'Created test-kit\.env.local. Add provider keys there when needed.'
}

Write-Host '[5/7] Converting synthetic source files...'
$previousKbRoot = $env:KB_ROOT
$previousWorkspace = $env:KB_WORKSPACE
try {
    $env:KB_ROOT = $demoRoot
    $env:KB_WORKSPACE = $workspace
    & $python (Join-Path $engineRoot 'scripts\convert.py') --workspace $workspace
    if ($LASTEXITCODE -ne 0) { throw 'Synthetic data conversion failed.' }

    Write-Host '[6/7] Initializing the demo data Git history...'
    if (-not (Test-Path -LiteralPath (Join-Path $demoRoot '.git'))) {
        & $git -C $demoRoot init
        & $git -C $demoRoot config user.name 'GroundMap Internal Tester'
        & $git -C $demoRoot config user.email 'groundmap-test@localhost'
    }
    & $git -C $demoRoot add .
    & $git -C $demoRoot diff --cached --quiet
    if ($LASTEXITCODE -ne 0) {
        & $git -C $demoRoot commit -m 'Initialize synthetic GroundMap test workspace'
    }

    Write-Host '[7/7] Running health checks...'
    & $python (Join-Path $engineRoot 'scripts\k.py') --workspace $workspace health --json
    if ($LASTEXITCODE -ne 0) { throw 'Knowledge-base health check failed.' }
    & $python (Join-Path $engineRoot 'scripts\k.py') --workspace $workspace list-broken-refs --json
    if ($LASTEXITCODE -ne 0) { throw 'Broken-reference check failed.' }

    if (-not $SkipTests) {
        & $npm --prefix (Join-Path $engineRoot 'web') test
        if ($LASTEXITCODE -ne 0) { throw 'Web tests failed.' }
        & $npm --prefix (Join-Path $engineRoot 'tools\debug-console') test
        if ($LASTEXITCODE -ne 0) { throw 'Debug-console tests failed.' }
    }
} finally {
    $env:KB_ROOT = $previousKbRoot
    $env:KB_WORKSPACE = $previousWorkspace
}

$markerPath = Join-Path $kitRoot '.setup-complete'
@{
    completedAt = (Get-Date).ToUniversalTime().ToString('o')
    audioModel = $AudioModel
    audioModelStatus = $audioModelStatus
    pythonVersion = $pythonVersion
    nodeMajor = $nodeMajor
} | ConvertTo-Json | Set-Content -LiteralPath $markerPath -Encoding UTF8

if (-not $SkipShortcut) {
    try {
        $desktop = [Environment]::GetFolderPath('Desktop')
        $shortcutPath = Join-Path $desktop 'GroundMap Internal Test.lnk'
        $shell = New-Object -ComObject WScript.Shell
        $shortcut = $shell.CreateShortcut($shortcutPath)
        $shortcut.TargetPath = Join-Path $kitRoot '00-INSTALL-AND-START.cmd'
        $shortcut.WorkingDirectory = $engineRoot
        $shortcut.Description = 'Install, start, and open GroundMap'
        $shortcut.Save()
        Write-Host "Desktop shortcut created: $shortcutPath"
    } catch {
        Write-Warning "Desktop shortcut could not be created: $($_.Exception.Message)"
    }
}

Write-Host ''
Write-Host 'Setup complete. The one-click launcher can now start GroundMap directly.' -ForegroundColor Green
