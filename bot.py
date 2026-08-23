import asyncio
import html
import random
from datetime import datetime, timedelta, timezone

from aiogram import Bot, Dispatcher, F
from aiogram.filters import CommandStart
from aiogram.types import (
    CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup, LabeledPrice,
    Message, PreCheckoutQuery
)

from config import *
from db import connect, ensure_user, init_db, user, top_users, users_count, all_user_ids, setting, set_setting
from combat import resolve

ADMIN_STATE = {}
PAGE_SIZE = 8


def money(n):
    return f'{int(n):,}'.replace(',', ' ')


def now():
    return datetime.now(timezone.utc)


def back(target='home'):
    return InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text='⬅️ Назад', callback_data=target)]])


def home_kb(uid):
    rows = [
        [InlineKeyboardButton(text='🏭 Ферма', callback_data='farm'), InlineKeyboardButton(text='🪖 Армия', callback_data='army')],
        [InlineKeyboardButton(text='🛒 Магазин', callback_data='shop'), InlineKeyboardButton(text='⚔️ Атака', callback_data='attack')],
        [InlineKeyboardButton(text='🎁 Бонусы', callback_data='bonus'), InlineKeyboardButton(text='💳 Донат', callback_data='donate')],
        [InlineKeyboardButton(text='👤 Профиль', callback_data='profile'), InlineKeyboardButton(text='🏆 Топ', callback_data='top')],
        [InlineKeyboardButton(text='ℹ️ Помощь', callback_data='help')],
    ]
    if uid == ADMIN_ID:
        rows.append([InlineKeyboardButton(text='⚙️ Админ-панель', callback_data='admin')])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def admin_kb():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text='👥 Пользователи', callback_data='a_users'), InlineKeyboardButton(text='💰 Выдать деньги', callback_data='a_money')],
        [InlineKeyboardButton(text='🪖 Выдать армию', callback_data='a_army'), InlineKeyboardButton(text='🗑 Обнулить игрока', callback_data='a_reset')],
        [InlineKeyboardButton(text='🏭 Фермы', callback_data='a_farms'), InlineKeyboardButton(text='⚔️ Бои', callback_data='a_battles')],
        [InlineKeyboardButton(text='🎁 Бонусы', callback_data='a_bonus'), InlineKeyboardButton(text='🎫 Промокоды', callback_data='a_promos')],
        [InlineKeyboardButton(text='📢 Рассылка', callback_data='a_broadcast'), InlineKeyboardButton(text='📊 Статистика', callback_data='a_stats')],
        [InlineKeyboardButton(text='💳 Донат', callback_data='a_donate'), InlineKeyboardButton(text='⚙️ Настройки', callback_data='a_settings')],
        [InlineKeyboardButton(text='⬅️ Главное меню', callback_data='home')]
    ])


def shop_kb():
    rows=[]
    for key, item in UNITS.items():
        rows.append([InlineKeyboardButton(text=f"{item['title']} · {money(item['price'])}", callback_data=f'buy:{key}')])
    rows.append([InlineKeyboardButton(text='⬅️ Назад', callback_data='home')])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def army_text(u):
    return '🪖 <b>ТВОЯ АРМИЯ</b>\n\n' + '\n'.join(f"{item['title']}: <b>{u[key]}</b>" for key,item in UNITS.items())


def home_text(u):
    return (f"🪖 <b>ВОЕННАЯ СТРАТЕГИЯ</b>\n\n"
            f"💰 Баланс: <b>{money(u['balance'])}</b>\n"
            f"🏭 Ферма: <b>{u['farm_level']}/10</b>\n"
            f"💸 Налог: <b>{money(u['tax'])}</b>\n\nВыбери раздел:")


async def edit(call, text, kb):
    try:
        await call.message.edit_text(text, reply_markup=kb, parse_mode='HTML')
    except Exception:
        await call.message.answer(text, reply_markup=kb, parse_mode='HTML')
    await call.answer()


