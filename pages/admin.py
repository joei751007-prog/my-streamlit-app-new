from datetime import datetime, timezone, timedelta
import streamlit as st
from streamlit_autorefresh import st_autorefresh
from supabase_client import supabase  # 用於 API 直接查詢與更新資料
from database import (
    get_tasks,
    robot_check_in,
    get_robot_check_time
)
import pandas as pd  # 如果最上面沒有，請記得加這行

st.set_page_config(page_title="後台管理", layout="wide")

st.title("後台管理")

# 台灣時間設定
tw_tz = timezone(timedelta(hours=8))

# ========================================================
# ✨【修正】後台同步自動將 UTC 時間轉回台灣時間 (+8)
# ========================================================

def format_time(iso_string):
    if not iso_string or iso_string == "none":
        return "none"
    try:
        dt = pd.to_datetime(iso_string).tz_convert("Asia/Taipei")
        return dt.strftime("%Y-%m-%d %H:%M:%S")
    except Exception:
        return iso_string.replace("T", " ").split(".")[0][:19]

# ========================================================
# ✨【修改】API 入口（自動辨識單次/定時並計算下次時間）
# ========================================================
query = st.query_params

if "api" in query and query["api"] == "complete":
    task_id = int(query["task_id"])
    current_time_obj = datetime.now(tw_tz)
    current_time_iso = current_time_obj.isoformat()
    
    try:
        # 1. 率先到資料庫查出這個 task_id 的任務類型與設定秒數
        task_res = supabase.table("tasks").select("*").eq("id", task_id).execute()
        
        if task_res.data and len(task_res.data) > 0:
            task_info = task_res.data[0]
            task_type = task_info.get("task_type")
            
            # 2. 【分支 A】如果是單次任務
            if task_type == "single":
                supabase.table("tasks").update({
                    "status": "done",
                    "execute_time": current_time_iso
                }).eq("id", task_id).execute()
                
            # 3. 【分支 B】如果是定時任務
            elif task_type == "periodic":
                seconds = task_info.get("interval_seconds") or 600
                # 💡 依照您的精準構想：下一次執行時間 = 當前收到 API 時間 + 秒數
                next_time_obj = current_time_obj + timedelta(seconds=seconds)
                next_time_iso = next_time_obj.isoformat()
                
                supabase.table("tasks").update({
                    "status": "定時中",  # 狀態保持定時中
                    "last_execute_time": current_time_iso,
                    "next_execute_time": next_time_iso
                }).eq("id", task_id).execute()
                
        st.write("OK")
    except Exception as e:
        st.write(f"API 處理失敗: {e}")
        
    st.stop()


# ========================================================
# 登入驗證管理（維持原有機制）
# ========================================================
if "login" not in st.session_state:
    st.session_state.login = False

if not st.session_state.login:
    password = st.text_input("請輸入管理密碼", type="password")
    if st.button("登入"):
        if password == st.secrets["password"]:
            st.session_state.login = True
            st.success("登入成功")
            st.rerun()
        else:
            st.error("密碼錯誤")
    st.stop()


# ========================================================
# 登入後管理畫面
# ========================================================
if st.session_state.login:
    st.success("登入成功")

if st.button("登出"):
    st.session_state.login = False
    st.rerun()

if st.button("刷新頁面"):
    st.rerun()

st_autorefresh(
    interval=5 * 1000,
    key="admin_refresh"
)

robot_time = get_robot_check_time()
st.info(f"Robot 最後簽到時間：{robot_time}")

if st.button("Robot 簽到"):
    robot_check_in()
    st.success("簽到成功")
    st.rerun()

st.divider()

# ========================================================
# ✨【修改】後台管理列表欄位同步 (呈現 10 個欄位)
# ========================================================
st.subheader("全任務細節後台監控")

# 設定適合 10 個欄位展開的比例
cols_layout = [1, 2, 4, 2, 2, 2, 3, 3, 3, 3]
headers = [
    "**id**", "**姓名**", "**網址**", "**類型**", "**秒數**", 
    "**狀態**", "**請求時間**", "**執行時間**", "**上次執行**", "**下次執行**"
]

# 渲染表頭
header_cols = st.columns(cols_layout)
for col, h_name in zip(header_cols, headers):
    with col:
        st.markdown(h_name)

# 渲染資料列
df = get_tasks()

for _, row in df.iterrows():
    row_cols = st.columns(cols_layout)
    
    with row_cols[0]: st.write(row["id"])
    with row_cols[1]: st.write(row["name"])
    with row_cols[2]: st.write(row["url"])
    with row_cols[3]: st.write("單次" if row["task_type"] == "single" else "定時")
    with row_cols[4]: st.write(f"{row['interval_seconds']}s" if row["task_type"] == "periodic" else "none")
    with row_cols[5]: st.write(row["status"])
    
    # 時間欄位格式化美化輸出
    with row_cols[6]: st.write(format_time(row["request_time"]) if row["task_type"] == "single" else "none")
    with row_cols[7]: st.write(format_time(row["execute_time"]) if row["task_type"] == "single" else "none")
    with row_cols[8]: st.write(format_time(row["last_execute_time"]) if row["task_type"] == "periodic" else "none")
    with row_cols[9]: st.write(format_time(row["next_execute_time"]) if row["task_type"] == "periodic" else "none")