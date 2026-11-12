$ErrorActionPreference = 'Stop'
$root = (Resolve-Path (Join-Path $PSScriptRoot '..\..')).Path
$script:base = 'http://127.0.0.1:8180/api/v1'
$cred = Import-Clixml (Join-Path $root '.local-test\nf015.credentials.xml')
$pw = (New-Object System.Net.NetworkCredential('', $cred.Admin)).Password
$login = Invoke-RestMethod -Method Post -Uri "$script:base/auth/login" -ContentType 'application/json' -Body (@{username='nf015_admin';password=$pw}|ConvertTo-Json -Compress)
$script:token = $login.data.token
function Api($path,$method='GET',$body=$null) {
  $h=@{Authorization="Bearer $script:token"}
  if($null -eq $body){ return Invoke-RestMethod -Method $method -Uri "$script:base$path" -Headers $h }
  Invoke-RestMethod -Method $method -Uri "$script:base$path" -Headers $h -ContentType 'application/json' -Body ($body|ConvertTo-Json -Depth 20 -Compress)
}
$ds=@(
 @{deviceCode='NF015_R01_A';deviceName='NF015合成终端A';deviceTypeCode='SIMULATOR';isSimulator=$true;simulatedDeviceType='MOBILE_ROBOT';areaCode='F2_TEST';positionX=800;positionY=4100;accessEndpoint='http://127.0.0.1:18132';accessCredentialRef='local-test/NF015_R01_A';statusReportInterval=5;remark='NF015 synthetic'},
 @{deviceCode='NF015_R01_B';deviceName='NF015合成备用终端B';deviceTypeCode='SIMULATOR';isSimulator=$true;simulatedDeviceType='MOBILE_ROBOT';areaCode='F2_TEST';positionX=810;positionY=4150;accessEndpoint='http://127.0.0.1:18137';accessCredentialRef='local-test/NF015_R01_B';statusReportInterval=5;remark='NF015 synthetic'}
)
$deviceTokens=@{}; $agents=@{}
$existing=@(Api '/devices?page=1&size=100').data.content
$robot=(Get-Content (Join-Path $root 'scripts/test-fixtures/devices.json') -Raw|ConvertFrom-Json|Where-Object simulatedDeviceType -eq 'MOBILE_ROBOT'|Select-Object -First 1)
foreach($d in $ds){
 if($existing.deviceCode -notcontains $d.deviceCode){[void](Api '/devices' 'POST' $d)}
 $deviceTokens[$d.deviceCode]=(Api "/devices/$($d.deviceCode)/device-token/rotate" 'POST').data.accessToken
 $env:SIMULATOR_PORT=$d.accessEndpoint.Split(':')[-1]; $env:SIMULATOR_DEVICE_CODE=$d.deviceCode; $env:SIMULATED_DEVICE_TYPE='MOBILE_ROBOT'; $env:SIMULATOR_DEVICE_TOKEN=$deviceTokens[$d.deviceCode]
 Remove-Item Env:SIMULATOR_AGENT_CODE -ErrorAction SilentlyContinue; Remove-Item Env:SIMULATOR_REPORT_URL -ErrorAction SilentlyContinue
 $env:SIMULATOR_X=[string]$d.positionX; $env:SIMULATOR_Y=[string]$d.positionY; $env:SIMULATOR_ZONE='F2_TEST'; $env:SIMULATOR_HEARTBEAT_INTERVAL_SECONDS='5'; $env:SIMULATOR_EXECUTION_DELAY_MS='700'
 $p=Start-Process -FilePath 'C:\Program Files\jdk-17.0.12\bin\java.exe' -ArgumentList @('-Xms32m','-Xmx128m','-XX:MaxMetaspaceSize=128m','-XX:+UseSerialGC','-jar',(Join-Path $root 'simulator\target\device-simulator-runtime.jar')) -WorkingDirectory $root -RedirectStandardOutput (Join-Path $root ".local-test\$($d.deviceCode).log") -RedirectStandardError (Join-Path $root ".local-test\$($d.deviceCode)-err.log") -WindowStyle Hidden -PassThru
 Set-Content (Join-Path $root ".local-test\$($d.deviceCode).pid") $p.Id
 $healthUntil=(Get-Date).AddSeconds(30); $health=$null
 do{Start-Sleep 1;try{$health=Invoke-RestMethod -Uri "$($d.accessEndpoint)/device-api/v1/health?nonce=nf015-gate" -Headers @{Authorization="Bearer $($deviceTokens[$d.deviceCode])"} -TimeoutSec 2}catch{}}while($null -eq $health -and (Get-Date)-lt $healthUntil)
 if($null -eq $health -or $health.deviceCode -ne $d.deviceCode -or $health.nonce -ne 'nf015-gate'){throw "Simulator health handshake failed for $($d.deviceCode)"}
 [void](Api "/devices/$($d.deviceCode)/connection-test" 'POST')
 $a=(Api '/device-agents?page=1&size=100').data.content|Where-Object deviceCode -eq $d.deviceCode|Select-Object -First 1
 $agents[$d.deviceCode]=$a.agentId
 $until=(Get-Date).AddSeconds(25); do{Start-Sleep 1;$aNow=(Api '/device-agents?page=1&size=100').data.content|Where-Object deviceCode -eq $d.deviceCode|Select-Object -First 1}while($aNow.onlineStatus -ne 'ONLINE' -and (Get-Date)-lt $until)
 if($aNow.onlineStatus -ne 'ONLINE'){throw "Simulator $($d.deviceCode) did not reach ONLINE"}
 $existingCapabilities=(Api "/devices/$($d.deviceCode)/capabilities").data
 foreach($c in $robot.capabilities){
  $cb=@{capabilityCode=$c.capabilityCode;capabilityName=$c.capabilityName;capabilityType=$c.capabilityType;inputParams=$c.inputParams;outputParams=$c.outputParams;capabilityDescription=$c.capabilityDescription}
  if(@($existingCapabilities|Where-Object capabilityCode -eq $c.capabilityCode).Count -eq 0){[void](Api "/devices/$($d.deviceCode)/capabilities" 'POST' $cb)}
  $tested=(Api "/devices/$($d.deviceCode)/capabilities/$($c.capabilityCode)/test" 'POST').data
  if($tested.capabilityStatus -ne 'TESTED_PASSED'){throw "Capability test failed: $($c.capabilityCode)"}
  [void](Api "/devices/$($d.deviceCode)/capabilities/$($c.capabilityCode)/status" 'POST' @{status='ENABLED'})
 }
}
$tpl=(Api '/baseline-templates').data|Where-Object templateIntent -eq 'SPECIAL_PASSENGER_SERVICE'|Select-Object -First 1
$ip=@(
 @{name='targetLocation';type='String';required=$true;defaultValue='F2_TEST_GATE';range=''},
 @{name='routePreference';type='String';required=$true;defaultValue='BARRIER_FREE';range='SHORTEST/BARRIER_FREE'},
 @{name='escortMode';type='String';required=$true;defaultValue='LEAD';range='LEAD/FOLLOW'},
 @{name='maxDuration';type='Integer';required=$true;defaultValue='600';range='60~1800'},
 @{name='notificationType';type='String';required=$true;defaultValue='BOTH';range='VOICE/TEXT/BOTH'},
 @{name='notificationContent';type='String';required=$true;defaultValue='合成测试通知';range=''},
 @{name='repeatCount';type='Integer';required=$true;defaultValue='1';range='1~5'}
)
$steps=@(
 @{capabilityType='CAP_NAVIGATION';paramMapping=@(@{target='targetLocation';source='TEMPLATE_INPUT.targetLocation'},@{target='routePreference';source='TEMPLATE_INPUT.routePreference'});stepTimeout=60;completionCondition='routeGenerated=true'},
 @{capabilityType='CAP_NOTIFICATION';paramMapping=@(@{target='notificationType';source='TEMPLATE_INPUT.notificationType'},@{target='notificationContent';source='TEMPLATE_INPUT.notificationContent'},@{target='repeatCount';source='TEMPLATE_INPUT.repeatCount'});stepTimeout=60;completionCondition='notificationStatus=SUCCESS'},
 @{capabilityType='CAP_ESCORT';paramMapping=@(@{target='targetLocation';source='TEMPLATE_INPUT.targetLocation'},@{target='escortMode';source='TEMPLATE_INPUT.escortMode'},@{target='maxDuration';source='TEMPLATE_INPUT.maxDuration'});stepTimeout=60;completionCondition='arrivalStatus=ARRIVED'}
)
$tpl=Api '/baseline-templates' 'POST' @{templateName='NF015合成特殊旅客基线';templateIntent='SPECIAL_PASSENGER_SERVICE';inputParams=$ip;steps=$steps}
$tpl=$tpl.data
$dry=Api "/baseline-templates/$($tpl.id)/dry-run" 'POST' @{inputParams=@{targetLocation='F2_TEST_GATE';routePreference='BARRIER_FREE';escortMode='LEAD';maxDuration=600;notificationType='BOTH';notificationContent='合成测试通知';repeatCount=1};simulatedDevices=@(@{stepSeq=1;agentId=$agents.NF015_R01_A},@{stepSeq=2;agentId=$agents.NF015_R01_B},@{stepSeq=3;agentId=$agents.NF015_R01_A})}
$until=(Get-Date).AddSeconds(120); do{Start-Sleep 2;$dry=Api "/baseline-templates/$($tpl.id)/dry-runs/$($dry.data.taskId)"}while($dry.data.result -eq 'RUNNING' -and (Get-Date)-lt $until)
if($dry.data.result -ne 'SUCCESS'){throw "Dry-run failed: $($dry.data.result)"}
[void](Api "/baseline-templates/$($tpl.id)/enable" 'POST')
$verified=(Api "/baseline-templates/$($tpl.id)").data
if($verified.templateStatus -ne 'ENABLED'){throw 'Template not ENABLED after query'}
$secure=@{NF015_R01_A=(ConvertTo-SecureString $deviceTokens.NF015_R01_A -AsPlainText -Force);NF015_R01_B=(ConvertTo-SecureString $deviceTokens.NF015_R01_B -AsPlainText -Force)}; $secure|Export-Clixml (Join-Path $root '.local-test\nf015-device.credentials.xml')
[pscustomobject]@{taskDefinitions=1;devices=2;deviceAgents=2;onlineAgents=2;testedEnabledCapabilities=$robot.capabilities.Count;dryRunPassedTemplates=1;enabledBaselineTemplates=1;templateId=$tpl.id;templateVersion=$verified.templateVersion;dryRun='SUCCESS'}|ConvertTo-Json -Compress
