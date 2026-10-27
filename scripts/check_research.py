import asyncio
import json
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from dotenv import load_dotenv
load_dotenv()
from app.research import research

async def main():
    symbol = sys.argv[1] if len(sys.argv) > 1 else 'INFY'
    result = await research(symbol, 'promises', lambda m: print(m, flush=True))
    Path('tmp').mkdir(exist_ok=True)
    Path(f'tmp/research-{symbol}.json').write_text(json.dumps(result, indent=2), encoding='utf-8')
    print(json.dumps({'ticker': result['ticker'], 'mode': result['mode'], 'cards': len(result['cards']), 'comparisons': len(result['comparisons']), 'sources': len(result['sources']), 'gaps': result['gaps']}))

asyncio.run(main())
