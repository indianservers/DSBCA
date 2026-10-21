param([ValidateSet('migrate','seed','api','test','worker')][string]$Task='api')
$ErrorActionPreference='Stop'
$root=Split-Path $PSScriptRoot -Parent
$env:DSBCA_PHASE4_TASK=$Task
Push-Location (Join-Path $root 'backend')
try {
$code = @'
import os
from dotenv import load_dotenv
load_dotenv('.env.phase4.local',override=True)
task=os.environ['DSBCA_PHASE4_TASK']
if task != 'test':
 from app.release_qa import guard
 guard()
if task=='migrate':
 from alembic import command
 from alembic.config import Config
 command.upgrade(Config('alembic.ini'),'head')
elif task=='seed':
 from app.release_qa import seed
 seed()
elif task=='api':
 import uvicorn
 uvicorn.run('app.main:app',host='127.0.0.1',port=8004,log_level='info',access_log=False)
elif task=='worker':
 import asyncio
 from app.professional.worker import main
 asyncio.run(main(100))
elif task=='test':
 import pytest
 raise SystemExit(pytest.main(['-q']))
'@
$code | & .venv/Scripts/python.exe -
if($LASTEXITCODE -ne 0){throw 'Phase 4 task failed'}
} finally {Pop-Location;Remove-Item Env:DSBCA_PHASE4_TASK}
