"""Single-owner persistent brands, campaigns, and anonymous response records."""
from __future__ import annotations
from contextlib import contextmanager
from datetime import datetime, timezone, timedelta, date
from pathlib import Path
import hashlib
import json
import os
import secrets
import sqlite3
from urllib.parse import urlsplit

KST=timezone(timedelta(hours=9))


def now(): return datetime.now(KST).isoformat(timespec='seconds')


@contextmanager
def database():
    folder=Path(os.getenv('DONGNAE_DATA_DIR',str(Path(__file__).parent/'.data')))
    folder.mkdir(parents=True,exist_ok=True)
    db=sqlite3.connect(folder/'studio.sqlite3',timeout=20)
    db.row_factory=sqlite3.Row
    db.executescript('''
    PRAGMA journal_mode=WAL;
    PRAGMA foreign_keys=ON;
    CREATE TABLE IF NOT EXISTS brands(id TEXT PRIMARY KEY,name TEXT NOT NULL,payload TEXT NOT NULL,updated TEXT NOT NULL);
    CREATE TABLE IF NOT EXISTS campaigns(id TEXT PRIMARY KEY,name TEXT NOT NULL,payload TEXT NOT NULL,created TEXT NOT NULL,active INTEGER NOT NULL DEFAULT 1);
    CREATE TABLE IF NOT EXISTS variants(id TEXT PRIMARY KEY,campaign_id TEXT NOT NULL REFERENCES campaigns(id),label TEXT NOT NULL,token TEXT UNIQUE NOT NULL,code TEXT UNIQUE NOT NULL,payload TEXT NOT NULL);
    CREATE TABLE IF NOT EXISTS events(id INTEGER PRIMARY KEY,variant_id TEXT NOT NULL REFERENCES variants(id),kind TEXT NOT NULL,visitor TEXT NOT NULL,day TEXT NOT NULL,created TEXT NOT NULL,UNIQUE(variant_id,kind,visitor,day));
    CREATE TABLE IF NOT EXISTS redemptions(id INTEGER PRIMARY KEY,variant_id TEXT NOT NULL REFERENCES variants(id),reference_hash TEXT NOT NULL,created TEXT NOT NULL,UNIQUE(variant_id,reference_hash));
    CREATE TABLE IF NOT EXISTS markets(id TEXT PRIMARY KEY,region TEXT NOT NULL,payload TEXT NOT NULL,created TEXT NOT NULL);
    CREATE TABLE IF NOT EXISTS artifacts(id INTEGER PRIMARY KEY,campaign_id TEXT,label TEXT NOT NULL,path TEXT NOT NULL,created TEXT NOT NULL);
    ''')
    try:
        yield db
        db.commit()
    finally: db.close()


def safe_url(value):
    value=value.strip()
    if not value: return ''
    p=urlsplit(value)
    if p.scheme not in ('http','https') or not p.hostname or p.username or p.password or any(c in value for c in '\r\n'):
        raise ValueError('링크는 사용자 정보가 없는 http 또는 https 주소여야 합니다.')
    return value


def save_brand(name,payload,brand_id=None):
    if not name.strip(): raise ValueError('브랜드명을 입력해 주세요.')
    identity=brand_id or secrets.token_hex(8)
    with database() as db:
        db.execute('INSERT INTO brands VALUES(?,?,?,?) ON CONFLICT(id) DO UPDATE SET name=excluded.name,payload=excluded.payload,updated=excluded.updated',
                   (identity,name.strip(),json.dumps(payload,ensure_ascii=False),now()))
    return identity


def list_brands():
    with database() as db:
        return [dict(row)|{'data':json.loads(row['payload'])} for row in db.execute('SELECT * FROM brands ORDER BY updated DESC')]


def create_campaign(name,settings,variants):
    if not name.strip() or not variants: raise ValueError('캠페인명과 광고 문구가 필요합니다.')
    settings=dict(settings)
    settings['booking_url']=safe_url(settings.get('booking_url',''))
    settings['map_url']=safe_url(settings.get('map_url',''))
    expiry=date.fromisoformat(settings['expires'])
    if expiry<datetime.now(KST).date(): raise ValueError('쿠폰 종료일은 오늘 이후로 설정해 주세요.')
    identity=secrets.token_hex(8)
    with database() as db:
        db.execute('INSERT INTO campaigns(id,name,payload,created) VALUES(?,?,?,?)',(identity,name.strip(),json.dumps(settings,ensure_ascii=False),now()))
        for variant in variants:
            if not variant.get('headline','').strip(): raise ValueError('각 광고의 첫 문장을 입력해 주세요.')
            db.execute('INSERT INTO variants VALUES(?,?,?,?,?,?)',(secrets.token_hex(8),identity,variant['label'],secrets.token_urlsafe(24),
                'DN-'+secrets.token_hex(4).upper(),json.dumps(variant,ensure_ascii=False)))
    return identity