async def cmd_start(message: Message):
    await ensure_user(message.from_user.id, message.from_user.username)
    await message.answer(home_text(await user(message.from_user.id)), reply_markup=home_kb(message.from_user.id), parse_mode='HTML')


async def claim_daily(call):
    uid=call.from_user.id; u=await user(uid); today=now().date().isoformat()
    if u['daily_claim']==today: return await edit(call,'❌ Ежедневный бонус уже получен сегодня.',back('bonus'))
    db=await connect(); await db.execute('UPDATE users SET balance=balance+500000,daily_claim=? WHERE user_id=?',(today,uid)); await db.commit(); await db.close()
    await edit(call,'🎁 Ты получил <b>500 000</b>.',back('bonus'))


async def subscription_claim(call, bot):
    uid=call.from_user.id
    if not CHANNEL_USERNAME: return await edit(call,'⚠️ Канал ещё не настроен администратором.',back('bonus'))
    try:
        member=await bot.get_chat_member(CHANNEL_USERNAME,uid)
        if member.status in ('left','kicked'): raise ValueError
    except Exception:
        return await edit(call,'❌ Сначала подпишись на канал, затем нажми кнопку ещё раз.',InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text='📢 Открыть канал',url='https://t.me/'+CHANNEL_USERNAME.lstrip('@'))],[InlineKeyboardButton(text='⬅️ Назад',callback_data='bonus')]]))
    u=await user(uid)
    if u['sub_claim']: return await edit(call,'❌ Бонус за подписку уже получен.',back('bonus'))
    db=await connect(); await db.execute('UPDATE users SET balance=balance+1500000,sub_claim=1 WHERE user_id=?',(uid,)); await db.commit(); await db.close()
    await edit(call,'🎁 Бонус за подписку: <b>1 500 000</b>.',back('bonus'))


async def buy(call, key):
    uid=call.from_user.id; item=UNITS[key]; u=await user(uid)
    if u['balance']<item['price']: return await edit(call,f"❌ Недостаточно денег.\nНужно: <b>{money(item['price'])}</b>.",back('shop'))
    db=await connect(); await db.execute(f'UPDATE users SET balance=balance-?,{key}={key}+1 WHERE user_id=?',(item['price'],uid)); await db.commit(); await db.close()
    await edit(call,f"✅ Куплено: <b>{item['title']}</b>\n💰 Списано: <b>{money(item['price'])}</b>",back('shop'))


async def farm(call):
    u=await user(call.from_user.id); f=FARMS[u['farm_level']]
    tax_status='❌ Ферма остановлена' if u['tax']>=TAX_MAX else '✅ Работает'
    kb=[[InlineKeyboardButton(text='💰 Получить выплату',callback_data='payout'),InlineKeyboardButton(text='⬆️ Улучшить',callback_data='upgrade')],[InlineKeyboardButton(text='💸 Оплатить налог',callback_data='paytax')],[InlineKeyboardButton(text='⬅️ Назад',callback_data='home')]]
    text=(f"🏭 <b>ФЕРМА</b>\n\nУровень: <b>{u['farm_level']}/10</b>\nДоход: <b>{money(f['income'])}/час</b>\nНалог: <b>{money(u['tax'])}</b>\nСтатус: {tax_status}\n\nНалог после выплаты увеличивается случайно на 20–50 тыс.\nМаксимальный долг: 1 млн.")
    await edit(call,text,InlineKeyboardMarkup(inline_keyboard=kb))


