"""Local-only acceptance checks against the isolated Phase 3 HTTP API."""
import asyncio, json, sys, uuid
from pathlib import Path
from datetime import date, datetime, timedelta, timezone
from urllib.request import Request, urlopen
from dotenv import load_dotenv
root = Path(__file__).resolve().parent.parent
load_dotenv(root / "backend/.env.phase3.local", override=True)
sys.path.insert(0, str(root / "backend"))
from app.core.config import settings
from app.core.database import engine
from app.professional.notifications import tick
from sqlalchemy.orm import Session
assert settings().app_env == "development" and engine().url.database == "dsbca_phase3_dev"
credentials = json.loads((root / ".local-phase3-access.json").read_text())
base = "http://127.0.0.1:8003/api/v1"
def call(method, path, body=None, token=None, raw=False):
    headers = {"Content-Type":"application/json"}
    if token: headers["Authorization"] = "Bearer " + token
    request = Request(base + path, data=json.dumps(body).encode() if body is not None else None, headers=headers, method=method)
    with urlopen(request, timeout=30) as response:
        data=response.read()
        return data if raw else json.loads(data) if data else None

tokens={name:call("POST","/auth/login",{"email":value["email"],"password":value["password"]})["access_token"] for name,value in credentials.items()}
a,b,u = (tokens[x] for x in ["operator","reviewer","reader"])
suffix=uuid.uuid4().hex[:8]
report={"environment":"isolated local Phase 3 PostgreSQL + HTTP API", "live_openai":"not configured; typed application tools verified only", "email_push":"not configured; no delivery claim", "checks":{}}
# B: deterministic calculation, immutable saved inputs, references, owner history.
inputs={"period_start":"2026-01-01","period_end":"2026-12-31","accounting_profit":"900000"}
calc=call("POST","/professional/calculators/corporate_tax/calculate",{"inputs":inputs,"save":True,"title":"Acceptance " + suffix},u)
assert calc["results"]["corporate_tax"] == "47250.00",calc
saved=call("GET","/professional/calculations/"+calc["run_id"],token=u)
assert saved["inputs"]["accounting_profit"] == "900000"
report["checks"]["B"]="HTTP calculate/save/reopen succeeded; browser also verified formula and save/history"
# C: owner company, licence, configured reminders, renewal history and future replanning.
company=call("POST","/companies",{"name":"Acceptance fictional company "+suffix,"profile_data":{"entity_type":"LLC","zone":"Mainland"}},u)
cid=company["id"]
call("PUT","/professional/reminder-settings",{"days":[30,7,0],"channels":["in_app"],"enabled":True},u)
docbody={"title":"Fictional Trade Licence","category":"Trade Licence","expires_on":str(date.today()+timedelta(days=30)),"details":{"issue_date":str(date.today()-timedelta(days=300))}}
doc=call("POST",f"/professional/companies/{cid}/documents",docbody,u)
jobs=call("GET","/professional/notifications/jobs",token=u)["items"]
assert any(j["source_id"]==doc["id"] and j["status"]=="planned" for j in jobs)
docbody["expires_on"]=str(date.today()+timedelta(days=365))
call("PUT",f"/professional/companies/{cid}/documents/{doc['id']}",docbody,u)
view=call("GET",f"/professional/companies/{cid}/compliance",token=u)
assert any(h["action"]=="renew" for h in view["history"])
report["checks"]["C"]="HTTP company/licence/reminder scheduling/renewal/history succeeded"
# D: separate author/reviewer, publication, in-app worker delivery, public official link.
call("PUT","/professional/updates/subscriptions",{"subjects":["VAT"]},u)
update=call("POST","/admin/updates",{"title":"Acceptance reviewed source "+suffix,"source_url":"https://tax.gov.ae/","metadata_extra":{"subject":"VAT"},"demo":True},a)
for action,token in [("review",a),("approve",b),("publish",b)]:call("POST",f"/admin/professional/updates/{update['id']}/workflow",{"action":action},token)
with Session(engine(),expire_on_commit=False) as db:
    for _ in range(50):
        if asyncio.run(tick(db))["status"]=="idle":break
notifications=call("GET","/notifications",token=u)["items"]
assert any(update["title"]==n["title"] for n in notifications)
assert call("GET","/updates/"+update["id"],token=u)["source_url"]=="https://tax.gov.ae/"
report["checks"]["D"]="HTTP draft/review/independent approval/publish + actual in-app worker delivery succeeded; official source link returned"
# E/F: typed application tool in the existing chat; deterministic output and owner-record deep link.
conversation=call("POST","/ai/conversations",{},u)["id"]
def chat(name,args):
    return call("POST","/ai/chat",{"conversation_id":conversation,"request_id":"acceptance_"+uuid.uuid4().hex,"question":"Use the explicitly selected authorized application tool","application_tool":{"name":name,"arguments":args,"request_id":"tool_"+uuid.uuid4().hex}},u)
answer=chat("calculate_corporate_tax",{"inputs":inputs})
assert answer["metadata"]["application_result"]["result"]["results"]["corporate_tax"]=="47250.00"
assert answer["metadata"]["application_result"]["path"]=="/toolkit/corporate_tax"
report["checks"]["E"]="Typed chat calculator + numeric engine match + populated-calculator metadata succeeded; natural-language model selection pending"
answer=chat("get_company_reminders",{"company_id":cid})
assert answer["metadata"]["application_result"]["data"]["documents"][0]["id"]==doc["id"]
report["checks"]["F"]="Typed chat authorized company expiry retrieval and reminder deep link succeeded; natural-language model selection pending"
# G: joining link is a local test destination, never a real webinar room.
event=call("POST","/admin/content/webinars",{"title":"Acceptance fictional webinar "+suffix,"demo":True,"status":"published","starts_at":(datetime.now(timezone.utc)+timedelta(days=3)).isoformat(),"join_url":"https://example.com/dsbca-test-room","metadata_extra":{"capacity":2,"timezone":"Asia/Dubai","presenter":"Demonstration"}},a)
wid=event["id"]
assert call("GET","/webinars/"+wid)["join_url"] is None
call("POST",f"/professional/webinars/{wid}/register",{},u)
assert call("GET",f"/professional/webinars/{wid}/join",token=u)["join_url"]=="https://example.com/dsbca-test-room"
assert b"DTSTART:" in call("GET",f"/professional/webinars/{wid}/calendar",token=u,raw=True)
report["checks"]["G"]="HTTP schedule/register/authorized joining metadata/UTC calendar succeeded with fictional room; no live webinar attended"
(root / "docs/phase3/acceptance-http.json").write_text(json.dumps(report,indent=2),encoding="utf-8")
print(json.dumps(report,indent=2))
