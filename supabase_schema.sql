-- ═══════════════════════════════════════════════════════════════
-- trading_os Dashboard — Supabase Schema
-- Run this in the Supabase SQL Editor (once)
-- ═══════════════════════════════════════════════════════════════

-- 1. System heartbeat (overwritten every 30s during market hours)
CREATE TABLE IF NOT EXISTS trading_state (
    id              INTEGER PRIMARY KEY DEFAULT 1,
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    market_open     BOOLEAN DEFAULT false,
    capital         REAL DEFAULT 0,
    deployed_pct    REAL DEFAULT 0,
    day_pnl         REAL DEFAULT 0,
    total_pnl       REAL DEFAULT 0,
    open_positions  INTEGER DEFAULT 0,
    positions_json  JSONB DEFAULT '[]'::jsonb,
    -- F&O specific
    fo_open_positions INTEGER DEFAULT 0,
    fo_margin_used  REAL DEFAULT 0,
    fo_day_pnl      REAL DEFAULT 0,
    fo_open_pnl     REAL DEFAULT 0,
    fo_positions_json JSONB DEFAULT '[]'::jsonb,
    -- System health
    strategy_active TEXT DEFAULT '',
    win_rate        REAL DEFAULT 0,
    total_trades    INTEGER DEFAULT 0,
    consecutive_losses INTEGER DEFAULT 0
);

-- Insert the single row
INSERT INTO trading_state (id) VALUES (1) ON CONFLICT (id) DO NOTHING;

-- 2. Trade log (append-only, ~5-10 rows/day)
CREATE TABLE IF NOT EXISTS trades (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    timestamp       TIMESTAMPTZ NOT NULL DEFAULT now(),
    strategy        TEXT NOT NULL,
    symbol          TEXT NOT NULL,
    direction       TEXT NOT NULL,
    entry_price     REAL NOT NULL,
    exit_price      REAL,
    quantity        INTEGER DEFAULT 0,
    pnl             REAL DEFAULT 0,
    pnl_pct         REAL DEFAULT 0,
    exit_reason     TEXT DEFAULT '',
    entry_reason    TEXT DEFAULT '',
    stop_loss       REAL DEFAULT 0,
    target          REAL DEFAULT 0,
    hold_duration_s INTEGER DEFAULT 0
);

-- Index for fast date-range queries
CREATE INDEX IF NOT EXISTS idx_trades_timestamp ON trades (timestamp DESC);
CREATE INDEX IF NOT EXISTS idx_trades_strategy ON trades (strategy);

-- 3. Signal log (append-only, ~20-50 rows/day)
CREATE TABLE IF NOT EXISTS signals (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    timestamp       TIMESTAMPTZ NOT NULL DEFAULT now(),
    strategy        TEXT NOT NULL DEFAULT 'gap_fade',
    symbol          TEXT NOT NULL,
    gap_pct         REAL DEFAULT 0,
    score           REAL DEFAULT 0,
    action          TEXT NOT NULL,
    filter_result   TEXT DEFAULT 'PASS',
    reason          TEXT DEFAULT '',
    was_traded      BOOLEAN DEFAULT false
);

CREATE INDEX IF NOT EXISTS idx_signals_timestamp ON signals (timestamp DESC);
CREATE INDEX IF NOT EXISTS idx_signals_strategy ON signals (strategy);

-- 4. Daily summary (1 row/day per strategy)
CREATE TABLE IF NOT EXISTS daily_summary (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    date            DATE NOT NULL,
    strategy        TEXT NOT NULL,
    trades          INTEGER DEFAULT 0,
    wins            INTEGER DEFAULT 0,
    losses          INTEGER DEFAULT 0,
    pnl             REAL DEFAULT 0,
    max_drawdown    REAL DEFAULT 0,
    capital_eod     REAL DEFAULT 0,
    win_rate        REAL DEFAULT 0,
    profit_factor   REAL DEFAULT 0,
    UNIQUE(date, strategy)
);

CREATE INDEX IF NOT EXISTS idx_daily_date ON daily_summary (date DESC);

-- 5. F&O trades (Iron Condor specific)
CREATE TABLE IF NOT EXISTS fo_trades (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    timestamp       TIMESTAMPTZ NOT NULL DEFAULT now(),
    symbol          TEXT NOT NULL,
    strategy        TEXT NOT NULL DEFAULT 'iron_condor',
    direction       TEXT DEFAULT 'CREDIT',
    legs_json       JSONB DEFAULT '[]'::jsonb,
    premium_collected REAL DEFAULT 0,
    margin_used     REAL DEFAULT 0,
    pnl             REAL DEFAULT 0,
    exit_reason     TEXT DEFAULT '',
    vix_at_entry    REAL DEFAULT 0,
    dte_at_entry    INTEGER DEFAULT 0,
    regime          TEXT DEFAULT '',
    hold_days       INTEGER DEFAULT 0
);

CREATE INDEX IF NOT EXISTS idx_fo_trades_timestamp ON fo_trades (timestamp DESC);

-- Enable Row Level Security (public read, authenticated write)
ALTER TABLE trading_state ENABLE ROW LEVEL SECURITY;
ALTER TABLE trades ENABLE ROW LEVEL SECURITY;
ALTER TABLE signals ENABLE ROW LEVEL SECURITY;
ALTER TABLE daily_summary ENABLE ROW LEVEL SECURITY;
ALTER TABLE fo_trades ENABLE ROW LEVEL SECURITY;

-- Allow anonymous read access (for the public dashboard)
CREATE POLICY "Public read trading_state" ON trading_state FOR SELECT USING (true);
CREATE POLICY "Public read trades" ON trades FOR SELECT USING (true);
CREATE POLICY "Public read signals" ON signals FOR SELECT USING (true);
CREATE POLICY "Public read daily_summary" ON daily_summary FOR SELECT USING (true);
CREATE POLICY "Public read fo_trades" ON fo_trades FOR SELECT USING (true);

-- Allow service role to insert/update (your laptop uses service_role key)
CREATE POLICY "Service write trading_state" ON trading_state FOR ALL USING (true) WITH CHECK (true);
CREATE POLICY "Service write trades" ON trades FOR ALL USING (true) WITH CHECK (true);
CREATE POLICY "Service write signals" ON signals FOR ALL USING (true) WITH CHECK (true);
CREATE POLICY "Service write daily_summary" ON daily_summary FOR ALL USING (true) WITH CHECK (true);
CREATE POLICY "Service write fo_trades" ON fo_trades FOR ALL USING (true) WITH CHECK (true);
