"""Bounded loopback QA measurements; never targets Neon or a hosted API."""
import asyncio
import gzip
import json
import statistics
import sys
import time
import uuid
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from urllib.request import Request, urlopen
from dotenv import load_dotenv

root = Path(__file__).resolve().parent.parent
load_dotenv(root / 'backend/.env.phase4.local', override=True)
sys.path.insert(0, str(root / 'backend'))
from app.release_qa import guard, QAFixtureEmbeddings
from app.core.database import engine
from app.ai.retrieval import retrieve
from app.ai.schemas import ChatInput
from app.ai.configuration import current_config
from app import models as m
from sqlalchemy import select, text
from sqlalchemy.orm import Session

guard()
base = 'http://127.0.0.1:8004/api/v1'
credentials = json.loads((root / '.local-phase4-access.json').read_text())


def call(method, path, body=None, token=None, raw=False):
    headers = {'Content-Type': 'application/json'}
    if token:
        headers['Authorization'] = 'Bearer ' + token
    req = Request(base + path, data=json.dumps(body).encode() if body is not None else None, headers=headers, method=method)
    start = time.perf_counter()
    with urlopen(req, timeout=30) as response:
        data = response.read()
    return (data if raw else json.loads(data)), (time.perf_counter() - start) * 1000


tokens = {name: call('POST', '/auth/login', {k: credentials[name][k] for k in ['email', 'password']})[0]['access_token'] for name in ['operator', 'reader']}
u, a = tokens['reader'], tokens['operator']
cid = call('GET', '/companies', token=u)[0]['items'][0]['id']
report = {'environment': 'Windows loopback HTTP, local PostgreSQL 17.6, QA fixtures, pool 2/0, no hosted load', 'http': {}, 'assets': {}, 'query_plans': {}}


def measure(label, method, path, body=None, token=None, count=20, concurrency=4, raw=False):
    with ThreadPoolExecutor(max_workers=concurrency) as executor:
        elapsed = list(executor.map(lambda _: call(method, path, body, token, raw)[1], range(count)))
    ordered = sorted(elapsed)
    report['http'][label] = {'requests': count, 'concurrency': concurrency, 'median_ms': round(statistics.median(elapsed), 2), 'p95_ms': round(ordered[max(0, int(len(ordered) * .95) - 1)], 2), 'max_ms': round(max(elapsed), 2), 'errors': 0}


measure('dashboard', 'GET', '/dashboard', token=u)
measure('content_list', 'GET', '/videos')
measure('company_compliance', 'GET', f'/professional/companies/{cid}/compliance', token=u)
measure('admin_pagination', 'GET', '/admin/users?page=1&page_size=20', token=a)
measure('calculator_npv', 'POST', '/professional/calculators/npv/calculate', {'inputs': {'discount_rate': '.1', 'cashflows': ['-1000', '600', '600']}}, u, count=10, concurrency=2)
measure('profile_writes', 'PATCH', '/users/me', {'name': 'QA measurement reader'}, u, count=12, concurrency=2)
call('PATCH', '/users/me', {'name': 'Development Reader'}, u)
pub = call('GET', '/publications', token=u)[0]['items'][0]
chapter = call('GET', f"/publications/{pub['id']}/chapters", token=u)[0]['items'][0]
measure('private_learning_pdf', 'GET', f"/professional/media/{chapter['asset_id']}/download", token=u, count=10, concurrency=2, raw=True)
conversation = call('POST', '/ai/conversations', {}, u)[0]['id']
payload = {'conversation_id': conversation, 'request_id': 'measure_' + uuid.uuid4().hex, 'question': 'Calculate VAT using the selected explicit facts', 'application_tool': {'name': 'calculate_vat', 'request_id': 'measure_tool_' + uuid.uuid4().hex, 'arguments': {'inputs': {'period_start': '2026-01-01', 'period_end': '2026-12-31', 'amount': '1000', 'inclusive': False, 'treatment': 'standard'}}}}
req = Request(base + '/ai/chat/stream', data=json.dumps(payload).encode(), headers={'Content-Type': 'application/json', 'Authorization': 'Bearer ' + u}, method='POST')
start = time.perf_counter()
first_event = first_answer = None
with urlopen(req, timeout=30) as response:
    while True:
        line = response.readline()
        if not line:
            break
        if line.startswith(b'event:') and first_event is None:
            first_event = (time.perf_counter() - start) * 1000
        if b'event: answer_delta' in line and first_answer is None:
            first_answer = (time.perf_counter() - start) * 1000
report['typed_chat_stream'] = {'first_event_ms': round(first_event, 2), 'first_validated_answer_ms': round(first_answer, 2), 'total_ms': round((time.perf_counter() - start) * 1000, 2), 'live_openai': False, 'meaning': 'Deterministic typed tool, not generative model latency'}
with Session(engine()) as db:
    user = db.scalar(select(m.User).where(m.User.email == credentials['reader']['email']))
    config = current_config(db)[1]
    request = ChatInput(conversation_id=conversation, request_id='retrieval_measurement', question='trial balance review workflow', include_demo=True)
    elapsed = []
    count = 0
    for _ in range(5):
        start = time.perf_counter()
        evidence = asyncio.run(retrieve(db, request, user, config, QAFixtureEmbeddings()))
        elapsed.append((time.perf_counter() - start) * 1000)
        count = len(evidence)
    report['retrieval'] = {'runs': 5, 'median_ms': round(statistics.median(elapsed), 2), 'evidence_count': count, 'method': 'Real PostgreSQL FTS plus explicitly synthetic QA exact vectors; no native pgvector/OpenAI measurement'}
    queries = {
        'scheduler': "SELECT id FROM notification_jobs WHERE status IN ('planned','retry') AND due_at <= now() ORDER BY due_at LIMIT 1",
        'conversation_history': "SELECT id FROM chat_conversations WHERE owner_id=:owner AND deleted_at IS NULL ORDER BY updated_at DESC LIMIT 20",
        'company_expiries': 'SELECT id FROM company_documents WHERE company_id=:company ORDER BY expires_on LIMIT 20',
        'admin_pagination': 'SELECT id FROM users ORDER BY created_at DESC,id LIMIT 20',
        'full_text': "SELECT id FROM knowledge_chunks WHERE to_tsvector('english',text) @@ websearch_to_tsquery('english','trial balance') LIMIT 8",
    }
    for name, query in queries.items():
        try:
            plan = db.execute(text('EXPLAIN (ANALYZE, BUFFERS, FORMAT JSON) ' + query), {'owner': user.id, 'company': cid}).scalar()
            report['query_plans'][name] = plan
        except Exception as exc:
            db.rollback()
            report['query_plans'][name] = {'not_measured': type(exc).__name__}
for name in ['dsbca_user', 'dsbca_admin']:
    folder = root / 'apps' / name / 'build/web'
    js = (folder / 'main.dart.js').read_bytes()
    report['assets'][name] = {'main_js_bytes': len(js), 'gzip_bytes': len(gzip.compress(js)), 'total_build_bytes': sum(p.stat().st_size for p in folder.rglob('*') if p.is_file())}
(root / 'docs/phase4/performance.json').write_text(json.dumps(report, indent=2, default=str), encoding='utf-8')
print(json.dumps({k: v for k, v in report.items() if k != 'query_plans'}, indent=2))
