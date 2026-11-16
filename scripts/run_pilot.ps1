# Run a manifest on several parallel shards (improvement I10).
#
#   powershell -ExecutionPolicy Bypass -File scripts\run_pilot.ps1
#   powershell -ExecutionPolicy Bypass -File scripts\run_pilot.ps1 -Manifest manifests\x.csv -Name x -Shards 4
#
# Outputs go outside OneDrive (decision D7). Rerunning resumes: completed runs are skipped.
param(
  [string]$Manifest = "manifests\pilot.csv",
  [string]$Name = "pilot",
  [int]$Shards = 6,
  [string]$Daily = "first",
  [string]$Rscript = "C:\Program Files\R\R-4.6.1\bin\Rscript.exe"
)
$ErrorActionPreference = "Stop"
$repo = Split-Path -Parent $PSScriptRoot
$out = Join-Path $env:USERPROFILE "malaria-runs\$Name"
$logs = Join-Path $out "logs"
New-Item -ItemType Directory -Force $logs | Out-Null
Set-Location $repo

# Keep the computer awake (not the screen) while this script runs.
Add-Type -Namespace Win32 -Name Power -MemberDefinition @'
[DllImport("kernel32.dll")] public static extern uint SetThreadExecutionState(uint flags);
'@
$ES_CONTINUOUS = [uint32]"0x80000000"; $ES_SYSTEM_REQUIRED = [uint32]"0x00000001"
[Win32.Power]::SetThreadExecutionState($ES_CONTINUOUS -bor $ES_SYSTEM_REQUIRED) | Out-Null

$started = Get-Date
"Started $started  manifest=$Manifest  shards=$Shards  out=$out" | Tee-Object (Join-Path $logs "batch.log") -Append
$procs = foreach ($i in 1..$Shards) {
  $log = Join-Path $logs ("shard{0:D2}" -f $i)
  Start-Process -FilePath $Rscript -WindowStyle Hidden -PassThru `
    -RedirectStandardOutput "$log.out.txt" -RedirectStandardError "$log.err.txt" `
    -ArgumentList @("native_runner.R", "--manifest", $Manifest, "--out", "`"$out`"",
                    "--shard", $i, "--of", $Shards, "--daily", $Daily)
}
$procs | Wait-Process
[Win32.Power]::SetThreadExecutionState($ES_CONTINUOUS) | Out-Null

$codes = $procs | ForEach-Object { $_.Refresh(); $_.ExitCode }
$report = @("Started  $started", "Finished $(Get-Date)",
            "Elapsed  $([math]::Round(((Get-Date) - $started).TotalHours, 2)) h",
            "Exit codes by shard: $($codes -join ', ')")
$report | Set-Content (Join-Path $out "DONE.txt")
$report | Tee-Object (Join-Path $logs "batch.log") -Append
