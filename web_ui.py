import streamlit as st
import pandas as pd
import sqlite3
import sqlglot
from sqlglot import exp
import shutil
import os
import graphviz

# ==========================================
# 1. 狀態管理與 RF 資料庫初始化
# ==========================================
if 'sql_query' not in st.session_state:
    st.session_state.sql_query = """-- 尋找 N78 頻段中，訊號小於 -110 的問題點
SELECT s.site_id, r.band, d.rsrp
FROM cell_sites s
JOIN rf_sectors r ON s.site_id = r.site_id
JOIN drive_tests d ON r.sector_id = d.sector_id
WHERE r.band = 'N78' AND d.rsrp < -110;"""

if 'preview_passed' not in st.session_state:
    st.session_state.preview_passed = False

def update_query(new_query):
    st.session_state.sql_query = new_query
    st.session_state.preview_passed = False

def init_rf_db():
    """初始化具備關聯性的 RF 電信資料庫"""
    conn = sqlite3.connect("rf_production.db")
    
    # 建立三張關聯表：基站、扇區、路測數據
    conn.execute("CREATE TABLE IF NOT EXISTS cell_sites (site_id INTEGER PRIMARY KEY, latitude FLOAT, longitude FLOAT)")
    conn.execute("CREATE TABLE IF NOT EXISTS rf_sectors (sector_id INTEGER PRIMARY KEY, site_id INTEGER, band TEXT, azimuth INTEGER)")
    conn.execute("CREATE TABLE IF NOT EXISTS drive_tests (log_id INTEGER PRIMARY KEY, sector_id INTEGER, rsrp INTEGER)")
    
    # 若為空，寫入測試用假資料
    if conn.execute("SELECT COUNT(*) FROM cell_sites").fetchone()[0] == 0:
        conn.executemany("INSERT INTO cell_sites VALUES (?, ?, ?)", [(1001, 25.01, 121.50), (1002, 25.02, 121.51)])
        conn.executemany("INSERT INTO rf_sectors VALUES (?, ?, ?, ?)", [(1, 1001, 'N78', 120), (2, 1001, 'B28', 240), (3, 1002, 'N78', 0)])
        conn.executemany("INSERT INTO drive_tests VALUES (?, ?, ?)", [(101, 1, -115), (102, 1, -85), (103, 3, -120)])
        conn.commit()
    return conn

def backup_db():
    shutil.copy("rf_production.db", "rf_backup.db")

def restore_db():
    if os.path.exists("rf_backup.db"):
        shutil.copy("rf_backup.db", "rf_production.db")
        st.toast("⏪ 射頻資料庫已回溯至上一個安全狀態！", icon="⏳")

conn = init_rf_db()

# ==========================================
# 2. 介面佈局：ER 圖與資料字典
# ==========================================
st.set_page_config(page_title="SQL-Lens: RF架構", layout="wide")
st.title("📡 SQL-Lens：射頻資料庫互動開發站")
st.markdown("---")

col_schema, col_action = st.columns([1, 2])

with col_schema:
    st.subheader("🗂️ 系統 ER 關聯圖 (Schema)")
    # 動態繪製 ER 圖
    er_graph = graphviz.Digraph(node_attr={'shape': 'record', 'style': 'filled', 'fillcolor': '#f8f9fa'})
    er_graph.node('cell_sites', '{cell_sites (基站)|+ site_id (INT) PK\n latitude (FLOAT)\n longitude (FLOAT)}')
    er_graph.node('rf_sectors', '{rf_sectors (扇區)|+ sector_id (INT) PK\n # site_id (INT) FK\n band (TEXT)\n azimuth (INT)}')
    er_graph.node('drive_tests', '{drive_tests (路測)|+ log_id (INT) PK\n # sector_id (INT) FK\n rsrp (INT)}')
    
    er_graph.edge('cell_sites', 'rf_sectors', label=' 1:N')
    er_graph.edge('rf_sectors', 'drive_tests', label=' 1:N')
    st.graphviz_chart(er_graph)

