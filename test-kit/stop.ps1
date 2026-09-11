[CmdletBinding()]
param()

$ErrorActionPreference = 'Stop'
$kitRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$runtimeRoot = Join-Path $kitRoot '.runtime'

function Stop-RecordedProcess([string]$RecordPath) {
    if (-not (Test-Path -LiteralPath $RecordPath)) { return }
    $record = Get-Content -LiteralPath $RecordPath -Raw | ConvertFrom-Json
    $process = Get-Process -Id ([int]$record.pid) -ErrorAction SilentlyContinue
    if ($process) {
        $actualStart = $process.StartTime.ToUniversalTime()
        $recordedStart = [DateTime]::Parse($record.startedAt).ToUniversalTime()
        if ([Math]::Abs(($actualStart - $recordedStart).TotalSeconds) -le 2) {
            Stop-Process -Id $process.Id -Force
            Write-Host "Stopped listener process $($process.Id)."
        } else {
            Write-Warning "Skipped reused PID $($process.Id); start time did not match."
        }
    }
    if ($record.launcherPid) {
        $launcher = Get-Process -Id ([int]$record.launcherPid) -ErrorAction SilentlyContinue
        if ($launcher) {
            $launcherStart = $launcher.StartTime.ToUniversalTime()
            $recordedLauncherStart = [DateTime]::Parse($record.launcherStartedAt).ToUniversalTime()
            if ([Math]::Abs(($launcherStart - $recordedLauncherStart).TotalSeconds) -le 2) {
                Stop-Process -Id $launcher.Id -Force
            }
        }
    }
    Remove-Item -LiteralPath $RecordPath -Force
}

Stop-RecordedProcess (Join-Path $runtimeRoot 'console.process.json')
Stop-RecordedProcess (Join-Path $runtimeRoot 'web.process.json')
Write-Host 'GroundMap test services are stopped.' -ForegroundColor Green
