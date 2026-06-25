import streamlit as st
import pandas as pd
import sqlite3
import sqlglot
from sqlglot import exp
import shutil
import os

# ==========================================
# 1. 系統環境與資料庫核心初始化
# ==========================================
st.set_page_config(page_title="RF-Lens Ultimate", layout="wide", page_icon="📡")

if 'sql_query' not in st.session_state:
    st.session_state.sql_query = "SELECT * FROM rf_sectors;"
if 'preview_passed' not in st.session_state:
    st.session_state.preview_passed = False

def update_query(new_query):
    """一鍵注入語法並安全上鎖"""
    st.session_state.sql_query = new_query
    st.session_state.preview_passed = False

def init_rf_db():
    """建立具備高階關聯性的 RF 電信資料庫"""
    conn = sqlite3.connect("rf_ultimate.db")
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
# 2. 核心功能分頁系統
# ==========================================
tab_manual, tab_sandbox, tab_monitor = st.tabs(["📖 完整操作手冊", "🧪 全方位互動沙盒", "📊 即時數據監控"])

# --- 分頁 1：完整操作手冊 ---
with tab_manual:
    st.header("📘 RF-Lens 終極全方位操作手冊")
    st.markdown("""
    ### 📡 一、射頻數據結構與型態定義 (Schema)
    本系統完全對應真實電信基站維運之空間與物理參數：
    1. **基站資料表 (`cell_sites`)**
       - `site_id` (INTEGER, PK): 基站唯一編號
       - `site_name` (TEXT): 基站基地名稱
       - `lat / lon` (FLOAT): 空間經緯度座標
    2. **射頻扇區表 (`rf_sectors`)**
       - `sector_id` (INTEGER, PK): 射頻天線扇區編號
       - `site_id` (INTEGER, FK): 關聯之實體基站
       - `band` (TEXT): 運行頻段 (如 5G N78)
       - `azimuth / tilt` (INTEGER): 方位角 / 下傾角 (物理微調控制項)
    3. **路測品質表 (`drive_tests`)**
       - `log_id` (INTEGER, PK): 訊號紀錄流編號
       - `sector_id` (INTEGER, FK): 接收訊號之對應天線
       - `rsrp` (INTEGER): 參考訊號接收功率 (dBm，越接近 0 訊號越強)
       - `sinr` (FLOAT): 信噪比 (越高代表抗干擾能力越強)

    ### 🛠️ 二、核心操作指南
    - **安全防禦機制**：進行 `UPDATE` 或 `DELETE` 時，系統會強制開啟沙盒攔截，未點擊「安全預覽」前，正式執行按鈕將維持灰色鎖定。
    - **效能分析引擎**：每次預覽會自動執行 `EXPLAIN QUERY PLAN`，若寫出缺乏 Index 的「全表掃描 (SCAN TABLE)」低效語法，系統會即時亮起黃燈警告。
    - **時光機回溯**：每次正式執行寫入前，系統會在背景複製 `.db` 快照，若操作失誤，可一鍵點擊 `Undo` 完美還原。
    """)

