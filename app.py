import streamlit as st
import pandas as pd
from streamlit_autorefresh import st_autorefresh

# ✨【修改】從 database 引入全新定義的暫停與繼續功能
from database import (
    add_task,
    get_tasks,
    request_task,
    pause_task,
    resume_task,
    delete_task,
    get_robot_check_time
)

# =========================
# 頁面設定
# =========================
st.set_page_config(
    page_title="定位系統",
    layout="wide"
)

st.title("PIAYIXIA定位任務系統_大雅版_V1.0_By沒時間玩咚奇剛")

# =========================
# 自動刷新
# =========================
st_autorefresh(
    interval=10 * 1000,
    key="auto_refresh"
)

# =========================
# 手動刷新按鈕
# =========================
if st.button("刷新頁面"):
    st.rerun()

# =========================
# Robot 最後巡邏時間
# =========================
robot_time = get_robot_check_time()
st.info(f"Robot 最後巡邏時間：{robot_time}")

# =========================
# ✨【修正】自動將資料庫的 UTC 時間轉回台灣時間 (+8)
# =========================
# =========================
# 🔄【修正防呆版】自動將資料庫的 UTC 時間轉回台灣時間 (+8)
# =========================
def format_time(iso_string):
    # 💡 增強空值與型態檢查：如果為空、或是 Pandas 的 NaN，直接回傳 "-"
    if iso_string is None or pd.isna(iso_string) or iso_string == "":
        return "-"
    
    try:
        # 強制轉成字串型態確保安全，再進 pandas 轉換時區
        dt = pd.to_datetime(str(iso_string)).tz_convert("Asia/Taipei")
        return dt.strftime("%Y-%m-%d %H:%M:%S")
    except Exception:
        # 💡 備用邏輯防護：確保一定是字串才能用 replace
        if isinstance(iso_string, str):
            return iso_string.replace("T", " ").split(".")[0][:19]
        return "-"

# =========================
# ✨【修改後】新增資料 (將下拉選單移出 form 以支援動態即時刷新)
# =========================
st.subheader("新增資料")

# 💡 關鍵修改：將下拉選單移到 form 外面，這樣切換時網頁才會即時刷新渲染
task_type_display = st.selectbox("任務類型", ["單次任務", "定時任務"])
task_type = "single" if task_type_display == "單次任務" else "periodic"

# 💡 根據選擇，在外部決定要不要準備秒數欄位，或者直接放入 form 內
interval_seconds = None

# 使用 form 來包裝需要點擊「新增」才送出的欄位
with st.form("my_form", clear_on_submit=True):
    name = st.text_input("名稱")
    url = st.text_input("網址")
    
    # 💡 如果選擇定時，就在 form 裡面動態秀出秒數輸入欄位
    if task_type == "periodic":
        interval_seconds = st.number_input("執行間隔 (秒)", min_value=10, value=600, step=10)
        
    submitted = st.form_submit_button("新增")
    
    if submitted:
        if name and url:
            # 呼叫資料庫寫入方法
            add_task(name, url, task_type, interval_seconds)
            st.success("新增成功")
            # 強制刷新畫面，讓下方的任務列表立刻同步更新
            st.rerun()
        else:
            st.error("請輸入完整資料")

st.divider()

# =========================
# 任務列表
# =========================
st.subheader("任務列表")

# =========================
# 表頭 (維持 2:4:2:2:8:2 完美對齊)
# =========================
header1, header2, header3, header4, header5, header6 = st.columns([2, 4, 2, 2, 8, 2])

with header1: st.markdown("**姓名**")
with header2: st.markdown("**網址**")
with header3: st.markdown("**類型/定時(秒)**") # ✨ 欄位重新定義
with header4: st.markdown("**狀態**")
with header5: st.markdown("**時間紀錄**")         # ✨ 欄位重新定義
with header6: st.markdown("**操作/刪除**")         # ✨ 欄位重新定義

# =========================
# 顯示任務列表
# =========================
df = get_tasks()

for _, row in df.iterrows():
    col1, col2, col3, col4, col5, col6 = st.columns([2, 4, 2, 2, 8, 2])
    
    # 1. 姓名
    with col1:
        st.write(row["name"])
        
    # 2. 網址
    with col2:
        st.write(row["url"])
        
    # 3. ✨【修改】類型 / 定時(秒) 顯示邏輯
    with col3:
        if row["task_type"] == "single":
            st.write("單次")
        else:
            st.write(f"定時 ({row['interval_seconds']}s)")
            
    # 4. 狀態
    with col4:
        st.write(row["status"])
        
    # 5. ✨【修改】時間紀錄顯示邏輯 (根據類型呈現不同時間組合)
    with col5:
        if row["task_type"] == "single":
            req_t = format_time(row["request_time"])
            exe_t = format_time(row["execute_time"])
            st.write(f"請求：{req_t} / 執行：{exe_t}")
        else:
            last_t = format_time(row["last_execute_time"])
            next_t = format_time(row["next_execute_time"])
            st.write(f"上次：{last_t} / 下次：{next_t}")
            
    # 6. ✨【修改】操作與刪除按鈕動態邏輯
    with col6:
        # ---- 分支 A：單次任務的操作防護 ----
        if row["task_type"] == "single":
            if row["status"] in ["pending", "running"]:
                st.write("等任務完成再操作")
            else:
                # 為了省版面並排，按鈕可以用並列的 columns
                btn_col1, btn_col2 = st.columns(2)
                with btn_col1:
                    if st.button("定位", key=f"req_{row['id']}"):
                        request_task(row["id"])
                        st.rerun()
                with btn_col2:
                    if st.button("刪除", key=f"del_{row['id']}"):
                        delete_task(row["id"])
                        st.rerun()
                        
        # ---- 分支 B：定時任務的操作防護 ----
        else:
            btn_col1, btn_col2 = st.columns(2)
            
            if row["status"] == "定時中":
                with btn_col1:
                    # 💡 按下暫停：狀態變暫停，下次執行時間清空
                    if st.button("暫停", key=f"pause_{row['id']}"):
                        pause_task(row["id"])
                        st.rerun()
                with btn_col2:
                    if st.button("刪除", key=f"del_{row['id']}"):
                        delete_task(row["id"])
                        st.rerun()
                        
            elif row["status"] == "暫停":
                with btn_col1:
                    # 💡 按下繼續：狀態變回定時中，下次執行時間設為當前時間
                    if st.button("繼續", key=f"resume_{row['id']}"):
                        resume_task(row["id"])
                        st.rerun()
                with btn_col2:
                    if st.button("刪除", key=f"del_{row['id']}"):
                        delete_task(row["id"])
                        st.rerun()
            else:
                # 防呆：定時任務若處於執行中(running)，不提供操作
                st.write("任務執行中...")