import asyncio, html, random
from datetime import datetime, timedelta, timezone
from aiogram import Bot, Dispatcher, F
from aiogram.filters import CommandStart
from aiogram.types import CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup, Message
from config import BOT_TOKEN, ADMIN_ID, FARMS, UNITS, DONATIONS, UNIT_BY_ID
from db import connect, init_db, ensure_user, user, top_users, users_count, all_user_ids, setting, set_setting, is_admin
from settings import init_settings, get_int, get_str
from combat import resolve

STATE={}; BATTLES={}; NEXT_BATTLE=1
MESSAGE_DEFAULTS={'home':'🪖 <b>ВОЕННАЯ СТРАТЕГИЯ</b>\n\n💵 Баланс: <b>{balance}</b>\n🏭 Ферма: <b>{farm}</b>/10\n💸 Налог: <b>{tax}</b>\n\n⚔️ Выбери раздел командования:','profile':'🛰 <b>ЛИЧНОЕ ДОСЬЕ</b>\n\n👤 Боец: <b>{username}</b>\n💵 Капитал: <b>{balance}</b>\n🏭 Ферма: <b>{farm}</b>/10\n🏆 Побед: <b>{wins}</b>\n💀 Поражений: <b>{losses}</b>','army':'🎖 <b>СОСТАВ ВОЙСК</b>\n\n{army}','shop':'🛒 <b>ВОЕННЫЙ АРСЕНАЛ</b>\n\nВыберите единицу. После выбора бот запросит количество.\n\n💵 Все цены указаны в долларах.','bonus':'🎁 <b>БОЕВОЕ СНАБЖЕНИЕ</b>\n\nЕжедневный приз выбирается случайно по таблице шансов.\n🎖 Бонус за подписку: <b>${sub}</b>','donate':'💳 <b>ПОПОЛНЕНИЕ БАЛАНСА</b>\n\n50 ⭐ — <b>${d50}</b>\n100 ⭐ — <b>${d100}</b>\n500 ⭐ — <b>${d500}</b>\n\n📨 Для покупки Stars напишите: <b>{contact}</b>','top':'🏆 <b>ГЕНЕРАЛЫ НЕДЕЛИ</b>\n\n{rows}','farm':'🏭 <b>ВОЕННО-ПРОМЫШЛЕННАЯ ФЕРМА</b>\n\nУровень: <b>{level}/10</b>\nПроизводство: <b>${income}/час</b>\nНалог: <b>${tax}</b>\nСтатус: <b>{status}</b>','admin':'⚙️ <b>ЦЕНТР КОМАНДОВАНИЯ</b>\n\nУправление экономикой, армиями, кейсами, сообщениями и пользователями.'}

async def seed():
    await init_settings(ADMIN_ID); db=await connect()
    for k,v in MESSAGE_DEFAULTS.items(): await db.execute('INSERT OR IGNORE INTO message_templates(key,text) VALUES(?,?)',(k,v))
    cases=[('case1','📦 КЕЙС I — ПЕХОТНЫЙ',45000,0),('case2','📦 КЕЙС II — БРОНЕТЕХНИКА',5000000,0),('president','🎖 ПРЕЗИДЕНТСКИЙ КЕЙС',0,50)]
    for c in cases: await db.execute('INSERT OR IGNORE INTO cases(id,title,price,stars) VALUES(?,?,?,?)',c)
    prizes={'case1':[('soldier',2,75),('soldier',10,15),('interceptor',11,10)],'case2':[('bmp',1,80),('tank',1,10),('helicopter',1,7.5),('plane',1,2.5)],'president':[('helicopter',1,90),('plane',1,8),('missile',1,2)]}
    for cid,items in prizes.items():
        cur=await db.execute('SELECT COUNT(*) c FROM case_prizes WHERE case_id=?',(cid,)); n=(await cur.fetchone())['c']
        if not n:
            for unit,amount,weight in items: await db.execute('INSERT INTO case_prizes(case_id,unit,amount,weight) VALUES(?,?,?,?)',(cid,unit,amount,weight))
    await db.execute('INSERT OR IGNORE INTO admins(user_id) VALUES(?)',(ADMIN_ID,)); await db.commit(); await db.close()

