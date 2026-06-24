#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
V20 Signal Scanner – Mobile Friendly HTML Dashboard with Password Lock
"""

import yfinance as yf
import pandas as pd
from datetime import datetime, timedelta
from pathlib import Path
from tqdm import tqdm
import logging
from concurrent.futures import ThreadPoolExecutor

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Configurable parameters (edit these directly in the script)
THRESHOLD_PERCENT = 20
DAYS_BACK = 1095
MAX_WORKERS = 10
SIGNAL_STRENGTH_THRESHOLD = 50

# Define constants
HTML_NAME = "index.html"
START_DATE = (datetime.today() - timedelta(days=DAYS_BACK)).strftime('%Y-%m-%d')
END_DATE = (datetime.today() + timedelta(days=1)).strftime('%Y-%m-%d')

# Stock list
all_stocks = [
    "3MINDIA","ABB","ABBOTINDIA","ABSLAMC","ACE","AIIL","AJANTPHARM","AJAXENGG","AKZOINDIA","ALIVUS",
    "ALKEM","ANANDRATHI","APARINDS","APLAPOLLO","ASIANPAINT","AVANTIFEED","AWL","BALUFORGE","BAYERCROP","BEL",
    "BERGEPAINT","BLS","BLUEJET","BLUESTARCO","BOSCHLTD","BSE","BSOFT","CAMS","CAPLIPOINT","CASTROLIND",
    "CDSL","CELLO","CERA","CGPOWER","CHAMBLFERT","CIGNITITEC","CIPLA","CLEAN","CMSINFO","COALINDIA",
    "COCHINSHIP","COFORGE","COLPAL","CONCORDBIO","COROMANDEL","CRISIL","CUMMINSIND","DABUR","DATAPATTNS","DBCORP",
    "DHANUKA","DIVISLAB","DIXON","DODLA","DOLATALGO","DOMS","DRREDDY","ECLERX","EICHERMOT","EIHOTEL",
    "ELECON","EMAMILTD","EMCURE","ENGINERSIN","FIEMIND","FINEORG","FORCEMOT","GABRIEL","GANESHHOU","GARFIBRES",
    "GHCL","GILLETTE","GLAXO","GODFRYPHLP","GPIL","GPPL","GRAVITA","GRINDWELL","GRSE","GRWRHITECH",
    "HAL","HAVELLS","HBLENGINE","HCLTECH","HDFCAMC","HEROMOTOCO","HEXT","HINDCOPPER","HINDUNILVR","HSCL",
    "HYUNDAI","ICICIGI","IEX","IGIL","IGL","IMFA","INDGN","INDIAMART","INFY","INGERRAND",
    "INOXINDIA","IRCTC","ITC","JBCHEPHARM","JWL","JYOTHYLAB","KEI","KFINTECH","KIRLOSBROS","KIRLPNU",
    "KPITTECH","KSB","KSCL","LALPATHLAB","LICI","LLOYDSME","LTIM","LTTS","MAITHANALL","MANINFRA",
    "MARICO","MARKSANS","MARUTI","MAZDOCK","MCX","MGL","MPHASIS","MSTCLTD","MSUMI","NATCOPHARM",
    "NATIONALUM","NBCC","NCC","NESCO","NEWGEN","NIITMTS","NMDC","OFSS","PAGEIND","PERSISTENT",
    "PETRONET","PFIZER","PGHH","PGHL","PIDILITIND","PIIND","POLYCAB","POLYMED","RAILTEL","RATNAMANI",
    "RITES","SANOFI","SCHAEFFLER","SHAKTIPUMP","SHARDAMOTR","SHAREINDIA","SHRIPISTON","SIEMENS","SKFINDIA","SOLARINDS",
    "SPLPETRO","SUMICHEM","SUNPHARMA","SUNTV","SUPREMEIND","SURYAROSNI","SUZLON","SYMPHONY","TANLA","TARIL",
    "TATAELXSI","TATATECH","TBOTEK","TCI","TCS","TI","TIINDIA","TIMKEN","TRITURBINE","UNITDSPR",
    "UTIAMC","VBL","VESUVIUS","VINATIORGA","VOLTAMP","VSTIND","WAAREEENER","WAAREERTL","WELCORP","ZENSARTECH",
    "ZENTEC","ZFCVINDIA","ZYDUSLIFE","JIOFIN","ANGELONE","BAJAJHLDNG","ULTRACEMCO",
    "ACC","TEAMLEASE","QUESS","ASTRAZEN","ERIS","APOLLOHOSP","MEDANTA","FORTIS",
    "ADANIPORTS","JSWINFRA","GODREJCP","KAJARIACER","HONAUT","DMART","RELAXO","MRF","M&M","TATAMOTORS",
    "INDHOTEL","RADICO","UBL","MAHABANK","ICICIBANK","CANBK","KARURVYSYA","SBIN","INDIANB","UNIONBANK",
    "AXISBANK","J&KBANK","BANKBARODA","PNB","HDFCBANK","CSBBANK","AUBANK","TMB","SOUTHBANK","IDBI",
    "KOTAKBANK","JSFB","FEDERALBNK","CUB","UJJIVANSFB","BANKINDIA","POONAWALLA","BAJFINANCE","RECLTD","SHRIRAMFIN",
    "LICHSGFIN","MUTHOOTFIN","CHOLAHLDNG","CHOLAFIN","AIIL","HUDCO","TVSHLTD","BAJAJHFL","PNBHOUSING","SBICARD",
    "SUNDARMFIN","IREDA","FIVESTAR","AADHARHFC","CANFINHOME","APTUS","CRISIL","AAVAS","REPCOHOME"
]

def download_data(symbol: str) -> pd.DataFrame | None:
    try:
        df = yf.Ticker(symbol + ".NS").history(start=START_DATE, end=END_DATE)
        if df.empty:
            logging.warning(f"No data retrieved for {symbol}.NS")
            return None
        df = df[['Open', 'High', 'Low', 'Close']].dropna()
        df['MA200'] = df['Close'].rolling(window=200).mean()
        return df
    except Exception as e:
        logging.error(f"Error downloading data for {symbol}.NS: {str(e)}")
        return None

def find_v20_signals(df: pd.DataFrame):
    signals = []
    latest_close = df['Close'].iloc[-1]
    streak_low = streak_high = None

    for idx in range(1, len(df)):
        cur = df.iloc[idx]
        ma200 = cur.get('MA200', float('inf'))

        # Skip if MA200 is NaN (not enough data for 200-day MA)
        if pd.isna(ma200):
            continue

        if cur['Close'] > cur['Open']:
            streak_low = cur['Low'] if streak_low is None else min(streak_low, cur['Low'])
            streak_high = cur['High'] if streak_high is None else max(streak_high, cur['High'])
            continue

        if streak_low and streak_high and streak_low != 0:
            pct_move = (streak_high - streak_low) / streak_low * 100
            if pct_move >= THRESHOLD_PERCENT and streak_low < ma200:
                proximity = (latest_close - streak_low) / streak_low * 100
                if not pd.isna(proximity) and not pd.isna(latest_close):
                    score = round(pct_move * abs(proximity) / 100, 2)  # Signal strength score
                    signals.append((
                        df.index[idx].date(), round(streak_low, 2),
                        round(streak_high, 2), round(pct_move, 2),
                        round(latest_close, 2), round(proximity, 2), score
                    ))
        streak_low = streak_high = None
    return signals

def save_html(signals_list: list, filename: str) -> None:
    import json
    import os

    # Calculate IST time (UTC + 5:30) if running in GitHub Actions (UTC), else local time
    if os.environ.get("GITHUB_ACTIONS") == "true":
        utc_now = datetime.utcnow()
        ist_now = utc_now + timedelta(hours=5, minutes=30)
        latest_date = ist_now.strftime('%b %d, %Y, %I:%M %p') + " IST"
    else:
        latest_date = datetime.now().strftime('%b %d, %Y, %I:%M %p')

    # Convert list of signals to JSON
    signals_json = json.dumps(signals_list)

    html = """<!DOCTYPE html>
