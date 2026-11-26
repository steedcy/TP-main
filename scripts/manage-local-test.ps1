param(
    [ValidateSet('Start','StartAll','Stop','Status','DeviceFault','UseKimi','UseFaultModel','Frontend','ModelFixture')]
    [string]$Action='Status',
    [string]$Device,
    [string]$Mode
)
$ErrorActionPreference='Stop'
$tipRoot=(Resolve-Path -LiteralPath (Split-Path -Parent $PSScriptRoot)).Path
$tipPython=Join-Path $env:USERPROFILE '.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe'
if (!(Test-Path -LiteralPath $tipPython)) { $tipPython=(Get-Command python).Source }
$tipTool=Join-Path $PSScriptRoot 'local-test-environment.py'
function Stop-TipOwnedService([string]$Name) {
    $tipRegistry=Join-Path $tipRoot '.local-test\processes.json'
    if (!(Test-Path -LiteralPath $tipRegistry)) { return }
    $tipEntries=Get-Content -LiteralPath $tipRegistry -Raw | ConvertFrom-Json
    foreach ($tipEntry in $tipEntries.PSObject.Properties) {
        if ($Name -ne '*' -and $tipEntry.Name -ne $Name) { continue }
        $tipProcess=Get-CimInstance Win32_Process -Filter "ProcessId=$($tipEntry.Value.pid)"
        if ($tipProcess -and $tipProcess.CommandLine -and $tipProcess.CommandLine.Contains($tipRoot)) {
            Stop-Process -Id $tipProcess.ProcessId -Force
            Write-Output "Stopped owned service: $($tipEntry.Name)"
        }
    }
}
Push-Location -LiteralPath $tipRoot
try {
    switch ($Action) {
        'Stop' { Stop-TipOwnedService '*' }
        'Status' { & $tipPython -X utf8 $tipTool status }
        'Frontend' { & $tipPython -X utf8 $tipTool frontend }
        'ModelFixture' { & $tipPython -X utf8 $tipTool model-fixture }
        'DeviceFault' { & $tipPython -X utf8 $tipTool fault $Device $Mode }
        'Start' { & $tipPython -X utf8 $tipTool backend; if ($LASTEXITCODE -eq 0) { & $tipPython -X utf8 $tipTool start } }
        'StartAll' {
            & $tipPython -X utf8 $tipTool backend
            if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
            & $tipPython -X utf8 $tipTool start
            if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
            $frontendListening = Get-NetTCPConnection -LocalPort 5173 -State Listen -ErrorAction SilentlyContinue
            if (-not $frontendListening) {
                & $tipPython -X utf8 $tipTool frontend
                if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
            } else {
                Write-Output 'Frontend already listening on http://127.0.0.1:5173'
            }
            Write-Output 'All services ready: Frontend http://127.0.0.1:5173 | Backend http://127.0.0.1:8080 | All active simulators started'
        }
        'UseKimi' { Stop-TipOwnedService 'backend'; & $tipPython -X utf8 $tipTool backend --provider moonshot }
        'UseFaultModel' { Stop-TipOwnedService 'backend'; & $tipPython -X utf8 $tipTool backend --provider fault }
    }
}
finally { Pop-Location }