def money(n): return f'{int(n):,}'.replace(',',' ')
def now(): return datetime.now(timezone.utc)
def esc(s): return html.escape(str(s or ''))
async def T(key,fallback=''): return await setting('msg_'+key,await setting(key,fallback or MESSAGE_DEFAULTS.get(key,'')))
async def save_message(key,text): await set_setting('msg_'+key,text)

def kb(rows):
    """Build an inline keyboard from either rows of buttons or a single flat row.

    Both forms are accepted so a caller cannot accidentally crash the bot by
    passing [('A','a'), ('B','b')] instead of [[('A','a'), ('B','b')]].
    """
    if not rows:
        return InlineKeyboardMarkup(inline_keyboard=[])
    first=rows[0]
    if isinstance(first, tuple) and len(first)==2 and all(isinstance(x,str) for x in first):
        rows=[rows]
    keyboard=[]
    for row in rows:
        buttons=[]
        for item in row:
            if not isinstance(item,(tuple,list)) or len(item)!=2:
                raise ValueError('Keyboard button must be a (text, callback_data) pair')
            text,callback_data=item
            buttons.append(InlineKeyboardButton(text=str(text),callback_data=str(callback_data)))
        keyboard.append(buttons)
    return InlineKeyboardMarkup(inline_keyboard=keyboard)

def back(target='home'): return kb([('⬅️ Назад',target)])
def home_kb(admin=False):
    rows=[[('🏭 Ферма','farm'),('🎖 Армия','army')],[('🛒 Арсенал','shop'),('⚔️ Атака','attack')],[('🎁 Бонус','bonus'),('📦 Кейсы','cases')],[('👤 Профиль','profile'),('🏆 Топ','top')],[('💳 Донат','donate'),('📖 Правила','rules')],[('ℹ️ Помощь','help')]]
    if admin: rows.append([('⚙️ Админ-панель','admin')])
    return kb(rows)
def admin_kb(): return kb([[('💰 Валюта и курс','a_currency'),('🎁 Бонусы','a_bonus')],[('📦 Кейсы','a_cases'),('🎟 Промокоды','a_promos')],[('📢 Заработать','a_earn'),('💳 Донат','a_donate')],[('📕 Правила','a_rules'),('👥 Админы','a_admins')],[('🎖 Выдать / списать','a_give'),('📣 Рассылка','a_broadcast')],[('📊 Статистика','a_stats'),('✏️ Редактировать','a_edit')],[('🏭 Фермы','a_farms'),('⚔️ Бои','a_battles')],[('⬅️ Назад','home')]])
def army_text(u): return '\n'.join(f"{v['title']}: <b>{u[k]}</b>" for k,v in UNITS.items())
async def army_report(u): return (await T('army',MESSAGE_DEFAULTS['army'])).format(army=army_text(u))
async def home_text(uid):
    u=await user(uid); return (await T('home',MESSAGE_DEFAULTS['home'])).format(balance=money(u['balance']),farm=u['farm_level'],tax=money(u['tax']))
async def admin_check(uid): return await is_admin(uid,ADMIN_ID)
async def edit_call(c,text,markup=None):
    try: await c.message.edit_text(text,reply_markup=markup,parse_mode='HTML')
    except Exception: await c.message.answer(text,reply_markup=markup,parse_mode='HTML')
    await c.answer()

async def start(m):
    await ensure_user(m.from_user.id,m.from_user.username); await m.answer(await home_text(m.from_user.id),reply_markup=home_kb(await admin_check(m.from_user.id)),parse_mode='HTML')
async def profile(c):
    u=await user(c.from_user.id); raw=await T('profile',MESSAGE_DEFAULTS['profile']); name='@'+u['username'] if u['username'] else 'не указан'; await edit_call(c,raw.format(username=esc(name),balance=money(u['balance']),farm=u['farm_level'],wins=u['attacks_won'],losses=u['attacks_lost']),back())
async def shop(c):
    rows=[[(f"{v['title']}  ${money(v['price'])}",f'buyq:{k}')] for k,v in UNITS.items() if k!='artillery']; rows.append([('⬅️ Назад','home')]); await edit_call(c,await T('shop',MESSAGE_DEFAULTS['shop']),kb(rows))
