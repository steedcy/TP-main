param(
    [string]$ProjectRoot = (Split-Path -Parent $PSScriptRoot)
)

$ErrorActionPreference = 'Stop'
$simulatorPath = Join-Path $ProjectRoot 'simulator'

if (-not (Get-Command mvn -ErrorAction SilentlyContinue)) {
    throw 'Maven (mvn) is required. Install Maven and ensure it is on PATH.'
}

if ([string]::IsNullOrWhiteSpace($env:SIMULATOR_DEVICE_CODE)) {
    throw 'Set SIMULATOR_DEVICE_CODE before starting the simulator.'
}
if ([string]::IsNullOrWhiteSpace($env:SIMULATOR_DEVICE_TOKEN)) {
    throw 'Set SIMULATOR_DEVICE_TOKEN before starting the simulator.'
}
if ([string]::IsNullOrWhiteSpace($env:SIMULATED_DEVICE_TYPE)) {
    throw 'Set SIMULATED_DEVICE_TYPE to SMART_DISPLAY, BAGGAGE_SCANNER, FLIGHT_DELAY_BOARD, or MOBILE_ROBOT.'
}

if (-not (Test-Path -LiteralPath (Join-Path $simulatorPath 'pom.xml'))) {
    throw "Simulator project was not found at: $simulatorPath"
}

Push-Location $simulatorPath
try {
    & mvn spring-boot:run
    if ($LASTEXITCODE -ne 0) {
        throw "Simulator exited with code $LASTEXITCODE. Check device configuration and platform availability."
    }
}
finally {
    Pop-Location
}
