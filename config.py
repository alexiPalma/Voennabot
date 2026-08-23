import os
from dotenv import load_dotenv
load_dotenv()
BOT_TOKEN=os.getenv('BOT_TOKEN','')
ADMIN_ID=int(os.getenv('ADMIN_ID','0'))
DB_PATH=os.getenv('DB_PATH','voennabot.db')
FARMS={1:{'income':15000,'upgrade':0},2:{'income':36000,'upgrade':900000},3:{'income':50000,'upgrade':1000000},4:{'income':50000,'upgrade':2000000},5:{'income':100000,'upgrade':3000000},6:{'income':140000,'upgrade':6000000},7:{'income':220000,'upgrade':9000000},8:{'income':333000,'upgrade':11000000},9:{'income':777000,'upgrade':18000000},10:{'income':899000,'upgrade':30000000}}
UNITS={'soldier':{'title':'🪖 Пехота','price':20000,'loss':1000},'drone':{'title':'🛩 БПЛА','price':120000,'loss':20000},'interceptor':{'title':'🎯 Дрон-перехватчик','price':4000,'loss':4000},'bmp':{'title':'🚙 БМП','price':1000000,'loss':55000},'tank':{'title':'🛡 Танк','price':3000000,'loss':100000},'helicopter':{'title':'🚁 Вертолёт','price':4000000,'loss':100000},'plane':{'title':'✈️ Самолёт','price':6000000,'loss':500000},'missile':{'title':'🚀 Ракета','price':20000000,'loss':1000000}}
DONATIONS={50:5000000,100:11000000,500:100000000}
DAILY_BONUS=500000
SUB_BONUS=1500000
TAX_INCREMENT_MIN=20000
TAX_INCREMENT_MAX=50000
TAX_MAX=1000000
ATTACK_COOLDOWN_HOURS=1
