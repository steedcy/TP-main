$ErrorActionPreference = 'Stop'
$required = @('NF015_BASE_URL','NF015_ADMIN_USER','NF015_ADMIN_PASSWORD','NF015_OPERATOR_USER','NF015_OPERATOR_PASSWORD','NF015_DB_HOST','NF015_DB_PORT','NF015_DB_NAME','NF015_DB_SCHEMA','NF015_REDIS_HOST','NF015_REDIS_PORT','NF015_REDIS_DB')
foreach ($name in $required) { if ([string]::IsNullOrWhiteSpace([Environment]::GetEnvironmentVariable($name))) { throw "Missing required NF015 environment variable: $name" } }
if ($env:NF015_BASE_URL -ne 'http://127.0.0.1:8180/api/v1' -or $env:NF015_DB_HOST -ne '127.0.0.1' -or $env:NF015_DB_PORT -ne '55432' -or $env:NF015_DB_NAME -ne 'nf015_v197' -or $env:NF015_DB_SCHEMA -ne 'tip_nf015_v197_20261112' -or $env:NF015_REDIS_HOST -ne '127.0.0.1' -or $env:NF015_REDIS_PORT -ne '56379' -or $env:NF015_REDIS_DB -ne '0') { throw 'NF015 isolation gate rejected non-fixed endpoint/database/schema/Redis settings.' }
$ports = @(Get-NetTCPConnection -State Listen -LocalPort 55432,56379,8180 -ErrorAction SilentlyContinue | Select-Object -ExpandProperty LocalPort -Unique)
if (@(55432,56379,8180 | Where-Object { $_ -notin $ports }).Count -gt 0) { throw 'NF015 isolation gate requires listeners on PostgreSQL 55432, Redis 56379 and backend 8180.' }
function Login($user,$password,$expectedRole) {
  $body = @{ username=$user; password=$password } | ConvertTo-Json -Compress
  $res = Invoke-RestMethod -Method Post -Uri "$env:NF015_BASE_URL/auth/login" -ContentType 'application/json' -Body $body
  if ($res.code -ne 200 -or -not $res.data.token -or $res.data.user.role -ne $expectedRole) { throw "Authentication gate failed for expected role $expectedRole." }
  return $res.data.token
}
$adminToken=Login $env:NF015_ADMIN_USER $env:NF015_ADMIN_PASSWORD 'CONFIG_ADMIN'
$operatorToken=Login $env:NF015_OPERATOR_USER $env:NF015_OPERATOR_PASSWORD 'OPERATOR'
$admin=Invoke-RestMethod -Uri "$env:NF015_BASE_URL/devices?page=1&size=1" -Headers @{Authorization="Bearer $adminToken"}
$operator=Invoke-RestMethod -Uri "$env:NF015_BASE_URL/tasks?page=1&size=1" -Headers @{Authorization="Bearer $operatorToken"}
if ($admin.code -ne 200 -or $operator.code -ne 200) { throw 'Role-authorized API gate failed.' }
[pscustomobject]@{endpoint='127.0.0.1:8180';postgres='127.0.0.1:55432/nf015_v197/tip_nf015_v197_20261112';redis='127.0.0.1:56379/0';adminLogin='HTTP 200 token CONFIG_ADMIN';operatorLogin='HTTP 200 token OPERATOR';authorizedApis='PASS';secretsRecorded=$false} | ConvertTo-Json -Compress
