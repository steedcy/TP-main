$ErrorActionPreference = 'Stop'
$root = (Resolve-Path (Join-Path $PSScriptRoot '..\..')).Path
$random = [Security.Cryptography.RandomNumberGenerator]::Create()
$adminBytes = New-Object byte[] 16
$operatorBytes = New-Object byte[] 16
$random.GetBytes($adminBytes)
$random.GetBytes($operatorBytes)
$adminPass = [BitConverter]::ToString($adminBytes).Replace('-', '')
$operatorPass = [BitConverter]::ToString($operatorBytes).Replace('-', '')
[pscustomobject]@{ Admin = (ConvertTo-SecureString $adminPass -AsPlainText -Force); Operator = (ConvertTo-SecureString $operatorPass -AsPlainText -Force) } | Export-Clixml (Join-Path $root '.local-test\nf015.credentials.xml')
$cp = 'C:\Users\savy\.m2\repository\org\springframework\security\spring-security-crypto\6.2.4\spring-security-crypto-6.2.4.jar;C:\Users\savy\.m2\repository\org\springframework\spring-jcl\6.1.6\spring-jcl-6.1.6.jar'
$hashHelper = Join-Path $root '.local-test\NfHash'
$adminHash = $adminPass | & 'C:\Program Files\jdk-17.0.12\bin\java.exe' -cp "$hashHelper;$root\.local-test;$cp" NfHash
if ($LASTEXITCODE -ne 0 -or $adminHash -notmatch '^\$2[aby]\$') { throw 'Admin BCrypt generation failed.' }
$operatorHash = $operatorPass | & 'C:\Program Files\jdk-17.0.12\bin\java.exe' -cp "$hashHelper;$root\.local-test;$cp" NfHash
if ($LASTEXITCODE -ne 0 -or $operatorHash -notmatch '^\$2[aby]\$') { throw 'Operator BCrypt generation failed.' }
$sql = "UPDATE tip_nf015_v197_20261112.users SET password_hash='$adminHash',failed_login_attempts=0,locked_at=NULL,locked_reason=NULL,status='ACTIVE' WHERE username='nf015_admin'; UPDATE tip_nf015_v197_20261112.users SET password_hash='$operatorHash',failed_login_attempts=0,locked_at=NULL,locked_reason=NULL,status='ACTIVE' WHERE username='nf015_operator';"
$sql | & 'C:\Program Files\PostgreSQL\15\bin\psql.exe' -h 127.0.0.1 -p 55432 -U nf015_test -d nf015_v197 -v ON_ERROR_STOP=1
Remove-Variable adminHash,operatorHash,sql
Write-Output 'Reset isolated synthetic accounts with BCrypt. Passwords/hashes suppressed.'
