$ErrorActionPreference = 'Stop'
$repo = (Resolve-Path (Join-Path $PSScriptRoot '../../..')).Path
$records = @()
foreach ($name in @('runtime-v175.json','model-v175-runtime.json','vite-v175-runtime.json')) {
    $state = Get-Content -LiteralPath (Join-Path $repo ".local-test/$name") -Raw | ConvertFrom-Json
    $ownedProcessId = [int]$state.pid
    $process = Get-CimInstance Win32_Process -Filter "ProcessId=$ownedProcessId"
    if ($process) {
        if ($process.CommandLine.IndexOf($repo,[System.StringComparison]::OrdinalIgnoreCase) -lt 0) { throw "PID $ownedProcessId is no longer an owned process" }
        $record = [ordered]@{ pid=$ownedProcessId; port=$state.port; command=$process.CommandLine; before='owned'; at=(Get-Date).ToUniversalTime().ToString('o') }
        $result = & taskkill.exe /PID $ownedProcessId /T /F 2>&1
        $record.exitCode = $LASTEXITCODE
        $record.output = ($result | Out-String).Trim()
        $records += $record
    }
}
Start-Sleep -Seconds 1
$ports = @(18129,18117,18132,18133,18134,18135,15179)
$listeners = @(Get-NetTCPConnection -State Listen | Where-Object { $_.LocalPort -in $ports } | Select-Object LocalPort,OwningProcess)
$out = [ordered]@{ at=(Get-Date).ToUniversalTime().ToString('o'); timezone='Asia/Shanghai'; tag='V1.175'; productSha='02a38cb08e14ece1968a800a18423219fdf76c8b'; processes=$records; ports=$ports; remainingListeners=$listeners; allReleased=($listeners.Count -eq 0); sharedPostgresqlRedis='not stopped/reset; GPT schema/Redis10 only'; cleanup='All tasks/versions/failure evidence retained; fixture configurations restored before process stop' }
$out | ConvertTo-Json -Depth 10 | Set-Content -LiteralPath (Join-Path $repo 'acceptance/stage3/evidence/SRS_F022-V1.175-process-cleanup-20261107.json') -Encoding utf8
Write-Output "Stopped $($records.Count) owned process trees; remaining listeners: $($listeners.Count)"
if ($listeners.Count -ne 0) { throw 'Owned ports remain in use' }
