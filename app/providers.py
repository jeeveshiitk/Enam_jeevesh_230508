"""Public-source adapters. Screener is a link directory, never research evidence."""
import asyncio
import hashlib
import io
import re
from datetime import datetime, timedelta, timezone
from urllib.parse import quote, urljoin, urlparse

import httpx
from bs4 import BeautifulSoup
from pypdf import PdfReader

from app import store
from app.domain import COMPANIES, IST, classify, now, price_summary

HEADERS = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/131.0 Safari/537.36', 'Accept-Language': 'en-US,en;q=0.9'}
LIMIT = asyncio.Semaphore(4)


async def request(url, **kwargs):
    async with LIMIT:
        async with httpx.AsyncClient(headers=HEADERS, timeout=25, follow_redirects=True) as client:
            response = await client.get(url, **kwargs)
            response.raise_for_status()
            return response


async def prices(symbol):
    cached = store.get('price:' + symbol, 3600)
    if cached:
        return cached
    url = f'https://query1.finance.yahoo.com/v8/finance/chart/{quote(symbol)}.NS'
    response = await request(url, params={'interval': '1d', 'range': '3mo'})
    chart = response.json()['chart']['result'][0]
    values = chart['indicators']['quote'][0]
    current = datetime.now(IST)
    rows = []
    for i, stamp in enumerate(chart.get('timestamp', [])):
        day = datetime.fromtimestamp(stamp, IST).date()
        # Today's bar is intraday until after the exchange close + publication buffer.
        if day == current.date() and (current.hour, current.minute) < (16, 0):
            continue
        rows.append({'date': day.isoformat(), 'close': values['close'][i], 'volume': values['volume'][i]})
    result = price_summary(symbol, rows)
    store.put('price:' + symbol, result)
    return result


async def company_page(symbol):
    cached = store.get('directory:' + symbol, 21600)
    if cached:
        return cached
    for suffix in ('/consolidated/', '/'):
        url = f'https://www.screener.in/company/{quote(symbol)}{suffix}'
        try:
            response = await request(url)
            if 'Annual reports' in response.text:
                store.put('directory:' + symbol, response.text)
                return response.text
        except httpx.HTTPStatusError as exc:
            if exc.response.status_code != 404:
                raise
    raise ValueError('No company documents found for this NSE symbol.')


def document_links(html):
    soup = BeautifulSoup(html, 'html.parser')
    docs = []
    for heading in soup.find_all(['h2', 'h3']):
        label = heading.get_text(' ', strip=True).lower()
        kind = 'annual_report' if 'annual report' in label else 'transcript' if 'concall' in label else None
        if not kind:
            continue
        container = heading.find_parent(class_='documents') or heading.parent
        for a in container.find_all('a', href=True):
            title = a.get_text(' ', strip=True)
            if kind == 'transcript' and 'transcript' not in title.lower():
                continue
            href = urljoin('https://www.screener.in', a['href'])
            if urlparse(href).scheme != 'https':
                continue
            row = a.find_parent('li') or a.parent
            period = row.get_text(' ', strip=True)
            period = re.sub(r'\s*(AI Summary|Transcript|PPT|REC)\s*', ' ', period).strip()
            period = ('Earnings call ' if kind == 'transcript' else '') + period
            docs.append({'kind': kind, 'title': period[:140], 'url': href})
    # Keep directory ordering (newest first), preserving unique source links.
    seen = set()
    result = []
    counts = {'annual_report': 0, 'transcript': 0}
    for d in docs:
        maximum = 1 if d['kind'] == 'annual_report' else 4
        if d['url'] not in seen and counts[d['kind']] < maximum:
            seen.add(d['url'])
            counts[d['kind']] += 1
            result.append(d)
    return result


def parse_exchange_date(value):
    for fmt in ('%d-%b-%Y %H:%M:%S', '%d-%m-%Y %H:%M:%S', '%Y-%m-%d %H:%M:%S'):
        try:
            return datetime.strptime(value, fmt).replace(tzinfo=IST).isoformat()
        except (ValueError, TypeError):
            pass
    return None


async def nse_filings():
    async with httpx.AsyncClient(headers={**HEADERS, 'Referer': 'https://www.nseindia.com/'}, timeout=20, follow_redirects=True) as client:
        await client.get('https://www.nseindia.com/')
        end = datetime.now(IST)
        response = await client.get('https://www.nseindia.com/api/corporate-announcements', params={'index': 'equities', 'from_date': (end - timedelta(days=30)).strftime('%d-%m-%Y'), 'to_date': end.strftime('%d-%m-%Y')})
        response.raise_for_status()
        rows = response.json()
    symbols = {c['ticker'] for c in COMPANIES}
    result = []
    for row in rows:
        if row.get('symbol') not in symbols:
            continue
        title = (row.get('desc', '') + ' — ' + row.get('attchmntText', '')).strip(' —')
        date = parse_exchange_date(row.get('an_dt', ''))
        url = row.get('attchmntFile', '')
        if not date or not url.startswith('https://'):
            continue
        category, priority = classify(title)
        result.append(dict(id=hashlib.sha256(url.encode()).hexdigest()[:16], ticker=row['symbol'], title=title, date=date, url=url, category=category, priority=priority, provider='NSE'))
    return result


