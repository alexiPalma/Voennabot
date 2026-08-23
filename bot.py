import asyncio
import os
import random
from datetime import datetime, timedelta, timezone

import aiosqlite
from aiogram import Bot, Dispatcher, F
from aiogram.filters import CommandStart
from aiogram.types import CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup, Message
from dotenv import load_dotenv

load_dotenv()
TOKEN = os.getenv("BOT_TOKEN", "")
ADMIN_ID = int(os.getenv("ADMIN_ID", "0"))
DB = "voennabot.db"

FARMS = {
    1: (15_000, 0), 2: (36_000, 900_000), 3: (50_000, 1_000_000),
    4: (50_000, 2_000_000), 5: (100_000, 3_000_000), 6: (140_000, 6_000_000),
    7: (220_000, 9_000_000), 8: (333_000, 11_000_000), 9: (777_000, 18_000_000),
    10: (899_000, 30_000_000),
}
UNITS = {
    "soldier": ("🪖 Пехота", 20_000), "drone": ("🛩 БПЛА", 120_000),
    "interceptor": ("🎯 Дрон-перехватчик", 4_000), "bmp": ("🚙 БМП", 1_000_000),
    "tank": ("🛡 Танк", 3_000_000), "helicopter": ("🚁 Вертолёт", 4_000_000),
    "plane": ("✈️ Самолёт", 6_000_000), "missile": ("🚀 Ракета", 20_000_000),
}

async def db():
    conn = await aiosqlite.connect(DB)
    conn.row_factory = aiosqlite.Row
    await conn.execute("""CREATE TABLE IF NOT EXISTS users(
        user_id INTEGER PRIMARY KEY, username TEXT, balance INTEGER DEFAULT 0,
        farm_level INTEGER DEFAULT 1, tax INTEGER DEFAULT 0, last_payout TEXT,
        daily_claim TEXT, sub_claim INTEGER DEFAULT 0,
        soldier INTEGER DEFAULT 0, drone INTEGER DEFAULT 0, interceptor INTEGER DEFAULT 0,
        bmp INTEGER DEFAULT 0, tank INTEGER DEFAULT 0, helicopter INTEGER DEFAULT 0,
        plane INTEGER DEFAULT 0, missile INTEGER DEFAULT 0, last_attack TEXT)""")
    await conn.commit()
    return conn

async def ensure_user(user_id: int, username: str | None):
    conn = await db()
    await conn.execute("INSERT OR IGNORE INTO users(user_id,username,last_payout) VALUES(?,?,?)", (user_id, username or "", datetime.now(timezone.utc).isoformat()))
    await conn.execute("UPDATE users SET username=? WHERE user_id=?", (username or "", user_id))
    await conn.commit()
    await conn.close()

async def get_user(user_id):
    conn = await db(); cur = await conn.execute("SELECT * FROM users WHERE user_id=?", (user_id,)); row = await cur.fetchone(); await conn.close(); return row

async def change_balance(user_id, amount):
    conn = await db(); await conn.execute("UPDATE users SET balance=balance+? WHERE user_id=?", (amount, user_id)); await conn.commit(); await conn.close()

def money(n): return f"{n:,}".replace(",", " ")

def main_menu(admin=False):
    rows = [
        [InlineKeyboardButton(text="🏭 Ферма", callback_data="farm"), InlineKeyboardButton(text="🪖 Армия", callback_data="army")],
        [InlineKeyboardButton(text="🛒 Магазин", callback_data="shop"), InlineKeyboardButton(text="⚔️ Атака", callback_data="attack")],
        [InlineKeyboardButton(text="🎁 Бонус", callback_data="bonus"), InlineKeyboardButton(text="💳 Донат", callback_data="donate")],
        [InlineKeyboardButton(text="👤 Профиль", callback_data="profile"), InlineKeyboardButton(text="🏆 Топ", callback_data="top")],
        [InlineKeyboardButton(text="ℹ️ Помощь", callback_data="help")],
    ]
    if admin: rows.append([InlineKeyboardButton(text="⚙️ Админ-панель", callback_data="admin")])
    return InlineKeyboardMarkup(inline_keyboard=rows)