# --- 分頁 2：全方位互動沙盒 ---
with tab_sandbox:
    # 響應式行動端 ER 結構表
    with st.expander("🕸️ 射頻資料庫實體關聯 (ER Schema) — 行動端最佳化", expanded=True):
        st.markdown("""
        | 📡 基站表 (`cell_sites`) | 📐 扇區表 (`rf_sectors`) | 📈 路測表 (`drive_tests`) |
        | :--- | :--- | :--- |
        | 🔑 **site_id** `INT` (主鍵) | 🔑 **sector_id** `INT` (主鍵) | 🔑 **log_id** `INT` (主鍵) |
        | 📝 site_name `TEXT` | 🔗 **site_id** `INT` (外鍵 ➜ 基站) | 🔗 **sector_id** `INT` (外鍵 ➜ 扇區) |
        | 📍 lat, lon `FLOAT` | 📻 band `TEXT` / azimuth, tilt `INT` | 📶 rsrp `INT` / sinr `FLOAT` |
        """)
        st.caption("🔗 資料串接血緣：基站 (1) ➔ (N) 扇區 (1) ➔ (N) 路測數據")

    st.subheader("🛠️ 射頻 SQL 開發終端機")
    
    # 語法庫快捷鍵（基礎到進階全涵蓋）
    st.markdown("**💡 點擊一鍵帶入實戰 SQL 指令：**")
    g1, g2, g3 = st.columns(3)
    g4, g5, g6 = st.columns(3)
    
    g1.button("📄 1. 基礎查詢 (SELECT)", on_click=update_query, args=("SELECT * FROM drive_tests WHERE rsrp < -110;",), use_container_width=True)
    g2.button("➕ 2. 數據注入 (INSERT)", on_click=update_query, args=("INSERT INTO rf_sectors (site_id, band, azimuth, tilt) VALUES (102, 'N78', 90, 4);",), use_container_width=True)
    g3.button("✏️ 3. 安全更新 (UPDATE)", on_click=update_query, args=("UPDATE rf_sectors SET tilt = 6 WHERE sector_id = 1;",), use_container_width=True)
    g4.button("🔗 4. 三表聯查 (INNER JOIN)", on_click=update_query, args=("SELECT s.site_name, r.band, d.rsrp \nFROM cell_sites s \nJOIN rf_sectors r ON s.site_id = r.site_id \nJOIN drive_tests d ON r.sector_id = d.sector_id;",), use_container_width=True)
    g5.button("📊 5. 巨觀彙總 (GROUP BY)", on_click=update_query, args=("SELECT sector_id, COUNT(*) as 測點數, AVG(rsrp) as 平均訊號 \nFROM drive_tests \nGROUP BY sector_id;",), use_container_width=True)
    g6.button("🚀 6. 高階架構 (WITH / CTE)", on_click=update_query, args=("WITH LowSignal AS (\n    SELECT sector_id FROM drive_tests WHERE rsrp < -100\n)\nSELECT r.* FROM rf_sectors r \nJOIN LowSignal l ON r.sector_id = l.sector_id;",), use_container_width=True)

    query_input = st.text_area("SQL 編輯區 (支援手動修改)", value=st.session_state.sql_query, height=140)

    # 按鈕控制
    b1, b2 = st.columns(2)
    with b1:
        if st.button("👁️ 1. 安全預覽與效能分析 (Dry Run)", use_container_width=True):
            try:
                parsed = sqlglot.parse_one(query_input)
                
                # 效能 X 光機 (EXPLAIN)
                plan_df = pd.read_sql_query(f"EXPLAIN QUERY PLAN {query_input}", conn)
                if any("SCAN TABLE" in row['detail'] for _, row in plan_df.iterrows()):
                    st.warning("⚠️ [效能警示] 偵測到全表掃描 (SCAN TABLE)，大數據環境下建議針對 FK 建立 Index。")
                else:
                    st.success("⚡ [效能優良] 查詢計畫已最佳化。")
                
                # 安全防呆攔截
                if isinstance(parsed, (exp.Update, exp.Delete)):
                    where = parsed.args.get("where")
                    if not where: 
                        st.error("🚨 嚴重攔截：禁止無 WHERE 條件的全表破壞性操作！")
                    else:
                        df = pd.read_sql_query(f"SELECT * FROM {parsed.find(exp.Table).name} {where}", conn)
                        st.warning(f"⚠️ 安全防護：本次操作預計影響 {len(df)} 筆數據，請於右側確認執行。")
                        st.dataframe(df, use_container_width=True)
                        st.session_state.preview_passed = True
                else:
                    # SELECT 查詢直接呈現
                    st.dataframe(pd.read_sql_query(query_input, conn), use_container_width=True)
            except Exception as e: 
                st.error(f"語法解析錯誤: {e}")
    
    with b2:
        is_disabled = not st.session_state.preview_passed
        if st.button("⚡ 2. 確認無誤，正式寫入資料庫", type="primary", disabled=is_disabled, use_container_width=True):
            try:
                shutil.copy("rf_ultimate.db", "rf_ultimate_backup.db") # 瞬間建立時光機快照
                conn.execute(query_input)
                conn.commit()
                st.success("💥 數據寫入成功！")
                st.session_state.preview_passed = False
                st.balloons()
            except Exception as e: 
                st.error(f"執行失敗: {e}")
                
        if os.path.exists("rf_ultimate_backup.db"):
            if st.button("⏪ 發現操作失誤？一鍵時光機復原 (Undo)", use_container_width=True):
                conn.close()
                shutil.copy("rf_ultimate_backup.db", "rf_ultimate.db")
                conn = init_rf_db()
                st.toast("⏪ 射頻資料庫已成功回溯至上一個安全狀態！", icon="⏳")
                st.rerun()

# --- 分頁 3 : 即時數據監控 ---
with tab_monitor:
    st.subheader("📊 資料庫即時快照 (Live Metrics)")
    st.write("**📡 1. 基站現況表 (cell_sites)**")
    st.dataframe(pd.read_sql_query("SELECT * FROM cell_sites", conn), use_container_width=True)
    st.write("**📐 2. 射頻天線扇區表 (rf_sectors)**")
    st.dataframe(pd.read_sql_query("SELECT * FROM rf_sectors", conn), use_container_width=True)
    st.write("**📈 3. 路測訊號品質表 (drive_tests)**")
    st.dataframe(pd.read_sql_query("SELECT * FROM drive_tests", conn), use_container_width=True)
