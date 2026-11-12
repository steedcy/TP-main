$ErrorActionPreference = 'Stop'
$root = (Resolve-Path (Join-Path $PSScriptRoot '..\..')).Path
$data = (Resolve-Path (Join-Path $root '.local-test\nf015-pgdata')).Path
$pgctl = 'C:\Program Files\PostgreSQL\15\bin\pg_ctl.exe'
if (-not (Get-NetTCPConnection -State Listen -LocalPort 55432 -ErrorAction SilentlyContinue)) {
  & $pgctl -D $data -l (Join-Path $root '.local-test\nf015-postgres.log') -o '-p 55432 -h 127.0.0.1' start
  if ($LASTEXITCODE -ne 0) { throw 'Isolated PostgreSQL 55432 failed to start.' }
}
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
$env:DB_HOST = '127.0.0.1'
$env:DB_PORT = '55432'
$env:DB_NAME = 'nf015_v197'
$env:DB_USERNAME = 'nf015_test'
$env:SPRING_DATASOURCE_URL = 'jdbc:postgresql://127.0.0.1:55432/nf015_v197?currentSchema=tip_nf015_v197_20261112'
$env:REDIS_HOST = '127.0.0.1'
$env:REDIS_PORT = '56379'
$env:SPRING_FLYWAY_DEFAULT_SCHEMA = 'tip_nf015_v197_20261112'
$env:SPRING_FLYWAY_SCHEMAS = 'tip_nf015_v197_20261112'
$env:SERVER_PORT = '8180'
$env:APP_DEVICE_ADAPTER_PUBLIC_BASE_URL = 'http://127.0.0.1:8180'
$jar = (Resolve-Path (Join-Path $root 'backend\target\airport-ai-app-1.0.0.jar')).Path
$java = 'C:\Program Files\jdk-17.0.12\bin\java.exe'
$proc = Start-Process -FilePath $java -ArgumentList @('-Xms128m','-Xmx512m','-XX:+UseSerialGC','-jar',$jar) -WorkingDirectory $root -RedirectStandardOutput (Join-Path $root '.local-test\nf015-backend-out.log') -RedirectStandardError (Join-Path $root '.local-test\nf015-backend-err.log') -WindowStyle Hidden -PassThru
Set-Content (Join-Path $root '.local-test\nf015-backend.pid') $proc.Id
Write-Output "Started isolated backend PID $($proc.Id); credential values suppressed."
