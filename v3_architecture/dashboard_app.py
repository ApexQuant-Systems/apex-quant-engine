import os
import sys
import sqlite3
import pandas as pd
import numpy as np
import streamlit as st
from datetime import datetime, timezone

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT_DIR = os.path.dirname(BASE_DIR)
if ROOT_DIR not in sys.path:
    sys.path.append(ROOT_DIR)

st.set_page_config(page_title="Apex Quant OS v3.0", page_icon="🛰️", layout="wide")

DB_PATH = "./data/forward_testing_vault.db"

def load_live_database_rows():
    if not os.path.exists(DB_PATH): return pd.DataFrame()
    try:
        conn = sqlite3.connect(DB_PATH)
        df = pd.read_sql_query("SELECT * FROM live_book", conn)
        conn.close()
        return df
    except Exception: return pd.DataFrame()

def load_market_telemetry():
    if not os.path.exists(DB_PATH): return pd.DataFrame()
    try:
        conn = sqlite3.connect(DB_PATH)
        df = pd.read_sql_query("SELECT * FROM market_telemetry", conn)
        conn.close()
        return df
    except Exception: return pd.DataFrame()

def load_risk_alerts():
    """Extracts historical risk rejection exceptions from the storage layer."""
    if not os.path.exists(DB_PATH): return pd.DataFrame()
    try:
        conn = sqlite3.connect(DB_PATH)
        df = pd.read_sql_query("SELECT * FROM risk_alerts ORDER BY id DESC", conn)
        conn.close()
        return df
    except Exception: return pd.DataFrame()

def get_live_paper_wallet_balance():
    if not os.path.exists(DB_PATH): return 30000.0, 0.0
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='paper_wallet'")
        if not cursor.fetchone():
            conn.close()
            return 30000.0, 0.0
        cursor.execute("SELECT balance, initial_capital FROM paper_wallet WHERE account_id = 'APEX_PAPER_01'")
        row = cursor.fetchone()
        conn.close()
        if row:
            return row[0], row[0] - row[1]
        return 30000.0, 0.0
    except Exception: return 30000.0, 0.0

df_data = load_live_database_rows()
if df_data.empty:
    df_data = pd.DataFrame(columns=['id', 'asset', 'style', 'direction', 'entry_time', 'entry_price', 'sl', 'tp', 'current_sl', 'exit_time', 'realized_r', 'status'])

current_balance, closed_pnl_dollars = get_live_paper_wallet_balance()
df_closed = df_data[df_data['status'] == 'CLOSED'] if not df_data.empty else pd.DataFrame()
df_active = df_data[df_data['status'] == 'ACTIVE'] if not df_data.empty else pd.DataFrame()

st.sidebar.title("🛰️ Apex Quant OS v3.0")
st.sidebar.markdown("`SYSTEM REGIME: LOCAL VALIDATION`")
st.sidebar.markdown("---")
page = st.sidebar.radio("Application Navigation Terminal", ["1. Dashboard", "2. Markets", "3. Trades", "4. Strategies", "5. Analytics", "6. Risk Center", "7. Trade Journal", "8. Broker Center", "9. Settings", "10. System Health"])

clean_page_title = page.split(". ")[1]
st.title(f"📊 Apex Quant OS — {clean_page_title}")
st.markdown("---")

if "Dashboard" in page:
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Account Balance", f"${current_balance:,.2f}", f"${closed_pnl_dollars:+,.2f} Net PnL")
    col2.metric("Daily/Monthly Drawdown", "0.00%", "🛡️ Safe Zone")
    col3.metric("Portfolio Heat Ceiling", "6.0%", "Max Sizing Bound")
    col4.metric("Active Execution Slots", f"{len(df_active)} / 6 Engaged")
    st.subheader("📈 Forward Equity Curve Trajectory")
    if df_closed.empty: st.info("Awaiting closed forward operation metrics to populate equity trajectory curves.")
    else:
        df_closed_sorted = df_closed.sort_values('exit_time')
        df_closed_sorted['cum_r'] = df_closed_sorted['realized_r'].cumsum()
        st.line_chart(df_closed_sorted['cum_r'])

elif "Markets" in page:
    st.subheader("📡 Multi-Timeframe Structural Trend Scanner")
    df_markets = load_market_telemetry()
    if df_markets.empty:
        st.info("Awaiting initial background ticker stream telemetry...")
    else:
        st.dataframe(df_markets.rename(columns={'asset': 'Asset Ticker', 'asset_class': 'Asset Class', 'htf_bias': 'HTF Bias (4H)', 'mtf_trend': 'MTF Trend (1H)', 'ltf_trigger': 'LTF Trigger (15M)', 'last_price': 'Last Price', 'updated_at': 'Last Update (UTC)'}), use_container_width=True)

elif "Trades" in page:
    st.subheader("⚡ Runtime Transaction Ledger")
    if df_data.empty: st.info("The transaction journal ledger is currently empty.")
    else: st.dataframe(df_data.rename(columns={'id': 'Trade ID', 'asset': 'Asset', 'style': 'Strategy Set', 'direction': 'Direction', 'entry_price': 'Entry Price', 'sl': 'Initial SL', 'tp': 'Target TP', 'current_sl': 'Trailing SL', 'status': 'Position Status', 'realized_r': 'Realized R'}), use_container_width=True)

