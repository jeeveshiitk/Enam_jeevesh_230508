"""Exercise demo tickers outside the portfolio without hard-wiring the engine."""
import asyncio
import json
import logging
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from dotenv import load_dotenv
load_dotenv()
from app.research import research
logging.getLogger('pypdf').setLevel(logging.ERROR)

async def main():
    for symbol in ['PERSISTENT', 'KPITTECH', 'HAVELLS', 'ASIANPAINT']:
        try:
            r = await research(symbol, 'promises', lambda m: print(symbol + ': ' + m, flush=True))
            Path('tmp').mkdir(exist_ok=True)
            Path(f'tmp/research-{symbol}.json').write_text(json.dumps(r, indent=2), encoding='utf-8')
            print(json.dumps({'ticker':symbol,'mode':r['mode'],'cards':len(r['cards']),'comparisons':len(r['comparisons']),'sources':len(r['sources']),'gaps':r['gaps']}), flush=True)
        except Exception as exc:
            print(symbol + ': ' + type(exc).__name__, flush=True)

asyncio.run(main())
