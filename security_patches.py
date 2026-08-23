import asyncio


async def install(botmod):
    """Defensive wrappers for economy, admin, and battle handlers."""
    original_callback = botmod.callback
    original_handle = botmod.handle_text
    locks = {}
    battle_locks = {}

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
                return await original_callback(c, bot)

        if data.startswith('target:'):
            try:
                target_id = int(data.split(':', 1)[1])
            except (ValueError, IndexError):
                return await c.answer('Некорректная цель.', show_alert=True)
            for b in botmod.BATTLES.values():
                if uid in (b['attacker'], b['defender']) or target_id in (b['attacker'], b['defender']):
                    return await c.answer('❌ Один из игроков уже участвует в другом бою.', show_alert=True)
            async with user_lock(uid):
                return await original_callback(c, bot)

        if data.startswith('bconfirm:'):
            try:
                bid = int(data.split(':', 1)[1])
            except (ValueError, IndexError):
                return await c.answer('Некорректный бой.', show_alert=True)
            async with battle_lock(bid):
                return await original_callback(c, bot)

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

        # The original UI had buttons for adding/removing admins but no text-state handler.
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