async def payout(call):
    uid=call.from_user.id; u=await user(uid); t=now(); last=datetime.fromisoformat(u['last_payout'])
    if u['tax']>=TAX_MAX: return await edit(call,'❌ Ферма остановлена. Налог достиг 1 000 000 — сначала погаси налог.',back('farm'))
    if u['tax']>0: return await edit(call,f"❌ Сначала оплати налог <b>{money(u['tax'])}</b>.",back('farm'))
    if t-last<timedelta(hours=1):
        left=timedelta(hours=1)-(t-last); return await edit(call,f'⏳ До следующей выплаты: <b>{left.seconds//3600:02}:{(left.seconds%3600)//60:02}:{left.seconds%60:02}</b>.',back('farm'))
    income=FARMS[u['farm_level']]['income']; new_tax=min(TAX_MAX,random.randint(TAX_INCREMENT_MIN,TAX_INCREMENT_MAX))
    db=await connect(); await db.execute('UPDATE users SET balance=balance+?,last_payout=?,tax=? WHERE user_id=?',(income,t.isoformat(),new_tax,uid)); await db.commit(); await db.close()
    await edit(call,f'✅ Выплата: <b>+{money(income)}</b>\n💸 Новый налог: <b>{money(new_tax)}</b>.',back('farm'))


async def paytax(call):
    uid=call.from_user.id; u=await user(uid)
    if u['tax']<=0: return await edit(call,'✅ Налог уже оплачен.',back('farm'))
    if u['balance']<u['tax']: return await edit(call,f"❌ Нужно <b>{money(u['tax'])}</b>, а есть <b>{money(u['balance'])}</b>.",back('farm'))
    db=await connect(); await db.execute('UPDATE users SET balance=balance-tax,tax=0 WHERE user_id=?',(uid,)); await db.commit(); await db.close()
    await edit(call,'✅ Налог оплачен. Ферма снова работает.',back('farm'))


async def upgrade(call):
    uid=call.from_user.id; u=await user(uid); lvl=u['farm_level']
    if lvl>=10: return await edit(call,'🏭 Ферма уже 10 уровня.',back('farm'))
    cost=FARMS[lvl+1]['upgrade']
    if u['balance']<cost: return await edit(call,f"❌ Для {lvl+1} уровня нужно <b>{money(cost)}</b>.",back('farm'))
    db=await connect(); await db.execute('UPDATE users SET balance=balance-?,farm_level=? WHERE user_id=?',(cost,lvl+1,uid)); await db.commit(); await db.close()
    await edit(call,f'⬆️ Ферма улучшена до <b>{lvl+1} уровня</b>.',back('farm'))


async def create_stars_invoice(call, bot, stars):
    if stars not in DONATIONS: return await call.answer('Неизвестный пакет',show_alert=True)
    await bot.send_invoice(chat_id=call.from_user.id,title=f'Донат {stars} ⭐',description=f'Пополнение игрового баланса на {money(DONATIONS[stars])}',payload=f'donate:{stars}',currency='XTR',prices=[LabeledPrice(label=f'{stars} Stars',amount=stars)])
    await call.answer()


async def attack_menu(call):
    rows=[]; uid=call.from_user.id
    db=await connect(); cur=await db.execute('SELECT user_id,username,balance,farm_level FROM users WHERE user_id!=? ORDER BY balance DESC LIMIT 30',(uid,)); targets=await cur.fetchall(); await db.close()
    if not targets: return await edit(call,'⚔️ Пока нет других игроков.',back('home'))
    for r in targets:
        name='@'+r['username'] if r['username'] else f"ID {r['user_id']}"
        rows.append([InlineKeyboardButton(text=f"🎯 {name} · {money(r['balance'])}",callback_data=f"target:{r['user_id']}")])
    rows.append([InlineKeyboardButton(text='⬅️ Назад',callback_data='home')])
    await edit(call,'⚔️ <b>ВЫБОР ПРОТИВНИКА</b>\n\nОдна атака в час. После боя проигравший теряет 20% армии.',InlineKeyboardMarkup(inline_keyboard=rows))


