# Voennabot

Telegram military strategy game. The player enters through `/start`; the rest of the game is operated with inline buttons.

## Run

1. Copy `.env.example` to `.env`.
2. Set `BOT_TOKEN`, `ADMIN_ID` and optionally `CHANNEL_USERNAME`.
3. Install dependencies: `pip install -r requirements.txt`.
4. Start: `python bot.py`.

## Included

- SQLite database with persistent users, army, farm, attacks, promos and battle log.
- Farm levels 1–10 with hourly income and tax blocking.
- Daily 500,000 bonus.
- 1,500,000 channel-subscription bonus with membership check.
- Army shop: infantry, UAVs, interceptor drones, IFVs, tanks, helicopters, aircraft and missiles.
- One-hour attack cooldown.
- Combat resolver with the supplied counter probabilities and unit relationships.
- Losing side loses 20% of its army; winner keeps its army.
- 5% reward based on the value of units lost by the losing side.
- Telegram Stars donation packages: 50 → 5,000,000; 100 → 11,000,000; 500 → 100,000,000.
- Pre-checkout and successful-payment handling for Stars.
- Inline-button admin panel: player lookup, money, army grants, reset, broadcast, promo codes, statistics, farm/battle/donation settings.
- No large command list: `/start` is the central entry point.

## Configuration

`.env.example` contains the required variables. The bot must have permission to check channel membership for the subscription reward.

## Game values

Prices and farm values are centralized in `config.py`, while battle rules are isolated in `combat.py`, so balance changes do not require rewriting the bot UI.
