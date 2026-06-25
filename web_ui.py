import streamlit as st
import pandas as pd
import sqlite3
import sqlglot
from sqlglot import exp
import shutil
import os

# ==========================================
# 1. 系統初始化與電信資料庫核心
# ==========================================
st.set_page_config(page_title="RF-Lens Pro: 射頻大師", layout="wide", page_icon="📡")

if 'sql_query' not in st.session_state:
    st.session_state.sql_query = "SELECT * FROM rf_sectors;"
if 'preview_passed' not in st.session_state:
    st.session_state.preview_passed = False

def init_rf_db():
    conn = sqlite3.connect("rf_master.db")
    conn.execute("CREATE TABLE IF NOT EXISTS cell_sites (site_id INTEGER PRIMARY KEY, site_name TEXT, lat FLOAT, lon FLOAT)")
    conn.execute("CREATE TABLE IF NOT EXISTS rf_sectors (sector_id INTEGER PRIMARY KEY, site_id INTEGER, band TEXT, azimuth INTEGER, tilt INTEGER)")
    conn.execute("CREATE TABLE IF NOT EXISTS drive_tests (log_id INTEGER PRIMARY KEY, sector_id INTEGER, rsrp INTEGER, sinr FLOAT)")
    
    if conn.execute("SELECT COUNT(*) FROM cell_sites").fetchone()[0] == 0:
        conn.executemany("INSERT INTO cell_sites VALUES (?, ?, ?, ?)", [(101, '台北信義站', 25.03, 121.56), (102, '台中港站', 24.26, 120.51)])
        conn.executemany("INSERT INTO rf_sectors VALUES (?, ?, ?, ?, ?)", [(1, 101, 'N78', 0, 3), (2, 101, 'N78', 120, 3), (3, 102, 'B28', 180, 5)])
        conn.executemany("INSERT INTO drive_tests VALUES (?, ?, ?, ?)", [(1, 1, -85, 15.5), (2, 1, -112, 2.1), (3, 3, -105, 8.4)])
        conn.commit()
    return conn

conn = init_rf_db()

# ==========================================
# 2. 互動式 ER 圖 (行動端極簡表格版)
# ==========================================
def render_interactive_er():
    st.markdown("""
    | 📡 基站 (`cell_sites`) | 📐 扇區 (`rf_sectors`) | 📈 路測 (`drive_tests`) |
    | :--- | :--- | :--- |
    | 🔑 **site_id** (主鍵) | 🔑 **sector_id** (主鍵) | 🔑 **log_id** (主鍵) |
    | 📝 site_name | 🔗 **site_id** (外鍵) | 🔗 **sector_id** (外鍵) |
    | 📍 lat, lon | 📻 band, azimuth, tilt | 📶 rsrp, sinr |
    """)
    st.caption("🔗 關聯血緣：基站 (1) ➔ (N) 扇區 (1) ➔ (N) 路測數據")

# ==========================================
# 3. 介面佈局：分頁系統
# ==========================================
tab_manual, tab_sandbox, tab_monitor = st.tabs(["📖 操作手冊", "🧪 互動沙盒", "📊 即時監控"])

# --- 分頁 1：完整操作手冊 ---
with tab_manual:
    st.header("📘 RF-Lens 系統操作指南")
    st.markdown("""
    ### 1. 射頻數據結構說明
    本系統採用 **三層關聯模型**：
    - **基站層 (`cell_sites`)**：物理位置與經緯度。
    - **扇區層 (`rf_sectors`)**：發射參數（頻段、角度）。
    - **路測層 (`drive_tests`)**：終端接收到的真實訊號品質。

    ### 2. 核心 SQL 指令操作
    - **查詢 (SELECT)**：用於尋找訊號劣化（如 RSRP < -110）的熱點。
    - **關聯 (JOIN)**：當你需要從「訊號數值」反查「天線方位角」時，必須透過 `sector_id` 串接兩表。
    - **防呆更新 (UPDATE)**：修改天線傾角 (`tilt`) 時，系統會強制要求預覽受影響範圍。
    """)
    st.success("💡 提示：點擊上方『互動沙盒』開始實際操作。")

# --- 分頁 2：互動沙盒 (解除強制分欄，適配手機版) ---
with tab_sandbox:
    # 將 Schema 收納進折疊面板，預設展開。手機上極度省空間。
    with st.expander("🕸️ 點擊展開/收合：射頻資料 Schema (ER 結構)", expanded=True):
        render_interactive_er()

    st.subheader("🛠️ SQL 射頻開發終端")
    
    # 快捷鍵
    c1, c2, c3 = st.columns(3)
    if c1.button("🔍 訊號查核"):
        st.session_state.sql_query = "SELECT s.site_name, r.band, d.rsrp FROM cell_sites s JOIN rf_sectors r ON s.site_id = r.site_id JOIN drive_tests d ON r.sector_id = d.sector_id WHERE d.rsrp < -100;"
    if c2.button("📐 批次調整"):
        st.session_state.sql_query = "UPDATE rf_sectors SET azimuth = 180 WHERE site_id = 101;"
    if c3.button("🔄 重置"):
        st.session_state.sql_query = "SELECT * FROM rf_sectors;"

    query_input = st.text_area("SQL 編輯區", value=st.session_state.sql_query, height=120)

    # 執行邏輯
    b1, b2 = st.columns(2)
    with b1:
        if st.button("👁️ 安全預覽 (Dry Run)", use_container_width=True):
            try:
                parsed = sqlglot.parse_one(query_input)
                if isinstance(parsed, (exp.Update, exp.Delete)):
                    where = parsed.args.get("where")
                    if not where: st.error("🚨 警告：偵測到全表修改，已自動攔截！")
                    else:
                        df = pd.read_sql_query(f"SELECT * FROM {parsed.find(exp.Table).name} {where}", conn)
                        st.warning(f"⚠️ 預覽：即時影響 {len(df)} 筆數據。")
                        st.dataframe(df, use_container_width=True)
                        st.session_state.preview_passed = True
                elif isinstance(parsed, exp.Select):
                    st.dataframe(pd.read_sql_query(query_input, conn), use_container_width=True)
            except Exception as e: st.error(f"解析錯誤: {e}")
    
    with b2:
        if st.button("⚡ 正式執行並備份", type="primary", disabled=not st.session_state.preview_passed, use_container_width=True):
            shutil.copy("rf_master.db", "rf_backup.db")
            conn.execute(query_input)
            conn.commit()
            st.success("✅ 執行成功！")
            st.session_state.preview_passed = False
            st.balloons()
            
    # 一鍵復原按鈕
    if os.path.exists("rf_backup.db"):
        if st.button("⏪ 發現錯誤？一鍵復原 (Undo)", use_container_width=True):
            conn.close()
            shutil.copy("rf_backup.db", "rf_master.db")
            conn = init_rf_db()
            st.toast("⏪ 已成功回溯至上一個狀態！", icon="⏳")
            st.rerun()

# --- 分頁 3：即時數據快照 ---
with tab_monitor:
    st.subheader("📊 數據全視角透視 (Live Metrics)")
    st.write("**📡 基站表 (cell_sites)**")
    st.dataframe(pd.read_sql_query("SELECT * FROM cell_sites", conn), use_container_width=True)
    st.write("**📐 扇區表 (rf_sectors)**")
    st.dataframe(pd.read_sql_query("SELECT * FROM rf_sectors", conn), use_container_width=True)
    st.write("**📈 路測表 (drive_tests)**")
    st.dataframe(pd.read_sql_query("SELECT * FROM drive_tests", conn), use_container_width=True)
