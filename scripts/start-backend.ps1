param(
    [string]$ProjectRoot = (Split-Path -Parent $PSScriptRoot)
)

$ErrorActionPreference = 'Stop'
$backendPath = Join-Path $ProjectRoot 'backend'

# Already-running terminals may not have inherited newly saved Windows variables.
# Read only these settings, without displaying or copying credentials to files.
foreach ($settingName in @('MOONSHOT_API_KEY', 'MOONSHOT_BASE_URL', 'MOONSHOT_MODEL',
        'MOONSHOT_MAX_TOKENS', 'PLANNING_MODEL_PROVIDER')) {
    if ([string]::IsNullOrWhiteSpace([Environment]::GetEnvironmentVariable($settingName, 'Process'))) {
        foreach ($settingScope in @('User', 'Machine')) {
            $settingValue = [Environment]::GetEnvironmentVariable($settingName, $settingScope)
            if (-not [string]::IsNullOrWhiteSpace($settingValue)) {
                [Environment]::SetEnvironmentVariable($settingName, $settingValue, 'Process')
                break
            }
        }
    }
}
if ([string]::IsNullOrWhiteSpace($env:PLANNING_MODEL_PROVIDER) -and
        -not [string]::IsNullOrWhiteSpace($env:MOONSHOT_API_KEY)) {
    $env:PLANNING_MODEL_PROVIDER = 'moonshot'
}
if ($env:PLANNING_MODEL_PROVIDER -eq 'moonshot' -and
        [string]::IsNullOrWhiteSpace($env:MOONSHOT_API_KEY)) {
    throw 'Moonshot provider selected, but MOONSHOT_API_KEY is missing.'
}

if (-not (Get-Command mvn -ErrorAction SilentlyContinue)) {
    throw 'Maven (mvn) is required. Install Maven and ensure it is on PATH.'
}

if ([string]::IsNullOrWhiteSpace($env:DEVICE_CREDENTIAL_ENCRYPTION_KEY) -or $env:DEVICE_CREDENTIAL_ENCRYPTION_KEY.Length -lt 32) {
    throw 'Set DEVICE_CREDENTIAL_ENCRYPTION_KEY to a secret of at least 32 characters before starting the backend.'
}

if (-not (Test-Path -LiteralPath (Join-Path $backendPath 'pom.xml'))) {
    throw "Backend project was not found at: $backendPath"
}

Push-Location $backendPath
try {
    & mvn spring-boot:run
    if ($LASTEXITCODE -ne 0) {
        throw "Backend exited with code $LASTEXITCODE. Check database, Redis, and application configuration."
    }
}
finally {
    Pop-Location
}