async def cases(c):
    db=await connect(); cur=await db.execute('SELECT * FROM cases WHERE active=1'); cs=await cur.fetchall(); await db.close(); rows=[]
    for x in cs: rows.append([((f"{x['title']} · ${money(x['price'])}" if not x['stars'] else f"{x['title']} · {x['stars']} ⭐"),f'case:{x["id"]}')])
    rows.append([('⬅️ Назад','home')]); await edit_call(c,'📦 <b>АРМЕЙСКИЕ КЕЙСЫ</b>\n\nВыберите кейс:',kb(rows))
async def open_case(c,cid):
    db=await connect(); cur=await db.execute('SELECT * FROM cases WHERE id=?',(cid,)); case=await cur.fetchone()
    if not case: await db.close(); return await c.answer('Кейс не найден',show_alert=True)
    if cid=='president': await db.close(); return await edit_call(c,await donate_text(),kb([('💳 Донат','donate'),('⬅️ Назад','cases')]))
    u=await user(c.from_user.id)
    if u['balance']<case['price']: await db.close(); return await edit_call(c,f"❌ Недостаточно средств.\nНужно: <b>${money(case['price'])}</b>.",back('cases'))
    cur=await db.execute('SELECT * FROM case_prizes WHERE case_id=?',(cid,)); prizes=await cur.fetchall(); await db.close(); r=random.uniform(0,100); acc=0; prize=prizes[-1]
    for p in prizes:
        acc+=float(p['weight'])
        if r<=acc: prize=p; break
    db=await connect(); await db.execute('UPDATE users SET balance=balance-? WHERE user_id=?',(case['price'],c.from_user.id)); await db.execute(f'UPDATE users SET {prize["unit"]}={prize["unit"]}+? WHERE user_id=?',(prize['amount'],c.from_user.id)); await db.commit(); await db.close()
    await edit_call(c,f"📦 <b>КЕЙС ОТКРЫТ</b>\n\n{case['title']}\n\n🎖 Выпало: <b>{UNITS[prize['unit']]['title']} × {prize['amount']}</b>\n🎲 Шанс: <b>{prize['weight']}%</b>\n💵 Стоимость: <b>${money(case['price'])}</b>",back('cases'))
async def buy_start(c,key):
    if key not in UNITS or key=='artillery': return
    STATE[c.from_user.id]=('buy',key); await edit_call(c,f"🛒 <b>{UNITS[key]['title']}</b>\n\nЦена: <b>${money(UNITS[key]['price'])}</b> за 1 шт.\n\nВведите количество:",back('shop'))
async def do_buy(m,key,qty):
    if qty<=0 or qty>1_000_000: return await m.answer('❌ Некорректное количество.')
    price=UNITS[key]['price']*qty; u=await user(m.from_user.id)
    if u['balance']<price: return await m.answer(f'❌ Недостаточно средств.\nНужно: <b>${money(price)}</b>.',parse_mode='HTML')
    STATE.pop(m.from_user.id,None); await m.answer(f"🛒 <b>ПОДТВЕРЖДЕНИЕ ЗАКАЗА</b>\n\n{UNITS[key]['title']} × <b>{qty}</b>\n💵 Итого: <b>${money(price)}</b>",reply_markup=kb([('✅ Купить',f'buyok:{key}:{qty}'),('❌ Отмена','shop')]),parse_mode='HTML')
async def buy_confirm(c,key,qty):
    if key not in UNITS or key=='artillery' or qty<=0 or qty>1_000_000: return await c.answer('Некорректный заказ',show_alert=True)
    price=UNITS[key]['price']*qty; u=await user(c.from_user.id)
    if u['balance']<price: return await edit_call(c,'❌ Денег уже недостаточно.',back('shop'))
    db=await connect(); await db.execute(f'UPDATE users SET balance=balance-?,{key}={key}+? WHERE user_id=?',(price,qty,c.from_user.id)); await db.commit(); await db.close(); await edit_call(c,f"✅ <b>ЗАКАЗ ВЫПОЛНЕН</b>\n\n{UNITS[key]['title']} × <b>{qty}</b>\n💵 Списано: <b>${money(price)}</b>",back('shop'))
