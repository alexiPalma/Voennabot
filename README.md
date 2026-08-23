# Voennabot

Telegram military strategy game. The player enters through `/start`; the rest of the game is operated with inline buttons.

## Run

1. Copy `.env.example` to `.env`.
2. Set only `BOT_TOKEN` and `ADMIN_ID`.
3. Install dependencies: `pip install -r requirements.txt`.
4. Start the hardened launcher: `python run.py`.

## Included

- SQLite persistence for users, army, farms, promos, cases, messages and battle logs.
- Farm levels 1–10 with hourly income and tax blocking.
- Daily prize table with the configured probabilities.
- Channel-subscription reward configured from the admin panel.
- Army shop with quantity confirmation.
- Cases, including the 50-Star presidential case redirect to the donation screen.
- Symmetric combat resolver: both armies participate in combat.
- One active battle per player in the hardened runtime.
- Losing side loses the configured percentage of its army; winner keeps its army.
- Configurable winner/loser rewards.
- Inline-button admin panel with currency, bonuses, cases, promos, earnings, donation text, rules, admins, grants, broadcast, statistics, message editor, farms and battle settings.
- Database integrity guards against negative balances, negative army counts, invalid farm levels and invalid tax values.
- Runtime validation for admin amounts, settings and high-value actions.
- `/start` remains the central user entry point; the extra commands are restricted admin operations.

## Configuration

`.env` contains only technical secrets. The channel username, bonus values, donation contact and other game settings are stored in SQLite and edited from the admin panel.

The bot must have sufficient Telegram permissions to check channel membership for the subscription reward.

## Game values

Prices and farm values are centralized in `config.py`; battle rules are isolated in `combat.py`; runtime safety wrappers are in `security_patches.py` and are loaded by `run.py`.
