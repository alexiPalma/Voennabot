import aiosqlite
from datetime import datetime, timezone
from config import DB_PATH, UNITS

UNIT_COLUMNS = ', '.join(f'{k} INTEGER NOT NULL DEFAULT 0' for k in UNITS)

async def connect():
    db = await aiosqlite.connect(DB_PATH)
    db.row_factory = aiosqlite.Row
    return db

async def init_db():
    db = await connect()
    await db.execute(f'''CREATE TABLE IF NOT EXISTS users (
        user_id INTEGER PRIMARY KEY,
        username TEXT NOT NULL DEFAULT '',
        balance INTEGER NOT NULL DEFAULT 0,
        farm_level INTEGER NOT NULL DEFAULT 1,
        tax INTEGER NOT NULL DEFAULT 0,
        last_payout TEXT NOT NULL,
        daily_claim TEXT NOT NULL DEFAULT '',
        sub_claim INTEGER NOT NULL DEFAULT 0,
        last_attack TEXT NOT NULL DEFAULT '',
        attacks_won INTEGER NOT NULL DEFAULT 0,
        attacks_lost INTEGER NOT NULL DEFAULT 0,
        {UNIT_COLUMNS}
    )''')
    await db.execute('''CREATE TABLE IF NOT EXISTS settings (key TEXT PRIMARY KEY, value TEXT NOT NULL)''')
    await db.execute('''CREATE TABLE IF NOT EXISTS promos (code TEXT PRIMARY KEY, amount INTEGER NOT NULL, uses INTEGER NOT NULL DEFAULT 0, max_uses INTEGER NOT NULL DEFAULT 1)''')
    await db.execute('''CREATE TABLE IF NOT EXISTS promo_uses (code TEXT, user_id INTEGER, PRIMARY KEY(code,user_id))''')
    await db.execute('''CREATE TABLE IF NOT EXISTS battle_log (id INTEGER PRIMARY KEY AUTOINCREMENT, attacker INTEGER, defender INTEGER, winner INTEGER, report TEXT, created_at TEXT)''')
    await db.commit(); await db.close()

async def ensure_user(user_id, username=''):
    db = await connect()
    now = datetime.now(timezone.utc).isoformat()
    await db.execute('INSERT OR IGNORE INTO users(user_id,username,last_payout) VALUES(?,?,?)', (user_id, username or '', now))
    await db.execute('UPDATE users SET username=? WHERE user_id=?', (username or '', user_id))
    await db.commit(); await db.close()

async def user(user_id):
    db = await connect(); cur = await db.execute('SELECT * FROM users WHERE user_id=?', (user_id,)); row = await cur.fetchone(); await db.close(); return row

async def setting(key, default=None):
    db=await connect(); cur=await db.execute('SELECT value FROM settings WHERE key=?',(key,)); row=await cur.fetchone(); await db.close(); return row['value'] if row else default

async def set_setting(key,value):
    db=await connect(); await db.execute('INSERT INTO settings(key,value) VALUES(?,?) ON CONFLICT(key) DO UPDATE SET value=excluded.value',(key,str(value))); await db.commit(); await db.close()

async def users_count():
    db=await connect(); cur=await db.execute('SELECT COUNT(*) c FROM users'); n=(await cur.fetchone())['c']; await db.close(); return n

async def top_users(limit=10):
    db=await connect(); cur=await db.execute('SELECT user_id,username,balance,farm_level,soldier,drone,bmp,tank,helicopter,plane,missile FROM users ORDER BY balance DESC LIMIT ?', (limit,)); rows=await cur.fetchall(); await db.close(); return rows

async def all_user_ids():
    db=await connect(); cur=await db.execute('SELECT user_id FROM users'); rows=await cur.fetchall(); await db.close(); return [r['user_id'] for r in rows]