async def do_attack(call, defender_id):
    uid=call.from_user.id
    if uid==defender_id: return await call.answer('Нельзя атаковать себя',show_alert=True)
    a=await user(uid); d=await user(defender_id)
    if not a or not d: return await call.answer('Игрок не найден',show_alert=True)
    if a['last_attack']:
        last=datetime.fromisoformat(a['last_attack']); left=timedelta(hours=1)-(now()-last)
        if left.total_seconds()>0: return await edit(call,f'⏳ До следующей атаки: <b>{left.seconds//60} мин.</b>.',back('attack'))
    if sum(a[k] for k in UNITS)==0: return await edit(call,'❌ У тебя нет армии.',back('attack'))
    if sum(d[k] for k in UNITS)==0: return await edit(call,'❌ У противника нет армии.',back('attack'))
    aa,dd,winner,events=resolve(a,d)
    # The attacker's army remains after a victory. The defender loses 20% on defeat.
    if winner=='attacker':
        dd={k:max(0,int(d[k]*0.8)) for k in UNITS}
    else:
        aa={k:max(0,int(a[k]*0.8)) for k in UNITS}
    # Combat costs are charged for actual units lost from the original army.
    cost=0
    for k in UNITS:
        original=a[k]; remaining=aa[k]
        cost += max(0,original-remaining)*UNITS[k]['loss']
    db=await connect()
    sets=', '.join(f'{k}=?' for k in UNITS)
    vals=[aa[k] for k in UNITS]
    await db.execute(f'UPDATE users SET {sets},last_attack=?,attacks_won=attacks_won+? WHERE user_id=?',(*vals,now().isoformat(),1 if winner=='attacker' else 0,uid))
    dvals=[dd[k] for k in UNITS]
    await db.execute(f'UPDATE users SET {sets},attacks_lost=attacks_lost+? WHERE user_id=?',(*dvals,1 if winner=='defender' else 0,defender_id))
    if cost:
        await db.execute('UPDATE users SET balance=MAX(0,balance-?) WHERE user_id=?',(cost,uid))
    await db.execute('INSERT INTO battle_log(attacker,defender,winner,report,created_at) VALUES(?,?,?,?,?)',(uid,defender_id,uid if winner=='attacker' else defender_id,'\n'.join(events[-20:]),now().isoformat()))
    await db.commit(); await db.close()
    title='🏆 <b>ПОБЕДА!</b>' if winner=='attacker' else '💀 <b>ПОРАЖЕНИЕ!</b>'
    report='\n'.join(events[-12:]) or 'Бой прошёл без специальных срабатываний.'
    await edit(call,f"{title}\n\n{report}\n\n💸 Стоимость твоих потерь: <b>{money(cost)}</b>\n📉 Проигравшая армия потеряла <b>20%</b>.",back('home'))


async def promo_use(call, code):
    uid=call.from_user.id; code=code.strip().upper(); db=await connect(); cur=await db.execute('SELECT * FROM promos WHERE code=?',(code,)); p=await cur.fetchone()
    if not p: await db.close(); return await edit(call,'❌ Промокод не найден.',back('bonus'))
    cur=await db.execute('SELECT 1 FROM promo_uses WHERE code=? AND user_id=?',(code,uid)); used=await cur.fetchone()
    if used or p['uses']>=p['max_uses']: await db.close(); return await edit(call,'❌ Промокод уже использован или закончился.',back('bonus'))
    await db.execute('INSERT INTO promo_uses(code,user_id) VALUES(?,?)',(code,uid)); await db.execute('UPDATE promos SET uses=uses+1 WHERE code=?',(code,)); await db.execute('UPDATE users SET balance=balance+? WHERE user_id=?',(p['amount'],uid)); await db.commit(); await db.close()
    await edit(call,f"🎫 Промокод активирован: <b>+{money(p['amount'])}</b>.",back('bonus'))


