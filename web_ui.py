import streamlit as st
import time
import pandas as pd
from engine import check_unsafe_sql, generate_mock_data, get_connection

# 介面基礎設定
st.set_page_config(page_title="SQL-Lens", layout="centered", page_icon="🔍")
st.title("🔍 SQL-Lens 效能與品質透鏡")
st.markdown("---")

# 側邊欄：環境配置
with st.sidebar:
    st.header("⚙️ 核心設定")
    real_db_path = st.text_input("真實資料庫路徑", value="production.db")
    mock_db_path = st.text_input("測試資料庫路徑", value="benchmark.db")
    st.markdown("*(在地感核心：穩重、結構、安全)*")

tab1, tab2, tab3 = st.tabs(["🛡️ 安全掃描", "⚡ 資料生成", "⚖️ 數據比對"])

# 分頁 1：靜態語法防呆
with tab1:
    st.subheader("靜態防呆 (AST)")
    query_input = st.text_area("輸入 SQL", value="UPDATE users SET status = 'active';", height=100)
    if st.button("執行快篩", type="primary"):
        try:
            check_unsafe_sql(query_input)
            st.success("✅ 檢查通過！未發現危險操作。")
        except Exception:
            st.error("🚨 攔截！偵測到無 WHERE 條件的危險操作。")

# 分頁 2：基準資料注入
with tab2:
    st.subheader("高效基準資料注入")
    row_count = st.slider("資料筆數", 1000, 100000, 50000, 1000)
    if st.button("🚀 開始生成"):
        with st.spinner("Generator 分塊寫入中..."):
            start = time.time()
            generate_mock_data(mock_db_path, total_rows=row_count)
            st.success(f"⚡ 完成！耗時 {time.time()-start:.2f} 秒")

# 分頁 3：記憶體級比對
with tab3:
    st.subheader("記憶體級比對 (Zero-Copy)")
    if st.button("⚖️ 啟動比對"):
        try:
            conn = get_connection(mock_db_path)
            conn.execute(f"ATTACH DATABASE '{real_db_path}' AS real_db;")
            # 利用 EXCEPT 進行無暫存檔比對
            query = """
                SELECT status, COUNT(*) as count FROM main.users GROUP BY status
                EXCEPT
                SELECT status, COUNT(*) as count FROM real_db.users GROUP BY status;
            """
            df_diff = pd.read_sql_query(query, conn)
            
            if df_diff.empty:
                st.success("🎉 品質保證：資料特徵 100% 吻合！")
                st.balloons()
            else:
                st.error("❌ 偵測到不一致！")
                st.dataframe(df_diff, use_container_width=True)
            conn.close()
        except Exception as e:
            st.error(f"比對失敗，請確認資料庫：{e}")
