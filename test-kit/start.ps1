[CmdletBinding()]
param([switch]$NoBrowser)

$ErrorActionPreference = 'Stop'
$kitRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$engineRoot = Split-Path -Parent $kitRoot
$runtimeRoot = Join-Path $kitRoot '.runtime'
$demoRoot = Join-Path $kitRoot 'demo-data'
$envFile = Join-Path $kitRoot '.env.local'

function Import-DotEnv([string]$Path) {
    if (-not (Test-Path -LiteralPath $Path)) { return }
    foreach ($line in Get-Content -LiteralPath $Path) {
        $trimmed = $line.Trim()
        if (-not $trimmed -or $trimmed.StartsWith('#')) { continue }
        $separator = $trimmed.IndexOf('=')
        if ($separator -le 0) { throw "Invalid .env.local line: $line" }
        $name = $trimmed.Substring(0, $separator).Trim()
        $value = $trimmed.Substring($separator + 1).Trim()
        if ($name -notmatch '^[A-Za-z_][A-Za-z0-9_]*$') { throw "Invalid variable name: $name" }
        [Environment]::SetEnvironmentVariable($name, $value, 'Process')
    }
}

function Test-Http([string]$Url) {
    try {
        $response = Invoke-WebRequest -UseBasicParsing -Uri $Url -TimeoutSec 2
        return $response.StatusCode -ge 200 -and $response.StatusCode -lt 500
    } catch { return $false }
}

function Wait-Http([string]$Url, [int]$Seconds) {
    $deadline = (Get-Date).AddSeconds($Seconds)
    do {
        if (Test-Http $Url) { return $true }
        Start-Sleep -Milliseconds 500
    } while ((Get-Date) -lt $deadline)
    return $false
}

function Get-ListeningPid([int]$Port) {
    foreach ($line in (& netstat.exe -ano -p tcp)) {
        if ($line -match "^\s*TCP\s+\S+:$Port\s+\S+\s+LISTENING\s+(\d+)\s*$") {
            return [int]$Matches[1]
        }
    }
    throw "No listening process found for port $Port."
}

New-Item -ItemType Directory -Force -Path $runtimeRoot | Out-Null
Import-DotEnv $envFile
if (-not $env:KB_ROOT) { $env:KB_ROOT = $demoRoot }
if (-not $env:KB_WORKSPACE) { $env:KB_WORKSPACE = 'groundmap-demo' }
if (-not $env:KB_API_BASE) { $env:KB_API_BASE = 'http://127.0.0.1:3006' }
if (-not $env:NEXT_PUBLIC_KB_URL) { $env:NEXT_PUBLIC_KB_URL = $env:KB_API_BASE }
if (-not $env:NEXT_PUBLIC_CONSOLE_URL) { $env:NEXT_PUBLIC_CONSOLE_URL = 'http://127.0.0.1:3100' }
$env:NO_PROXY = 'localhost,127.0.0.1'
$env:no_proxy = $env:NO_PROXY

$resolvedKbRoot = (Resolve-Path -LiteralPath $env:KB_ROOT).Path
$workspaceRoot = Join-Path $resolvedKbRoot ("workspaces\" + $env:KB_WORKSPACE)
if (-not (Test-Path -LiteralPath $workspaceRoot -PathType Container)) {
    throw "Workspace not found: $workspaceRoot"
}
if (-not (Test-Path -LiteralPath (Join-Path $engineRoot 'web\node_modules'))) {
    throw 'Dependencies are missing. Run 01-FIRST-TIME-SETUP.cmd first.'
}

$webPidPath = Join-Path $runtimeRoot 'web.process.json'
$consolePidPath = Join-Path $runtimeRoot 'console.process.json'
if ((Test-Http 'http://127.0.0.1:3006/api/workspaces') -or (Test-Http 'http://127.0.0.1:3100')) {
    if (-not (Test-Path -LiteralPath $webPidPath) -and -not (Test-Path -LiteralPath $consolePidPath)) {
        throw 'Port 3006 or 3100 is already in use by another process. Close it before starting this test kit.'
    }
}

$npm = (Get-Command npm.cmd -ErrorAction Stop).Source
$stdinPath = Join-Path $runtimeRoot 'stdin.txt'
Set-Content -LiteralPath $stdinPath -Value '' -Encoding ASCII
$web = Start-Process -FilePath $npm -ArgumentList @('run','dev') -WorkingDirectory (Join-Path $engineRoot 'web') -WindowStyle Hidden -PassThru -RedirectStandardInput $stdinPath -RedirectStandardOutput (Join-Path $runtimeRoot 'web.out.log') -RedirectStandardError (Join-Path $runtimeRoot 'web.err.log')

$console = Start-Process -FilePath $npm -ArgumentList @('run','dev') -WorkingDirectory (Join-Path $engineRoot 'tools\debug-console') -WindowStyle Hidden -PassThru -RedirectStandardInput $stdinPath -RedirectStandardOutput (Join-Path $runtimeRoot 'console.out.log') -RedirectStandardError (Join-Path $runtimeRoot 'console.err.log')

if (-not (Wait-Http 'http://127.0.0.1:3006/api/workspaces' 45)) {
    throw 'Knowledge console did not start. Check test-kit\.runtime\web.err.log.'
}
if (-not (Wait-Http 'http://127.0.0.1:3100' 45)) {
    throw 'Query console did not start. Check test-kit\.runtime\console.err.log.'
}

$webListener = Get-Process -Id (Get-ListeningPid 3006) -ErrorAction Stop
$consoleListener = Get-Process -Id (Get-ListeningPid 3100) -ErrorAction Stop
@{
    pid = $webListener.Id
    startedAt = $webListener.StartTime.ToUniversalTime().ToString('o')
    name = $webListener.ProcessName
    launcherPid = $web.Id
    launcherStartedAt = $web.StartTime.ToUniversalTime().ToString('o')
} | ConvertTo-Json | Set-Content -LiteralPath $webPidPath -Encoding UTF8
@{
    pid = $consoleListener.Id
    startedAt = $consoleListener.StartTime.ToUniversalTime().ToString('o')
    name = $consoleListener.ProcessName
    launcherPid = $console.Id
    launcherStartedAt = $console.StartTime.ToUniversalTime().ToString('o')
} | ConvertTo-Json | Set-Content -LiteralPath $consolePidPath -Encoding UTF8

$knowledgeUrl = $env:NEXT_PUBLIC_KB_URL.TrimEnd('/') + '/?ws=' + [Uri]::EscapeDataString($env:KB_WORKSPACE)
$consoleUrl = 'http://127.0.0.1:3100/?ws=' + [Uri]::EscapeDataString($env:KB_WORKSPACE)
if (-not $NoBrowser) {
    Start-Process $knowledgeUrl
    Start-Process $consoleUrl
}
Write-Host "GroundMap is running for workspace '$($env:KB_WORKSPACE)'." -ForegroundColor Green
Write-Host "Knowledge console: $knowledgeUrl"
Write-Host "Query console: $consoleUrl"