elif "Strategies" in page:
    st.subheader("🧠 Strategy Sandbox Performance")
    strategy_mapping = {"SET_1_MACRO_INVESTING": "Macro Investing", "SET_2_MEDIUM_SWING": "Medium Swing", "SET_3_SHORT_POSITION": "Short Position", "SET_4_INTRADAY_EXPANSION": "Intraday Expansion"}
    for key, name in strategy_mapping.items():
        st.markdown(f"### 🧱 Set: {name}")
        df_strat = df_data[df_data['style'] == key] if not df_data.empty else pd.DataFrame()
        df_strat_closed = df_strat[df_strat['status'] == 'CLOSED'] if not df_strat.empty else pd.DataFrame()
        trades_count = len(df_strat_closed)
        win_rate = (len(df_strat_closed[df_strat_closed['realized_r'] > 0]) / trades_count * 100) if trades_count > 0 else 0.0
        st.columns(3)[0].metric("Forward Trades", f"{trades_count}")
        st.columns(3)[1].metric("Forward Win Rate", f"{win_rate:.1f}%")
        st.columns(3)[2].metric("Forward Expectancy", f"{df_strat_closed['realized_r'].mean() if trades_count > 0 else 0.0:+.2f}R")
        st.markdown("---")

elif "Analytics" in page:
    st.subheader("🔬 High-Fidelity Attribution Scoring")
    col1, col2, col3 = st.columns(3)
    col1.metric("Total Trades", f"{len(df_closed)}")
    col2.metric("Win Rate", f"{(len(df_closed[df_closed['realized_r'] > 0]) / len(df_closed) * 100) if not df_closed.empty else 0.0:.1f}%")
    col3.metric("Profit Factor", f"{df_closed[df_closed['realized_r'] > 0]['realized_r'].sum() / abs(df_closed[df_closed['realized_r'] <= 0]['realized_r'].sum()) if not df_closed.empty and df_closed['realized_r'].sum() != 0 else 0.0:.2f}")

# ==========================================================================================
# MODULE 6: RISK CENTER (DYNAMIC EXCEPTION LINK)
# ==========================================================================================
elif "Risk Center" in page:
    st.subheader("🛡️ Automated Portfolio Risk Management Gateways")
    col1, col2, col3 = st.columns(3)
    col1.metric("Total Portfolio Heat Sizing", f"{len(df_active) * 1.0}%", "Ceiling Bounds: 6.0%")
    col2.metric("Daily Drawdown Breaker", "0.00%", "Threshold Trigger: 2.0%")
    col3.metric("Weekly Drawdown Breaker", "0.00%", "Threshold Trigger: 4.0%")
    
    st.markdown("---")
    st.subheader("🚨 Live Risk Exception Firewall Log")
    df_alerts = load_risk_alerts()
    if df_alerts.empty:
        st.success("🟢 No portfolio risk violations detected. System is running cleanly inside parameters.")
    else:
        st.warning("⚠️ Risk Firewall Interventions Recorded:")
        st.dataframe(df_alerts.rename(columns={'timestamp': 'Log Time (UTC)', 'asset': 'Asset Ticker', 'rule_violated': 'Firewall Action / Rule Blocked', 'current_price': 'Trigger Price'}), use_container_width=True)

elif "Trade Journal" in page:
    with st.form("Journal Entry Log"):
        asset_input = st.text_input("Asset Ticker Symbol", "BTCUSDT")
        strategy_select = st.selectbox("Strategy Source", ["SET_4_INTRADAY_EXPANSION"])
        setup_reason = st.text_area("Rationale")
        compliance_check = st.checkbox("Confirm Strict Mechanical Compliance")
        if st.form_submit_button("Submit Journal Entry") and compliance_check:
            st.success(f"📓 Journal entry processed for {asset_input}!")

elif "Broker Center" in page:
    st.info("Operating inside Mode A: Read-Only Telemetry (Local Validation Sandbox)")
    st.columns(2)[0].metric("Exchange Balance", "$0.00", "Disconnected")
    st.columns(2)[1].metric("Gateway Latency Sync", "0ms", "Offline")

elif "Settings" in page:
    st.text_input("Target DB Vault Source Path", value=os.path.abspath(DB_PATH))
    st.slider("Baseline Single-Slot Sizing Weight Risk Parameter (%)", min_value=0.1, max_value=2.0, value=1.0, step=0.1)

elif "System Health" in page:
    db_status = "🟢 Healthy" if os.path.exists(DB_PATH) else "🔴 Missing"
    st.success(f"### 💾 Storage Layer\n\n**Vault Status:** {db_status}\n\n**Type:** SQLite v3\n\n**Last Modification:** `{datetime.fromtimestamp(os.path.getmtime(DB_PATH), tz=timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC') if os.path.exists(DB_PATH) else 'N/A'}`")
