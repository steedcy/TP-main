$ErrorActionPreference = 'Stop'
$root = (Resolve-Path (Join-Path $PSScriptRoot '..\..')).Path
$credential = Import-Clixml (Join-Path $root '.local-test\nf015.credentials.xml')
$env:NF015_ADMIN_USER = 'nf015_admin'
$env:NF015_ADMIN_PASSWORD = (New-Object System.Net.NetworkCredential('', $credential.Admin)).Password
$env:NF015_OPERATOR_USER = 'nf015_operator'
$env:NF015_OPERATOR_PASSWORD = (New-Object System.Net.NetworkCredential('', $credential.Operator)).Password
$env:NF015_BASE_URL = 'http://127.0.0.1:8180/api/v1'
$env:NF015_DB_HOST = '127.0.0.1'
$env:NF015_DB_PORT = '55432'
$env:NF015_DB_NAME = 'nf015_v197'
$env:NF015_DB_SCHEMA = 'tip_nf015_v197_20261112'
$env:NF015_REDIS_HOST = '127.0.0.1'
$env:NF015_REDIS_PORT = '56379'
$env:NF015_REDIS_DB = '0'
& (Join-Path $PSScriptRoot 'nf015-v197-gate.ps1')
Remove-Variable credential -ErrorAction SilentlyContinue
