def get_sheets():
    if "gcp_service_account" in st.secrets:
        creds_info = dict(st.secrets["gcp_service_account"])
        if "json_data" in creds_info:
            creds_info = json.loads(creds_info["json_data"])
            
        # private_key の自動補正処理
        if "private_key" in creds_info:
            key = creds_info["private_key"]
            # \n 文字の置換
            key = key.replace("\\n", "\n")
            # 実際の改行が含まれている場合の正規化
            if "-----BEGIN PRIVATE KEY-----" in key and "\n" not in key:
                key = key.replace("-----BEGIN PRIVATE KEY-----", "-----BEGIN PRIVATE KEY-----\n")
                key = key.replace("-----END PRIVATE KEY-----", "\n-----END PRIVATE KEY-----")
            creds_info["private_key"] = key
            
        creds = Credentials.from_service_account_info(creds_info, scopes=SCOPES)
    else:
        creds = Credentials.from_service_account_file("credentials.json", scopes=SCOPES)
        
    client = gspread.authorize(creds)
    m_doc = client.open_by_key(MASTER_KEY)
    a_doc = client.open_by_key(ATTENDANCE_KEY)
    
    return m_doc.sheet1, a_doc.sheet1