DAILY_PRIZES=[('💵 $100 000',50,'money',100000),('🎯 10 перехватчиков',20,'interceptor',10),('🛩 2 БПЛА',10,'drone',2),('🚙 1 БМП',5,'bmp',1),('🛩 10 БПЛА',5,'drone',10),('🛡 1 танк',2.5,'tank',1),('💵 $300 000',2.5,'money',300000),('🎯 50 перехватчиков',4.9,'interceptor',50),('🚁 1 вертолёт',0.1,'helicopter',1)]
async def bonus(c):
    raw=await T('bonus',MESSAGE_DEFAULTS['bonus']); text=raw.format(sub=money(await get_int('subscription_bonus')))+'\n\n<b>Шансы:</b>\n'+'\n'.join(f'{n} — {p}%' for n,p,_,_ in DAILY_PRIZES); await edit_call(c,text,kb([[('🎁 Забрать ежедневный приз','daily'),('📢 За подписку','sub')],[('🎟 Ввести промокод','promo')],[('⬅️ Назад','home')]]))
async def daily(c):
    uid=c.from_user.id; u=await user(uid); today=now().date().isoformat()
    if u['daily_claim']==today: return await edit_call(c,'❌ Ежедневный приз уже получен сегодня.',back('bonus'))
    r=random.uniform(0,100); acc=0; prize=DAILY_PRIZES[-1]
    for p in DAILY_PRIZES:
        acc+=p[1]
        if r<=acc: prize=p; break
    _,_,unit,amount=prize; db=await connect();
    if unit=='money': await db.execute('UPDATE users SET balance=balance+?,daily_claim=? WHERE user_id=?',(amount,today,uid))
    else: await db.execute(f'UPDATE users SET {unit}={unit}+?,daily_claim=? WHERE user_id=?',(amount,today,uid))
    await db.commit(); await db.close(); await edit_call(c,f"🎁 <b>ЕЖЕДНЕВНЫЙ ПРИЗ</b>\n\n🎯 Выпало: <b>{prize[0]}</b>\n🎲 Шанс: <b>{prize[1]}%</b>",back('bonus'))
async def sub(c,bot):
    channel=await get_str('channel_username'); bonusv=await get_int('subscription_bonus')
    if not channel: return await edit_call(c,'❌ Канал ещё не настроен администратором.',back('bonus'))
    try:
        member=await bot.get_chat_member(channel,c.from_user.id)
        if member.status in ('left','kicked'): raise ValueError
    except Exception: return await edit_call(c,'📢 Сначала подпишитесь на канал, затем повторите проверку.',kb([('📢 Открыть канал','openchannel'),('🔄 Проверить','sub'),('⬅️ Назад','bonus')]))
    u=await user(c.from_user.id)
    if u['sub_claim']: return await edit_call(c,'❌ Бонус за подписку уже получен.',back('bonus'))
    db=await connect(); await db.execute('UPDATE users SET balance=balance+?,sub_claim=1 WHERE user_id=?',(bonusv,c.from_user.id)); await db.commit(); await db.close(); await edit_call(c,f'🎁 Бонус за подписку: <b>+${money(bonusv)}</b>.',back('bonus'))
async def donate_text(): return (await T('donate',MESSAGE_DEFAULTS['donate'])).format(d50=money(DONATIONS[50]),d100=money(DONATIONS[100]),d500=money(DONATIONS[500]),contact=esc(await get_str('donate_contact')))
async def top(c):
    rows=await top_users(10); medals=['🥇','🥈','🥉']; out=[f"{medals[i] if i<3 else '🎖️'} <b>{i+1}.</b> @{esc(r['username']) if r['username'] else 'боец'} — <b>${money(r['balance'])}</b>" for i,r in enumerate(rows)]; await edit_call(c,(await T('top',MESSAGE_DEFAULTS['top'])).format(rows='\n'.join(out) or 'Пока пусто.'),back())
async def farm(c):
    u=await user(c.from_user.id); f=FARMS[u['farm_level']]; status='⛔ ОСТАНОВЛЕНА' if u['tax']>=1_000_000 else '🟢 АКТИВНА'; await edit_call(c,(await T('farm',MESSAGE_DEFAULTS['farm'])).format(level=u['farm_level'],income=money(f['income']),tax=money(u['tax']),status=status),kb([('💰 Получить выплату','payout'),('⬆️ Улучшить','upgrade'),('💸 Оплатить налог','paytax'),('⬅️ Назад','home')]))
