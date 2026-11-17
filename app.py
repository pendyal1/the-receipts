"""Cloud Run entrypoint. The /chat interface supports evidence-backed investigations."""
import json
import os
import threading
import time
import uuid
from concurrent.futures import ThreadPoolExecutor, as_completed
from contextlib import contextmanager
from dataclasses import dataclass, field
from pathlib import Path

from fastapi import FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import FileResponse, JSONResponse, Response
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, ConfigDict, Field, field_validator

from receipts.config import INDUSTRIES, COMPANIES, MODEL
from receipts.model import Gemini
from receipts.research import Investigator, Ledger, Scope
from receipts.sources import Sources, bundled_company_directory
from receipts.logos import Logos, LogoBusy

ROOT = Path(__file__).parent
app = FastAPI(title='The Receipts', version='0.1.0')
app.mount('/static', StaticFiles(directory=ROOT / 'static'), name='static')
sources = Sources(offline=os.getenv('OFFLINE_DATA') == '1')
logos = Logos(sources)
model = Gemini()
investigator = Investigator(sources, model)
capacity = threading.BoundedSemaphore(2)
SESSION_PATTERN = r'^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$'


@dataclass
class Session:
    scope: dict | None = None
    question: str | None = None
    touched: float = field(default_factory=time.monotonic)
    lock: threading.RLock = field(default_factory=threading.RLock)
    active: int = 0


class Sessions:
    def __init__(self):
        self.records, self.lock = {}, threading.RLock()

    @contextmanager
    def conversation(self, requested=None):
        with self.lock:
            for sid, record in list(self.records.items()):
                if not record.active and time.monotonic() - record.touched > 1800:
                    self.records.pop(sid)
            sid = requested if requested in self.records else str(uuid.uuid4())
            if sid not in self.records:
                if len(self.records) >= 100:
                    idle = [(v.touched, k) for k, v in self.records.items() if not v.active]
                    if not idle:
                        raise HTTPException(503, 'All sessions are active. Retry shortly.')
                    self.records.pop(min(idle)[1])
                self.records[sid] = Session()
            record = self.records[sid]
            record.active += 1
        try:
            with record.lock:
                yield sid, record
        finally:
            with self.lock:
                record.active -= 1
                record.touched = time.monotonic()

    def clear(self, sid):
        with self.lock:
            record = self.records.get(sid)
            if record and record.active:
                raise HTTPException(409, 'Wait for the active investigation to finish before clearing it.')
            self.records.pop(sid, None)


sessions = Sessions()


class ChatRequest(BaseModel):
    model_config = ConfigDict(extra='forbid')
    message: str = Field(min_length=1, max_length=8000)
    session_id: str | None = Field(default=None, pattern=SESSION_PATTERN)
    scope: Scope | None = None

    @field_validator('message')
    @classmethod
    def nonblank(cls, value):
        if not value.strip():
            raise ValueError('Enter a question.')
        return value.strip()


class ToolCall(BaseModel):
    agent: str
    name: str
    args: dict
    result: str
    elapsed_ms: int = 0


class ChatResponse(BaseModel):
    response: str
    session_id: str
    tool_calls: list[ToolCall]
    investigation: dict


class ClearRequest(BaseModel):
    model_config = ConfigDict(extra='forbid')
    session_id: str = Field(pattern=SESSION_PATTERN)


@app.exception_handler(RequestValidationError)
async def invalid_request(request, exc):
    return JSONResponse(status_code=422, content={'error': 'invalid_input',
        'message': 'Check your question, tickers and dates. Use start ≤ as_of ≤ through, from 2012 through today, and at most three companies.'})


@app.exception_handler(Exception)
async def unexpected_error(request, exc):
    return JSONResponse(status_code=500, content={'error': 'request_failed', 'message': 'This request did not finish. Please retry; no result was invented.'})


@app.middleware('http')
async def headers(request, call_next):
    response = await call_next(request)
    response.headers.update({'X-Content-Type-Options': 'nosniff', 'Referrer-Policy': 'no-referrer',
        'Content-Security-Policy': "default-src 'self'; script-src 'self'; style-src 'self'; img-src 'self' data:; connect-src 'self'; frame-ancestors 'none'; base-uri 'none'; form-action 'self'"})
    response.headers.setdefault('Cache-Control', 'no-store')
    return response


