from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

EARN_TYPES = {
    'boost': ('🚀 Буст канала', 'earn_boost'),
    'channel': ('📢 Подписка на канал', 'earn_channel'),
    'group': ('👥 Подписка на группу', 'earn_group'),
}

# Формат команд администратора:
# /addboost https://t.me/+... 150000
# /addchannel https://t.me/... 150000
# /addgroup https://t.me/... 150000
# Сумма всегда хранится как целое число валюты.

def earn_admin_keyboard():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text='🚀 Буст канала', callback_data='earn_add:boost')],
        [InlineKeyboardButton(text='📢 Подписка на канал', callback_data='earn_add:channel')],
        [InlineKeyboardButton(text='👥 Подписка на группу', callback_data='earn_add:group')],
        [InlineKeyboardButton(text='📋 Список заданий', callback_data='earn_list')],
        [InlineKeyboardButton(text='⬅️ Назад', callback_data='admin')],
    ])


def earn_player_keyboard(items):
    rows=[]
    for item in items:
        kind=item['kind']; label=item['title']; reward=item['reward']
        rows.append([InlineKeyboardButton(text=f'{label} · +${reward:,}'.replace(',', ' '), url=item['url'])])
        rows.append([InlineKeyboardButton(text='✅ Проверить выполнение', callback_data=f'earn_check:{kind}:{item["id"]}')])
    return InlineKeyboardMarkup(inline_keyboard=rows or [[InlineKeyboardButton(text='⬅️ Назад', callback_data='home')]])


def parse_earn_command(text, command):
    parts=text.strip().split()
    if len(parts)!=3 or parts[0].lower()!=command:
        return None, 'Формат: '+command+' <ссылка> <сумма>'
    url=parts[1].strip()
    if not (url.startswith('https://t.me/') or url.startswith('http://t.me/')):
        return None, 'Ссылка должна быть ссылкой Telegram: https://t.me/...'
    try: reward=int(parts[2])
    except ValueError: return None, 'Сумма должна быть целым числом.'
    if reward<=0 or reward>2_000_000_000: return None, 'Некорректная сумма награды.'
    return (url,reward), None
