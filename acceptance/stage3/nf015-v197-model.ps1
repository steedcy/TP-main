$ErrorActionPreference = 'Stop'
$root = (Resolve-Path (Join-Path $PSScriptRoot '..\..')).Path
$local = Join-Path $root '.local-test'
$python = (Get-Command python -ErrorAction Stop).Source
$fixture = Join-Path $root 'acceptance\stage3\fixtures\nf015-v197-controlled-model.py'
$journal = Join-Path $local 'nf015-v197-model-requests.jsonl'
$env:NF015_MODEL_PORT = '18117'
$env:NF015_MODEL_JOURNAL = $journal
$proc = Start-Process -FilePath $python -ArgumentList @($fixture) -WorkingDirectory $root -RedirectStandardOutput (Join-Path $local 'nf015-v197-model-out.log') -RedirectStandardError (Join-Path $local 'nf015-v197-model-err.log') -WindowStyle Hidden -PassThru
Set-Content (Join-Path $local 'nf015-v197-model.pid') $proc.Id
Write-Output "Started NF015 controlled model PID $($proc.Id) on 127.0.0.1:18117; secrets suppressed."
