"""
trading_os — Live Dashboard
============================
Public Streamlit dashboard showing live trading performance.
Reads from Supabase (pushed every 30s by local trading system).

Deploy: Streamlit Community Cloud (free)
"""
import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
from datetime import datetime, timedelta, date
from supabase import create_client

# ── Page config ───────────────────────────────────────────────
st.set_page_config(
    page_title="trading_os — AI Hedge Fund",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="collapsed",
)


# ── Supabase connection ───────────────────────────────────────
@st.cache_resource
def get_supabase():
    url = st.secrets["SUPABASE_URL"]
    key = st.secrets["SUPABASE_KEY"]
    return create_client(url, key)


def fetch_state():
    """Fetch current trading state."""
    sb = get_supabase()
    res = sb.table("trading_state").select("*").eq("id", 1).execute()
    if res.data:
        return res.data[0]
    return {}


def fetch_trades(days=30):
    """Fetch recent trades."""
    sb = get_supabase()
    since = (datetime.now() - timedelta(days=days)).isoformat()
    res = sb.table("trades").select("*").gte("timestamp", since).order("timestamp", desc=True).execute()
    return pd.DataFrame(res.data) if res.data else pd.DataFrame()


def fetch_signals(days=7):
    """Fetch recent signals."""
    sb = get_supabase()
    since = (datetime.now() - timedelta(days=days)).isoformat()
    res = sb.table("signals").select("*").gte("timestamp", since).order("timestamp", desc=True).execute()
    return pd.DataFrame(res.data) if res.data else pd.DataFrame()


def fetch_daily_summary(days=90):
    """Fetch daily summary for equity curve."""
    sb = get_supabase()
    since = (date.today() - timedelta(days=days)).isoformat()
    res = sb.table("daily_summary").select("*").gte("date", since).order("date").execute()
    return pd.DataFrame(res.data) if res.data else pd.DataFrame()


def fetch_fo_trades(days=90):
    """Fetch F&O trades."""
    sb = get_supabase()
    since = (datetime.now() - timedelta(days=days)).isoformat()
    res = sb.table("fo_trades").select("*").gte("timestamp", since).order("timestamp", desc=True).execute()
    return pd.DataFrame(res.data) if res.data else pd.DataFrame()


# ── Navigation ────────────────────────────────────────────────
pages = {
    "🏠 Live Overview": "overview",
    "🎯 F&O Portfolio": "fno",
    "🧠 Explainability": "explainability",
    "📊 Performance": "performance",
}

# Sidebar navigation
with st.sidebar:
    st.title("trading_os")
    st.caption("AI Hedge Fund — NSE India")
    selected = st.radio("Navigate", list(pages.keys()), label_visibility="hidden")
    page = pages[selected]

    st.divider()
    st.caption("Auto-refreshes every 30s")
    st.caption("Data pushed from local system")


# ═══════════════════════════════════════════════════════════════
# PAGE: LIVE OVERVIEW
# ═══════════════════════════════════════════════════════════════

