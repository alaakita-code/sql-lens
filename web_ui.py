import streamlit as st
import pandas as pd
import sqlite3
import sqlglot
from sqlglot import exp
import shutil
import os

# ==========================================
# 1. 狀態管理與環境初始化
# ==========================================
if 'sql_query' not in st.session_state:
    st.session_state.sql_query = "SELECT * FROM users;"
if 'preview_passed' not in st.session_state:
    st.session_state.preview_passed = False

def update_query(new_query):
    """一鍵帶入語法並重置鎖定狀態"""
    st.session_state.sql_query = new_query
    st.session_state.preview_passed = False

def init_db():
    """初始化測試資料庫"""
    conn = sqlite3.connect("production.db")
    conn.execute("CREATE TABLE IF NOT EXISTS users (id INTEGER PRIMARY KEY, name TEXT, age INTEGER, status TEXT)")
    if conn.execute("SELECT COUNT(*) FROM users").fetchone()[0] == 0:
        conn.executemany("INSERT INTO users (name, age, status) VALUES (?, ?, ?)", 
                         [("User_A", 25, "pending"), ("User_B", 55, "inactive"), ("User_C", 60, "pending")])
        conn.commit()
    return conn

def backup_db():
    """執行前瞬間建立快照 (時光機)"""
    shutil.copy("production.db", "production_backup.db")

def restore_db():
    """一鍵回滾資料庫"""
    if os.path.exists("production_backup.db"):
        shutil.copy("production_backup.db", "production.db")
        st.toast("⏪ 已成功回溯至上一個狀態！", icon="⏳")

conn = init_db()

# ==========================================
# 2. 介面佈局 (Calm Technology 風格)
# ==========================================
st.set_page_config(page_title="SQL-Lens: 互動沙盒", layout="centered")
st.title("🔍 SQL-Lens：預覽沙盒與語法指南")

# 隱藏式教學面板
with st.expander("📖 系統操作指南與 SQL 語法庫 (點擊展開)", expanded=True):
    st.markdown("**👉 點擊按鈕，一鍵帶入標準語法：**")
    col_a, col_b, col_c = st.columns(3)
    with col_a:
        st.button("📄 查詢 (SELECT)", on_click=update_query, args=("SELECT * FROM users WHERE status = 'pending';",), use_container_width=True)
    with col_b:
        st.button("✏️ 更新 (UPDATE)", on_click=update_query, args=("UPDATE users SET status = 'active' WHERE age >= 50;",), use_container_width=True)
    with col_c:
        st.button("🗑️ 刪除 (DELETE)", on_click=update_query, args=("DELETE FROM users WHERE name = 'User_A';",), use_container_width=True)

st.markdown("---")
st.subheader("🛡️ SQL 編輯與防呆執行區")

# 核心輸入區
query_input = st.text_area("SQL 編輯區 (可手動修改)", value=st.session_state.sql_query, key="sql_query", height=100)

# ⚠️ 就是這裡！定義左右兩欄的佈局變數，之前遺漏了這行
col1, col2 = st.columns(2)

# ==========================================
# 3. 左側：沙盒預覽與效能 X 光機
# ==========================================
with col1:
    if st.button("👁️ 1. 預覽影響與效能 (Dry Run)", use_container_width=True):
        try:
            parsed = sqlglot.parse_one(query_input)
            
            # [效能 X 光機]
            plan_df = pd.read_sql_query(f"EXPLAIN QUERY PLAN {query_input}", conn)
            if any("SCAN TABLE" in row['detail'] for _, row in plan_df.iterrows()):
                st.warning("⚠️ [效能提示] 偵測到全表掃描 (SCAN TABLE)，資料量大時建議建立 Index。")
            else:
                st.success("⚡ [效能評估] 查詢計畫優良。")

            # [安全攔截與預覽]
            if isinstance(parsed, (exp.Update, exp.Delete)):
                table_name = parsed.find(exp.Table).name
                where_clause = parsed.args.get("where")
                
                if where_clause:
                    preview_sql = f"SELECT * FROM {table_name} {where_clause}"
                    df_preview = pd.read_sql_query(preview_sql, conn)
                    
                    if df_preview.empty:
                        st.info("💡 此條件下沒有找到任何符合的資料。")
                    else:
                        st.error(f"🚨 攔截成功！以下 {len(df_preview)} 筆資料即將受影響：")
                        st.dataframe(df_preview, use_container_width=True)
                        st.session_state.preview_passed = True # 預覽通過，解鎖執行按鈕
                else:
                    st.error("🚨 攔截：危險操作！禁止無 WHERE 條件的全表修改。")
            
            elif isinstance(parsed, exp.Select):
                df = pd.read_sql_query(query_input, conn)
                st.dataframe(df, use_container_width=True)
                
        except Exception as e:
            st.error(f"語法解析失敗，請檢查 SQL 結構: {e}")

# ==========================================
# 4. 右側：正式執行與時光機回溯
# ==========================================
with col2:
    is_disabled = not st.session_state.preview_passed
    if st.button("⚡ 2. 確認無誤，正式執行", type="primary", disabled=is_disabled, use_container_width=True):
        try:
            backup_db() # 執行前瞬間備份
            
            cursor = conn.cursor()
            cursor.execute(query_input)
            conn.commit()
            
            st.success(f"💥 執行完畢！影響了 {cursor.rowcount} 筆資料。")
            st.session_state.preview_passed = False # 重新上鎖
            st.balloons()
        except Exception as e:
            st.error(f"執行失敗: {e}")

    # 時光機復原按鈕 (只有當備份檔存在時才顯示)
    if os.path.exists("production_backup.db"):
        if st.button("⏪ 發現錯誤？一鍵復原 (Undo)", use_container_width=True):
            conn.close()
            restore_db()
            conn = init_db()
            st.rerun()

# ==========================================
# 5. 底部：即時快照
# ==========================================
st.markdown("---")
st.subheader("📊 資料庫即時快照")
st.dataframe(pd.read_sql_query("SELECT * FROM users", conn), use_container_width=True)