async def admin_action(call, action):
    if call.from_user.id!=ADMIN_ID: return await call.answer('Нет доступа',show_alert=True)
    if action=='a_stats': return await edit(call,f'📊 <b>СТАТИСТИКА</b>\n\nИгроков: <b>{await users_count()}</b>',admin_kb())
    if action=='a_farms':
        text='🏭 <b>ФЕРМЫ</b>\n\n'+'\n'.join(f"{i}. {money(v['income'])}/ч · улучшение {money(v['upgrade'])}" for i,v in FARMS.items())
        return await edit(call,text,admin_kb())
    if action=='a_donate': return await edit(call,'💳 <b>ДОНАТ</b>\n\n50 ⭐ → 5 000 000\n100 ⭐ → 11 000 000\n500 ⭐ → 100 000 000\n\nПлатёж зачисляется автоматически после успешной оплаты.',admin_kb())
    if action=='a_battles': return await edit(call,'⚔️ <b>БОИ</b>\n\n1 атака/час\nПроигравший: −20% армии\nПобедитель сохраняет армию по правилам игры\nНаграда за уничтожение: 5% цены единицы.',admin_kb())
    if action=='a_bonus': return await edit(call,'🎁 <b>БОНУСЫ</b>\n\nЕжедневный: 500 000\nЗа подписку: 1 500 000',admin_kb())
    if action=='a_settings': return await edit(call,f'⚙️ <b>НАСТРОЙКИ</b>\n\nКанал: <code>{html.escape(CHANNEL_USERNAME or "не задан")}</code>\nМакс. налог: {money(TAX_MAX)}\nНалог/час: 20–50 тыс.',admin_kb())
    if action in ('a_money','a_army','a_reset','a_broadcast','a_promos','a_users'):
        ADMIN_STATE[call.from_user.id]=action
        prompts={'a_money':'💰 Пришли: <code>ID сумма</code>\nНапример: <code>123456789 5000000</code>', 'a_army':'🪖 Пришли: <code>ID тип количество</code>\nТип: soldier/drone/interceptor/bmp/tank/helicopter/plane/missile', 'a_reset':'🗑 Пришли Telegram ID игрока.', 'a_broadcast':'📢 Пришли сообщение для рассылки.', 'a_promos':'🎫 Пришли: <code>КОД СУММА ЛИМИТ</code>', 'a_users':'👥 Пришли Telegram ID для просмотра профиля.'}
        return await edit(call,prompts[action],InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text='❌ Отмена',callback_data='admin')]]))
    await edit(call,'⚙️ Раздел готов.',admin_kb())


async def admin_message(message: Message, bot: Bot):
    if message.from_user.id!=ADMIN_ID or message.from_user.id not in ADMIN_STATE: return False
    action=ADMIN_STATE.pop(message.from_user.id); text=message.text.strip()
    try:
        if action=='a_money':
            uid,amount=map(int,text.split()); db=await connect(); await db.execute('UPDATE users SET balance=balance+? WHERE user_id=?',(amount,uid)); await db.commit(); await db.close(); await message.answer(f'✅ Баланс {uid}: {amount:+,}'.replace(',',' '),reply_markup=admin_kb()); return True
        if action=='a_army':
            uid,key,amount=text.split(); uid=int(uid); amount=int(amount); assert key in UNITS
            db=await connect(); await db.execute(f'UPDATE users SET {key}=MAX(0,{key}+?) WHERE user_id=?',(amount,uid)); await db.commit(); await db.close(); await message.answer('✅ Армия изменена.',reply_markup=admin_kb()); return True
        if action=='a_reset':
            uid=int(text); db=await connect(); await db.execute('UPDATE users SET balance=0,farm_level=1,tax=0,soldier=0,drone=0,interceptor=0,bmp=0,tank=0,helicopter=0,plane=0,missile=0 WHERE user_id=?',(uid,)); await db.commit(); await db.close(); await message.answer('✅ Игрок обнулён.',reply_markup=admin_kb()); return True
        if action=='a_users':
            u=await user(int(text));
            if not u: await message.answer('❌ Игрок не найден.',reply_markup=admin_kb())
            else: await message.answer(home_text(u)+'\n\n'+army_text(u),reply_markup=admin_kb(),parse_mode='HTML')
            return True
        if action=='a_promos':
            code,amount,limit=text.upper().split(); db=await connect(); await db.execute('INSERT OR REPLACE INTO promos(code,amount,max_uses) VALUES(?,?,?)',(code,int(amount),int(limit))); await db.commit(); await db.close(); await message.answer('✅ Промокод создан.',reply_markup=admin_kb()); return True
        if action=='a_broadcast':
            sent=0
            for uid in await all_user_ids():
                try: await bot.send_message(uid,text); sent+=1
                except Exception: pass
            await message.answer(f'📢 Рассылка завершена: {sent}.',reply_markup=admin_kb()); return True
    except Exception as e:
        await message.answer(f'❌ Ошибка формата: {html.escape(str(e))}',reply_markup=admin_kb())
        return True
    return True


