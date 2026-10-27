import pytest
from app.domain import alerts, change, classify, price_summary, ticker


def test_volume_baseline_excludes_current_session():
    rows = [{'date': f'2026-10-{i:02}', 'close': 100, 'volume': 100} for i in range(1, 22)]
    rows[-1].update(close=105, volume=300)
    summary = price_summary('TEST', rows)
    assert summary['volume_ratio'] == 3
    assert summary['baseline_sessions'] == 20
    assert summary['change'] == 5
    assert {a['kind'] for a in alerts([summary], [], 3, 2)} == {'price', 'volume'}
    assert alerts([summary], [], 6, 4) == []


def test_sparse_volume_does_not_trigger():
    rows = [{'date': '2026-10-01', 'close': 100, 'volume': 1}, {'date': '2026-10-02', 'close': 100, 'volume': 100}]
    assert alerts([price_summary('TEST', rows)], []) == []


def test_zero_denominator_and_negative_base():
    assert change(100, 0) is None
    assert change(-50, -100) == 50


@pytest.mark.parametrize('raw,expected', [(' infy.ns ', 'INFY'), ('M&M', 'M&M'), ('BAJAJ-AUTO','BAJAJ-AUTO')])
def test_ticker_normalization(raw, expected):
    assert ticker(raw) == expected


@pytest.mark.parametrize('raw', ['../secret', 'https://evil.test', '<script>', '', 'A B'])
def test_invalid_tickers(raw):
    with pytest.raises(ValueError):
        ticker(raw)


def test_notice_is_not_actual_results():
    assert classify('Board meeting intimation to consider financial results')[1] == 30
    assert classify('Audited financial results')[1] == 88
    assert classify('Earnings call transcript discussing financial results')[0] == 'earnings_call'


def test_category_alert_selection():
    filing = dict(id='x', ticker='INFY', title='CFO resigned', date='2026-10-27', category='management_change', priority=90, url='https://example.com')
    assert len(alerts([], [filing], categories=['management_change'])) == 1
    assert alerts([], [filing], categories=[]) == []
