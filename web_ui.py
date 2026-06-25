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
# 2. 核心功能分頁系統 (四大模組)
# ==========================================
tab_manual, tab_pipeline, tab_sandbox, tab_monitor = st.tabs(["📖 完整操作手冊", "🧽 資料清洗管線", "🧪 全方位互動沙盒", "📊 即時數據監控"])

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
    - **資料清洗 (ETL)**：支援上傳外部 CSV，進行一鍵去重、補缺後直接匯入資料庫。
    - **安全防禦機制**：進行 `UPDATE` 或 `DELETE` 時，強制開啟沙盒攔截，未點擊「安全預覽」前正式執行按鈕將維持鎖定。
    - **效能分析引擎**：每次預覽會自動執行 `EXPLAIN QUERY PLAN`，偵測全表掃描 (SCAN TABLE)。
    - **時光機回溯**：每次正式執行寫入前，系統會在背景複製快照，可一鍵點擊 `Undo` 完美還原。
    """)

# --- 分頁 2：資料清洗管線 (ETL Pipeline) ---
with tab_pipeline:
    st.subheader("🧽 CSV 數據匯入與自動清洗")
    st.caption("將外部收集的原始路測數據 (Raw Data) 上傳，去噪後再注入資料庫。")

    # 1. 上傳區塊 (加入備用載入機制)
    st.markdown("**📥 1. 匯入原始資料 (CSV)**")
    
    # 建立一個佔存變數來存放資料
    raw_df = None 
    
    # 並排顯示上傳區與測試按鈕
    col_up1, col_up2 = st.columns([1, 1])
    with col_up1:
        uploaded_file = st.file_uploader("上傳本地檔案", type="csv", label_visibility="collapsed")
    with col_up2:
        st.markdown("<div style='margin-top: 5px; color: #888; font-size: 14px;'>手機無法上傳？</div>", unsafe_allow_html=True)
        use_sample = st.button("🧪 一鍵載入含雜訊的測試資料", use_container_width=True)

    # 判斷資料來源
    if uploaded_file is not None:
        raw_df = pd.read_csv(uploaded_file)
    elif use_sample:
        # 故意製造含有「重複值」與「缺失值 NaN」的髒資料
        raw_df = pd.DataFrame({
            "sector_id": [1, 2, 1, 3, 2, None],
            "rsrp": [-85, -100, -85, -115, -95, -105],
            "sinr": [15.2, 5.5, 15.2, 2.1, 8.8, None]
        })
        st.toast("已載入測試用雜訊數據！", icon="🧪")

    # 2. 互動式清洗策略 (只有當 raw_df 有資料時才顯示)
    if raw_df is not None:
        st.write(f"**👀 原始資料預覽 (共 {len(raw_df)} 筆)：**")
        st.dataframe(raw_df, use_container_width=True)

        st.markdown("**⚙️ 2. 選擇資料清洗策略：**")
        c1, c2 = st.columns(2)
        drop_dups = c1.checkbox("🗑️ 移除重複資料列 (如第1與第3筆)", value=True)
        handle_na = c2.selectbox("🩹 缺失值 (NaN) 處理方式", ["不處理", "整列刪除 (Drop)", "數值補零 (Fill 0)"])

        # 執行清洗邏輯
        clean_df = raw_df.copy()
        if drop_dups:
            clean_df = clean_df.drop_duplicates()
        if handle_na == "整列刪除 (Drop)":
            clean_df = clean_df.dropna()
        elif handle_na == "數值補零 (Fill 0)":
            clean_df = clean_df.fillna(0)

        st.write(f"**✨ 清洗後資料預覽 (剩餘 {len(clean_df)} 筆)：**")
        st.dataframe(clean_df, use_container_width=True)

        # 3. 輸出與載入區塊
        st.markdown("**📤 3. 匯出與寫入：**")
        out1, out2 = st.columns(2)
        
        csv_buffer = clean_df.to_csv(index=False).encode('utf-8')
        out1.download_button(
            label="⬇️ 下載乾淨的 CSV",
            data=csv_buffer,
            file_name="cleaned_rf_data.csv",
            mime="text/csv",
            use_container_width=True
        )

        if out2.button("⚡ 正式匯入至資料庫 (drive_tests)", type="primary", use_container_width=True):
            try:
                clean_df.to_sql("drive_tests", conn, if_exists="append", index=False)
                st.success(f"💥 成功將 {len(clean_df)} 筆數據匯入資料庫！")
                st.balloons()
            except Exception as e:
                st.error(f"寫入失敗，請確認欄位是否吻合。錯誤：{e}")


# --- 分頁 3：全方位互動沙盒 ---
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
    
    # 語法庫快捷鍵
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

    # 執行與預覽區塊
    b1, b2 = st.columns(2)
    with b1:
        if st.button("👁️ 1. 安全預覽與效能分析 (Dry Run)", use_container_width=True):
            try:
                parsed = sqlglot.parse_one(query_input)
                
                # 效能 X 光機
                plan_df = pd.read_sql_query(f"EXPLAIN QUERY PLAN {query_input}", conn)
                if any("SCAN TABLE" in row['detail'] for _, row in plan_df.iterrows()):
                    st.warning("⚠️ [效能警示] 偵測到全表掃描 (SCAN TABLE)，建議針對 FK 建立 Index。")
                else:
                    st.success("⚡ [效能優良] 查詢計畫已最佳化。")
                
                # 防呆邏輯分流
                if isinstance(parsed, exp.Insert):
                    table_name = parsed.find(exp.Table).name
                    st.info(f"💡 動作偵測：新增資料至 `{table_name}` 表。")
                    st.warning("⚠️ 安全防護：請確認資料無誤後，於右側點擊正式寫入。")
                    st.session_state.preview_passed = True

                elif isinstance(parsed, (exp.Update, exp.Delete)):
                    where = parsed.args.get("where")
                    if not where: 
                        st.error("🚨 嚴重攔截：禁止無 WHERE 條件的全表破壞性操作！")
                    else:
                        df = pd.read_sql_query(f"SELECT * FROM {parsed.find(exp.Table).name} {where}", conn)
                        st.warning(f"⚠️ 安全防護：本次操作預計影響 {len(df)} 筆數據，請確認執行。")
                        st.dataframe(df, use_container_width=True)
                        st.session_state.preview_passed = True
                else:
                    st.dataframe(pd.read_sql_query(query_input, conn), use_container_width=True)
                    
            except Exception as e: 
                st.error(f"語法解析錯誤: {e}")
    
    with b2:
        is_disabled = not st.session_state.preview_passed
        if st.button("⚡ 2. 確認無誤，正式寫入資料庫", type="primary", disabled=is_disabled, use_container_width=True):
            try:
                shutil.copy("rf_ultimate.db", "rf_ultimate_backup.db")
                conn.execute(query_input)
                conn.commit()
                st.success("💥 數據操作成功！")
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

# --- 分頁 4 : 即時數據監控 ---
with tab_monitor:
    st.subheader("📊 資料庫即時快照 (Live Metrics)")
    st.write("**📡 1. 基站現況表 (cell_sites)**")
    st.dataframe(pd.read_sql_query("SELECT * FROM cell_sites", conn), use_container_width=True)
    st.write("**📐 2. 射頻天線扇區表 (rf_sectors)**")
    st.dataframe(pd.read_sql_query("SELECT * FROM rf_sectors", conn), use_container_width=True)
    st.write("**📈 3. 路測訊號品質表 (drive_tests)**")
    st.dataframe(pd.read_sql_query("SELECT * FROM drive_tests", conn), use_container_width=True)
