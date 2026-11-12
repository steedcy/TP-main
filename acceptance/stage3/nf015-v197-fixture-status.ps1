$root=(Resolve-Path (Join-Path $PSScriptRoot '..\..')).Path
$c=Import-Clixml (Join-Path $root '.local-test\nf015.credentials.xml')
$p=(New-Object System.Net.NetworkCredential('', $c.Admin)).Password
$r=Invoke-RestMethod -Method Post -Uri 'http://127.0.0.1:8180/api/v1/auth/login' -ContentType 'application/json' -Body (@{username='nf015_admin';password=$p}|ConvertTo-Json -Compress)
$h=@{Authorization="Bearer $($r.data.token)"}
$agents=Invoke-RestMethod -Uri 'http://127.0.0.1:8180/api/v1/device-agents?page=1&size=100' -Headers $h
$sim=Invoke-RestMethod -Uri 'http://127.0.0.1:8180/api/v1/simulators' -Headers $h
[pscustomobject]@{agents=@($agents.data.content|Where-Object {$_.deviceCode -like 'NF015*'}|Select-Object deviceCode,agentId,agentStatus,onlineStatus,workStatus,offlineReason);simulators=@($sim.data|Where-Object {$_.deviceCode -like 'NF015*'}|Select-Object deviceCode,onlineStatus,workStatus);simulatorLog=(Get-Content (Join-Path $root '.local-test\NF015_R01_A.log') -Tail 6)}|ConvertTo-Json -Depth 5 -Compress
