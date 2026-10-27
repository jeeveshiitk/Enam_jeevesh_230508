import asyncio
import os
import time
import uuid
from contextlib import asynccontextmanager, suppress
from datetime import datetime, timedelta, timezone
from typing import Literal

from dotenv import load_dotenv
load_dotenv()
from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field
from app import store
from app.domain import CATEGORIES, COMPANIES, alerts, ticker
from app.providers import refresh_feed
from app.research import research

JOBS = {}
TASKS = set()
REFRESH_LOCK = asyncio.Lock()
RESEARCH_SLOTS = asyncio.Semaphore(2)


def launch(coro):
    task = asyncio.create_task(coro)
    TASKS.add(task)
    task.add_done_callback(TASKS.discard)


async def refresh():
    if REFRESH_LOCK.locked():
        return
    async with REFRESH_LOCK:
        await refresh_feed()


async def periodic():
    minutes = int(os.getenv('REFRESH_MINUTES', '15'))
    if minutes <= 0:
        return
    while True:
        try:
            await refresh()
        except Exception:
            pass  # Preserve cache; source errors are exposed by feed status.
        await asyncio.sleep(max(minutes, 5) * 60)


@asynccontextmanager
async def lifespan(app):
    store.bootstrap()
    worker = asyncio.create_task(periodic())
    yield
    worker.cancel()
    with suppress(asyncio.CancelledError):
        await worker
    for task in TASKS:
        task.cancel()


app = FastAPI(title='FINN', lifespan=lifespan)


@app.middleware('http')
async def security_headers(request, call_next):
    response = await call_next(request)
    response.headers['X-Content-Type-Options'] = 'nosniff'
    response.headers['Referrer-Policy'] = 'strict-origin-when-cross-origin'
    response.headers['Content-Security-Policy'] = "default-src 'self'; script-src 'self'; style-src 'self'; img-src 'self' data:; connect-src 'self'; frame-ancestors 'none'; base-uri 'self'; form-action 'self'"
    return response


@app.get('/api/health')
def health():
    return {'ok': True, 'ai_configured': bool(os.getenv('GEMINI_API_KEY')), 'refreshing': REFRESH_LOCK.locked()}


@app.get('/api/portfolio')
def portfolio():
    return {'companies': COMPANIES, 'categories': CATEGORIES, 'research_examples': ['ASIANPAINT', 'PERSISTENT', 'KPITTECH', 'HAVELLS']}


@app.get('/api/feed')
def feed(hours: int = Query(24, ge=1, le=720), price: float = Query(3, ge=0.1, le=50), volume: float = Query(2, ge=1, le=20), categories: str = 'results,M&A,management_change,litigation'):
    data = store.get('feed') or dict(prices=[], filings=[], updated_at=None, failures=[], mode='empty', coverage='Waiting for first refresh', exchange_complete=False)
    cutoff = datetime.now(timezone.utc) - timedelta(hours=hours)
    filings = [f for f in data['filings'] if datetime.fromisoformat(f['date']) >= cutoff]
    # EOD alerts are also constrained by the selected calendar window.
    recent_prices = [p for p in data['prices'] if datetime.fromisoformat(p['date'] + 'T16:00:00+05:30') >= cutoff]
    return {**data, 'filings': filings, 'total_in_window': len(filings), 'alerts': alerts(recent_prices, filings, price, volume, categories.split(',')), 'refreshing': REFRESH_LOCK.locked()}


@app.post('/api/refresh', status_code=202)
async def refresh_api():
    data = store.get('feed') or {}
    recent = data.get('updated_at')
    if recent and (datetime.now(timezone.utc) - datetime.fromisoformat(recent)).total_seconds() < 60:
        return {'status': 'recent', 'message': 'Data was checked less than a minute ago.'}
    launch(refresh())
    return {'status': 'refreshing'}


class ResearchRequest(BaseModel):
    ticker: str = Field(min_length=1, max_length=35)
    topic: Literal['overview', 'promises', 'cash'] = 'promises'


async def run_research(job_id, symbol, topic):
    job = JOBS[job_id]
    try:
        async with RESEARCH_SLOTS:
            result = await research(symbol, topic, lambda message: job.update(message=message))
        job.update(status='complete', result=result)
    except Exception as exc:
        job.update(status='error', message=str(exc) if isinstance(exc, ValueError) else 'A source could not be reached. Please retry or choose another ticker.')


@app.post('/api/research', status_code=202)
async def create_research(body: ResearchRequest):
    try:
        symbol = ticker(body.ticker)
    except ValueError as exc:
        raise HTTPException(422, str(exc))
    for jid, job in list(JOBS.items()):
        if time.time() - job['started'] > 3600:
            del JOBS[jid]
        elif job['ticker'] == symbol and job['topic'] == body.topic and job['status'] == 'running':
            return {'job_id': jid}
    if sum(j['status'] == 'running' for j in JOBS.values()) >= 4:
        raise HTTPException(429, 'Research queue is full. Please try again shortly.')
    jid = uuid.uuid4().hex
    JOBS[jid] = dict(status='running', message='Queued for source discovery', started=time.time(), ticker=symbol, topic=body.topic)
    launch(run_research(jid, symbol, body.topic))
    return {'job_id': jid}


@app.get('/api/research/{job_id}')
def research_job(job_id: str):
    if job_id not in JOBS:
        raise HTTPException(404, 'Research session expired. Start a new search.')
    return JOBS[job_id]


@app.get('/')
def index():
    return FileResponse(store.ROOT / 'static' / 'index.html')


app.mount('/static', StaticFiles(directory=store.ROOT / 'static'), name='static')
