import streamlit as st
import time
import pandas as pd
import sqlite3
from engine import check_unsafe_sql, generate_mock_data, get_connection

# 1. 初始化狀態：確保介面有「記憶力」
if 'db_ready' not in st.session_state:
    st.session_state.db_ready = False
if 'logs' not in st.session_state:
    st.session_state.logs = []

st.set_page_config(page_title="SQL-Lens Pro", layout="wide")
st.title("🔍 SQL-Lens：互動式效能透鏡")

# 側邊欄：環境設定
with st.sidebar:
    st.header("⚙️ 核心設定")
    real_db = st.text_input("真實資料庫", value="production.db")
    mock_db = st.text_input("測試資料庫", value="benchmark.db")
    
    if st.button("🗑️ 清空環境"):
        st.session_state.db_ready = False
        st.session_state.logs = []
        st.rerun()

# 主介面佈局
col_left, col_right = st.columns([1, 1])

with col_left:
    st.subheader("🛡️ 安全掃描與執行")
    query = st.text_area("SQL 語法", value="UPDATE users SET status = 'active' WHERE id = 1;", height=150)
    
    if st.button("🚀 安全快篩並準備環境", type="primary"):
        try:
            check_unsafe_sql(query)
            st.success("✅ 語法安全檢查通過")
            
            # --- 動態日誌演示 ---
            log_area = st.empty()
            current_logs = "⏳ 啟動高品質管線...\n"
            for step in ["初始化 I/O...", "掛載記憶體快取...", "驗證 Schema..."]:
                time.sleep(0.4)
                current_logs += f"✔ {step}\n"
                log_area.code(current_logs, language="bash")
            
            st.session_state.db_ready = True
            st.toast("環境已就緒！", icon="🚀")
        except Exception:
            st.error("🚨 攔截：危險操作，拒絕執行！")

with col_right:
    st.subheader("⚡ 即時數據生成")
    # 連動機制：沒通過安全檢查不給按
    rows = st.number_input("生成筆數", 1000, 100000, 50000)
    
    if st.button("灌入 Mock 數據", disabled=not st.session_state.db_ready):
        # 視覺化進度條
        progress_bar = st.progress(0)
        status_text = st.empty()
        
        start_time = time.time()
        for percent in range(0, 101, 20):
            time.sleep(0.2) # 模擬高壓 I/O
            progress_bar.progress(percent)
            status_text.text(f"數據注入中... {percent}%")
            
        generate_mock_data(mock_db, total_rows=rows)
        st.success(f"⚡ 完成！耗時 {time.time()-start_time:.2f}s")

st.markdown("---")

# ⚖️ 下方：互動式數據比對中心
st.subheader("⚖️ 數據一致性監控（互動式編輯器）")

if st.session_state.db_ready:
    try:
        conn = get_connection(mock_db)
        # 這裡改用 st.data_editor，讓你可以直接在網頁改數據！
        df = pd.read_sql_query("SELECT status, COUNT(*) as count FROM users GROUP BY status", conn)
        
        st.write("💡 你可以直接點擊下方表格修改「count」，系統會即時模擬不一致狀態：")
        edited_df = st.data_editor(df, use_container_width=True, num_rows="dynamic")
        
        # 模擬比對邏輯
        if st.button("⚖️ 啟動 Zero-Copy 比對"):
            with st.spinner("進行記憶體級 EXCEPT 運算..."):
                time.sleep(0.5)
                # 簡單邏輯演示：若編輯過的數據與原數據不同，就噴錯誤
                if not edited_df.equals(df):
                    st.error("❌ 偵測到不一致！攔截部署管線。")
                else:
                    st.success("✅ 品質吻合，通過驗證！")
                    st.balloons()
        conn.close()
    except Exception:
        st.info("💡 請先完成「安全掃描」與「數據生成」來解鎖比對功能。")
else:
    st.warning("🔒 系統鎖定中。請先執行左側的安全快篩以啟動環境。")
