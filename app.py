import streamlit as st
import gspread
from google.oauth2.service_account import Credentials
import pandas as pd
from datetime import datetime

# ページ設定
st.set_page_config(page_title="空手道場 出席管理アプリ", layout="wide")

# Google Sheets API 認証設定
SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive"
]
JSON_FILE = "credentials.json"

MASTER_KEY = "16HSm3qYzzE2LqKE1EbDhI8ezWGQ2GCP98vHZgSapaDg"
ATTENDANCE_KEY = "1fIgWsyGjJ5VAsJ4QImoBDLFn_6rNPMvBt7cYg8V3xPs"

def get_sheets():
    creds = Credentials.from_service_account_file(JSON_FILE, scopes=SCOPES)
    client = gspread.authorize(creds)
    
    m_doc = client.open_by_key(MASTER_KEY)
    a_doc = client.open_by_key(ATTENDANCE_KEY)
    
    m_sheet = m_doc.sheet1
    a_sheet = a_doc.sheet1
    return m_sheet, a_sheet

try:
    sheet_master, sheet_attendance = get_sheets()
except Exception as e:
    st.error(f"スプレッドシートの接続エラー: {type(e).__name__} - {e}")
    st.stop()

# ------------------------------------
# 画面構成
# ------------------------------------
st.title("🥋 空手道場 出席管理システム")

# 名簿データの取得
master_records = sheet_master.get_all_records()
df_master = pd.DataFrame(master_records)

if df_master.empty or "名前" not in df_master.columns:
    st.warning("「甲子園口支部名簿」ファイルに『名前』列のデータが見つかりません。1行目に「名前」と入力されているか確認してください。")
    st.stop()

member_list = df_master["名前"].tolist()

# タブの切り替え
tab1, tab2 = st.tabs(["📝 出席登録", "📊 出席集計"])

# --- タブ1: 出席登録 ---
with tab1:
    st.header("日々の出席記録")
    
    with st.form("attendance_form", clear_on_submit=True):
        col1, col2 = st.columns(2)
        with col1:
            target_date = st.date_input("稽古日", datetime.now())
        with col2:
            selected_member = st.selectbox("練習生を選択", member_list)
        
        note = st.text_input("備考（遅刻・見学などがあれば入力）")
        
        submit_btn = st.form_submit_button("出席を記録する")
        
        if submit_btn:
            date_str = target_date.strftime("%Y-%m-%d")
            sheet_attendance.append_row([date_str, selected_member, note])
            st.success(f"✅ {date_str} ： {selected_member} さんの出席を記録しました！")

# --- タブ2: 出席集計 ---
with tab2:
    st.header("月間出席数の集計")
    
    attendance_records = sheet_attendance.get_all_records()
    df_attendance = pd.DataFrame(attendance_records)
    
    if df_attendance.empty or "日付" not in df_attendance.columns:
        st.info("まだ出席記録データがありません。")
    else:
        df_attendance["日付"] = pd.to_datetime(df_attendance["日付"])
        df_attendance["年月"] = df_attendance["日付"].dt.strftime("%Y-%m")
        available_months = sorted(df_attendance["年月"].unique(), reverse=True)
        
        selected_month = st.selectbox("集計対象の月を選択", available_months)
        
        df_filtered = df_attendance[df_attendance["年月"] == selected_month]
        total_days = df_filtered["日付"].nunique()
        st.metric(label=f"{selected_month} の総稽古日数", value=f"{total_days} 日")
        
        attendance_counts = df_filtered["名前"].value_counts().reset_index()
        attendance_counts.columns = ["名前", "出席日数"]
        
        df_summary = pd.merge(df_master[["名前"]], attendance_counts, on="名前", how="left").fillna(0)
        df_summary["出席日数"] = df_summary["出席日数"].astype(int)
        
        if total_days > 0:
            df_summary["出席率 (%)"] = ((df_summary["出席日数"] / total_days) * 100).round(1)
        
        st.dataframe(df_summary, use_container_width=True)