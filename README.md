# Reverie — Discord Moderation Bot

Reverie is a modern moderation and utilities bot for Discord built on discord.py 2.x. It focuses on clean moderator workflows, robust logging, and actionable analytics. The project uses MongoDB for persistent data and SQLite (aiosqlite) to track voice activity.

## Highlights
- Slash-commands first, automatic tree sync on startup
- Role-based permission model (maps to guild roles, plus Admin override)
- Rich, consistent embeds and ephemeral responses
- Timed actions with automatic expiration handlers (mutes, bans, notifications)
- Message context menu for quick text-mute with screenshot capture
- Voice online tracking, daily and weekly stats, tops
- Moderator actions tracking (daily, weekly, monthly, per-moderator)
- Greeting messages in DMs and/or a guild channel
- Profile violation notifications with reminders to moderators

## Requirements
- Python 3.11+ (3.13 tested)
- MongoDB (local or remote)
- Discord bot application with Privileged Gateway Intents enabled (Presence, Members, Message Content if needed)

## Quick start
1) Clone and enter the project
2) Create a virtual environment and install dependencies
3) Configure environment variables
4) Run the bot

```bash
python -m venv .venv
. .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env   # Windows: copy .env.example .env
# Edit .env and set DISCORD_TOKEN and MONGO_URI
python main.py
```

## Configuration
- Environment variables (loaded via python-dotenv, see `.env.example`):
  - `DISCORD_TOKEN` — your bot token
  - `MONGO_URI` — MongoDB connection string (e.g. `mongodb://localhost:27017`)
- Intents: the bot requests `discord.Intents.all()`; ensure they are enabled in the Developer Portal and when inviting the bot.
- Optional: `config.py` contains constants (e.g., log channel name patterns) you can adapt for your server.

## Data storage
- MongoDB database `Reverie` (collections for actions, punishments, roles, notifications, greeting, etc.)
- SQLite file `online.sqlite` used for voice online tracking (auto-initialized)

## Commands overview (selected)
Below is a non-exhaustive list of public slash-commands discovered in the codebase. Many return ephemeral responses and use embeds.

Greeting
- `/greet` — show greeting status (admin)
- `/dm-greet toggle`, `/dm-greet set-message` — manage DM greetings (admin)
- `/guild-greet toggle`, `/guild-greet set-message`, `/guild-greet set-channel` — manage guild greetings (admin)

Profile notifications
- `/notify <user> <place>` — notify a user about a profile violation; logs and schedules a reminder for the moderator

Online and stats
- `/online <user> <date> <open-only>` — show daily voice online; supports autocomplete and access rules
- `/week-online <week> [user]` — weekly per-user voice online (MD+)
- `/online-top <year> <month> <open-only> [this-guild]` — monthly top online
- `/hassle` — displays online on Hassle servers (fetched via HTTP)
- `/admin-online <date>` — daily online of the administration team (SPEC+)

Moderator tracking (group: `/tracking`)
- `/tracking my [date]` — my actions for a date (MD+)
- `/tracking moderator <moderator> [date]` — actions of a moderator (GMD+)
- `/tracking week <week> [moderator]` — weekly summary across moderators (GMD+)
- `/tracking month <mm.YYYY> <moderator>` — monthly stats (GMD+)
- `/tracking day <dd.mm.YYYY> [moderator]` — daily stats (GMD+)
- `/tracking check` — detect similar actions for review (CUR+)

Punishments and actions
- `/act <id>` — show action info (MD+)
- `/alist <user-id> [global]` — list a user’s punishments, optionally global (MD+)
- Warns: `/warn <user> <reason> [auto-kick]` (MD+), `/unwarn <user>` (MD+)
- Mutes: `/mute text|voice|full …` and `/unmute text|voice|full …` (MD+); also a message context menu for quick text mute with screenshot capture
- Bans: `/ban <user> <duration> <reason>` (MD+), `/unban <user>` (GMD+)
- Global bans: `/gban <user> <duration> <reason>` (CUR+), `/ungban <user>` (CUR+)
- Hides (timeouts): `/hide <user>`, `/unhide <user>` (MD+)

Notes
- Durations support compact formats, e.g. `1s`, `15m`, `2h`, `7d`; some commands accept `-1` for permanent (where allowed).
- Many commands may require proofs; the bot guides you and attaches links/screenshots through threads and webhooks.

## Permissions model
Reverie derives a “moderator level” from guild roles by name matching (Russian role names in the default setup):
- MD — «Модератор»
- SMD — «Старший модератор»
- AD — «Ассистент»
- GMD — «Главный модератор»
- SPEC — «Следящий»
- CUR — «Curator»
Server administrators are treated as highest level. Adjust role names in your guild to match, or adapt the logic in `core/security.py`.

## Project structure (simplified)
- `main.py` — entry point, starts the bot
- `core/` — bot class, security/permissions, validation, UI templates, features
- `cogs/` — feature modules (greeting, notifications, online, tracking, punishments)
- `database/` — MongoDB and SQLite access layers and domain models
- `buttons/` — interactive views and buttons
- `info/` — tracking models and formatters

## Development
- Dependencies are pinned in `requirements.txt`
- Slash commands are auto-synced on startup (`tree.sync()` in `cogs/main.py`)
- Logging is configured at INFO level in `main.py`
- Keep your token out of VCS; use `.env`

## Troubleshooting
- Slash commands missing: ensure the bot is in the guild, has application commands scope, and wait for initial sync; re-run once
- Missing permissions: the bot needs the rights implied by your actions (Manage Roles, Moderate Members, Ban Members, etc.)
- MongoDB errors: verify `MONGO_URI` and that MongoDB is reachable; local default is `mongodb://localhost:27017`
- Intents: enable Privileged Intents in the Developer Portal and re-invite the bot with them

## License
This project is licensed under the MIT License — see the [LICENSE](LICENSE) file for details.