def back(): return InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="⬅️ Назад", callback_data="home")]])

def admin_menu():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="👥 Пользователи", callback_data="adm_users"), InlineKeyboardButton(text="💰 Экономика", callback_data="adm_economy")],
        [InlineKeyboardButton(text="🏭 Фермы", callback_data="adm_farms"), InlineKeyboardButton(text="🪖 Армия", callback_data="adm_army")],
        [InlineKeyboardButton(text="⚔️ Бои", callback_data="adm_battles"), InlineKeyboardButton(text="🎁 Бонусы", callback_data="adm_bonus")],
        [InlineKeyboardButton(text="💳 Донат", callback_data="adm_donate"), InlineKeyboardButton(text="📢 Рассылка", callback_data="adm_broadcast")],
        [InlineKeyboardButton(text="🎫 Промокоды", callback_data="adm_promo")],
        [InlineKeyboardButton(text="⬅️ Главное меню", callback_data="home")],
    ])

async def home_text(uid):
    u = await get_user(uid)
    return f"🪖 <b>ВОЕННАЯ СТРАТЕГИЯ</b>\n\n💰 Баланс: <b>{money(u['balance'])}</b>\n🏭 Ферма: <b>{u['farm_level']} ур.</b>\n💸 Налог: <b>{money(u['tax'])}</b>\n\nВыбери раздел:"

async def cmd_start(message: Message):
    await ensure_user(message.from_user.id, message.from_user.username)
    await message.answer(await home_text(message.from_user.id), reply_markup=main_menu(message.from_user.id == ADMIN_ID), parse_mode="HTML")