def render_overview():
    st.title("🏠 Live Trading Overview")

    @st.fragment(run_every=30)
    def live_metrics():
        state = fetch_state()
        if not state:
            st.warning("No data yet. System hasn't pushed state.")
            return

        # Status indicator
        updated = state.get("updated_at", "")
        if updated:
            try:
                dt = datetime.fromisoformat(updated.replace("Z", "+00:00"))
                age_s = (datetime.now(dt.tzinfo) - dt).total_seconds()
                if age_s < 120:
                    st.success(f"🟢 System LIVE — last update {int(age_s)}s ago")
                elif age_s < 600:
                    st.warning(f"🟡 Last update {int(age_s/60)} min ago")
                else:
                    st.error(f"🔴 System offline — last seen {int(age_s/3600)}h ago")
            except Exception:
                st.info(f"Last update: {updated}")

        market = "🟢 OPEN" if state.get("market_open") else "🔴 CLOSED"
        strategy = state.get("strategy_active", "").replace("_", " ").title()

        # ── Top metrics row ───────────────────────────────────
        col1, col2, col3, col4, col5 = st.columns(5)
        with col1:
            st.metric("Market", market)
        with col2:
            day_pnl = state.get("day_pnl", 0)
            st.metric("Day P&L", f"₹{day_pnl:+,.0f}",
                      delta=f"{day_pnl:+,.0f}")
        with col3:
            st.metric("Total P&L", f"₹{state.get('total_pnl', 0):+,.0f}")
        with col4:
            wr = state.get("win_rate", 0) * 100
            st.metric("Win Rate", f"{wr:.1f}%")
        with col5:
            st.metric("Trades", state.get("total_trades", 0))

        # ── Second row: F&O + Capital ─────────────────────────
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            fo_pnl = state.get("fo_day_pnl", 0) + state.get("fo_open_pnl", 0)
            st.metric("F&O P&L", f"₹{fo_pnl:+,.0f}")
        with col2:
            st.metric("Strategy", strategy or "—")
        with col3:
            # Exclude gap_fade from position count
            eq_positions = [p for p in state.get("positions_json", [])
                           if "gap_fade" not in p.get("strategy", "")]
            st.metric("Open Positions",
                      f"{len(eq_positions)} eq + "
                      f"{state.get('fo_open_positions', 0)} fo")
        with col4:
            st.metric("Capital Deployed", f"{state.get('deployed_pct', 0):.0f}%")

        # ── Open positions table ──────────────────────────────
        positions = state.get("positions_json", [])
        fo_positions = state.get("fo_positions_json", [])

        if positions:
            # Filter out gap_fade positions (hidden temporarily)
            positions = [p for p in positions if "gap_fade" not in p.get("strategy", "")]

        if positions:
            st.subheader("Equity Positions")
            df_pos = pd.DataFrame(positions)
            if not df_pos.empty:
                df_pos["P&L%"] = df_pos["pnl_pct"].apply(lambda x: f"{x:+.2f}%")
                st.dataframe(
                    df_pos[["symbol", "direction", "strategy", "entry_price",
                            "current_price", "P&L%", "stop_loss", "target"]],
                    use_container_width=True,
                    hide_index=True,
                )

        if fo_positions:
            st.subheader("F&O Positions")
            for pos in fo_positions:
                with st.expander(
                    f"{pos['symbol']} {pos['strategy']} | "
                    f"DTE: {pos.get('dte', '?')} | "
                    f"P&L: ₹{pos.get('net_pnl', 0):+,.0f}"
                ):
                    col1, col2, col3 = st.columns(3)
                    col1.metric("Premium", f"₹{pos.get('premium_collected', 0):,.0f}")
                    col2.metric("Margin", f"₹{pos.get('margin_used', 0):,.0f}")
                    col3.metric("VIX@Entry", f"{pos.get('vix', 0):.1f}")
                    if pos.get("legs"):
                        st.dataframe(pd.DataFrame(pos["legs"]),
                                     use_container_width=True, hide_index=True)

    live_metrics()


# ═══════════════════════════════════════════════════════════════
# PAGE: GAP FADE
# ═══════════════════════════════════════════════════════════════

def render_gap_fade():
    st.title("📈 Gap Fade Portfolio")
    st.caption("36 stocks | 98%+ WR | Opening gap mean reversion")

    @st.fragment(run_every=30)
    def gap_fade_live():
        # Today's signals
        signals = fetch_signals(days=1)
        trades = fetch_trades(days=30)

        # Filter gap fade only
        if not trades.empty and "strategy" in trades.columns:
            gf_trades = trades[trades["strategy"].str.contains("gap_fade", na=False)]
        else:
            gf_trades = pd.DataFrame()

        if not signals.empty and "strategy" in signals.columns:
            gf_signals = signals[signals["strategy"].str.contains("gap_fade", na=False)]
        else:
            gf_signals = pd.DataFrame()

        # Metrics row
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            total = len(gf_trades)
            st.metric("Total Trades (30d)", total)
        with col2:
            if not gf_trades.empty and "pnl" in gf_trades.columns:
                wins = (gf_trades["pnl"] > 0).sum()
                wr = wins / len(gf_trades) * 100 if len(gf_trades) > 0 else 0
                st.metric("Win Rate", f"{wr:.1f}%")
            else:
                st.metric("Win Rate", "—")
        with col3:
            if not gf_trades.empty and "pnl" in gf_trades.columns:
                total_pnl = gf_trades["pnl"].sum()
                st.metric("Total P&L", f"₹{total_pnl:+,.0f}")
            else:
                st.metric("Total P&L", "—")
        with col4:
            today_signals = len(gf_signals)
            st.metric("Signals Today", today_signals)

        # Today's signals table
        if not gf_signals.empty:
            st.subheader("Today's Signals")
            display_cols = ["symbol", "gap_pct", "score", "action",
                           "filter_result", "reason", "was_traded"]
            available = [c for c in display_cols if c in gf_signals.columns]
            st.dataframe(gf_signals[available], use_container_width=True,
                         hide_index=True)

        # Trade history
        if not gf_trades.empty:
            st.subheader("Recent Trades")
            display_cols = ["timestamp", "symbol", "direction", "entry_price",
                           "exit_price", "pnl", "pnl_pct", "exit_reason"]
            available = [c for c in display_cols if c in gf_trades.columns]
            st.dataframe(gf_trades[available].head(20),
                         use_container_width=True, hide_index=True)

            # Gap vs P&L scatter
            if "gap_pct" in gf_signals.columns and "pnl" in gf_trades.columns:
                st.subheader("Gap Size vs P&L")
                # Merge signals with trades on symbol+date (simplified)
                fig = px.scatter(gf_trades, x="pnl_pct", y="pnl",
                                 color="direction",
                                 hover_data=["symbol", "exit_reason"],
                                 title="Trade P&L Distribution")
                fig.update_layout(template="plotly_dark")
                st.plotly_chart(fig, use_container_width=True)

            # Filter breakdown
            if not gf_signals.empty and "filter_result" in gf_signals.columns:
                st.subheader("Filter Breakdown")
                filter_counts = gf_signals["filter_result"].value_counts()
                fig = px.pie(values=filter_counts.values,
                             names=filter_counts.index,
                             title="Signal Filter Results")
                fig.update_layout(template="plotly_dark")
                st.plotly_chart(fig, use_container_width=True)

    gap_fade_live()


