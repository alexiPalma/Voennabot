import os
from dotenv import load_dotenv

load_dotenv()
BOT_TOKEN = os.getenv('BOT_TOKEN', '')
ADMIN_ID = int(os.getenv('ADMIN_ID', '0'))
CHANNEL_USERNAME = os.getenv('CHANNEL_USERNAME', '').strip()
DB_PATH = os.getenv('DB_PATH', 'voennabot.db')

FARMS = {
    1: {'income': 15_000, 'upgrade': 0},
    2: {'income': 36_000, 'upgrade': 900_000},
    3: {'income': 50_000, 'upgrade': 1_000_000},
    4: {'income': 50_000, 'upgrade': 2_000_000},
    5: {'income': 100_000, 'upgrade': 3_000_000},
    6: {'income': 140_000, 'upgrade': 6_000_000},
    7: {'income': 220_000, 'upgrade': 9_000_000},
    8: {'income': 333_000, 'upgrade': 11_000_000},
    9: {'income': 777_000, 'upgrade': 18_000_000},
    10: {'income': 899_000, 'upgrade': 30_000_000},
}

UNITS = {
    'soldier': {'title': '🪖 Пехота', 'price': 20_000, 'loss': 1_000},
    'drone': {'title': '🛩 БПЛА', 'price': 120_000, 'loss': 20_000},
    'interceptor': {'title': '🎯 Дрон-перехватчик', 'price': 4_000, 'loss': 4_000},
    'bmp': {'title': '🚙 БМП', 'price': 1_000_000, 'loss': 55_000},
    'tank': {'title': '🛡 Танк', 'price': 3_000_000, 'loss': 100_000},
    'helicopter': {'title': '🚁 Вертолёт', 'price': 4_000_000, 'loss': 100_000},
    'plane': {'title': '✈️ Самолёт', 'price': 6_000_000, 'loss': 500_000},
    'missile': {'title': '🚀 Ракета', 'price': 20_000_000, 'loss': 1_000_000},
}

DONATIONS = {50: 5_000_000, 100: 11_000_000, 500: 100_000_000}
DAILY_BONUS = 500_000
SUB_BONUS = 1_500_000
TAX_INCREMENT_MIN = 20_000
TAX_INCREMENT_MAX = 50_000
TAX_MAX = 1_000_000
ATTACK_COOLDOWN_HOURS = 1
