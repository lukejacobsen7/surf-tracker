# Surf Tracker

Checks the morning surf at New Smyrna Beach and sends a Telegram message only
when it is actually worth paddling out. Runs itself on GitHub Actions.

No API key: wave height, period, and direction come from the
[Open-Meteo Marine API](https://open-meteo.com/), which is free and
unauthenticated.

## What counts as worth it

A message is sent only if the wave height clears **2.0 ft** and the rated
condition is **Fair, Good, or Epic**. Anything below that stays silent, which
is the entire point — an alert that fires every morning gets ignored by the
second week.

## Setup

1. Fork or clone.
2. Add two repository secrets under **Settings → Secrets and variables →
   Actions**:
   - `TELEGRAM_BOT_TOKEN` — from [@BotFather](https://t.me/BotFather)
   - `TELEGRAM_CHAT_ID` — message the bot, then open
     `https://api.telegram.org/bot<TOKEN>/getUpdates`

## Another spot

Change `LAT`, `LON`, and `SPOT_NAME` at the top of `surf_check.py`. Thresholds
are the two constants right below them.

## Running it locally

```bash
pip install -r requirements.txt
TELEGRAM_BOT_TOKEN=... TELEGRAM_CHAT_ID=... python surf_check.py
```
