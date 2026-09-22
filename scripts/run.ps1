param([ValidateSet('preview','export','sync')][string]$Mode = 'preview')
$ErrorActionPreference = 'Stop'
$projectRoot = Split-Path -Parent $PSScriptRoot
$bundledPython = Join-Path $env:USERPROFILE '.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe'
$pythonCommand = $null
if (Test-Path -LiteralPath $bundledPython) { $pythonCommand = $bundledPython }
elseif (Get-Command py -ErrorAction SilentlyContinue) { $pythonCommand = (Get-Command py).Source }
elseif (Get-Command python -ErrorAction SilentlyContinue) { $pythonCommand = (Get-Command python).Source }
if (-not $pythonCommand) { throw 'Python 3 is required. Install it from python.org.' }
Set-Location -LiteralPath $projectRoot
if ($Mode -eq 'preview') {
    & $pythonCommand scripts/sync.py
    if ($LASTEXITCODE -ne 0) { throw 'Excel export failed; see details above.' }
    Write-Host 'Open http://localhost:8788 in your browser. Press Ctrl+C to stop.'
    & $pythonCommand -m http.server 8788 --bind 127.0.0.1 --directory public
} elseif ($Mode -eq 'export') {
    & $pythonCommand scripts/sync.py
} else {
    & $pythonCommand scripts/sync.py --watch --push
}
exit $LASTEXITCODE