# ═══════════════════════════════════════════════════════════════
# PAGE: F&O PORTFOLIO
# ═══════════════════════════════════════════════════════════════

def render_fno():
    st.title("🎯 F&O Iron Condor Portfolio")
    st.caption("NIFTY + BANKNIFTY + Stock Options | Positional 2-7 day hold")

    @st.fragment(run_every=30)
    def fno_live():
        state = fetch_state()
        fo_trades = fetch_fo_trades(days=90)

        # Live F&O metrics
        col1, col2, col3, col4, col5 = st.columns(5)
        with col1:
            st.metric("Open Positions", state.get("fo_open_positions", 0))
        with col2:
            st.metric("Margin Used", f"₹{state.get('fo_margin_used', 0):,.0f}")
        with col3:
            st.metric("Open P&L", f"₹{state.get('fo_open_pnl', 0):+,.0f}")
        with col4:
            st.metric("Day P&L", f"₹{state.get('fo_day_pnl', 0):+,.0f}")
        with col5:
            if not fo_trades.empty and "pnl" in fo_trades.columns:
                total_fo_pnl = fo_trades["pnl"].sum()
                st.metric("Total P&L", f"₹{total_fo_pnl:+,.0f}")
            else:
                st.metric("Total P&L", "—")

        # Active positions
        fo_positions = state.get("fo_positions_json", [])
        if fo_positions:
            st.subheader("Active Positions")
            for pos in fo_positions:
                pnl_color = "🟢" if pos.get("net_pnl", 0) >= 0 else "🔴"
                with st.expander(
                    f"{pnl_color} {pos['symbol']} | {pos['strategy']} | "
                    f"DTE {pos.get('dte', '?')}d | P&L ₹{pos.get('net_pnl', 0):+,.0f}"
                ):
                    c1, c2, c3, c4 = st.columns(4)
                    c1.metric("Premium Collected", f"₹{pos.get('premium_collected', 0):,.0f}")
                    c2.metric("Margin", f"₹{pos.get('margin_used', 0):,.0f}")
                    c3.metric("VIX at Entry", f"{pos.get('vix', 0):.1f}")
                    c4.metric("Regime", pos.get("regime", "—").title())

                    # Legs table
                    if pos.get("legs"):
                        legs_df = pd.DataFrame(pos["legs"])
                        st.dataframe(legs_df, use_container_width=True,
                                     hide_index=True)

        # Trade history
        if not fo_trades.empty:
            st.subheader("Closed F&O Trades")
            display_cols = ["timestamp", "symbol", "strategy", "pnl",
                           "premium_collected", "margin_used", "hold_days",
                           "exit_reason", "vix_at_entry", "regime"]
            available = [c for c in display_cols if c in fo_trades.columns]
            st.dataframe(fo_trades[available].head(20),
                         use_container_width=True, hide_index=True)

            # P&L waterfall
            if "pnl" in fo_trades.columns and len(fo_trades) > 1:
                st.subheader("P&L Waterfall")
                fo_sorted = fo_trades.sort_values("timestamp")
                fo_sorted["cumulative_pnl"] = fo_sorted["pnl"].cumsum()
                fig = go.Figure()
                fig.add_trace(go.Bar(
                    x=list(range(len(fo_sorted))),
                    y=fo_sorted["pnl"],
                    marker_color=["#10b981" if p > 0 else "#ef4444"
                                  for p in fo_sorted["pnl"]],
                    name="Trade P&L",
                ))
                fig.add_trace(go.Scatter(
                    x=list(range(len(fo_sorted))),
                    y=fo_sorted["cumulative_pnl"],
                    mode="lines",
                    name="Cumulative",
                    line=dict(color="#3b82f6", width=2),
                ))
                fig.update_layout(template="plotly_dark",
                                  title="Trade-by-Trade P&L")
                st.plotly_chart(fig, use_container_width=True)

    fno_live()


