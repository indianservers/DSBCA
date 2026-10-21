param(
  [ValidateSet('install','migrate','seed','api','user','admin','test','build')][string]$Task = 'api',
  [string]$ApiBaseUrl = 'http://localhost:8000'
)
$ErrorActionPreference = 'Stop'
$projectRoot = Split-Path $PSScriptRoot -Parent
$flutterCommand = Get-Command flutter -ErrorAction SilentlyContinue
$flutterExe = if ($flutterCommand) { $flutterCommand.Source } else { Join-Path $env:USERPROFILE '.cache\dsbca-flutter\bin\flutter.bat' }
$pythonExe = Join-Path $projectRoot 'backend\.venv\Scripts\python.exe'
function Checked { param([scriptblock]$Run) & $Run; if ($LASTEXITCODE -ne 0) { throw "Command failed with exit code $LASTEXITCODE" } }
Push-Location $projectRoot
try {
  switch ($Task) {
    install {
      if (!(Test-Path $pythonExe)) { Checked { python -m venv backend/.venv } }
      Checked { & $pythonExe -m pip install -r backend/requirements.txt }
      foreach ($app in @('dsbca_user','dsbca_admin')) { Push-Location "apps/$app"; try { Checked { & $flutterExe pub get } } finally { Pop-Location } }
      foreach ($package in @('api_client','design_system','shared_models','shared_utils')) { Push-Location "packages/$package"; try { Checked { & $flutterExe pub get } } finally { Pop-Location } }
    }
    { $_ -in 'migrate','seed','api' } {
      Push-Location backend
      try {
        if ($Task -eq 'migrate') { Checked { & $pythonExe -m alembic upgrade head } }
        elseif ($Task -eq 'seed') { Checked { & $pythonExe -m app.seed } }
        else { Checked { & $pythonExe -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000 } }
      } finally { Pop-Location }
    }
    { $_ -in 'user','admin' } {
      $port = if ($Task -eq 'user') { 5183 } else { 5184 }
      Push-Location "apps/dsbca_$Task"
      try { Checked { & $flutterExe run -d web-server --web-hostname 127.0.0.1 --web-port $port "--dart-define=API_BASE_URL=$ApiBaseUrl" } } finally { Pop-Location }
    }
    test {
      Push-Location backend; try { Checked { & $pythonExe -m pytest -q } } finally { Pop-Location }
      foreach ($app in @('dsbca_user','dsbca_admin')) { Push-Location "apps/$app"; try { Checked { & $flutterExe analyze }; Checked { & $flutterExe test } } finally { Pop-Location } }
      Push-Location packages/api_client; try { Checked { & $flutterExe test } } finally { Pop-Location }
    }
    build {
      foreach ($app in @('dsbca_user','dsbca_admin')) { Push-Location "apps/$app"; try { Checked { & $flutterExe build web --release "--dart-define=API_BASE_URL=$ApiBaseUrl" }; Copy-Item vercel.json build/web/vercel.json } finally { Pop-Location } }
    }
  }
} finally { Pop-Location }
