from datetime import datetime, timezone, timedelta
import pandas as pd
import streamlit as st
from supabase_client import supabase

# =========================
# 台灣時間設定
# =========================
tw_tz = timezone(timedelta(hours=8))

# =========================
# ✨【修改】新增任務 (支援單次與定時)
# =========================
def add_task(name, url, task_type, interval_seconds=None):
    try:
        current_time = datetime.now(tw_tz).isoformat()
        
        # 建立共用的基本資料基礎
        payload = {
            "name": name,
            "url": url,
            "task_type": task_type,
            "interval_seconds": interval_seconds if task_type == "periodic" else None,
            "request_time": None,
            "execute_time": None,
            "last_execute_time": None,
        }
        
        # 根據任務類型設定初始狀態與下次執行時間
        if task_type == "single":
            payload["status"] = "idle"
            payload["next_execute_time"] = None
        elif task_type == "periodic":
            payload["status"] = "定時中"
            # 💡 依照您的構想：定時任務一新增，下次執行時間直接設為「當前新增資料的時間」
            payload["next_execute_time"] = current_time
            
        supabase.table("tasks").insert(payload).execute()
    except Exception as e:
        st.error(f"資料庫新增任務失敗: {e}")

# =========================
# ✨【修改】取得所有任務 (對齊新欄位)
# =========================
def get_tasks():
    # 預設的完整新欄位清單，確保前後端欄位名稱一致不報錯
    all_columns = [
        "id", "name", "url", "task_type", "interval_seconds", 
        "status", "request_time", "execute_time", "last_execute_time", "next_execute_time"
    ]
    try:
        res = supabase.table("tasks") \
            .select("*") \
            .order("id", desc=True) \
            .execute()

        data = res.data or []
        
        if not data:
            return pd.DataFrame(columns=all_columns)
            
        return pd.DataFrame(data)
    except Exception as e:
        st.error(f"資料庫讀取任務失敗: {e}")
        return pd.DataFrame(columns=all_columns)

# =========================
# 發送定位請求 (單次任務專用)
# =========================
def request_task(task_id):
    try:
        # 改用 isoformat 寫入 TIMESTAMP 欄位
        request_time = datetime.now(tw_tz).isoformat()

        supabase.table("tasks") \
            .update({
                "status": "pending",
                "request_time": request_time
            }) \
            .eq("id", task_id) \
            .execute()
    except Exception as e:
        st.error(f"發送定位請求失敗: {e}")

# =========================
# ✨【新增】暫停定時任務
# =========================
def pause_task(task_id):
    try:
        supabase.table("tasks") \
            .update({
                "status": "暫停",
                # 💡 依照您的構想：按下暫停時，下次執行時間變成 None (防機器人誤抓)
                "next_execute_time": None
            }) \
            .eq("id", task_id) \
            .execute()
    except Exception as e:
        st.error(f"暫停任務失敗: {e}")

# =========================
# ✨【新增】繼續定時任務
# =========================
def resume_task(task_id):
    try:
        current_time = datetime.now(tw_tz).isoformat()
        
        supabase.table("tasks") \
            .update({
                "status": "定時中",
                # 💡 依照您的構想：按下繼續時，下次執行時間重新設定為當前按下繼續的時間
                "next_execute_time": current_time
            }) \
            .eq("id", task_id) \
            .execute()
    except Exception as e:
        st.error(f"恢復任務失敗: {e}")

# =========================
# 執行中狀態更新 (通常由後台或機器人觸發，此處保留供調用)
# =========================
def running_task(task_id):
    try:
        supabase.table("tasks") \
            .update({"status": "running"}) \
            .eq("id", task_id) \
            .execute()
    except Exception as e:
        print(f"變更任務狀態為執行中失敗 (ID: {task_id}): {e}")

# =========================
# 完成任務 (這裡前端只保留單純刪除，完成操作留給後台 API)
# =========================
def delete_task(task_id):
    try:
        supabase.table("tasks") \
            .delete() \
            .eq("id", task_id) \
            .execute()
    except Exception as e:
        st.error(f"刪除任務失敗: {e}")

# =========================
# Robot 最後巡邏時間（更新與讀取，維持不變但改用 ISO 格式）
# =========================
def update_robot_check_time():
    try:
        current_time = datetime.now(tw_tz).isoformat()
        supabase.table("system_status") \
            .update({"last_robot_check_time": current_time}) \
            .eq("id", 1) \
            .execute()
    except Exception as e:
        print(f"更新 Robot 巡邏時間失敗: {e}")

def get_robot_check_time():
    try:
        res = supabase.table("system_status") \
            .select("last_robot_check_time") \
            .eq("id", 1) \
            .execute()

        if res.data and len(res.data) > 0:
            raw_time = res.data[0].get("last_robot_check_time")
            if raw_time:
                # 💡 使用 pandas 將資料庫的 UTC 時間精準轉回台灣時間 (+8) 呈現
                dt = pd.to_datetime(raw_time).tz_convert("Asia/Taipei")
                return dt.strftime("%Y-%m-%d %H:%M:%S")
            return "無紀錄"
        return "無紀錄"
    except Exception as e:
        print(f"讀取 Robot 巡邏時間失敗: {e}")
        return "讀取錯誤"

def robot_check_in():
    update_robot_check_time()