def directory_filings(symbol, html):
    """Fallback only: indexed BSE documents, explicitly not complete exchange coverage."""
    soup = BeautifulSoup(html, 'html.parser')
    section = soup.select_one('#documents')
    if not section:
        return []
    result = []
    for a in section.find_all('a', href=True):
        href = a['href']
        if 'bseindia.com' not in urlparse(href).netloc:
            continue
        parent = a.find_parent('li') or a.parent
        text = parent.get_text(' ', strip=True)
        title = a.get_text(' ', strip=True)
        match = re.search(r'(\d{1,2})\s+([A-Za-z]{3})\s+(\d{4})', text)
        date = None
        if match:
            try:
                date = datetime.strptime(match.group(0), '%d %b %Y').replace(tzinfo=IST).isoformat()
            except ValueError:
                pass
        # Index may use short day-month dates. Mark inferred year in provider metadata.
        if not date:
            short = re.search(r'\b(\d{1,2})\s+([A-Za-z]{3})\b', text)
            if short:
                try:
                    current = datetime.now(IST)
                    parsed = datetime.strptime(short.group(0) + ' ' + str(current.year), '%d %b %Y').replace(tzinfo=IST)
                    if parsed > current + timedelta(days=1):
                        parsed = parsed.replace(year=current.year - 1)
                    date = parsed.isoformat()
                except ValueError:
                    pass
        if not date or not title or title in ('Transcript', 'Report', 'PPT'):
            continue
        category, priority = classify(title)
        result.append(dict(id=hashlib.sha256(href.encode()).hexdigest()[:16], ticker=symbol, title=title, date=date, url=href, category=category, priority=priority, provider='BSE via Screener (date only)'))
    return result


async def refresh_feed(progress=None):
    old = store.get('feed') or {}
    old_prices = {p['ticker']: p for p in old.get('prices', [])}
    failures, price_rows, fallback = [], [], []
    async def one(company):
        symbol = company['ticker']
        try:
            price_rows.append(await prices(symbol))
        except Exception as exc:
            failures.append({'ticker': symbol, 'source': 'Yahoo EOD', 'reason': type(exc).__name__})
            if symbol in old_prices:
                price_rows.append(old_prices[symbol])
        try:
            fallback.extend(directory_filings(symbol, await company_page(symbol)))
        except Exception as exc:
            failures.append({'ticker': symbol, 'source': 'Document index', 'reason': type(exc).__name__})
    tasks = [one(c) for c in COMPANIES]
    exchange = asyncio.create_task(nse_filings())
    await asyncio.gather(*tasks)
    complete = False
    try:
        filings = await exchange
        complete = True
    except Exception as exc:
        failures.append({'ticker': 'ALL', 'source': 'NSE announcements', 'reason': type(exc).__name__})
        filings = fallback
    # Merge retained history without relabelling its provider or dates.
    unique = {f['id']: f for f in old.get('filings', [])}
    unique.update({f['id']: f for f in filings})
    cutoff = datetime.now(timezone.utc) - timedelta(days=31)
    symbols = {c['ticker'] for c in COMPANIES}
    result = dict(updated_at=now(), prices=price_rows, filings=sorted([f for f in unique.values() if datetime.fromisoformat(f['date']) >= cutoff and f['ticker'] in symbols], key=lambda f: (f['priority'], f['date']), reverse=True), failures=failures, exchange_complete=complete, mode='live', coverage='NSE exchange feed' if complete else 'Partial: recent BSE filings indexed by Screener; exchange feed unavailable')
    store.put('feed', result)
    return result


async def read_document(doc):
    key = 'document:' + hashlib.sha256(doc['url'].encode()).hexdigest()
    cached = store.get(key, 7 * 86400)
    if cached:
        return cached
    # URLs originate in the selected company directory, not user input.
    async with LIMIT:
        async with httpx.AsyncClient(headers=HEADERS, timeout=45, follow_redirects=True) as client:
            async with client.stream('GET', doc['url']) as response:
                response.raise_for_status()
                chunks, size = [], 0
                async for part in response.aiter_bytes():
                    size += len(part)
                    if size > 30_000_000:
                        raise ValueError('Document exceeds 30 MB extraction limit')
                    chunks.append(part)
                raw = b''.join(chunks)
                final_url = str(response.url)
    if not raw.lstrip().startswith(b'%PDF'):
        raise ValueError('Source is not a readable PDF')
    def extract():
        reader = PdfReader(io.BytesIO(raw))
        return [{'page': i + 1, 'text': re.sub(r'\s+', ' ', p.extract_text() or '').strip()} for i, p in enumerate(reader.pages[:500])]
    pages = await asyncio.to_thread(extract)
    pages = [p for p in pages if len(p['text']) > 80]
    if not pages:
        raise ValueError('Scanned PDF needs OCR; no extractable text')
    result = {**doc, 'url': final_url, 'pages': pages, 'fetched_at': now()}
    store.put(key, result)
    return result
