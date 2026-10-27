import asyncio
import json
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from app.providers import company_page, document_links, directory_filings, prices, refresh_feed

async def main():
    if '--snapshot' in sys.argv:
        feed = await refresh_feed()
        Path('data/snapshot.json').write_text(json.dumps(feed, indent=2), encoding='utf-8')
        print(json.dumps({'prices': len(feed['prices']), 'filings': len(feed['filings']), 'failures': feed['failures'], 'coverage': feed['coverage']}))
    else:
        html = await company_page('INFY')
        print(json.dumps(document_links(html), indent=2))
        print(json.dumps(directory_filings('INFY', html)[:2]))
        print(json.dumps(await prices('INFY')))

asyncio.run(main())
