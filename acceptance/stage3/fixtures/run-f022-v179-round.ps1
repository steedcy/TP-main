$ErrorActionPreference = 'Stop'
$repo = (Resolve-Path (Join-Path $PSScriptRoot '../../..')).Path
# Build/test first. Support model/Vite must already be ready on owned ports.
# Primary suite waits for the real UI finish sentinel. No config writer or adapter
# probe is started concurrently; every following command waits for full cleanup.
$runs = @(
    @('fixtures/run-f022-v179-container-probe.py', 'container-probe'),
    @('fixtures/start-f022-v179-jar.py', 'start'),
    @('probe-f022-v179-flight-preset.py', 'flight-preset'),
    @('probe-f022-v179-suite.py', 'suite'),
    @('probe-f022-v179-mixed-clauses.py', 'mixed-clauses'),
    @('probe-f022-v179-baseline.py', 'baseline'),
    @('probe-f022-v179-replan-baseline.py', 'replan-baseline')
)
Push-Location -LiteralPath $repo
try {
    foreach ($run in $runs) {
        & python (Join-Path $repo "acceptance/stage3/$($run[0])") *> (Join-Path $repo ".local-test/f022-v179-$($run[1])-console.txt")
        if ($LASTEXITCODE -ne 0) { throw "Probe failed: $($run[0]); exit=$LASTEXITCODE" }
        Write-Output "Completed $($run[0])"
    }
} finally {
    Pop-Location
}