async def payout(c):
    u=await user(c.from_user.id); t=now(); last=datetime.fromisoformat(u['last_payout'])
    if u['tax']>=1_000_000: return await edit_call(c,'⛔ Ферма остановлена. Оплатите налог.',back('farm'))
    if u['tax']>0: return await edit_call(c,f'❌ Сначала оплатите налог: <b>${money(u["tax"])}</b>.',back('farm'))
    if t-last<timedelta(hours=1):
        left=timedelta(hours=1)-(t-last); return await edit_call(c,f'⏳ До выплаты: <b>{left.seconds//3600:02}:{(left.seconds%3600)//60:02}:{left.seconds%60:02}</b>.',back('farm'))
    income=FARMS[u['farm_level']]['income']; tax=random.randint(await get_int('tax_increment_min'),await get_int('tax_increment_max')); db=await connect(); await db.execute('UPDATE users SET balance=balance+?,last_payout=?,tax=? WHERE user_id=?',(income,t.isoformat(),tax,c.from_user.id)); await db.commit(); await db.close(); await edit_call(c,f'💰 Получено: <b>+${money(income)}</b>\n💸 Новый налог: <b>${money(tax)}</b>.',back('farm'))
async def paytax(c):
    u=await user(c.from_user.id)
    if u['tax']<=0: return await edit_call(c,'✅ Налог уже оплачен.',back('farm'))
    if u['balance']<u['tax']: return await edit_call(c,f'❌ Нужно <b>${money(u["tax"])}</b>.',back('farm'))
    db=await connect(); await db.execute('UPDATE users SET balance=balance-tax,tax=0 WHERE user_id=?',(c.from_user.id,)); await db.commit(); await db.close(); await edit_call(c,'✅ Налог оплачен. Производство восстановлено.',back('farm'))
async def upgrade(c):
    u=await user(c.from_user.id); lvl=u['farm_level']
    if lvl>=10: return await edit_call(c,'🏭 Максимальный уровень — 10.',back('farm'))
    cost=FARMS[lvl+1]['upgrade']
    if u['balance']<cost: return await edit_call(c,f'❌ Нужно <b>${money(cost)}</b>.',back('farm'))
    db=await connect(); await db.execute('UPDATE users SET balance=balance-?,farm_level=? WHERE user_id=?',(cost,lvl+1,c.from_user.id)); await db.commit(); await db.close(); await edit_call(c,f'⬆️ Ферма повышена до <b>{lvl+1} уровня</b>.',back('farm'))

async def battle_start(c,defender_id,bot):
    global NEXT_BATTLE
    uid=c.from_user.id; a=await user(uid); d=await user(defender_id)
    if not a or not d or uid==defender_id: return await c.answer('Неверный противник',show_alert=True)
    if sum(a[k] for k in UNITS)==0 or sum(d[k] for k in UNITS)==0: return await c.answer('У одной из сторон нет армии',show_alert=True)
    bid=NEXT_BATTLE; NEXT_BATTLE+=1; BATTLES[bid]={'attacker':uid,'defender':defender_id,'ok':set(),'running':False,'messages':{}}
    name=lambda r:'@'+r['username'] if r['username'] else f"ID {r['user_id']}"; text=f"⚔️ <b>ВЫЗОВ НА БОЙ</b>\n\n🟥 Атакующий: <b>{esc(name(a))}</b>\n{await army_report(a)}\n\n🟦 Противник: <b>{esc(name(d))}</b>\n{await army_report(d)}\n\nОбе стороны должны подтвердить бой. После двух подтверждений начинается 15-секундная фаза сражения."
    m1=await c.message.answer(text,reply_markup=kb([('✅ Подтвердить бой',f'bconfirm:{bid}'),('❌ Отказаться','home')]),parse_mode='HTML'); m2=await bot.send_message(defender_id,text,reply_markup=kb([('✅ Подтвердить бой',f'bconfirm:{bid}'),('❌ Отказаться',f'bdecline:{bid}')]),parse_mode='HTML'); BATTLES[bid]['messages']={uid:m1.message_id,defender_id:m2.message_id}; await c.answer()
async def battle_confirm(c,bid,bot):
    b=BATTLES.get(bid)
    if not b: return await c.answer('Бой уже завершён',show_alert=True)
    if c.from_user.id not in (b['attacker'],b['defender']): return await c.answer('Это не ваш бой',show_alert=True)
    b['ok'].add(c.from_user.id); await c.answer('Подтверждено')
    if len(b['ok'])<2: return await c.message.edit_reply_markup(reply_markup=kb([('⏳ Подтверждено — ждём вторую сторону',f'bconfirm:{bid}')]))
    if not b['running']: b['running']=True; await run_battle(bid,bot)
