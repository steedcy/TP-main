param(
    [switch]$WithFrontend
)

$ErrorActionPreference = 'Stop'
$manageScript = Join-Path $PSScriptRoot 'manage-local-test.ps1'
if ($WithFrontend) {
    & $manageScript -Action StartAll
} else {
    & $manageScript -Action Start
}