async def callbacks(call: CallbackQuery, bot: Bot):
    uid=call.from_user.id; await ensure_user(uid,call.from_user.username); d=call.data
    if d=='home': return await edit(call,home_text(await user(uid)),home_kb(uid))
    if d=='farm': return await farm(call)
    if d=='payout': return await payout(call)
    if d=='paytax': return await paytax(call)
    if d=='upgrade': return await upgrade(call)
    if d=='army': return await edit(call,army_text(await user(uid)),back('home'))
    if d=='shop': return await edit(call,'🛒 <b>МАГАЗИН</b>\n\nВыбери единицу:',shop_kb())
    if d.startswith('buy:'): return await buy(call,d.split(':',1)[1])
    if d=='bonus': return await edit(call,'🎁 <b>БОНУСЫ</b>\n\nЕжедневный: <b>500 000</b>\nЗа подписку: <b>1 500 000</b>\n\nПромокоды можно активировать кнопкой ниже.',InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text='🎁 Ежедневный',callback_data='daily')],[InlineKeyboardButton(text='📢 За подписку',callback_data='sub')],[InlineKeyboardButton(text='🎫 Ввести промокод',callback_data='promo')],[InlineKeyboardButton(text='⬅️ Назад',callback_data='home')]]))
    if d=='daily': return await claim_daily(call)
    if d=='sub': return await subscription_claim(call,bot)
    if d=='promo': ADMIN_STATE[uid]='promo_use'; return await edit(call,'🎫 Пришли промокод сообщением.',back('bonus'))
    if d=='donate': return await edit(call,'💳 <b>ДОНАТ ЗА TELEGRAM STARS</b>\n\nВыбери пакет:',InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text='50 ⭐ → 5 000 000',callback_data='stars:50')],[InlineKeyboardButton(text='100 ⭐ → 11 000 000',callback_data='stars:100')],[InlineKeyboardButton(text='500 ⭐ → 100 000 000',callback_data='stars:500')],[InlineKeyboardButton(text='⬅️ Назад',callback_data='home')]]))
    if d.startswith('stars:'): return await create_stars_invoice(call,bot,int(d.split(':')[1]))
    if d=='profile':
        u=await user(uid); return await edit(call,f'👤 <b>ПРОФИЛЬ</b>\n\nID: <code>{uid}</code>\nБаланс: <b>{money(u["balance"])}</b>\nФерма: <b>{u["farm_level"]}/10</b>\nПобед: <b>{u["attacks_won"]}</b>\nПоражений: <b>{u["attacks_lost"]}</b>',back('home'))
    if d=='attack': return await attack_menu(call)
    if d.startswith('target:'): return await do_attack(call,int(d.split(':')[1]))
    if d=='top':
        rows=await top_users(); text='🏆 <b>ТОП ИГРОКОВ</b>\n\n';
        for i,r in enumerate(rows,1): text+=f"{i}. {'@'+r['username'] if r['username'] else r['user_id']} — <b>{money(r['balance'])}</b>\n"
        return await edit(call,text,back('home'))
    if d=='help': return await edit(call,'ℹ️ <b>ПОМОЩЬ</b>\n\n🏭 Развивай ферму и оплачивай налог.\n🛒 Покупай войска.\n⚔️ Атакуй игроков раз в час.\n💰 За уничтожение техники предусмотрена награда 5% от её цены.\n🎁 Забирай бонусы.\n💳 Пополняй баланс за Telegram Stars.\n\nВсе функции находятся внутри меню /start.',back('home'))
    if d=='admin' and uid==ADMIN_ID: return await edit(call,'⚙️ <b>АДМИН-ПАНЕЛЬ</b>\n\nВсе управление через кнопки.',admin_kb())
    if d.startswith('a_'): return await admin_action(call,d)
    if d=='admin': return await call.answer('Нет доступа',show_alert=True)
    await call.answer()