# ==========================================
# 3. 操作區：語法庫與防呆沙盒
# ==========================================
with col_action:
    st.subheader("🛠️ 開發與指令沙盒")
    
    with st.expander("📖 帶入標準 RF 實戰語法", expanded=True):
        c1, c2, c3 = st.columns(3)
        c1.button("📄 多表聯查 (JOIN)", on_click=update_query, args=("SELECT s.site_id, r.band, d.rsrp FROM cell_sites s JOIN rf_sectors r ON s.site_id = r.site_id JOIN drive_tests d ON r.sector_id = d.sector_id WHERE r.band = 'N78' AND d.rsrp < -110;",), use_container_width=True)
        c2.button("✏️ 修正方位角 (UPDATE)", on_click=update_query, args=("UPDATE rf_sectors SET azimuth = 135 WHERE sector_id = 1;",), use_container_width=True)
        c3.button("🗑️ 刪除異常數據 (DELETE)", on_click=update_query, args=("DELETE FROM drive_tests WHERE rsrp < -140;",), use_container_width=True)

    query_input = st.text_area("SQL 終端機", value=st.session_state.sql_query, key="sql_query", height=120)

    # 執行與預覽按鈕區
    btn_col1, btn_col2 = st.columns(2)
    with btn_col1:
        if st.button("👁️ 1. 安全預覽 (Dry Run)", use_container_width=True):
            try:
                parsed = sqlglot.parse_one(query_input)
                
                if isinstance(parsed, (exp.Update, exp.Delete)):
                    table_name = parsed.find(exp.Table).name
                    where_clause = parsed.args.get("where")
                    
                    if where_clause:
                        preview_sql = f"SELECT * FROM {table_name} {where_clause}"
                        df_preview = pd.read_sql_query(preview_sql, conn)
                        if df_preview.empty:
                            st.info("💡 條件下無受影響的資料。")
                        else:
                            st.error(f"🚨 攔截！以下 {len(df_preview)} 筆 {table_name} 資料即將被修改：")
                            st.dataframe(df_preview, use_container_width=True)
                            st.session_state.preview_passed = True
                    else:
                        st.error("🚨 攔截：禁止無 WHERE 條件的全表危險操作！")
                
                elif isinstance(parsed, exp.Select):
                    df = pd.read_sql_query(query_input, conn)
                    st.success(f"✅ 查詢成功，共 {len(df)} 筆：")
                    st.dataframe(df, use_container_width=True)
                    
            except Exception as e:
                st.error(f"語法解析失敗: {e}")

    with btn_col2:
        is_disabled = not st.session_state.preview_passed
        if st.button("⚡ 2. 正式執行 (具備時光機)", type="primary", disabled=is_disabled, use_container_width=True):
            try:
                backup_db()
                cursor = conn.cursor()
                cursor.execute(query_input)
                conn.commit()
                st.success(f"💥 執行完畢！影響了 {cursor.rowcount} 筆資料。")
                st.session_state.preview_passed = False
                st.balloons()
            except Exception as e:
                st.error(f"執行失敗: {e}")

        if os.path.exists("rf_backup.db"):
            if st.button("⏪ 後悔了？一鍵復原 (Undo)", use_container_width=True):
                conn.close()
                restore_db()
                conn = init_rf_db()
                st.rerun()

# ==========================================
# 4. 底部：三張表的即時監控
# ==========================================
st.markdown("---")
st.subheader("📊 即時資料庫快照 (Live Tables)")
t1, t2, t3 = st.columns(3)
with t1:
    st.write("**1. 基站 (cell_sites)**")
    st.dataframe(pd.read_sql_query("SELECT * FROM cell_sites", conn), use_container_width=True)
with t2:
    st.write("**2. 扇區 (rf_sectors)**")
    st.dataframe(pd.read_sql_query("SELECT * FROM rf_sectors", conn), use_container_width=True)
with t3:
    st.write("**3. 路測 (drive_tests)**")
    st.dataframe(pd.read_sql_query("SELECT * FROM drive_tests", conn), use_container_width=True)