<html lang="en" data-theme="dark">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>V20 Scanner by Vishal Yadav</title>
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
  <link href="https://fonts.googleapis.com/css2?family=Outfit:wght@300;400;500;600;700&display=swap" rel="stylesheet">
  <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.2/css/all.min.css">
  <style>
    :root {
      --bg-gradient: linear-gradient(135deg, #0b0f19 0%, #111827 100%);
      --card-bg: rgba(30, 41, 59, 0.45);
      --card-border: rgba(255, 255, 255, 0.06);
      --text-primary: #f3f4f6;
      --text-secondary: #9ca3af;
      --accent-color: #6366f1;
      --accent-glow: rgba(99, 102, 241, 0.2);
      --success: #10b981;
      --success-glow: rgba(16, 185, 129, 0.15);
      --warning: #f59e0b;
      --danger: #ef4444;
      --header-text: #ffffff;
      --shadow: 0 10px 30px -10px rgba(0, 0, 0, 0.5);
      --input-bg: rgba(15, 23, 42, 0.6);
      --input-border: rgba(255, 255, 255, 0.1);
      --btn-active-bg: #6366f1;
      --btn-active-text: #ffffff;
      --btn-inactive-bg: rgba(255, 255, 255, 0.04);
      --btn-inactive-border: rgba(255, 255, 255, 0.08);
      --table-hdr-bg: rgba(15, 23, 42, 0.8);
      --table-row-even: rgba(255, 255, 255, 0.01);
      --table-row-hover: rgba(99, 102, 241, 0.06);
      --badge-strong: rgba(245, 158, 11, 0.15);
      --badge-strong-text: #fbbf24;
    }

    [data-theme="light"] {
      --bg-gradient: linear-gradient(135deg, #f8fafc 0%, #e2e8f0 100%);
      --card-bg: rgba(255, 255, 255, 0.7);
      --card-border: rgba(0, 0, 0, 0.06);
      --text-primary: #1e293b;
      --text-secondary: #64748b;
      --accent-color: #4f46e5;
      --accent-glow: rgba(79, 70, 229, 0.1);
      --success: #059669;
      --success-glow: rgba(5, 150, 105, 0.1);
      --warning: #d97706;
      --danger: #dc2626;
      --header-text: #0f172a;
      --shadow: 0 10px 30px -10px rgba(0, 0, 0, 0.06);
      --input-bg: rgba(255, 255, 255, 0.9);
      --input-border: rgba(0, 0, 0, 0.1);
      --btn-active-bg: #4f46e5;
      --btn-active-text: #ffffff;
      --btn-inactive-bg: rgba(0, 0, 0, 0.02);
      --btn-inactive-border: rgba(0, 0, 0, 0.08);
      --table-hdr-bg: rgba(241, 245, 249, 0.9);
      --table-row-even: rgba(0, 0, 0, 0.01);
      --table-row-hover: rgba(79, 70, 229, 0.04);
      --badge-strong: rgba(217, 119, 6, 0.1);
      --badge-strong-text: #b45309;
    }

    * {
      box-sizing: border-box;
      margin: 0;
      padding: 0;
    }

    body {
      font-family: 'Outfit', sans-serif;
      background: var(--bg-gradient);
      color: var(--text-primary);
      min-height: 100vh;
      padding: 0;
      transition: background 0.3s ease, color 0.3s ease;
      line-height: 1.5;
    }

    .container {
      max-width: 1200px;
      margin: 0 auto;
      padding: 24px 16px;
    }

    /* Password Overlay Styles */
    .password-overlay {
      position: fixed;
      top: 0;
      left: 0;
      width: 100%;
      height: 100%;
      background: linear-gradient(135deg, #0b0f19 0%, #111827 100%);
      display: flex;
      justify-content: center;
      align-items: center;
      z-index: 9999;
      padding: 20px;
    }

    [data-theme="light"] .password-overlay {
      background: linear-gradient(135deg, #f8fafc 0%, #e2e8f0 100%);
    }

    .password-card {
      background: var(--card-bg);
      border: 1px solid var(--card-border);
      backdrop-filter: blur(24px);
      -webkit-backdrop-filter: blur(24px);
      border-radius: 24px;
      padding: 40px 30px;
      max-width: 400px;
      width: 100%;
      text-align: center;
      box-shadow: 0 20px 40px -15px rgba(0, 0, 0, 0.5);
      display: flex;
      flex-direction: column;
      align-items: center;
      gap: 16px;
    }

    .password-icon {
      width: 64px;
      height: 64px;
      border-radius: 50%;
      background: var(--accent-glow);
      color: var(--accent-color);
      display: flex;
      justify-content: center;
      align-items: center;
      font-size: 24px;
      margin-bottom: 8px;
      box-shadow: 0 0 20px var(--accent-glow);
    }

    .password-card h2 {
      font-size: 24px;
      font-weight: 700;
      color: var(--text-primary);
    }

    .password-subtitle {
      font-size: 13px;
      color: var(--text-secondary);
      line-height: 1.5;
    }

    .password-input-wrapper {
      position: relative;
      width: 100%;
      margin-top: 8px;
    }

    .password-input-wrapper input {
      width: 100%;
      background: var(--input-bg);
      border: 1px solid var(--input-border);
      border-radius: 14px;
      padding: 14px 56px 14px 16px;
      color: var(--text-primary);
      font-family: inherit;
      font-size: 15px;
      outline: none;
      transition: all 0.2s ease;
    }

    .password-input-wrapper input:focus {
      border-color: var(--accent-color);
      box-shadow: 0 0 0 3px var(--accent-glow);
    }

    .password-input-wrapper button {
      position: absolute;
      right: 6px;
      top: 50%;
      transform: translateY(-50%);
      width: 42px;
      height: 42px;
      border-radius: 10px;
      background: var(--accent-color);
      border: none;
      color: #ffffff;
      display: flex;
      justify-content: center;
      align-items: center;
      cursor: pointer;
      font-size: 16px;
      transition: all 0.2s ease;
    }

    .password-input-wrapper button:hover {
      background: var(--accent-hover);
      box-shadow: 0 0 10px var(--accent-glow);
    }

    .password-error-msg {
      color: var(--danger);
      font-size: 12px;
      font-weight: 500;
      display: flex;
      align-items: center;
      gap: 6px;
      margin-top: 4px;
    }

    .password-error-msg.hidden {
      display: none;
    }

    /* Wrap standard content */
    #appContent {
      display: none;
    }

    header {
      display: flex;
      flex-direction: column;
      gap: 16px;
      margin-bottom: 32px;
      position: relative;
    }

    .header-top {
      display: flex;
      justify-content: space-between;
      align-items: center;
    }

    .title-area h1 {
      font-size: 28px;
      font-weight: 700;
      background: linear-gradient(to right, #818cf8, #c084fc);
      -webkit-background-clip: text;
      -webkit-text-fill-color: transparent;
      margin-bottom: 4px;
    }

    [data-theme="light"] .title-area h1 {
      background: linear-gradient(to right, #4f46e5, #9333ea);
      -webkit-background-clip: text;
      -webkit-text-fill-color: transparent;
    }

    .subtitle {
      font-size: 14px;
      color: var(--text-secondary);
      font-weight: 400;
    }

    .last-updated {
      font-size: 13px;
      color: var(--accent-color);
      font-weight: 600;
      margin-top: 8px;
      display: inline-flex;
      align-items: center;
      gap: 6px;
      background: var(--accent-glow);
      padding: 6px 12px;
      border-radius: 8px;
      border: 1px solid rgba(99, 102, 241, 0.15);
      align-self: flex-start;
    }

    .theme-toggle-btn {
      background: var(--btn-inactive-bg);
      border: 1px solid var(--btn-inactive-border);
      color: var(--text-primary);
      width: 40px;
      height: 40px;
      border-radius: 50%;
      display: flex;
      justify-content: center;
      align-items: center;
      cursor: pointer;
      font-size: 16px;
      transition: all 0.2s ease;
    }

    .theme-toggle-btn:hover {
      background: var(--btn-active-bg);
      color: var(--btn-active-text);
      border-color: var(--btn-active-bg);
      transform: scale(1.05);
    }

    .metrics-grid {
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
      gap: 16px;
      margin-bottom: 32px;
    }

    .metric-card {
      background: var(--card-bg);
      border: 1px solid var(--card-border);
      backdrop-filter: blur(16px);
      -webkit-backdrop-filter: blur(16px);
      border-radius: 16px;
      padding: 20px;
      display: flex;
      align-items: center;
      gap: 16px;
      box-shadow: var(--shadow);
      transition: transform 0.2s ease, box-shadow 0.2s ease;
    }

    .metric-card:hover {
      transform: translateY(-2px);
    }

    .metric-icon {
      width: 48px;
      height: 48px;
      border-radius: 12px;
      background: var(--accent-glow);
      color: var(--accent-color);
      display: flex;
      justify-content: center;
      align-items: center;
      font-size: 20px;
    }

    .metric-card.success-card .metric-icon {
      background: var(--success-glow);
      color: var(--success);
    }

    .metric-card.warning-card .metric-icon {
      background: rgba(245, 158, 11, 0.1);
      color: var(--warning);
    }

    .metric-info {
      display: flex;
      flex-direction: column;
    }

    .metric-val {
      font-size: 22px;
      font-weight: 700;
      color: var(--text-primary);
    }

    .metric-lbl {
      font-size: 12px;
      color: var(--text-secondary);
      font-weight: 500;
      text-transform: uppercase;
      letter-spacing: 0.05em;
    }

    .controls-panel {
      background: var(--card-bg);
      border: 1px solid var(--card-border);
      backdrop-filter: blur(16px);
      -webkit-backdrop-filter: blur(16px);
      border-radius: 16px;
      padding: 16px;
      margin-bottom: 24px;
      box-shadow: var(--shadow);
      display: flex;
      flex-direction: column;
      gap: 16px;
    }

    .search-sort-row {
      display: flex;
      flex-direction: column;
      gap: 12px;
    }

    .search-box {
      position: relative;
      flex-grow: 1;
    }

    .search-box i {
      position: absolute;
      left: 14px;
      top: 50%;
      transform: translateY(-50%);
      color: var(--text-secondary);
      font-size: 14px;
    }

    .search-input {
      width: 100%;
      background: var(--input-bg);
      border: 1px solid var(--input-border);
      border-radius: 12px;
      padding: 12px 16px 12px 40px;
      color: var(--text-primary);
      font-family: inherit;
      font-size: 14px;
      outline: none;
      transition: border-color 0.2s ease, box-shadow 0.2s ease;
    }

    .search-input:focus {
      border-color: var(--accent-color);
      box-shadow: 0 0 0 3px var(--accent-glow);
    }

    .select-dropdown {
      background: var(--input-bg);
      border: 1px solid var(--input-border);
      border-radius: 12px;
      padding: 12px 16px;
      color: var(--text-primary);
      font-family: inherit;
      font-size: 14px;
      outline: none;
      cursor: pointer;
      appearance: none;
      background-image: url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' fill='none' viewBox='0 0 24 24' stroke='%239ca3af'%3E%3Cpath stroke-linecap='round' stroke-linejoin='round' stroke-width='2' d='M19 9l-7 7-7-7'/%3E%3C/svg%3E");
      background-repeat: no-repeat;
      background-position: right 14px center;
      background-size: 16px;
      padding-right: 40px;
    }

    .filter-pills-row {
      display: flex;
      flex-wrap: wrap;
      justify-content: space-between;
      align-items: center;
      gap: 12px;
    }

    .filter-pills {
      display: flex;
      flex-wrap: wrap;
      gap: 8px;
    }

    .pill {
      background: var(--btn-inactive-bg);
      border: 1px solid var(--btn-inactive-border);
      color: var(--text-secondary);
      padding: 8px 16px;
      border-radius: 50px;
      font-size: 13px;
      font-weight: 500;
      cursor: pointer;
      transition: all 0.2s ease;
    }

    .pill:hover {
      color: var(--text-primary);
      border-color: var(--text-primary);
    }

    .pill.active {
      background: var(--btn-active-bg);
      border-color: var(--btn-active-bg);
      color: var(--btn-active-text);
      box-shadow: 0 4px 12px var(--accent-glow);
    }

    .view-toggles {
      display: flex;
      background: var(--input-bg);
      border: 1px solid var(--input-border);
      border-radius: 12px;
      padding: 4px;
    }

    .view-btn {
      background: transparent;
      border: none;
      color: var(--text-secondary);
      padding: 8px 16px;
      border-radius: 8px;
      font-size: 13px;
      font-weight: 500;
      cursor: pointer;
      display: flex;
      align-items: center;
      gap: 8px;
      transition: all 0.2s ease;
    }

    .view-btn.active {
      background: var(--card-bg);
      color: var(--text-primary);
      box-shadow: 0 2px 8px rgba(0,0,0,0.15);
      border: 1px solid var(--card-border);
    }

    .view-section {
      position: relative;
    }

    .grid-view {
      display: grid;
      grid-template-columns: repeat(auto-fill, minmax(280px, 1fr));
      gap: 16px;
    }

    .grid-view.hidden, .table-wrapper.hidden {
      display: none !important;
    }

    .signal-card {
      background: var(--card-bg);
      border: 1px solid var(--card-border);
      backdrop-filter: blur(16px);
      -webkit-backdrop-filter: blur(16px);
      border-radius: 16px;
      padding: 20px;
      box-shadow: var(--shadow);
      display: flex;
      flex-direction: column;
      gap: 16px;
      transition: transform 0.2s ease, border-color 0.2s ease;
      position: relative;
      overflow: hidden;
    }

    .signal-card:hover {
      transform: translateY(-4px);
      border-color: var(--accent-color);
    }

    .card-hdr {
      display: flex;
      justify-content: space-between;
      align-items: flex-start;
    }

    .symbol-badge {
      font-size: 18px;
      font-weight: 700;
      color: var(--text-primary);
      text-decoration: none;
      display: flex;
      align-items: center;
      gap: 8px;
    }

    .symbol-badge:hover {
      color: var(--accent-color);
    }

    .symbol-badge i {
      font-size: 12px;
      opacity: 0.5;
    }

    .date-badge {
      font-size: 12px;
      color: var(--text-secondary);
      background: rgba(255,255,255,0.04);
      padding: 4px 8px;
      border-radius: 6px;
    }

    .strength-indicator {
      display: inline-flex;
      align-items: center;
      gap: 4px;
      font-size: 11px;
      font-weight: 600;
      padding: 4px 8px;
      border-radius: 50px;
      background: var(--badge-strong);
      color: var(--badge-strong-text);
      align-self: flex-start;
      margin-top: -6px;
    }

    .card-stats {
      display: grid;
      grid-template-columns: 1fr 1fr;
      gap: 12px 16px;
      background: rgba(0, 0, 0, 0.1);
      padding: 12px;
      border-radius: 12px;
      border: 1px solid rgba(255, 255, 255, 0.02);
    }

    .stat-box {
      display: flex;
      flex-direction: column;
    }

    .stat-label {
      font-size: 11px;
      color: var(--text-secondary);
      text-transform: uppercase;
      letter-spacing: 0.02em;
    }

    .stat-value {
      font-size: 14px;
      font-weight: 600;
    }

    .proximity-value {
      display: flex;
      align-items: center;
      gap: 4px;
    }

    .proximity-value.near {
      color: var(--success);
    }

    .proximity-value.far {
      color: var(--text-primary);
    }

    .tv-link-btn {
      width: 100%;
      background: var(--btn-inactive-bg);
      border: 1px solid var(--btn-inactive-border);
      color: var(--text-primary);
      text-align: center;
      padding: 10px;
      border-radius: 12px;
      text-decoration: none;
      font-size: 13px;
      font-weight: 600;
      display: flex;
      justify-content: center;
      align-items: center;
      gap: 8px;
      transition: all 0.2s ease;
    }

    .tv-link-btn:hover {
      background: var(--accent-color);
      border-color: var(--accent-color);
      color: var(--btn-active-text);
      box-shadow: 0 4px 12px var(--accent-glow);
    }

    .table-wrapper {
      background: var(--card-bg);
      border: 1px solid var(--card-border);
      border-radius: 16px;
      overflow-x: auto;
      box-shadow: var(--shadow);
    }

    table {
      width: 100%;
      border-collapse: collapse;
      text-align: left;
      font-size: 14px;
    }

    th {
      background: var(--table-hdr-bg);
      color: var(--text-primary);
      font-weight: 600;
      padding: 16px;
      border-bottom: 1px solid var(--card-border);
      text-transform: uppercase;
      font-size: 11px;
      letter-spacing: 0.05em;
    }

    td {
      padding: 16px;
      border-bottom: 1px solid var(--card-border);
      color: var(--text-primary);
    }

    tr:nth-child(even) {
      background: var(--table-row-even);
    }

    tr:hover {
      background: var(--table-row-hover);
    }

    .table-tv-btn {
      color: var(--text-secondary);
      background: var(--btn-inactive-bg);
      border: 1px solid var(--btn-inactive-border);
      width: 32px;
      height: 32px;
      border-radius: 8px;
      display: inline-flex;
      justify-content: center;
      align-items: center;
      text-decoration: none;
      transition: all 0.2s ease;
    }

    .table-tv-btn:hover {
      background: var(--accent-color);
      border-color: var(--accent-color);
      color: var(--btn-active-text);
    }

    .td-symbol {
      font-weight: 700;
    }

    .td-proximity.near {
      color: var(--success);
      font-weight: 600;
    }

    .td-strength.strong {
      color: var(--warning);
      font-weight: 600;
    }

    .no-data-card {
      background: var(--card-bg);
      border: 1px solid var(--card-border);
      border-radius: 16px;
      padding: 60px 20px;
      text-align: center;
      box-shadow: var(--shadow);
      display: flex;
      flex-direction: column;
      align-items: center;
      justify-content: center;
      gap: 16px;
    }

    .no-data-card i {
      font-size: 48px;
      color: var(--text-secondary);
      opacity: 0.4;
    }

    .no-data-card h3 {
      font-size: 18px;
      font-weight: 600;
      color: var(--text-primary);
    }

    .no-data-card p {
      font-size: 14px;
      color: var(--text-secondary);
      max-width: 400px;
    }

    @media (min-width: 768px) {
      header {
        flex-direction: row;
        justify-content: space-between;
        align-items: center;
        margin-bottom: 40px;
      }

      .search-sort-row {
        flex-direction: row;
      }

      .controls-panel {
        padding: 20px;
      }
    }

    @keyframes fadeIn {
      from { opacity: 0; transform: translateY(10px); }
      to { opacity: 1; transform: translateY(0); }
    }

    .animate-fade-in {
      animation: fadeIn 0.3s cubic-bezier(0.4, 0, 0.2, 1) forwards;
    }
  </style>
</head>
<body>
  <!-- Password Lock Screen Overlay -->
  <div id="passwordOverlay" class="password-overlay">
    <div class="password-card animate-fade-in">
      <div class="password-icon"><i class="fas fa-lock"></i></div>
      <h2>V20 Scanner</h2>
      <p class="password-subtitle">This system is secure. Please enter password to access the scanner.</p>
      
      <div class="password-input-wrapper">
        <input type="password" id="passwordInput" placeholder="Enter Password..." autocomplete="current-password">
        <button id="unlockBtn" onclick="checkPassword()"><i class="fas fa-arrow-right"></i></button>
      </div>
      
      <div id="passwordError" class="password-error-msg hidden">
        <i class="fas fa-exclamation-circle"></i> Invalid password. Please try again.
      </div>
    </div>
  </div>

  <div id="appContent" class="container">
    <header>
      <div class="title-area">
        <h1>V20 Scanner by Vishal Yadav</h1>
        <div class="subtitle">Automated scanner identifying retracements near major support points. Refreshes hourly.</div>
        <div class="last-updated"><i class="far fa-clock"></i> Last Updated: <span>__LATEST_DATE__</span></div>
      </div>
      <div class="header-top">
        <button id="themeToggle" class="theme-toggle-btn" title="Toggle Light/Dark Theme">
          <i class="fas fa-moon"></i>
        </button>
      </div>
    </header>

    <div class="metrics-grid">
      <div class="metric-card">
        <div class="metric-icon"><i class="fas fa-satellite-dish"></i></div>
        <div class="metric-info">
          <div class="metric-val" id="totalSignals">0</div>
          <div class="metric-lbl">Total Signals</div>
        </div>
      </div>
      <div class="metric-card success-card">
        <div class="metric-icon"><i class="fas fa-percentage"></i></div>
        <div class="metric-info">
          <div class="metric-val" id="avgMove">0%</div>
          <div class="metric-lbl">Avg % Move</div>
        </div>
      </div>
      <div class="metric-card">
        <div class="metric-icon"><i class="fas fa-crosshairs"></i></div>
        <div class="metric-info">
          <div class="metric-val" id="avgProx">0%</div>
          <div class="metric-lbl">Avg Proximity</div>
        </div>
      </div>
      <div class="metric-card warning-card">
        <div class="metric-icon"><i class="fas fa-bolt"></i></div>
        <div class="metric-info">
          <div class="metric-val" id="avgStrength">0</div>
          <div class="metric-lbl">Avg Strength</div>
        </div>
      </div>
    </div>

    <div class="controls-panel">
      <div class="search-sort-row">
        <div class="search-box">
          <i class="fas fa-search"></i>
          <input type="text" id="searchInput" class="search-input" placeholder="Search stock symbol (e.g. ABB)...">
        </div>
        <select id="sortSelect" class="select-dropdown">
          <option value="date-desc">Date (Newest First)</option>
          <option value="prox-asc">Proximity (Closest to Buy Point)</option>
          <option value="strength-desc">Signal Strength (Highest First)</option>
          <option value="symbol-asc">Symbol (A to Z)</option>
        </select>
      </div>
      <div class="filter-pills-row">
        <div class="filter-pills">
          <div class="pill active" data-filter="all">All Signals</div>
          <div class="pill" data-filter="near-buy">Near Buy Point (&le; 5%)</div>
          <div class="pill" data-filter="strong">Strong Signals (&ge; 50)</div>
        </div>
        <div class="view-toggles">
          <button class="view-btn" id="cardViewBtn"><i class="fas fa-grip-2"></i>Cards</button>
          <button class="view-btn" id="tableViewBtn"><i class="fas fa-list"></i>Table</button>
        </div>
      </div>
    </div>

    <div class="view-section">
      <div id="gridContainer" class="grid-view"></div>

      <div id="tableContainer" class="table-wrapper hidden">
        <table>
          <thead>
            <tr>
              <th>Date</th>
              <th>Symbol</th>
              <th>Close</th>
              <th>Buy At (Streak Low)</th>
              <th>Sell At (Streak High)</th>
              <th>% Move</th>
              <th>Proximity</th>
              <th>Strength Score</th>
              <th>Chart</th>
            </tr>
          </thead>
          <tbody id="tableBody"></tbody>
        </table>
      </div>

      <div id="emptyState" class="no-data-card hidden">
        <i class="fas fa-search"></i>
        <h3 id="emptyTitle">No Signals Found</h3>
        <p id="emptyText">No stock signals matched your current search filters or scan thresholds.</p>
      </div>
    </div>

    <div style="text-align: center; margin-top: 40px; font-size: 12px; color: var(--text-secondary);">
      For educational purposes only.
    </div>
  </div>

  <script>
    const signals = __SIGNALS_JSON__;
    
    // Password protection logic
    const CORRECT_HASH = "83cf1727de5fd6520f9e9675b2bf095b0376c7e36e690e937d3f3b8486dc2b58"; // Hash of "raosahab"

    async function sha256(message) {
      const msgBuffer = new TextEncoder().encode(message);
      const hashBuffer = await crypto.subtle.digest('SHA-256', msgBuffer);
      const hashArray = Array.from(new Uint8Array(hashBuffer));
      return hashArray.map(b => b.toString(16).padStart(2, '0')).join('');
    }

    async function checkPassword() {
      const input = document.getElementById("passwordInput").value;
      const errorMsg = document.getElementById("passwordError");
      
      try {
        const hash = await sha256(input);
        if (hash === CORRECT_HASH) {
          localStorage.setItem("v20_unlocked", "true");
          document.getElementById("passwordOverlay").style.display = "none";
          document.getElementById("appContent").style.display = "block";
          calculateMetrics();
          render();
        } else {
          errorMsg.classList.remove("hidden");
          document.getElementById("passwordInput").value = "";
        }
      } catch (e) {
        console.error("SHA-256 error, using fallback plain text check", e);
        if (input === "raosahab") {
          localStorage.setItem("v20_unlocked", "true");
          document.getElementById("passwordOverlay").style.display = "none";
          document.getElementById("appContent").style.display = "block";
          calculateMetrics();
          render();
        } else {
          errorMsg.classList.remove("hidden");
          document.getElementById("passwordInput").value = "";
        }
      }
    }

    let searchQuery = "";
    let activeFilter = "all";
    let activeSort = "date-desc";
    let activeView = "card";

    const searchInput = document.getElementById("searchInput");
    const sortSelect = document.getElementById("sortSelect");
    const pills = document.querySelectorAll(".pill");
    const cardViewBtn = document.getElementById("cardViewBtn");
    const tableViewBtn = document.getElementById("tableViewBtn");
    const gridContainer = document.getElementById("gridContainer");
    const tableContainer = document.getElementById("tableContainer");
    const tableBody = document.getElementById("tableBody");
    const emptyState = document.getElementById("emptyState");
    const themeToggle = document.getElementById("themeToggle");
    const root = document.documentElement;

    const totalSignalsEl = document.getElementById("totalSignals");
    const avgMoveEl = document.getElementById("avgMove");
    const avgProxEl = document.getElementById("avgProx");
    const avgStrengthEl = document.getElementById("avgStrength");

    function init() {
      // Auto-unlock check
      if (localStorage.getItem("v20_unlocked") === "true") {
        document.getElementById("passwordOverlay").style.display = "none";
        document.getElementById("appContent").style.display = "block";
      } else {
        document.getElementById("passwordOverlay").style.display = "flex";
        document.getElementById("appContent").style.display = "none";
      }

      // Listen for enter key in password input
      document.getElementById("passwordInput").addEventListener("keypress", function(e) {
        if (e.key === "Enter") {
          checkPassword();
        }
      });

      if (window.innerWidth < 768) {
        setView("card");
      } else {
        setView("table");
      }

      const savedTheme = localStorage.getItem("theme") || "dark";
      setTheme(savedTheme);

      themeToggle.addEventListener("click", () => {
        const currentTheme = root.getAttribute("data-theme");
        const newTheme = currentTheme === "dark" ? "light" : "dark";
        setTheme(newTheme);
      });

      searchInput.addEventListener("input", (e) => {
        searchQuery = e.target.value.toLowerCase().trim();
        render();
      });

      sortSelect.addEventListener("change", (e) => {
        activeSort = e.target.value;
        render();
      });

      pills.forEach(pill => {
        pill.addEventListener("click", () => {
          pills.forEach(p => p.classList.remove("active"));
          pill.classList.add("active");
          activeFilter = pill.getAttribute("data-filter");
          render();
        });
      });

      cardViewBtn.addEventListener("click", () => setView("card"));
      tableViewBtn.addEventListener("click", () => setView("table"));

      calculateMetrics();
      render();
    }

    function setTheme(theme) {
      root.setAttribute("data-theme", theme);
      localStorage.setItem("theme", theme);
      const icon = themeToggle.querySelector("i");
      if (theme === "dark") {
        icon.className = "fas fa-sun";
      } else {
        icon.className = "fas fa-moon";
      }
    }

    function setView(view) {
      activeView = view;
      if (view === "card") {
        cardViewBtn.classList.add("active");
        tableViewBtn.classList.remove("active");
      } else {
        tableViewBtn.classList.add("active");
        cardViewBtn.classList.remove("active");
      }
      render();
    }

    function calculateMetrics() {
      if (!signals || signals.length === 0) return;

      totalSignalsEl.textContent = signals.length;
      
      const sumMove = signals.reduce((acc, sig) => acc + sig['PercentMove'], 0);
      avgMoveEl.textContent = (sumMove / signals.length).toFixed(1) + "%";

      const sumProx = signals.reduce((acc, sig) => acc + sig['Proximity'], 0);
      avgProxEl.textContent = (sumProx / signals.length).toFixed(1) + "%";

      const sumStrength = signals.reduce((acc, sig) => acc + sig['SignalStrength'], 0);
      avgStrengthEl.textContent = (sumStrength / signals.length).toFixed(1);
    }

    function getFilteredAndSorted() {
      let items = signals.filter(sig => {
        const matchSearch = sig.Symbol.toLowerCase().includes(searchQuery);
        if (!matchSearch) return false;

        if (activeFilter === "near-buy") {
          return sig.Proximity <= 5.0;
        } else if (activeFilter === "strong") {
          return sig.SignalStrength >= 50.0;
        }
        return true;
      });

      items.sort((a, b) => {
        if (activeSort === "date-desc") {
          return b.SignalDate.localeCompare(a.SignalDate) || a.Proximity - b.Proximity;
        } else if (activeSort === "prox-asc") {
          return a.Proximity - b.Proximity;
        } else if (activeSort === "strength-desc") {
          return b.SignalStrength - a.SignalStrength;
        } else if (activeSort === "symbol-asc") {
          return a.Symbol.localeCompare(b.Symbol);
        }
        return 0;
      });

      return items;
    }

    function render() {
      const items = getFilteredAndSorted();

      if (items.length === 0) {
        gridContainer.classList.add("hidden");
        tableContainer.classList.add("hidden");
        emptyState.classList.remove("hidden");
        if (signals.length === 0) {
          document.getElementById("emptyTitle").textContent = "No Signals Today";
          document.getElementById("emptyText").textContent = "The market did not trigger any V20 strategy signals in today's scan.";
        } else {
          document.getElementById("emptyTitle").textContent = "No Matching Signals";
          document.getElementById("emptyText").textContent = "Try modifying your search query or filter pills to see other results.";
        }
        return;
      }

      emptyState.classList.add("hidden");

      if (activeView === "card") {
        gridContainer.classList.remove("hidden");
        tableContainer.classList.add("hidden");
        renderCards(items);
      } else {
        gridContainer.classList.add("hidden");
        tableContainer.classList.remove("hidden");
        renderTable(items);
      }
    }

    function renderCards(items) {
      gridContainer.innerHTML = items.map(sig => {
        const proxClass = sig.Proximity <= 5.0 ? 'near' : 'far';
        const isStrong = sig.SignalStrength >= 50.0;
        
        return `
          <div class="signal-card animate-fade-in">
            <div class="card-hdr">
              <a href="https://in.tradingview.com/chart/?symbol=NSE:${sig.Symbol}" target="_blank" class="symbol-badge">
                ${sig.Symbol} <i class="fas fa-external-link-alt"></i>
              </a>
              <span class="date-badge">${sig.SignalDate}</span>
            </div>
            
            ${isStrong ? `
              <div class="strength-indicator">
                <i class="fas fa-star"></i> Strong Signal
              </div>
            ` : ''}

            <div class="card-stats">
              <div class="stat-box">
                <span class="stat-label">Close Price</span>
                <span class="stat-value">&#8377;${sig.Close.toLocaleString('en-IN')}</span>
              </div>
              <div class="stat-box">
                <span class="stat-label">Proximity</span>
                <span class="stat-value proximity-value ${proxClass}">
                  ${sig.Proximity.toFixed(2)}%
                </span>
              </div>
              <div class="stat-box">
                <span class="stat-label">Buy Point (Low)</span>
                <span class="stat-value">&#8377;${sig.BuyAt.toLocaleString('en-IN')}</span>
              </div>
              <div class="stat-box">
                <span class="stat-label">Sell Point (High)</span>
                <span class="stat-value">&#8377;${sig.SellAt.toLocaleString('en-IN')}</span>
              </div>
              <div class="stat-box">
                <span class="stat-label">% Move</span>
                <span class="stat-value">${sig.PercentMove.toFixed(2)}%</span>
              </div>
              <div class="stat-box">
                <span class="stat-label">Strength Score</span>
                <span class="stat-value">${sig.SignalStrength.toFixed(1)}</span>
              </div>
            </div>

            <a href="https://in.tradingview.com/chart/?symbol=NSE:${sig.Symbol}" target="_blank" class="tv-link-btn">
              <i class="fas fa-chart-line"></i> View TV Chart
            </a>
          </div>
        `;
      }).join('');
    }

    function renderTable(items) {
      tableBody.innerHTML = items.map(sig => {
        const proxClass = sig.Proximity <= 5.0 ? 'td-proximity near' : 'td-proximity';
        const strengthClass = sig.SignalStrength >= 50.0 ? 'td-strength strong' : 'td-strength';
        
        return `
          <tr class="animate-fade-in">
            <td>${sig.SignalDate}</td>
            <td class="td-symbol">${sig.Symbol}</td>
            <td>&#8377;${sig.Close.toLocaleString('en-IN')}</td>
            <td>&#8377;${sig.BuyAt.toLocaleString('en-IN')}</td>
            <td>&#8377;${sig.SellAt.toLocaleString('en-IN')}</td>
            <td>${sig.PercentMove.toFixed(2)}%</td>
            <td class="${proxClass}">${sig.Proximity.toFixed(2)}%</td>
            <td class="${strengthClass}">${sig.SignalStrength.toFixed(1)}</td>
            <td>
              <a href="https://in.tradingview.com/chart/?symbol=NSE:${sig.Symbol}" target="_blank" class="table-tv-btn" title="Open TradingView Chart">
                <i class="fas fa-chart-line"></i>
              </a>
            </td>
          </tr>
        `;
      }).join('');
    }

    window.addEventListener("DOMContentLoaded", init);
  </script>
</body>
</html>"""
    
    html = html.replace("__SIGNALS_JSON__", signals_json)
    html = html.replace("__LATEST_DATE__", latest_date)
    
    Path(filename).write_text(html, encoding='utf-8')
    print(f"HTML dashboard saved -> {filename}")

def main():
    signals = []
    def process_stock(sym):
        logging.info(f"Checking: {sym}")
        df = download_data(sym)
        if df is None:
            return []
        return [
            {
                'SignalDate': sig_date.strftime('%Y-%m-%d'),
                'Symbol': sym,
                'BuyAt': buy,
                'SellAt': sell,
                'PercentMove': pct,
                'Close': close,
                'Proximity': round(prox, 2),
                'SignalStrength': score
            }
            for sig_date, buy, sell, pct, close, prox, score in find_v20_signals(df)
        ]

    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        results = list(tqdm(executor.map(process_stock, all_stocks), total=len(all_stocks), desc="Scanning stocks", ncols=80))
    signals = [sig for sublist in results for sig in sublist]

    if not signals:
        logging.info("No signals found.")
        save_html([], HTML_NAME)
        return

    # Sort: First sort by Proximity ascending
    signals.sort(key=lambda x: x['Proximity'])
    # Then sort by SignalDate descending (stable sort)
    signals.sort(key=lambda x: x['SignalDate'], reverse=True)

    save_html(signals, HTML_NAME)

if __name__ == "__main__":
    main()