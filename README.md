# Voennabot

Telegram military strategy game.

## Run

1. Copy `.env.example` to `.env`.
2. Set `BOT_TOKEN` and `ADMIN_ID`.
3. Install dependencies: `pip install -r requirements.txt`.
4. Start: `python bot.py`.

The bot is designed around `/start` as the central interface. Main functions are opened through inline buttons rather than a large set of commands.

## Current foundation

- SQLite persistence
- Farm levels 1-10
- Hourly farm payouts
- Farm tax state
- Daily bonus
- Subscription bonus placeholder
- Army inventory and shop
- Admin-panel navigation
- Donation price display
- Main menu/profile/help/top/attack placeholders

Combat calculations and Telegram Stars payment should be implemented after the final battle rules are locked.
