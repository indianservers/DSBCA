param([ValidateSet('migrate','api','worker','seed','test','build')][string]$Task='api')
$ErrorActionPreference='Stop'
$projectRoot=Split-Path $PSScriptRoot -Parent
$pythonExe=Join-Path $projectRoot 'backend\.venv\Scripts\python.exe'
$env:DSBCA_PHASE2_TASK=$Task
Push-Location (Join-Path $projectRoot 'backend')
try {
 @'
import os
from dotenv import load_dotenv
load_dotenv('.env.phase2.local',override=True)
task=os.environ['DSBCA_PHASE2_TASK']
if task=='migrate':
 from alembic import command
 from alembic.config import Config
 command.upgrade(Config('alembic.ini'),'head')
elif task=='api':
 import uvicorn
 uvicorn.run('app.main:app',host='127.0.0.1',port=8002)
elif task=='worker':
 import asyncio
 from app.ai.worker import main
 asyncio.run(main(1000))
elif task=='seed':
 from app.ai.dev_seed import run
 run()
elif task=='test':
 import pytest
 raise SystemExit(pytest.main(['-q']))
'@ | & $pythonExe -
 if ($LASTEXITCODE -ne 0){throw "Phase 2 command failed: $LASTEXITCODE"}
} finally {Pop-Location;Remove-Item Env:DSBCA_PHASE2_TASK}
if($Task -eq 'build'){
 $flutter=Join-Path $env:USERPROFILE '.cache\dsbca-flutter\bin\flutter.bat'
 foreach($app in @('dsbca_user','dsbca_admin')){Push-Location (Join-Path $projectRoot "apps\$app");try{& $flutter build web --release --dart-define=API_BASE_URL=http://localhost:8002;if($LASTEXITCODE -ne 0){throw 'Flutter build failed'}}finally{Pop-Location}}
}