# ═══════════════════════════════════════════════════════════════
# PAGE: EXPLAINABILITY
# ═══════════════════════════════════════════════════════════════

def render_explainability():
    st.title("🧠 Trade Explainability")
    st.caption("Why each trade was taken or skipped")

    signals = fetch_signals(days=7)
    trades = fetch_trades(days=7)

    if signals.empty and trades.empty:
        st.info("No signals or trades in the last 7 days.")
        return

    # Trades taken — with entry reason
    if not trades.empty:
        st.subheader("Trades Taken — Why")
        for _, row in trades.head(15).iterrows():
            pnl = row.get("pnl", 0)
            icon = "✅" if pnl > 0 else "❌"
            sym = row.get("symbol", "?")
            direction = row.get("direction", "?")
            strategy = row.get("strategy", "?")
            reason = row.get("entry_reason", "") or row.get("exit_reason", "")

            with st.expander(
                f"{icon} {sym} {direction} | {strategy} | ₹{pnl:+,.0f}"
            ):
                c1, c2, c3, c4 = st.columns(4)
                c1.write(f"**Entry:** ₹{row.get('entry_price', 0):,.2f}")
                c2.write(f"**Exit:** ₹{row.get('exit_price', 0):,.2f}")
                c3.write(f"**P&L%:** {row.get('pnl_pct', 0):+.2f}%")
                c4.write(f"**Hold:** {row.get('hold_duration_s', 0)//60} min")
                st.write(f"**Exit Reason:** {row.get('exit_reason', '—')}")
                if reason:
                    st.write(f"**Entry Signal:** {reason}")

    # Signals rejected
    if not signals.empty:
        rejected = signals[signals.get("was_traded", pd.Series([True]*len(signals))) == False]
        if not rejected.empty:
            st.subheader("Signals Rejected — Why")
            for _, row in rejected.head(20).iterrows():
                st.write(
                    f"🚫 **{row.get('symbol', '?')}** "
                    f"(gap {row.get('gap_pct', 0):+.2f}%) — "
                    f"*{row.get('filter_result', '')}*: {row.get('reason', '')}"
                )


# ═══════════════════════════════════════════════════════════════
# PAGE: PERFORMANCE
# ═══════════════════════════════════════════════════════════════

