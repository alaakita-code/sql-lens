import streamlit as st
import pandas as pd
import sqlite3
import sqlglot
from sqlglot import exp

# 1. 初始化狀態：管理 SQL 輸入框與按鈕解鎖狀態
if 'sql_query' not in st.session_state:
    st.session_state.sql_query = "SELECT * FROM users;"
if 'preview_passed' not in st.session_state:
    st.session_state.preview_passed = False

def update_query(new_query):
    """點擊範例按鈕時，自動將語法帶入輸入框並重置鎖定狀態"""
    st.session_state.sql_query = new_query
    st.session_state.preview_passed = False

# 2. 介面與資料庫初始化
st.set_page_config(page_title="SQL-Lens: 互動沙盒", layout="centered")
st.title("🔍 SQL-Lens：預覽沙盒與語法指南")

def init_db():
    conn = sqlite3.connect("production.db")
    conn.execute("CREATE TABLE IF NOT EXISTS users (id INTEGER PRIMARY KEY, name TEXT, age INTEGER, status TEXT)")
    if conn.execute("SELECT COUNT(*) FROM users").fetchone()[0] == 0:
        conn.executemany("INSERT INTO users (name, age, status) VALUES (?, ?, ?)", 
                         [("User_A", 25, "pending"), ("User_B", 55, "inactive"), ("User_C", 60, "pending")])
        conn.commit()
    return conn

conn = init_db()

# 3. 內建操作手冊與語法庫 (隱藏式面板，維持介面極簡)
with st.expander("📖 系統操作指南與 SQL 語法庫 (點擊展開)", expanded=True):
    st.markdown("""
    **如何使用本沙盒？**
    1. **選擇語法**：點擊下方範例按鈕，系統會自動將標準語法帶入編輯區。
    2. **安全預覽**：點擊「👁️ 預覽受影響資料」，系統會攔截執行並模擬結果。
    3. **正式執行**：預覽確認無誤後，「⚡ 正式執行」的安全鎖才會解開。
    """)
    
    st.markdown("**👉 點擊按鈕，一鍵帶入標準語法：**")
    col_a, col_b, col_c = st.columns(3)
    with col_a:
        st.button("📄 一般查詢 (SELECT)", on_click=update_query, args=("SELECT * FROM users WHERE status = 'pending';",), use_container_width=True)
    with col_b:
        st.button("✏️ 條件更新 (UPDATE)", on_click=update_query, args=("UPDATE users SET status = 'active' WHERE age >= 50;",), use_container_width=True)
    with col_c:
        st.button("🗑️ 條件刪除 (DELETE)", on_click=update_query, args=("DELETE FROM users WHERE name = 'User_A';",), use_container_width=True)

st.markdown("---")

# 4. 核心互動區塊
st.subheader("🛡️ SQL 編輯與防呆執行區")

# 透過 key 綁定 session_state，讓按鈕可以控制輸入框的內容
query_input = st.text_area("SQL 編輯區 (可手動修改)", value=st.session_state.sql_query, key="sql_query", height=100)

col1, col2 = st.columns(2)

with col1:
    if st.button("👁️ 1. 預覽受影響資料 (Dry Run)", use_container_width=True):
        try:
            parsed = sqlglot.parse_one(query_input)
            
            # 處理 UPDATE / DELETE
            if isinstance(parsed, (exp.Update, exp.Delete)):
                table_name = parsed.find(exp.Table).name
                where_clause = parsed.args.get("where")
                
                if where_clause:
                    preview_sql = f"SELECT * FROM {table_name} {where_clause}"
                    df_preview = pd.read_sql_query(preview_sql, conn)
                    
                    if df_preview.empty:
                        st.warning("⚠️ 此條件下沒有找到任何符合的資料。")
                    else:
                        st.warning(f"⚠️ 攔截成功！以下 {len(df_preview)} 筆資料即將受影響：")
                        st.dataframe(df_preview, use_container_width=True)
                        st.session_state.preview_passed = True # 解鎖
                else:
                    st.error("🚨 攔截：危險操作！禁止無 WHERE 條件的全表修改。")
            
            # 處理 SELECT
            elif isinstance(parsed, exp.Select):
                df = pd.read_sql_query(query_input, conn)
                st.success(f"✅ 查詢成功，共 {len(df)} 筆：")
                st.dataframe(df, use_container_width=True)
                
        except Exception as e:
            st.error(f"語法解析失敗，請檢查 SQL 結構: {e}")

with col2:
    is_disabled = not st.session_state.preview_passed
    if st.button("⚡ 2. 確認無誤，正式執行", type="primary", disabled=is_disabled, use_container_width=True):
        try:
            cursor = conn.cursor()
            cursor.execute(query_input)
            conn.commit()
            st.success(f"💥 執行完畢！影響了 {cursor.rowcount} 筆資料。")
            st.session_state.preview_passed = False # 執行後重新上鎖
            st.balloons()
        except Exception as e:
            st.error(f"執行失敗: {e}")

st.markdown("---")
st.subheader("📊 資料庫即時快照")
st.dataframe(pd.read_sql_query("SELECT * FROM users", conn), use_container_width=True)
