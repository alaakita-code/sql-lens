import shutil # 新增匯入，用於檔案級快照
import os

# --- 新增：時光機備份與還原邏輯 ---
def backup_db():
    """執行前瞬間建立快照"""
    shutil.copy("production.db", "production_backup.db")

def restore_db():
    """一鍵回滾資料庫"""
    if os.path.exists("production_backup.db"):
        shutil.copy("production_backup.db", "production.db")
        st.toast("⏪ 已成功回溯至上一個狀態！", icon="⏳")

# ... (保留原有的 init_db 等邏輯) ...

# --- 優化：在 col1 的預覽區塊中，加入效能 X 光機 ---
with col1:
    if st.button("👁️ 1. 預覽受影響資料 (Dry Run)", use_container_width=True):
        try:
            parsed = sqlglot.parse_one(query_input)
            
            # 1. 效能 X 光機 (EXPLAIN QUERY PLAN)
            plan_df = pd.read_sql_query(f"EXPLAIN QUERY PLAN {query_input}", conn)
            profiler_warnings = [row['detail'] for _, row in plan_df.iterrows() if "SCAN TABLE" in row['detail']]
            
            if profiler_warnings:
                st.error("⚠️ [效能警告] 偵測到全表掃描 (SCAN TABLE)，建議建立 Index！")
            else:
                st.success("⚡ [效能評估] 查詢計畫優良，已使用 Index。")

            # 2. 原本的防呆攔截與預覽邏輯 (略，與上一版相同)
            # ... st.session_state.preview_passed = True ...

        except Exception as e:
            st.error(f"語法解析失敗: {e}")

# --- 優化：在 col2 的執行區塊中，加入時光機回溯 ---
with col2:
    is_disabled = not st.session_state.preview_passed
    if st.button("⚡ 2. 確認無誤，正式執行", type="primary", disabled=is_disabled, use_container_width=True):
        try:
            backup_db() # 執行前自動備份
            
            cursor = conn.cursor()
            cursor.execute(query_input)
            conn.commit()
            
            st.success(f"💥 執行完畢！影響了 {cursor.rowcount} 筆資料。")
            st.session_state.preview_passed = False
            st.balloons()
        except Exception as e:
            st.error(f"執行失敗: {e}")
            
    # 新增復原按鈕
    if os.path.exists("production_backup.db"):
        if st.button("⏪ 發現錯誤？一鍵復原 (Undo)", use_container_width=True):
            conn.close() # 先關閉連線以允許檔案覆蓋
            restore_db()
            conn = init_db() # 重新連線
            st.rerun() # 刷新畫面顯示舊資料
