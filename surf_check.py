#!/usr/bin/env python3
"""
Surf Tracker - New Smyrna Beach
Checks morning surf conditions via Open-Meteo (free, no API key needed)
and sends a Telegram message if conditions are favorable.
"""

import requests
from datetime import datetime
import os
import sys

# ── Spot configuration ────────────────────────────────────────────────────────
LAT = 29.0252
LON = -80.9272
SPOT_NAME = "New Smyrna Beach"
TIMEZONE = "America/New_York"

# ── Alert thresholds ──────────────────────────────────────────────────────────
MIN_WAVE_HEIGHT_FT = 2.0                          # Alert if >= 2 ft
ALERTABLE_CONDITIONS = {"Fair", "Good", "Epic"}   # Alert if condition in this set

# ── Credentials (set as GitHub Actions secrets) ───────────────────────────────
TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "")
TELEGRAM_CHAT_ID   = os.environ.get("TELEGRAM_CHAT_ID", "")


# ── API helpers ───────────────────────────────────────────────────────────────

def get_marine_data():
    """Fetch wave data from Open-Meteo Marine API (free, no key)."""
    resp = requests.get(
        "https://marine-api.open-meteo.com/v1/marine",
        params={
            "latitude": LAT,
            "longitude": LON,
            "hourly": "wave_height,wave_period,wave_direction,swell_wave_height,swell_wave_period",
            "timezone": TIMEZONE,
            "forecast_days": 1,
        },
        timeout=30,
    )
    resp.raise_for_status()
    return resp.json()


def get_wind_data():
    """Fetch wind data from Open-Meteo Weather API (free, no key)."""
    resp = requests.get(
        "https://api.open-meteo.com/v1/forecast",
        params={
            "latitude": LAT,
            "longitude": LON,
            "hourly": "wind_speed_10m,wind_direction_10m,wind_gusts_10m",
            "wind_speed_unit": "mph",
            "timezone": TIMEZONE,
            "forecast_days": 1,
        },
        timeout=30,
    )
    resp.raise_for_status()
    return resp.json()


# ── Unit / formatting helpers ─────────────────────────────────────────────────

def m_to_ft(meters):
    return meters * 3.28084


def degrees_to_cardinal(deg):
    dirs = ["N", "NNE", "NE", "ENE", "E", "ESE", "SE", "SSE",
            "S", "SSW", "SW", "WSW", "W", "WNW", "NW", "NNW"]
    return dirs[round(deg / 22.5) % 16]


def morning_index(times, target_hour=7):
    """Return the hourly index closest to the target hour."""
    for i, t in enumerate(times):
        if int(t[11:13]) == target_hour:
            return i
    # Fallback: first hour between 6–10 AM
    for i, t in enumerate(times):
        if 6 <= int(t[11:13]) <= 10:
            return i
    return 0


# ── Condition rating ──────────────────────────────────────────────────────────

def rate_conditions(wave_height_ft, wave_period_s, wind_speed_mph, wind_dir_deg):
    """
    Rate surf quality for NSB (east-facing beach).
    Offshore winds blow from the W/NW/SW (roughly 180–360°).
    Returns: "Flat" | "Poor" | "Fair" | "Good" | "Epic"
    """
    if wave_height_ft < 0.75:
        return "Flat"

    score = 0

    # Wave height
    if wave_height_ft >= 5:
        score += 4
    elif wave_height_ft >= 3:
        score += 3
    elif wave_height_ft >= 2:
        score += 2
    elif wave_height_ft >= 1:
        score += 1

    # Wave period (longer = better quality groundswell)
    if wave_period_s >= 12:
        score += 3
    elif wave_period_s >= 9:
        score += 2
    elif wave_period_s >= 7:
        score += 1

    # Wind (offshore = W/NW/SW for an east-facing beach)
    is_offshore = 180 <= wind_dir_deg <= 360 or wind_dir_deg <= 45
    if wind_speed_mph < 5:
        score += 3
    elif wind_speed_mph < 10:
        score += 2 if is_offshore else 1
    elif wind_speed_mph < 15:
        score += 1 if is_offshore else 0

    if score >= 8:
        return "Epic"
    elif score >= 6:
        return "Good"
    elif score >= 3:
        return "Fair"
    else:
        return "Poor"


# ── Telegram alert ───────────────────────────────────────────────────────────

def send_telegram(message):
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    resp = requests.post(url, json={"chat_id": TELEGRAM_CHAT_ID, "text": message}, timeout=30)
    resp.raise_for_status()
    print(f"Telegram message sent.")


# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M')}] Checking surf at {SPOT_NAME}...")

    try:
        marine = get_marine_data()
        wind   = get_wind_data()
    except requests.RequestException as e:
        print(f"ERROR fetching data: {e}", file=sys.stderr)
        sys.exit(1)

    idx = morning_index(marine["hourly"]["time"], target_hour=7)

    wave_height_m  = marine["hourly"]["wave_height"][idx]
    wave_period_s  = marine["hourly"]["wave_period"][idx]
    wave_dir_deg   = marine["hourly"]["wave_direction"][idx]
    wind_speed_mph = wind["hourly"]["wind_speed_10m"][idx]
    wind_dir_deg   = wind["hourly"]["wind_direction_10m"][idx]
    wind_gusts_mph = wind["hourly"]["wind_gusts_10m"][idx]

    # Guard against missing data
    if wave_height_m is None or wave_period_s is None:
        print("WARNING: Marine data unavailable for the target hour.")
        sys.exit(0)

    wave_height_ft = m_to_ft(wave_height_m)
    wind_cardinal  = degrees_to_cardinal(wind_dir_deg)
    condition      = rate_conditions(wave_height_ft, wave_period_s, wind_speed_mph, wind_dir_deg)

    print(f"  Waves      : {wave_height_ft:.1f} ft @ {wave_period_s:.0f}s")
    print(f"  Conditions : {condition}")
    print(f"  Wind       : {wind_speed_mph:.0f} mph {wind_cardinal} (gusts {wind_gusts_mph:.0f} mph)")

    if wave_height_ft >= MIN_WAVE_HEIGHT_FT and condition in ALERTABLE_CONDITIONS:
        date_str = datetime.now().strftime("%a %b %-d")
        message = (
            f"SURF ALERT - NSB\n"
            f"{date_str}\n"
            f"Waves: {wave_height_ft:.1f} ft @ {wave_period_s:.0f}s\n"
            f"Conditions: {condition}\n"
            f"Wind: {wind_speed_mph:.0f} mph {wind_cardinal} (gusts {wind_gusts_mph:.0f})"
        )
        print(f"\nConditions qualify! Sending Telegram alert...")
        print(f"---\n{message}\n---")

        if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
            print("WARNING: Telegram credentials not set. Skipping alert.")
        else:
            send_telegram(message)
    else:
        print(
            f"\nNo alert — need >= {MIN_WAVE_HEIGHT_FT} ft + {'/'.join(ALERTABLE_CONDITIONS)}. "
            f"Got {wave_height_ft:.1f} ft / {condition}."
        )


if __name__ == "__main__":
    main()