async def pre_checkout(q: PreCheckoutQuery):
    if not q.invoice_payload.startswith('donate:'): return await q.answer(ok=False,error_message='Неизвестный платёж')
    stars=int(q.invoice_payload.split(':')[1])
    if stars not in DONATIONS or q.currency!='XTR' or q.total_amount!=stars: return await q.answer(ok=False,error_message='Параметры платежа не совпадают')
    await q.answer(ok=True)


async def successful_payment(message: Message):
    p=message.successful_payment
    if not p.invoice_payload.startswith('donate:'): return
    stars=int(p.invoice_payload.split(':')[1]); amount=DONATIONS.get(stars,0)
    db=await connect(); await db.execute('UPDATE users SET balance=balance+? WHERE user_id=?',(amount,message.from_user.id)); await db.commit(); await db.close()
    await message.answer(f'✅ Оплата получена!\n💰 Начислено: <b>{money(amount)}</b>.',parse_mode='HTML',reply_markup=home_kb(message.from_user.id))


async def message_handler(message: Message, bot: Bot):
    if await admin_message(message,bot): return
    if message.from_user.id in ADMIN_STATE and ADMIN_STATE[message.from_user.id]=='promo_use':
        ADMIN_STATE.pop(message.from_user.id,None); return await promo_use_fake(message)


async def promo_use_fake(message):
    # Kept separate so the same state machine works for normal user messages.
    uid=message.from_user.id; code=message.text.strip().upper(); db=await connect(); cur=await db.execute('SELECT * FROM promos WHERE code=?',(code,)); p=await cur.fetchone()
    if not p: await db.close(); return await message.answer('❌ Промокод не найден.',reply_markup=home_kb(uid))
    cur=await db.execute('SELECT 1 FROM promo_uses WHERE code=? AND user_id=?',(code,uid)); used=await cur.fetchone()
    if used or p['uses']>=p['max_uses']: await db.close(); return await message.answer('❌ Промокод уже использован или закончился.',reply_markup=home_kb(uid))
    await db.execute('INSERT INTO promo_uses(code,user_id) VALUES(?,?)',(code,uid)); await db.execute('UPDATE promos SET uses=uses+1 WHERE code=?',(code,)); await db.execute('UPDATE users SET balance=balance+? WHERE user_id=?',(p['amount'],uid)); await db.commit(); await db.close(); await message.answer(f"🎫 Активировано: <b>+{money(p['amount'])}</b>",parse_mode='HTML',reply_markup=home_kb(uid))


async def main():
    if not BOT_TOKEN: raise RuntimeError('BOT_TOKEN не задан в .env')
    await init_db(); bot=Bot(BOT_TOKEN); dp=Dispatcher()
    dp.message.register(cmd_start,CommandStart())
    dp.pre_checkout_query.register(pre_checkout)
    dp.message.register(successful_payment,F.successful_payment)
    dp.message.register(message_handler)
    dp.callback_query.register(callbacks,F.data)
    await dp.start_polling(bot)


if __name__=='__main__': asyncio.run(main())