async def cb(call: CallbackQuery):
    uid = call.from_user.id
    await ensure_user(uid, call.from_user.username)
    data = call.data
    if data == "home": text, kb = await home_text(uid), main_menu(uid == ADMIN_ID)
    elif data == "farm":
        u = await get_user(uid); income, cost = FARMS[u['farm_level']]
        text = f"🏭 <b>ФЕРМА</b>\n\nУровень: <b>{u['farm_level']}/10</b>\nДоход в час: <b>{money(income)}</b>\nТекущий налог: <b>{money(u['tax'])}</b>\n\nНалог оплачивается для продолжения выплат."
        kb = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="💸 Получить выплату", callback_data="payout"), InlineKeyboardButton(text="⬆️ Улучшить", callback_data="upgrade")],[InlineKeyboardButton(text="⬅️ Назад", callback_data="home")]])
    elif data == "payout":
        u = await get_user(uid); now = datetime.now(timezone.utc); last = datetime.fromisoformat(u['last_payout'])
        if u['tax'] > 0: text, kb = "❌ Сначала оплатите налог фермы.", back()
        elif now - last < timedelta(hours=1): text, kb = f"⏳ Следующая выплата через {(timedelta(hours=1)-(now-last)).seconds//60} мин.", back()
        else:
            income = FARMS[u['farm_level']][0]; conn=await db(); await conn.execute("UPDATE users SET balance=balance+?,last_payout=?,tax=? WHERE user_id=?", (income, now.isoformat(), random.randint(20_000,50_000), uid)); await conn.commit(); await conn.close(); text, kb = f"✅ Получено <b>{money(income)}</b>!", back()
    elif data == "upgrade":
        u=await get_user(uid); lvl=u['farm_level']
        if lvl >= 10: text, kb = "🏭 Ферма уже максимального 10 уровня.", back()
        else:
            cost=FARMS[lvl+1][1]
            if u['balance'] < cost: text, kb = f"❌ Нужно {money(cost)}, у тебя {money(u['balance'])}.", back()
            else:
                conn=await db(); await conn.execute("UPDATE users SET balance=balance-?,farm_level=? WHERE user_id=?",(cost,lvl+1,uid)); await conn.commit(); await conn.close(); text, kb=f"⬆️ Ферма улучшена до <b>{lvl+1} уровня</b>!",back()
    elif data == "army":
        u=await get_user(uid); lines=["🪖 <b>АРМИЯ</b>"]+[f"{name}: <b>{u[key]}</b>" for key,(name,_) in UNITS.items()]
        text, kb="\n".join(lines), back()
    elif data == "shop":
        rows=[]
        for key,(name,price) in UNITS.items(): rows.append([InlineKeyboardButton(text=f"{name} — {money(price)}",callback_data=f"buy:{key}")])
        rows.append([InlineKeyboardButton(text="⬅️ Назад",callback_data="home")]); text, kb="🛒 <b>МАГАЗИН АРМИИ</b>\n\nВыбери, что купить:",InlineKeyboardMarkup(inline_keyboard=rows)
    elif data.startswith("buy:"):
        key=data.split(":",1)[1]; name,price=UNITS[key]; u=await get_user(uid)
        if u['balance']<price: text,kb=f"❌ Недостаточно денег. Нужно {money(price)}.",back()
        else:
            conn=await db(); await conn.execute(f"UPDATE users SET balance=balance-?,{key}={key}+1 WHERE user_id=?",(price,uid)); await conn.commit(); await conn.close(); text,kb=f"✅ Куплено: {name}\n💰 Списано: {money(price)}",back()
    elif data == "bonus":
        u=await get_user(uid); today=datetime.now(timezone.utc).date().isoformat(); text="🎁 <b>БОНУСЫ</b>\n\nЕжедневный бонус: <b>500 000</b>\nБонус за подписку: <b>1 500 000</b>"; kb=InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="🎁 Забрать 500 000",callback_data="daily"),InlineKeyboardButton(text="📢 Бонус за подписку",callback_data="sub")],[InlineKeyboardButton(text="⬅️ Назад",callback_data="home")]])
    elif data == "daily":
        u=await get_user(uid); today=datetime.now(timezone.utc).date().isoformat()
        if u['daily_claim']==today: text,kb="❌ Сегодня бонус уже получен.",back()
        else:
            conn=await db(); await conn.execute("UPDATE users SET balance=balance+500000,daily_claim=? WHERE user_id=?",(today,uid)); await conn.commit(); await conn.close(); text,kb="🎁 Получено <b>500 000</b>!",back()
    elif data == "donate": text,kb="💳 <b>ДОНАТ</b>\n\n50 ⭐ — 5 000 000\n100 ⭐ — 11 000 000\n500 ⭐ — 100 000 000\n\nОплата Stars подключается через Telegram Payments.",back()
    elif data == "profile":
        u=await get_user(uid); text,kb=f"👤 <b>ПРОФИЛЬ</b>\n\nID: <code>{uid}</code>\nБаланс: <b>{money(u['balance'])}</b>\nФерма: <b>{u['farm_level']}/10</b>",back()
    elif data == "attack": text,kb="⚔️ <b>АТАКА</b>\n\nЗдесь будет выбор противника и расчёт боя по заданным тобой правилам.\n\n⏱ Ограничение: 1 атака в час.",back()
    elif data == "top": text,kb="🏆 <b>ТОП</b>\n\nТаблица лидеров будет формироваться по балансу и армии.",back()
    elif data == "help": text,kb="ℹ️ <b>ПОМОЩЬ</b>\n\nРазвивай ферму, покупай армию и атакуй других игроков. Все функции доступны через меню /start.",back()
    elif data == "admin" and uid == ADMIN_ID: text,kb="⚙️ <b>АДМИН-ПАНЕЛЬ</b>\n\nУправление ботом через кнопки.",admin_menu()
    elif data.startswith("adm_") and uid == ADMIN_ID: text,kb=f"⚙️ <b>РАЗДЕЛ АДМИН-ПАНЕЛИ</b>\n\nРаздел: <code>{data[4:]}</code>\n\nЗдесь подключается управление соответствующими настройками.",admin_menu()
    else: text,kb="❌ Нет доступа.",back()
    await call.message.edit_text(text,reply_markup=kb,parse_mode="HTML"); await call.answer()

async def main():
    if not TOKEN: raise RuntimeError("BOT_TOKEN is not set")
    bot=Bot(TOKEN); dp=Dispatcher(); dp.message.register(cmd_start,CommandStart()); dp.callback_query.register(cb,F.data); await db(); await dp.start_polling(bot)

if __name__ == "__main__": asyncio.run(main())