@app.get('/')
def index():
    return FileResponse(ROOT / 'static' / 'index.html')


@app.get('/health')
def health():
    return {'status': 'ok', 'model': MODEL, 'snapshot_files': len(list((ROOT / 'data' / 'snapshots').glob('*.json.gz'))),
            'revision': os.getenv('K_REVISION', 'local'), 'commit': os.getenv('APP_COMMIT', 'local')}


@app.get('/catalog')
def catalog():
    return {'industries': INDUSTRIES, 'companies': {t: v[0] for t, v in COMPANIES.items()},
            'limits': {'companies': 3, 'research_rounds': 2, 'researcher_turns': 3,
                       'deadline_seconds': 240, 'sessions': 'In memory; expire after 30 minutes idle or service restart.'}}


@app.get('/company-logo/{ticker}')
def company_logo(ticker: str, request: Request):
    company = bundled_company_directory().get(ticker.upper())
    if not company:
        return Response(status_code=204, headers={'X-Logo-Status': 'unavailable', 'Cache-Control': 'public, max-age=900'})
    asset = logos.local_asset(company)
    if asset:
        return FileResponse(asset, headers={'X-Logo-Status': 'available', 'Cache-Control': 'public, max-age=86400'})
    try:
        logo = logos.get(company)
    except LogoBusy:
        return Response(status_code=503, headers={'Retry-After': '1', 'Cache-Control': 'no-store'})
    if not logo:
        return Response(status_code=204, headers={'X-Logo-Status': 'unavailable', 'Cache-Control': 'public, max-age=900'})
    headers = {'ETag': logo.etag, 'X-Logo-Status': 'available', 'X-Logo-Source': logo.source,
               'Cache-Control': 'public, max-age=86400'}
    if request.headers.get('if-none-match') == logo.etag:
        return Response(status_code=304, headers=headers)
    return Response(logo.body, media_type=logo.media_type, headers=headers)


@app.post('/chat', response_model=ChatResponse)
def chat(request: ChatRequest):
    if not capacity.acquire(blocking=False):
        raise HTTPException(429, 'Two investigations are running. Please retry shortly.')
    try:
        with sessions.conversation(request.session_id) as (sid, session):
            scope = request.scope.model_dump(mode='json') if request.scope else None
            result = investigator.run(request.message, scope, session.scope, session.question)
            if result['investigation'].get('scope'):
                session.scope = result['investigation']['scope']
                session.question = request.message
            return {**result, 'session_id': sid}
    finally:
        capacity.release()


@app.post('/evidence', response_model=ChatResponse)
def evidence_preview(request: ChatRequest):
    if not request.scope:
        raise HTTPException(422, 'Choose companies and all three research dates to open an evidence preview.')
    if not capacity.acquire(blocking=False):
        raise HTTPException(429, 'The research desk is busy. Please retry shortly.')
    try:
        ledger = Ledger()
        scope = request.scope
        tasks = [('Claims', 'claims', scope.tickers[0]), ('Financials', 'financials_then', scope.tickers[0]),
                 ('Context', 'macro', scope.tickers[0])]
        tasks += [('Peers', 'financials_later', t) for t in scope.tickers]
        tasks += [('Context', 'prices', t) for t in scope.tickers]
        with ThreadPoolExecutor(max_workers=4) as pool:
            futures = [pool.submit(investigator.tool, ledger, a, n, t, scope) for a, n, t in tasks]
            for future in as_completed(futures):
                future.result()
        with sessions.conversation(request.session_id) as (sid, session):
            session.scope = scope.model_dump(mode='json')
            session.question = request.message
            return {'response': 'Evidence preview: public-source records only. Run an AI investigation to cross-examine claims and synthesize a cited report.',
                'session_id': sid, 'tool_calls': ledger.traces,
                'investigation': {'status': 'preview', 'scope': scope.model_dump(mode='json'), 'report': None,
                    'rounds': 0, 'evidence': list(ledger.evidence.values()),
                    'limits': ['Preview does not run AI agents or establish whether management delivered.']}}
    finally:
        capacity.release()


@app.post('/clear')
def clear(request: ClearRequest):
    sessions.clear(request.session_id)
    return {'status': 'ok'}


if __name__ == '__main__':
    import uvicorn
    uvicorn.run(app, host='0.0.0.0', port=int(os.getenv('PORT', '8000')))
