Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

$Root = Split-Path -Parent $PSScriptRoot
Set-Location $Root

python -m pip install -r requirements-all.txt -c constraints.txt
python -m pyserve `
  --app demo.trivial_app:application `
  --host 127.0.0.1 `
  --port 8000 `
  --model threaded