async def run_battle(bid,bot):
    b=BATTLES.get(bid); a=await user(b['attacker']); d=await user(b['defender']); _,_,winner,events=resolve(a,d); phrases=['🛰 Разведка фиксирует позиции войск...','🛩 БПЛА выходят на цель...','🎯 Перехватчики открывают охоту...','🚙 БМП продвигаются вперёд...','🛡 Бронетехника вступает в бой...','🚁 Вертолёты заходят с фланга...','✈️ Самолёты атакуют воздушные цели...','🚀 Ракетный удар произведён...','💥 Линия фронта содрогается...','⚔️ Последний обмен ударами...']
    for i in range(15,0,-1):
        text=f"⚔️ <b>БОЙ ИДЁТ</b>\n\n⏱ <b>00:{i:02}</b>\n{phrases[(15-i)%len(phrases)]}\n\n🔴 Силы сторон уже вступили в контакт..."
        for uid,msgid in b['messages'].items():
            try: await bot.edit_message_text(text,chat_id=uid,message_id=msgid,parse_mode='HTML')
            except Exception: pass
        await asyncio.sleep(1)
    loser_id=b['defender'] if winner=='attacker' else b['attacker']; win_id=b['attacker'] if winner=='attacker' else b['defender']; loser=d if loser_id==b['defender'] else a; lost={k:int(loser[k]*0.20) for k in UNITS}; value=sum(lost[k]*UNITS[k]['price'] for k in UNITS); win_reward=int(value*await get_int('kill_reward_percent')/100); lose_reward=int(value*await get_int('loser_reward_percent')/100); sets=', '.join(f'{k}=?' for k in UNITS); vals=[max(0,loser[k]-lost[k]) for k in UNITS]
    db=await connect(); await db.execute(f'UPDATE users SET {sets},attacks_lost=attacks_lost+1,balance=balance+? WHERE user_id=?',(*vals,lose_reward,loser_id)); await db.execute('UPDATE users SET attacks_won=attacks_won+1,balance=balance+?,last_attack=? WHERE user_id=?',(win_reward,now().isoformat(),win_id)); await db.execute('INSERT INTO battle_log(attacker,defender,winner,report,created_at) VALUES(?,?,?,?,?)',(b['attacker'],b['defender'],win_id,'\n'.join(events),now().isoformat())); await db.commit(); await db.close(); lost_lines='\n'.join(f"{UNITS[k]['title']}: -{lost[k]}" for k in UNITS if lost[k]) or 'Нет потерь.'; report='\n'.join(events[-8:]) or 'Силы столкнулись без дополнительных событий.'; win_text=f"🏆 <b>WIN</b>\n\n{report}\n\n💰 Заработано: <b>+${money(win_reward)}</b>\n🪖 Армия победителя остаётся на месте."; lose_text=f"💀 <b>LOSE</b>\n\n{report}\n\n📉 Потери — 20% армии:\n{lost_lines}\n\n💰 Компенсация: <b>+${money(lose_reward)}</b>"
    for uid,msgid in b['messages'].items():
        try: await bot.edit_message_text(win_text if uid==win_id else lose_text,chat_id=uid,message_id=msgid,reply_markup=back(),parse_mode='HTML')
        except Exception: await bot.send_message(uid,win_text if uid==win_id else lose_text,reply_markup=back(),parse_mode='HTML')
    BATTLES.pop(bid,None)

async def admin_panel(c):
    if not await admin_check(c.from_user.id): return await c.answer('Нет доступа',show_alert=True)
    await edit_call(c,await T('admin',MESSAGE_DEFAULTS['admin']),admin_kb())
