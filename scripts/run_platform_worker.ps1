param(
    [string]$EnvironmentFile = "",
    [switch]$Continuous,
    [int]$IntervalSeconds = 30
)
$ErrorActionPreference = "Stop"
$WorkspaceRoot = Split-Path -Parent $PSScriptRoot
. (Join-Path $PSScriptRoot 'env-d-drive.ps1')
$env:PYTHONPATH = Join-Path $WorkspaceRoot 'services/api/src'
$env:PYTHONDONTWRITEBYTECODE = '1'
$WorkerArguments = @('-B','-m','lw_care_api.platform.control.worker','--interval',[string]$IntervalSeconds)
if ($EnvironmentFile) { $WorkerArguments += @('--env-file',$EnvironmentFile) }
if (-not $Continuous) { $WorkerArguments += '--once' }
& (Join-Path $WorkspaceRoot '.venv/Scripts/python.exe') @WorkerArguments
if ($LASTEXITCODE -ne 0) { throw 'The operating worker failed; inspect the redacted outcome and durable job state.' }
