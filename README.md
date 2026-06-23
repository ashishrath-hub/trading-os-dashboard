# trading_os — Live Dashboard

Public Streamlit dashboard showing live trading performance.

## Architecture

```
Laptop (trading_os)              Cloud
─────────────────               ─────
main.py runs strategies    →    Supabase (free tier)
state_exporter pushes           ↓
  every 30s during market       Streamlit Community Cloud
                                reads + auto-refreshes
```

## Setup

### 1. Supabase
- Create project at https://supabase.com
- Run `supabase_schema.sql` in SQL Editor
- Copy URL + anon key to `.env`

### 2. Local (trading_os)
Add to `.env`:
```
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_KEY=your-anon-key
```

### 3. Streamlit Cloud
- Push this `dashboard/` folder to a separate GitHub repo
- Connect to Streamlit Community Cloud
- Add secrets: SUPABASE_URL, SUPABASE_KEY

## Pages
- 🏠 Live Overview — System status, P&L, open positions
- 📈 Gap Fade — Signals, trades, win rate, filter breakdown
- 🎯 F&O Portfolio — Iron Condors, Greeks, theta, VIX
- 🧠 Explainability — Why trades taken/skipped
- 📊 Performance — Equity curve, heatmap, drawdown