async def admin_section(c,s):
    if not await admin_check(c.from_user.id): return await c.answer('Нет доступа',show_alert=True)
    if s=='a_currency': text='💰 <b>ВАЛЮТА И КУРС</b>'; rows=[('💵 Символ валюты','set:currency_symbol'),('📈 Курс','set:currency_rate')]
    elif s=='a_bonus': text='🎁 <b>БОНУСЫ</b>'; rows=[('🎁 Ежедневный','set:daily_bonus'),('📢 За подписку','set:subscription_bonus'),('📡 Канал','set:channel_username')]
    elif s=='a_donate': text='💳 <b>ДОНАТ</b>'; rows=[('50 ⭐','set:donate_50'),('100 ⭐','set:donate_100'),('500 ⭐','set:donate_500'),('📨 Кому писать','set:donate_contact')]
    elif s=='a_earn': text='📢 <b>ЗАРАБОТАТЬ</b>'; rows=[('📡 Канал','set:channel_username'),('💵 Сумма','set:subscription_bonus')]
    elif s=='a_rules': text=await get_str('rules_text'); rows=[('✏️ Изменить правила','set:rules_text')]
    elif s=='a_farms': text='🏭 <b>ФЕРМЫ</b>\n\nРедактируйте доход уровней и налог.'; rows=[(f'Уровень {i} доход','set:farm_'+str(i)+'_income') for i in range(1,11)]+[('💸 Налог макс.','set:tax_max')]
    elif s=='a_battles': text='⚔️ <b>БОИ</b>'; rows=[('⏱ Кулдаун','set:attack_cooldown_minutes'),('📉 Потери %','set:loss_percent'),('🏆 Награда %','set:kill_reward_percent'),('💰 LOSE %','set:loser_reward_percent')]
    elif s=='a_stats': text=f"📊 <b>СТАТИСТИКА</b>\n\n👥 Игроков: <b>{await users_count()}</b>\n⚔️ Активных боёв: <b>{len(BATTLES)}</b>"; rows=[]
    elif s=='a_promos': text='🎟 <b>ПРОМОКОДЫ</b>\n\nСоздать: <code>/newpromo CODE SUM USES</code>'; rows=[]
    elif s=='a_cases': text='📦 <b>КЕЙСЫ</b>\n\nКейс I — $45 000\n75%: 2 пехоты\n15%: 10 пехоты\n10%: 11 перехватчиков\n\nКейс II — $5 000 000\n80%: БМП\n10%: танк\n7.5%: вертолёт\n2.5%: самолёт\n\nПрезидентский — 50 ⭐\n90%: вертолёт\n8%: самолёт\n2%: ракета'; rows=[]
    elif s=='a_admins':
        db=await connect(); cur=await db.execute('SELECT user_id FROM admins'); ar=await cur.fetchall(); await db.close(); text='👥 <b>АДМИНЫ</b>\n\n'+'\n'.join(f'• <code>{x[0]}</code>' for x in ar)+f'\n\n👑 Владелец: <code>{ADMIN_ID}</code>'; rows=[('➕ Добавить админа','admin_add'),('➖ Удалить админа','admin_del')]
    elif s=='a_give': text='🎖 <b>ВЫДАТЬ / СПИСАТЬ</b>\n\n<code>/givepehot @username ID количество</code>\n<code>/givecash @username сумма</code>\n\nID войск: 1 пехота · 2 перехватчик · 3 БПЛА · 4 БМП · 5 танк · 6 вертолёт · 7 самолёт · 8 ракета · 9 артиллерия'; rows=[]
    elif s=='a_broadcast': text='📣 <b>РАССЫЛКА</b>\n\nИспользуйте: <code>/broadcast текст</code>'; rows=[]
    elif s=='a_edit': text='✏️ <b>РЕДАКТОР СООБЩЕНИЙ</b>\n\nВыберите шаблон для изменения.'; rows=[[('🏠 Главное','edit:home'),('👤 Профиль','edit:profile')],[('🎖 Армия','edit:army'),('🛒 Арсенал','edit:shop')],[('🎁 Бонус','edit:bonus'),('💳 Донат','edit:donate')],[('🏆 Топ','edit:top'),('🏭 Ферма','edit:farm')],[('⚙️ Админка','edit:admin')]]
    else: text='Раздел'; rows=[]
    rows=[rows] if rows and isinstance(rows[0],tuple) else rows
    await edit_call(c,text,kb(rows+[[('⬅️ Назад','admin')]]))

async def set_prompt(c,key):
    if not await admin_check(c.from_user.id): return await c.answer('Нет доступа',show_alert=True)
    STATE[c.from_user.id]=('set',key); current=await get_str(key); await edit_call(c,f'✏️ <b>Изменение параметра</b>\n\nКлюч: <code>{esc(key)}</code>\nТекущее значение: <code>{esc(current)}</code>\n\nОтправьте новое значение сообщением.',back('admin'))
