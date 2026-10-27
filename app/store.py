"""Small durable cache. Provider failures never replace last successful data."""
import json
import sqlite3
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / 'data'
DATA.mkdir(exist_ok=True)
DB = DATA / 'finn.sqlite'


def connect():
    con = sqlite3.connect(DB, timeout=20)
    con.execute('CREATE TABLE IF NOT EXISTS cache (key TEXT PRIMARY KEY, value TEXT NOT NULL, saved REAL NOT NULL)')
    return con


def put(key, value):
    with connect() as con:
        con.execute('INSERT OR REPLACE INTO cache VALUES (?,?,?)', (key, json.dumps(value), time.time()))


def get(key, max_age=None):
    with connect() as con:
        row = con.execute('SELECT value,saved FROM cache WHERE key=?', (key,)).fetchone()
    if not row or (max_age is not None and time.time() - row[1] > max_age):
        return None
    return json.loads(row[0])


def bootstrap():
    seed = DATA / 'snapshot.json'
    if seed.exists() and get('feed') is None:
        put('feed', json.loads(seed.read_text(encoding='utf-8')))
