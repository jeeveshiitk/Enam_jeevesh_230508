import re
from datetime import datetime, timezone, timedelta

IST = timezone(timedelta(hours=5, minutes=30))
PORTFOLIO = [
    ('RELIANCE', 'Reliance Industries', 'Energy & retail', 'Large'),
    ('TCS', 'Tata Consultancy Services', 'IT services', 'Large'),
    ('HDFCBANK', 'HDFC Bank', 'Banking', 'Large'),
    ('INFY', 'Infosys', 'IT services', 'Large'),
    ('BHARTIARTL', 'Bharti Airtel', 'Telecom', 'Large'),
    ('ITC', 'ITC', 'Consumer staples', 'Large'),
    ('LT', 'Larsen & Toubro', 'Infrastructure', 'Large'),
    ('SUNPHARMA', 'Sun Pharmaceutical', 'Healthcare', 'Large'),
    ('MARUTI', 'Maruti Suzuki', 'Automobiles', 'Large'),
    ('TITAN', 'Titan Company', 'Consumer discretionary', 'Large'),
    ('TRENT', 'Trent', 'Retail', 'Large'),
    ('POLYCAB', 'Polycab India', 'Electrical equipment', 'Mid'),
    ('DIXON', 'Dixon Technologies', 'Electronics', 'Mid'),
    ('APLAPOLLO', 'APL Apollo Tubes', 'Building materials', 'Mid'),
    ('CDSL', 'Central Depository Services', 'Market infrastructure', 'Mid'),
    ('CAMS', 'Computer Age Management Services', 'Financial services', 'Mid'),
    ('ELECON', 'Elecon Engineering', 'Industrial machinery', 'Small'),
    ('GARFIBRES', 'Garware Technical Fibres', 'Technical textiles', 'Small'),
]
COMPANIES = [dict(zip(('ticker', 'name', 'sector', 'size'), row)) for row in PORTFOLIO]

# More specific event types precede generic financial-results references.
RULES = [
    ('management_change', 90, r'resign|appoint.*(?:director|chief|ceo|cfo|managing)|cessation|change.*management'),
    ('M&A', 95, r'acquisition|merger|demerger|joint venture|sale of.*stake|scheme of arrangement'),
    ('litigation', 92, r'litigation|penalt|regulatory order|insolvency|fine imposed|show cause'),
    ('fund_raise', 85, r'fund.?rais|qip|rights issue|preferential|buy.?back|commercial paper'),
    ('pledging', 82, r'pledge|encumbrance'),
    ('capex', 84, r'capex|capacity expansion|new plant'),
    ('earnings_call', 65, r'concall|conference call|earnings call|transcript'),
    ('investor_meetings', 20, r'investor meet|analyst meet|institutional investor'),
    ('results', 88, r'financial result|quarterly result|annual result|audited result'),
    ('credit_rating', 65, r'credit rating|rating.*(?:reaffirm|upgrade|downgrade)'),
    ('dividend', 60, r'dividend'),
    ('bonus_split', 70, r'bonus issue|stock split|sub.?division'),
    ('insider_trading', 55, r'insider|trading.*(?:promoter|designated)|disclosure.*(?:29\(|7\(2)'),
    ('postal_ballot', 15, r'postal ballot'),
    ('agm_egm', 15, r'annual general meeting|extraordinary general|agm|egm'),
    ('press_release', 55, r'press release|order win|partnership|product launch'),
]
CATEGORIES = [x[0] for x in RULES] + ['unclassified']


def classify(title):
    for category, priority, pattern in RULES:
        if re.search(pattern, title, re.I):
            # A board-meeting notice is not delivered results.
            if category == 'results' and re.search(r'board meeting|intimation|notice', title, re.I):
                return category, 30
            return category, priority
    return 'unclassified', 10


def ticker(value):
    value = value.strip().upper().removesuffix('.NS')
    if not re.fullmatch(r'[A-Z0-9][A-Z0-9&-]{0,29}', value):
        raise ValueError('Enter an NSE symbol, for example INFY or M&M.')
    return value


def now():
    return datetime.now(timezone.utc).isoformat()


def change(current, previous):
    return None if previous in (None, 0) or current is None else round((current - previous) / abs(previous) * 100, 2)


def price_summary(symbol, rows):
    rows = sorted((r for r in rows if r.get('close') is not None), key=lambda r: r['date'])
    if len(rows) < 2:
        raise ValueError('Not enough trading sessions')
    latest, previous = rows[-1], rows[-2]
    volumes = [r['volume'] for r in rows[-21:-1] if r.get('volume') is not None]
    average = sum(volumes) / len(volumes) if volumes else 0
    return dict(ticker=symbol, close=round(latest['close'], 2), date=latest['date'],
                change=change(latest['close'], previous['close']), volume=latest.get('volume'),
                volume_ratio=round(latest['volume'] / average, 2) if average and latest.get('volume') is not None else None,
                baseline_sessions=len(volumes), history=[r['close'] for r in rows[-30:]],
                source=f'https://finance.yahoo.com/quote/{symbol}.NS/history/')


def alerts(prices, filings, price_threshold=3, volume_threshold=2, categories=None):
    result = []
    for p in prices:
        if p.get('change') is not None and abs(p['change']) >= price_threshold:
            result.append(dict(id=f"price:{p['ticker']}:{p['date']}", ticker=p['ticker'], kind='price', title=f"{p['change']:+.2f}% at close", date=p['date'], source=p['source']))
        if p.get('volume_ratio') is not None and p['baseline_sessions'] >= 10 and p['volume_ratio'] >= volume_threshold:
            result.append(dict(id=f"volume:{p['ticker']}:{p['date']}", ticker=p['ticker'], kind='volume', title=f"{p['volume_ratio']:.1f}× usual volume", date=p['date'], source=p['source']))
    for f in filings:
        if f['category'] in (categories or []) and f['priority'] >= 50:
            result.append(dict(id=f['id'], ticker=f['ticker'], kind='filing', title=f['title'], date=f['date'], source=f['url']))
    return result