def render_performance():
    st.title("📊 Performance History")

    daily = fetch_daily_summary(days=90)
    trades = fetch_trades(days=90)
    fo_trades = fetch_fo_trades(days=90)

    if daily.empty and trades.empty:
        st.info("No performance data yet. Run the system for a few days.")
        return

    # ── Equity Curve ──────────────────────────────────────────
    if not daily.empty and "pnl" in daily.columns:
        st.subheader("Equity Curve")
        daily_sorted = daily.sort_values("date")
        daily_sorted["cumulative_pnl"] = daily_sorted["pnl"].cumsum()

        fig = go.Figure()
        fig.add_trace(go.Scatter(
            x=daily_sorted["date"],
            y=daily_sorted["cumulative_pnl"],
            mode="lines+markers",
            fill="tozeroy",
            line=dict(color="#10b981", width=2),
            name="Cumulative P&L",
        ))
        fig.update_layout(
            template="plotly_dark",
            title="Cumulative P&L (All Strategies)",
            yaxis_title="P&L (₹)",
            xaxis_title="Date",
        )
        st.plotly_chart(fig, use_container_width=True)

    # ── Monthly Heatmap ───────────────────────────────────────
    if not trades.empty and "timestamp" in trades.columns and "pnl" in trades.columns:
        st.subheader("Monthly P&L Heatmap")
        trades_copy = trades.copy()
        trades_copy["date"] = pd.to_datetime(trades_copy["timestamp"]).dt.date
        trades_copy["month"] = pd.to_datetime(trades_copy["timestamp"]).dt.to_period("M").astype(str)

        monthly = trades_copy.groupby("month")["pnl"].sum().reset_index()
        if len(monthly) > 1:
            fig = px.bar(monthly, x="month", y="pnl",
                         color="pnl",
                         color_continuous_scale=["#ef4444", "#fbbf24", "#10b981"],
                         title="Monthly P&L")
            fig.update_layout(template="plotly_dark")
            st.plotly_chart(fig, use_container_width=True)

    # ── Drawdown Chart ────────────────────────────────────────
    if not trades.empty and "pnl" in trades.columns:
        st.subheader("Drawdown")
        trades_sorted = trades.sort_values("timestamp")
        cum_pnl = trades_sorted["pnl"].cumsum()
        running_max = cum_pnl.cummax()
        drawdown = cum_pnl - running_max

        fig = go.Figure()
        fig.add_trace(go.Scatter(
            x=list(range(len(drawdown))),
            y=drawdown,
            fill="tozeroy",
            line=dict(color="#ef4444", width=1),
            name="Drawdown",
        ))
        fig.update_layout(template="plotly_dark",
                          title="Drawdown from Peak",
                          yaxis_title="Drawdown (₹)")
        st.plotly_chart(fig, use_container_width=True)

    # ── Win Rate Trend ────────────────────────────────────────
    if not trades.empty and "pnl" in trades.columns and len(trades) >= 5:
        st.subheader("Rolling Win Rate (20 trades)")
        trades_sorted = trades.sort_values("timestamp").reset_index(drop=True)
        wins = (trades_sorted["pnl"] > 0).astype(int)
        rolling_wr = wins.rolling(window=min(20, len(wins))).mean() * 100

        fig = go.Figure()
        fig.add_trace(go.Scatter(
            x=list(range(len(rolling_wr))),
            y=rolling_wr,
            mode="lines",
            line=dict(color="#3b82f6", width=2),
            name="Win Rate %",
        ))
        fig.add_hline(y=50, line_dash="dash", line_color="#6b7280")
        fig.update_layout(template="plotly_dark",
                          title="Rolling 20-Trade Win Rate",
                          yaxis_title="Win Rate %",
                          yaxis_range=[0, 100])
        st.plotly_chart(fig, use_container_width=True)

    # ── Best & Worst Trades ───────────────────────────────────
    if not trades.empty and "pnl" in trades.columns:
        st.subheader("Best & Worst Trades")
        col1, col2 = st.columns(2)
        with col1:
            st.write("**Top 5 Winners**")
            best = trades.nlargest(5, "pnl")[["symbol", "strategy", "pnl", "pnl_pct", "direction"]]
            st.dataframe(best, use_container_width=True, hide_index=True)
        with col2:
            st.write("**Top 5 Losers**")
            worst = trades.nsmallest(5, "pnl")[["symbol", "strategy", "pnl", "pnl_pct", "direction"]]
            st.dataframe(worst, use_container_width=True, hide_index=True)

    # ── Summary Stats ─────────────────────────────────────────
    st.subheader("Overall Statistics")
    all_trades = pd.concat([trades, fo_trades]) if not fo_trades.empty else trades
    if not all_trades.empty and "pnl" in all_trades.columns:
        col1, col2, col3, col4, col5 = st.columns(5)
        total_pnl = all_trades["pnl"].sum()
        wins = (all_trades["pnl"] > 0).sum()
        losses = (all_trades["pnl"] <= 0).sum()
        avg_win = all_trades[all_trades["pnl"] > 0]["pnl"].mean() if wins > 0 else 0
        avg_loss = all_trades[all_trades["pnl"] <= 0]["pnl"].mean() if losses > 0 else 0

        col1.metric("Total Trades", len(all_trades))
        col2.metric("Win Rate", f"{wins/len(all_trades)*100:.1f}%")
        col3.metric("Total P&L", f"₹{total_pnl:+,.0f}")
        col4.metric("Avg Win", f"₹{avg_win:+,.0f}")
        col5.metric("Avg Loss", f"₹{avg_loss:,.0f}")


# ═══════════════════════════════════════════════════════════════
# ROUTER
# ═══════════════════════════════════════════════════════════════

if page == "overview":
    render_overview()
elif page == "fno":
    render_fno()
elif page == "explainability":
    render_explainability()
elif page == "performance":
    render_performance()
