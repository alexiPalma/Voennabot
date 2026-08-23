import random
from config import UNITS

# A deterministic, transparent combat resolver based on the rules supplied for the game.
# It never creates units and only removes units that the defender/attacker actually owns.

def roll(p): return random.random() < p

def destroy(state, unit, amount):
    n=min(max(0,int(amount)), state.get(unit,0)); state[unit]-=n; return n

def resolve(attacker, defender):
    a={k:attacker[k] for k in UNITS}; d={k:defender[k] for k in UNITS}; events=[]

    # Missiles: one missile can hit the specified target groups. Each missile is consumed.
    missiles=destroy(a,'missile',a['missile'])
    for _ in range(missiles):
        # The game specifies alternatives; one missile chooses one primary ground target.
        target=random.choice(['soldier','bmp','tank'])
        if target=='soldier': killed=destroy(d,'soldier',350); events.append(f'🚀 Ракета уничтожила {killed} пехоты')
        elif target=='bmp': killed=destroy(d,'bmp',22); events.append(f'🚀 Ракета уничтожила {killed} БМП')
        else:
            killed=destroy(d,'tank',random.randint(7,10)); events.append(f'🚀 Ракета уничтожила {killed} танков')
        if d['helicopter'] and roll(.70): destroy(d,'helicopter',1); events.append('🚀 Ракета сбила вертолёт (70%)')

    # Planes: each plane attempts one listed strike. Plane-v-plane is a 45% counter.
    planes=destroy(a,'plane',a['plane'])
    for _ in range(planes):
        if d['plane'] and roll(.45): destroy(d,'plane',1); events.append('✈️ Самолёт сбил самолёт (45%)'); continue
        if not roll(.70): continue
        choices=[]
        if d['soldier']: choices.append(('soldier',150))
        if d['bmp']: choices.append(('bmp',18))
        if d['tank']: choices.append(('tank',6))
        if d['drone']: choices.append(('drone',50))
        if d['helicopter']: choices.append(('helicopter',1))
        if choices:
            unit,n=random.choice(choices); killed=destroy(d,unit,n); events.append(f'✈️ Самолёт уничтожил {killed} {UNITS[unit]["title"]} (70%)')

    # Helicopters: one helicopter chooses one of the listed targets.
    helis=destroy(a,'helicopter',a['helicopter'])
    for _ in range(helis):
        if d['helicopter'] and roll(.70): destroy(d,'helicopter',1); events.append('🚁 Вертолёт сбил вертолёт (70%)'); continue
        choices=[]
        if d['soldier']: choices.append(('soldier',80))
        if d['bmp']: choices.append(('bmp',10))
        if d['tank']: choices.append(('tank',3))
        if d['drone']: choices.append(('drone',20))
        if choices:
            unit,n=random.choice(choices); killed=destroy(d,unit,n); events.append(f'🚁 Вертолёт уничтожил {killed} {UNITS[unit]["title"]}')

    # Tanks: tank-v-tank 70%; otherwise tank attacks up to 2 BMP or 40 infantry.
    tanks=destroy(a,'tank',a['tank'])
    for _ in range(tanks):
        if d['tank'] and roll(.70): destroy(d,'tank',1); events.append('🛡 Танк уничтожил танк (70%)'); continue
        if d['bmp']: killed=destroy(d,'bmp',2); events.append(f'🛡 Танк уничтожил {killed} БМП')
        elif d['soldier']: killed=destroy(d,'soldier',40); events.append(f'🛡 Танк уничтожил {killed} пехоты')

    # BMPs: 90% BMP-v-BMP, and a 65% three-BMP attempt against one tank.
    bmps=destroy(a,'bmp',a['bmp'])
    groups=bmps//3
    for _ in range(groups):
        if d['tank'] and roll(.65): destroy(d,'tank',1); events.append('🚙 3 БМП уничтожили танк (65%)')
    for _ in range(bmps):
        if d['bmp'] and roll(.90): destroy(d,'bmp',1); events.append('🚙 БМП уничтожила БМП (90%)')
        elif d['soldier']: killed=destroy(d,'soldier',10); events.append(f'🚙 БМП уничтожила {killed} пехоты')

    # Drones: 30 drones vs helicopter at 80%; drones do not counter drones.
    drone_groups=a['drone']//30
    for _ in range(drone_groups):
        if d['helicopter'] and roll(.80): destroy(d,'helicopter',1); events.append('🛩 30 БПЛА сбили вертолёт (80%)')

    # Interceptors: each has 5% against one drone.
    ints=destroy(a,'interceptor',a['interceptor'])
    for _ in range(ints):
        if d['drone'] and roll(.05): destroy(d,'drone',1); events.append('🎯 Перехватчик сбил БПЛА (5%)')

    # Infantry: 7 infantry has 70% against one drone, and infantry only directly counters infantry.
    for _ in range(a['soldier']//7):
        if d['drone'] and roll(.70): destroy(d,'drone',1); events.append('🪖 7 пехотинцев сбили БПЛА (70%)')
    # Soldier-v-soldier is intentionally 1-for-1.
    if d['soldier'] and a['soldier']:
        killed=min(a['soldier'],d['soldier']); destroy(d,'soldier',killed); events.append(f'🪖 Пехота против пехоты: {killed} уничтожено')

    # 15 soldiers -> 1 BMP as a combat counter; apply remaining grouped infantry after direct infantry combat.
    for _ in range(a['soldier']//15):
        if d['bmp']: destroy(d,'bmp',1); events.append('🪖 15 пехотинцев уничтожили БМП')

    # Any attacker unit already consumed above is represented by the remaining a state.
    # Winner is based on whether the defender still has combat units.
    defender_left=sum(d.values()); attacker_left=sum(a.values())
    winner='attacker' if defender_left==0 and attacker_left>0 else ('defender' if attacker_left==0 and defender_left>0 else ('attacker' if attacker_left>defender_left else 'defender'))
    return a,d,winner,events
