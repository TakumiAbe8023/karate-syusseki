import streamlit as st
import gspread
from google.oauth2.service_account import Credentials
import pandas as pd
from datetime import datetime
import json
import base64

# ページ設定
st.set_page_config(page_title="空手道場 出席管理アプリ", layout="centered")

# スプレッドシートID
MASTER_KEY = "16HSm3qYzzE2LqKE1EbDhI8ezWGQ2GCP98vHZgSapaDg"
ATTENDANCE_KEY = "1fIgWsyGjJ5VAsJ4QImoBDLFn_6rNPMvBt7cYg8V3xPs"

SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive"
]

@st.cache_resource
def get_sheets():
    if "GCP_CREDS_BASE64" in st.secrets:
        raw_b64 = st.secrets["GCP_CREDS_BASE64"].strip()
        decoded_bytes = base64.b64decode(raw_b64)
        creds_info = json.loads(decoded_bytes.decode("utf-8"))
        creds = Credentials.from_service_account_info(creds_info, scopes=SCOPES)
    else:
        creds = Credentials.from_service_account_file("credentials.json", scopes=SCOPES)
        
    client = gspread.authorize(creds)
    m_doc = client.open_by_key(MASTER_KEY)
    a_doc = client.open_by_key(ATTENDANCE_KEY)
    return m_doc.sheet1, a_doc.sheet1

try:
    sheet_master, sheet_attendance = get_sheets()
except Exception as e:
    st.error(f"スプレッドシート接続エラー: {e}")
    st.stop()

st.title("🥋 空手道場 出席管理システム")

# 名簿データの取得
master_records = sheet_master.get_all_records()
df_master = pd.DataFrame(master_records)

if df_master.empty or "名前" not in df_master.columns:
    st.warning("「甲子園口支部名簿」に『名前』列のデータが見つかりません。")
    st.stop()

member_list = df_master["名前"].tolist()

# タブの切り替え（「記録の削除」タブを追加）
tab1, tab2, tab3 = st.tabs(["📝 出席登録", "📊 出席集計", "🗑️ 記録の削除"])

# --- タブ1: 出席登録 ---
with tab1:
    st.header("日々の出席記録")
    with st.form("attendance_form", clear_on_submit=True):
        target_date = st.date_input("稽古日", datetime.now())
        selected_member = st.selectbox("練習生を選択", member_list)
        note = st.text_input("備考（遅刻・見学など）")
        submit_btn = st.form_submit_button("出席を記録する")
        
        if submit_btn:
            date_str = target_date.strftime("%Y-%m-%d")
            
            # 既存の記録を取得して重複チェック
            attendance_records = sheet_attendance.get_all_records()
            df_curr = pd.DataFrame(attendance_records)
            
            is_duplicate = False
            if not df_curr.empty and "日付" in df_curr.columns and "名前" in df_curr.columns:
                # 日付文字列の一致確認
                df_curr["日付_str"] = pd.to_datetime(df_curr["日付"]).dt.strftime("%Y-%m-%d")
                duplicate_check = df_curr[(df_curr["日付_str"] == date_str) & (df_curr["名前"] == selected_member)]
                if not duplicate_check.empty:
                    is_duplicate = True
            
            if is_duplicate:
                st.error(f"⚠️ {date_str} の {selected_member} さんの出席記録は既に存在します！")
            else:
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
        
        # 重複を除いてユニークな出席日数（稽古日ごとに1回）で集計
        df_unique = df_filtered.drop_duplicates(subset=["日付", "名前"])
        attendance_counts = df_unique["名前"].value_counts().reset_index()
        attendance_counts.columns = ["名前", "出席日数"]
        
        df_summary = pd.merge(df_master[["名前"]], attendance_counts, on="名前", how="left").fillna(0)
        df_summary["出席日数"] = df_summary["出席日数"].astype(int)
        
        if total_days > 0:
            df_summary["出席率 (%)"] = ((df_summary["出席日数"] / total_days) * 100).round(1)
        
        st.dataframe(df_summary, use_container_width=True)

# --- タブ3: 記録の削除 ---
with tab3:
    st.header("誤登録データの削除")
    all_rows = sheet_attendance.get_all_values()
    
    if len(all_rows) <= 1:
        st.info("削除できる出席記録がありません。")
    else:
        # ヘッダーを除くレコード一覧（スプレッドシートの行番号を保持）
        options = []
        for idx, row in enumerate(all_rows[1:], start=2):
            date_val = row[0] if len(row) > 0 else ""
            name_val = row[1] if len(row) > 1 else ""
            note_val = row[2] if len(row) > 2 else ""
            options.append({
                "row_num": idx,
                "label": f"行{idx}: {date_val} | {name_val} ({note_val})"
            })
        
        selected_option = st.selectbox(
            "削除したい記録を選択してください",
            options,
            format_func=lambda x: x["label"]
        )
        
        if st.button("選択した記録を削除する", type="primary"):
            row_to_delete = selected_option["row_num"]
            sheet_attendance.delete_rows(row_to_delete)
            st.success(f"✅ {selected_option['label']} を削除しました！")
            st.rerun()