async def edit_prompt(c,key):
    if not await admin_check(c.from_user.id): return await c.answer('Нет доступа',show_alert=True)
    STATE[c.from_user.id]=('editmsg',key); current=await T(key,MESSAGE_DEFAULTS.get(key,'')); await edit_call(c,f'✏️ <b>РЕДАКТИРОВАНИЕ СООБЩЕНИЯ</b>\n\nКлюч: <code>{esc(key)}</code>\n\nТекущий текст:\n{current}\n\nОтправьте новый текст.',back('a_edit'))

async def text_handler(m):
    st=STATE.get(m.from_user.id)
    if not st: return
    typ,key=st
    if typ=='buy': return await do_buy(m,key,int(m.text.strip()) if m.text.strip().isdigit() else 0)
    if typ=='set':
        if not await admin_check(m.from_user.id): STATE.pop(m.from_user.id,None); return
        value=m.text.strip()
        if key in {'daily_bonus','subscription_bonus','tax_increment_min','tax_increment_max','tax_max','attack_cooldown_minutes','loss_percent','kill_reward_percent','loser_reward_percent'} or key.startswith('farm_') or key.startswith('donate_'):
            if key!='donate_contact' and not value.isdigit(): return await m.answer('❌ Для этого параметра нужно число.')
        await set_setting(key,value); STATE.pop(m.from_user.id,None); return await m.answer('✅ Настройка сохранена.')
    if typ=='editmsg':
        if not await admin_check(m.from_user.id): STATE.pop(m.from_user.id,None); return
        await save_message(key,m.text); STATE.pop(m.from_user.id,None); return await m.answer('✅ Сообщение сохранено.')

async def callback(c:CallbackQuery,bot:Bot):
    d=c.data
    if d=='home': return await edit_call(c,await home_text(c.from_user.id),home_kb(await admin_check(c.from_user.id)))
    if d=='farm': return await farm(c)
    if d=='payout': return await payout(c)
    if d=='paytax': return await paytax(c)
    if d=='upgrade': return await upgrade(c)
    if d=='profile': return await profile(c)
    if d=='army': return await edit_call(c,await army_report(await user(c.from_user.id)),back())
    if d=='shop': return await shop(c)
    if d.startswith('buyq:'): return await buy_start(c,d.split(':',1)[1])
    if d.startswith('buyok:'):
        _,key,qty=d.split(':'); return await buy_confirm(c,key,int(qty))
    if d=='cases': return await cases(c)
    if d.startswith('case:'): return await open_case(c,d.split(':',1)[1])
    if d=='bonus': return await bonus(c)
    if d=='daily': return await daily(c)
    if d=='sub': return await sub(c,bot)
    if d=='donate': return await edit_call(c,await donate_text(),kb([('⬅️ Назад','home')]))
    if d=='top': return await top(c)
    if d=='help': return await edit_call(c,await get_str('help_text'),back())
    if d=='rules': return await edit_call(c,await get_str('rules_text'),back())
    if d=='attack':
        await edit_call(c,'⚔️ <b>АТАКА</b>\n\nВведите Telegram username противника сообщением в формате <code>@username</code>.',back()); STATE[c.from_user.id]=('attack_target',None); return
    if d=='admin': return await admin_panel(c)
    if d.startswith('a_'): return await admin_section(c,d)
    if d.startswith('set:'): return await set_prompt(c,d.split(':',1)[1])
    if d.startswith('edit:'): return await edit_prompt(c,d.split(':',1)[1])
    if d.startswith('bconfirm:'): return await battle_confirm(c,int(d.split(':',1)[1]),bot)
    if d.startswith('bdecline:'):
        BATTLES.pop(int(d.split(':',1)[1]),None); return await edit_call(c,'❌ Бой отменён.',back())
    await c.answer()

async def main():
    if not BOT_TOKEN: raise RuntimeError('BOT_TOKEN is empty')
    await init_db(); await seed(); bot=Bot(BOT_TOKEN); dp=Dispatcher(); dp.message.register(start,CommandStart()); dp.message.register(text_handler,F.text); dp.callback_query.register(callback,F.data); print('Voennabot started'); await dp.start_polling(bot)
if __name__=='__main__': asyncio.run(main())