def get_campaign(identity):
    with database() as db:
        row=db.execute('SELECT * FROM campaigns WHERE id=?',(identity,)).fetchone()
        if not row: return None
        result=dict(row)|{'settings':json.loads(row['payload'])}
        result['variants']=[dict(v)|{'copy':json.loads(v['payload'])} for v in db.execute('SELECT * FROM variants WHERE campaign_id=? ORDER BY label',(identity,))]
        return result


def list_campaigns():
    with database() as db:
        return [dict(row) for row in db.execute('SELECT id,name,created,active FROM campaigns ORDER BY created DESC')]


def public_variant(token):
    with database() as db:
        row=db.execute('SELECT v.*,c.name,c.payload AS settings,c.active FROM variants v JOIN campaigns c ON c.id=v.campaign_id WHERE v.token=?',(token,)).fetchone()
        if not row: return None
        result=dict(row)
        result['settings']=json.loads(result['settings']); result['copy']=json.loads(result['payload'])
        result['available']=bool(result['active']) and date.fromisoformat(result['settings']['expires'])>=datetime.now(KST).date()
        return result


def record_event(token,kind,visitor):
    if kind not in ('view','booking_click','map_click','coupon_claim'): raise ValueError('지원하지 않는 기록입니다.')
    variant=public_variant(token)
    if not variant or not variant['available']: return False
    day=datetime.now(KST).date().isoformat()
    anonymous=hashlib.sha256((token+str(visitor)+day).encode()).hexdigest()
    with database() as db:
        cursor=db.execute('INSERT OR IGNORE INTO events(variant_id,kind,visitor,day,created) VALUES(?,?,?,?,?)',
                         (variant['id'],kind,anonymous,day,now()))
        return cursor.rowcount==1


def redeem(code,reference):
    if not reference.strip(): raise ValueError('중복 확인용 거래·방문 식별번호를 입력해 주세요. 전화번호나 이름은 넣지 마세요.')
    with database() as db:
        row=db.execute('SELECT token FROM variants WHERE code=?',(code.strip().upper(),)).fetchone()
    variant=public_variant(row['token']) if row else None
    if not variant or not variant['available']: raise ValueError('사용 가능한 쿠폰이 아닙니다. 코드·기간·활성 상태를 확인하세요.')
    ref=hashlib.sha256(reference.strip().encode()).hexdigest()
    with database() as db:
        cursor=db.execute('INSERT OR IGNORE INTO redemptions(variant_id,reference_hash,created) VALUES(?,?,?)',(variant['id'],ref,now()))
        return cursor.rowcount==1


def set_campaign_active(identity,active):
    with database() as db: db.execute('UPDATE campaigns SET active=? WHERE id=?',(int(active),identity))


def campaign_stats(identity):
    campaign=get_campaign(identity)
    if not campaign: return []
    result=[]
    with database() as db:
        for v in campaign['variants']:
            item={'variant':v['label'],'coupon':v['code'],'views':0,'booking_click':0,'map_click':0,'coupon_claim':0,'redeemed':0}
            for row in db.execute('SELECT kind,COUNT(*) AS n FROM events WHERE variant_id=? GROUP BY kind',(v['id'],)):
                item['views' if row['kind']=='view' else row['kind']]=row['n']
            item['redeemed']=db.execute('SELECT COUNT(*) FROM redemptions WHERE variant_id=?',(v['id'],)).fetchone()[0]
            result.append(item)
    return result


def save_market(rows):
    with database() as db:
        for row in rows:
            identity=hashlib.sha256(json.dumps({key:row[key] for key in ['region','metric','unit','source_url','as_of']},ensure_ascii=False,sort_keys=True).encode()).hexdigest()
            db.execute('INSERT INTO markets VALUES(?,?,?,?) ON CONFLICT(id) DO UPDATE SET payload=excluded.payload,created=excluded.created',(identity,row['region'],json.dumps(row,ensure_ascii=False),now()))


def get_market(region):
    with database() as db:
        return [json.loads(row[0]) for row in db.execute('SELECT payload FROM markets WHERE region=? ORDER BY created DESC',(region.strip(),))]


def record_artifact(campaign_id,label,path):
    path=Path(path).resolve()
    outputs=(Path(__file__).parent/'outputs').resolve()
    if not path.is_relative_to(outputs) or not path.is_file(): raise ValueError('완성 영상 경로가 올바르지 않습니다.')
    with database() as db:
        db.execute('INSERT INTO artifacts(campaign_id,label,path,created) VALUES(?,?,?,?)',(campaign_id,label,str(path),now()))


def list_artifacts():
    outputs=(Path(__file__).parent/'outputs').resolve()
    with database() as db:
        return [dict(row) for row in db.execute('SELECT * FROM artifacts ORDER BY id DESC LIMIT 30')
                if Path(row['path']).resolve().is_relative_to(outputs) and Path(row['path']).is_file()]
