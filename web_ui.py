import streamlit as st
import pandas as pd
import sqlite3
import sqlglot
from sqlglot import exp

st.set_page_config(page_title="SQL-Lens: 預覽沙盒", layout="centered")
st.title("🔍 SQL-Lens：真實預覽與互動")
st.markdown("---")

# 確保資料庫存在並有基本資料 (防呆初始化)
def init_db():
    conn = sqlite3.connect("production.db")
    conn.execute("CREATE TABLE IF NOT EXISTS users (id INTEGER PRIMARY KEY, name TEXT, age INTEGER, status TEXT)")
    # 若為空則塞入測試資料
    if conn.execute("SELECT COUNT(*) FROM users").fetchone()[0] == 0:
        conn.executemany("INSERT INTO users (name, age, status) VALUES (?, ?, ?)", 
                         [("User_A", 25, "pending"), ("User_B", 55, "inactive"), ("User_C", 60, "pending")])
        conn.commit()
    return conn

conn = init_db()

st.subheader("🛡️ 互動式 SQL 預覽沙盒 (Dry Run)")
st.info("輸入 UPDATE 或 DELETE 語法，點擊預覽，系統會攔截並顯示「即將受影響的資料」。")

# 預設一段危險的修改指令
query_input = st.text_area("SQL 編輯區", value="UPDATE users SET status = 'active' WHERE age > 50;", height=100)

col1, col2 = st.columns(2)

with col1:
    if st.button("👁️ 1. 預覽受影響資料 (Dry Run)"):
        try:
            # 透過 AST 解析 SQL
            parsed = sqlglot.parse_one(query_input)
            
            # 如果是修改或刪除操作
            if isinstance(parsed, (exp.Update, exp.Delete)):
                table_name = parsed.find(exp.Table).name
                where_clause = parsed.args.get("where")
                
                if where_clause:
                    # 動態組合出 SELECT 語法來進行預覽
                    preview_sql = f"SELECT * FROM {table_name} {where_clause}"
                    df_preview = pd.read_sql_query(preview_sql, conn)
                    
                    if df_preview.empty:
                        st.warning("⚠️ 此條件下沒有找到任何符合的資料。")
                    else:
                        st.warning(f"⚠️ 攔截成功！以下 {len(df_preview)} 筆資料即將被修改/刪除：")
                        st.dataframe(df_preview, use_container_width=True)
                        st.session_state['preview_passed'] = True # 解鎖執行按鈕
                else:
                    st.error("🚨 攔截：缺乏 WHERE 條件，為保護資料庫，拒絕全表預覽與執行！")
            
            # 如果只是一般查詢
            elif isinstance(parsed, exp.Select):
                df = pd.read_sql_query(query_input, conn)
                st.success(f"✅ 查詢成功，共 {len(df)} 筆：")
                st.dataframe(df, use_container_width=True)
                
        except Exception as e:
            st.error(f"語法解析失敗: {e}")

with col2:
    # 執行按鈕，預設鎖定，預覽成功後才可點擊
    is_disabled = not st.session_state.get('preview_passed', False)
    if st.button("⚡ 2. 確認無誤，正式執行", type="primary", disabled=is_disabled):
        try:
            cursor = conn.cursor()
            cursor.execute(query_input)
            conn.commit()
            st.success(f"💥 執行完畢！共影響了 {cursor.rowcount} 筆資料。")
            st.session_state['preview_passed'] = False # 執行後重新鎖定
            st.balloons()
        except Exception as e:
            st.error(f"執行失敗: {e}")

st.markdown("---")
st.subheader("📊 當前資料庫即時快照")
# 隨時可見的真實資料狀態，支援點擊欄位排序
st.dataframe(pd.read_sql_query("SELECT * FROM users", conn), use_container_width=True)
