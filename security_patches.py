import asyncio
from datetime import datetime, timezone


async def install(botmod):
    """Defensive wrappers for economy, admin, and battle handlers."""
    original_callback = botmod.callback
    original_handle = botmod.handle_text
    locks = {}
    battle_locks = {}
    battle_creation_lock = asyncio.Lock()

    async def sync_runtime_settings():
        # The original UI imports config objects once. Mutate those objects in place so
        # admin-panel changes immediately affect the running bot without a restart.
        for level in range(1, 11):
            income = await botmod.get_int(f'farm_{level}_income')
            botmod.FARMS[level]['income'] = income
            if level >= 2:
                botmod.FARMS[level]['upgrade'] = await botmod.get_int(f'farm_{level}_upgrade')
        for key in botmod.UNITS:
            setting_key = f'price_{key}'
            if await botmod.setting(setting_key) is not None:
                botmod.UNITS[key]['price'] = await botmod.get_int(setting_key)
        for stars in (50, 100, 500):
            value = await botmod.setting(f'donate_{stars}')
            if value is not None:
                botmod.DONATIONS[stars] = int(value)

    def user_lock(uid):
        return locks.setdefault(uid, asyncio.Lock())

    def battle_lock(bid):
        return battle_locks.setdefault(bid, asyncio.Lock())

    async def secure_callback(c, bot):
        uid = c.from_user.id
        data = c.data or ''
        protected = data in {'daily', 'sub', 'payout', 'paytax', 'upgrade'} or data.startswith(('buyok:', 'case:'))
        if protected:
            async with user_lock(uid):
                await sync_runtime_settings()
                return await original_callback(c, bot)

        if data.startswith('target:'):
            try:
                target_id = int(data.split(':', 1)[1])
            except (ValueError, IndexError):
                return await c.answer('Некорректная цель.', show_alert=True)
            async with battle_creation_lock:
                for bid, b in list(botmod.BATTLES.items()):
                    created = b.get('created_at', 0)
                    if created and (datetime.now(timezone.utc).timestamp() - created) > 600:
                        botmod.BATTLES.pop(bid, None)
                        continue
                    if uid in (b['attacker'], b['defender']) or target_id in (b['attacker'], b['defender']):
                        return await c.answer('❌ Один из игроков уже участвует в другом бою.', show_alert=True)

                attacker = await botmod.user(uid)
                if attacker and attacker['last_attack']:
                    try:
                        cooldown = await botmod.get_int('attack_cooldown_minutes')
                        elapsed = (datetime.now(timezone.utc) - datetime.fromisoformat(attacker['last_attack'])).total_seconds()
                        if elapsed < cooldown * 60:
                            left = int(cooldown * 60 - elapsed)
                            return await c.answer(f'⏳ Следующая атака через {left // 60} мин.', show_alert=True)
                    except (ValueError, TypeError):
                        pass

                before = set(botmod.BATTLES)
                async with user_lock(uid):
                    result = await original_callback(c, bot)
                for bid in set(botmod.BATTLES) - before:
                    botmod.BATTLES[bid]['created_at'] = datetime.now(timezone.utc).timestamp()
                return result

        if data.startswith('bconfirm:'):
            try:
                bid = int(data.split(':', 1)[1])
            except (ValueError, IndexError):
                return await c.answer('Некорректный бой.', show_alert=True)
            async with battle_lock(bid):
                b = botmod.BATTLES.get(bid)
                if not b:
                    return await c.answer('Бой уже завершён или отменён.', show_alert=True)
                if b.get('created_at') and datetime.now(timezone.utc).timestamp() - b['created_at'] > 600:
                    botmod.BATTLES.pop(bid, None)
                    return await c.answer('⏱ Бой просрочен. Создайте новый вызов.', show_alert=True)
                attacker_id = b['attacker']
                result = await original_callback(c, bot)
                if bid not in botmod.BATTLES:
                    db = await botmod.connect()
                    await db.execute('UPDATE users SET last_attack=? WHERE user_id=?', (botmod.now().isoformat(), attacker_id))
                    await db.commit()
                    await db.close()
                return result

        await sync_runtime_settings()
        return await original_callback(c, bot)

    async def secure_handle(message, bot):
        text = (message.text or '').strip()
        uid = message.from_user.id
        state = botmod.STATE.get(uid)

        if text.startswith(('/givepehot ', '/takepehot ')):
            parts = text.split()
            if len(parts) == 4:
                try:
                    amount = int(parts[3])
                except ValueError:
                    amount = 0
                if amount <= 0:
                    return await message.answer('❌ Количество должно быть положительным числом.')

        if text.startswith('/givecash '):
            parts = text.split()
            if len(parts) == 3:
                try:
                    amount = int(parts[2])
                except ValueError:
                    amount = 0
                if amount <= 0:
                    return await message.answer('❌ Сумма должна быть положительным числом.')

        if text.startswith('/newpromo '):
            parts = text.split()
            if len(parts) == 4:
                try:
                    amount, uses = int(parts[2]), int(parts[3])
                except ValueError:
                    return await message.answer('❌ Сумма и количество использований должны быть числами.')
                if amount <= 0 or uses <= 0 or amount > 10**15 or uses > 10**9:
                    return await message.answer('❌ Некорректная сумма или лимит использований.')

        if state and state[0] in {'admin_add', 'admin_del'}:
            if not await botmod.admin_check(uid):
                botmod.STATE.pop(uid, None)
                return await message.answer('❌ Нет доступа.')
            try:
                target = int(text)
            except ValueError:
                return await message.answer('❌ Нужен Telegram ID числом.')
            if target <= 0:
                return await message.answer('❌ Некорректный Telegram ID.')
            db = await botmod.connect()
            if state[0] == 'admin_add':
                await db.execute('INSERT OR IGNORE INTO admins(user_id) VALUES(?)', (target,))
                result = '✅ Администратор добавлен.'
            else:
                if target == botmod.ADMIN_ID:
                    await db.close()
                    botmod.STATE.pop(uid, None)
                    return await message.answer('❌ Владельца удалить нельзя.')
                await db.execute('DELETE FROM admins WHERE user_id=?', (target,))
                result = '✅ Администратор удалён.'
            await db.commit()
            await db.close()
            botmod.STATE.pop(uid, None)
            return await message.answer(result)

        if state and state[0] == 'setting':
            key = state[1]
            numeric = {
                'daily_bonus','subscription_bonus','tax_increment_min','tax_increment_max','tax_max',
                'attack_cooldown_minutes','loss_percent','kill_reward_percent','loser_reward_percent',
                'donate_50','donate_100','donate_500','currency_rate',
                *{f'farm_{i}_income' for i in range(1, 11)},
                *{f'farm_{i}_upgrade' for i in range(2, 11)},
                *{f'price_{k}' for k in botmod.UNITS},
            }
            if key in numeric:
                try:
                    value = int(text)
                except ValueError:
                    return await message.answer('❌ Здесь нужно целое число.')
                if value < 0 or value > 10**15:
                    return await message.answer('❌ Значение вне допустимого диапазона.')
                if key == 'attack_cooldown_minutes' and value < 1:
                    return await message.answer('❌ Кулдаун должен быть не меньше 1 минуты.')
                if key in {'loss_percent','kill_reward_percent','loser_reward_percent'} and value > 100:
                    return await message.answer('❌ Процент не может быть больше 100.')
            elif key == 'channel_username':
                if len(text) > 200 or ' ' in text or not text.startswith(('@', 'https://t.me/')):
                    return await message.answer('❌ Укажи @username канала или ссылку https://t.me/...')
            elif key == 'donate_contact' and len(text) > 200:
                return await message.answer('❌ Контакт слишком длинный.')

        return await original_handle(message, bot)

    botmod.callback = secure_callback
    botmod.handle_text = secure_handle
