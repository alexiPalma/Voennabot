import random
from config import UNITS

def roll(p): return random.random() < p
def destroy(s,u,n):
    n=min(max(0,int(n)),s.get(u,0)); s[u]=s.get(u,0)-n; return n

def resolve(attacker, defender):
    a={k:int(attacker[k]) for k in UNITS}; d={k:int(defender[k]) for k in UNITS}; events=[]
    # Missiles
    for _ in range(a['missile']):
        targets=[('soldier',350),('bmp',22),('tank',random.randint(7,10))]
        if d['soldier'] or d['bmp'] or d['tank']:
            available=[x for x in targets if d[x[0]]>0]; unit,n=random.choice(available); killed=destroy(d,unit,n); events.append(f'🚀 Ракета уничтожила {killed} {UNITS[unit]["title"]}')
        if d['helicopter'] and roll(.70): destroy(d,'helicopter',1); events.append('🚀 Ракета сбила вертолёт — 70%')
    # Planes
    for _ in range(a['plane']):
        if d['plane'] and roll(.45): destroy(d,'plane',1); events.append('✈️ Самолёт сбил самолёт — 45%'); continue
        if not roll(.70): events.append('✈️ Самолёт не прошёл удар — 30%'); continue
        choices=[x for x in [('soldier',150),('bmp',18),('tank',6),('drone',50),('helicopter',1)] if d[x[0]]>0]
        if choices:
            unit,n=random.choice(choices); killed=destroy(d,unit,n); events.append(f'✈️ Самолёт уничтожил {killed} {UNITS[unit]["title"]} — 70%')
    # Helicopters
    for _ in range(a['helicopter']):
        if d['helicopter'] and roll(.70): destroy(d,'helicopter',1); events.append('🚁 Вертолёт сбил вертолёт — 70%'); continue
        choices=[x for x in [('soldier',80),('bmp',10),('tank',3),('drone',20)] if d[x[0]]>0]
        if choices:
            unit,n=random.choice(choices); killed=destroy(d,unit,n); events.append(f'🚁 Вертолёт уничтожил {killed} {UNITS[unit]["title"]}')
    # Tanks
    for _ in range(a['tank']):
        if d['tank'] and roll(.70): destroy(d,'tank',1); events.append('🛡 Танк уничтожил танк — 70%'); continue
        if d['bmp']: destroy(d,'bmp',2); events.append('🛡 Танк уничтожил до 2 БМП')
        elif d['soldier']: destroy(d,'soldier',40); events.append('🛡 Танк уничтожил до 40 пехоты')
    # BMP
    for _ in range(a['bmp']//3):
        if d['tank'] and roll(.65): destroy(d,'tank',1); events.append('🚙 3 БМП контрят танк — 65%')
    for _ in range(a['bmp']):
        if d['bmp'] and roll(.90): destroy(d,'bmp',1); events.append('🚙 БМП контрит БМП — 90%')
        elif d['soldier']: destroy(d,'soldier',10); events.append('🚙 БМП уничтожила до 10 пехоты')
    # Drones: 2 drones counter 15 infantry; 30 drones counter helicopter at 80%; drones never counter drones.
    for _ in range(a['drone']//2):
        if d['soldier']: destroy(d,'soldier',15); events.append('🛩 2 БПЛА уничтожили до 15 пехоты')
    for _ in range(a['drone']//30):
        if d['helicopter'] and roll(.80): destroy(d,'helicopter',1); events.append('🛩 30 БПЛА сбили вертолёт — 80%')
    # Interceptors
    for _ in range(a['interceptor']):
        if d['drone'] and roll(.05): destroy(d,'drone',1); events.append('🎯 Перехватчик сбил БПЛА — 5%')
    # Infantry: only infantry directly, plus 7 infantry -> drone at 70%.
    for _ in range(a['soldier']//7):
        if d['drone'] and roll(.70): destroy(d,'drone',1); events.append('🪖 7 пехотинцев сбили БПЛА — 70%')
    if a['soldier'] and d['soldier']:
        n=min(a['soldier'],d['soldier']); destroy(d,'soldier',n); events.append(f'🪖 Пехота против пехоты: {n}')
    # 15 infantry -> 1 BMP as the stated infantry counter ratio.
    for _ in range(a['soldier']//15):
        if d['bmp']: destroy(d,'bmp',1); events.append('🪖 15 пехотинцев уничтожили БМП')
    # Artillery is included in army composition and losses; its combat effects are intentionally not invented until a damage rule is supplied.
    combat_d=sum(d[k] for k in UNITS if k!='artillery'); combat_a=sum(a[k] for k in UNITS if k!='artillery')
    winner='attacker' if combat_d==0 and combat_a>0 else ('defender' if combat_a==0 and combat_d>0 else ('attacker' if combat_a>combat_d else 'defender'))
    return a,d,winner,events
