"""
報名名單後台頁面（給店家用）。
放在 pages/ 資料夾下，Streamlit 會自動加到側邊欄選單，網址為 /admin。
"""
import pandas as pd
import streamlit as st

import db

st.set_page_config(page_title="報名名單後台", page_icon="📋", layout="wide")

STATUS_LABEL = {
    "pending": "待付款",
    "paid": "已付款 ✅",
    "cancelled": "已取消",
    "confirm_failed": "確認失敗（需人工核對）",
}


def check_password() -> bool:
    """簡單的密碼保護，密碼存在 secrets 裡，不寫死在程式碼中。"""
    if st.session_state.get("admin_authed"):
        return True

    st.title("🔒 後台登入")
    password = st.text_input("請輸入後台密碼", type="password")
    if st.button("登入"):
        correct_password = st.secrets["admin"]["password"]
        if password == correct_password:
            st.session_state["admin_authed"] = True
            st.rerun()
        else:
            st.error("密碼錯誤")
    return False


def show_dashboard():
    st.title("📋 報名名單")

    with st.spinner("讀取報名資料中..."):
        records = db.get_all_registrations()

    if not records:
        st.info("目前還沒有任何報名紀錄。")
        return

    df = pd.DataFrame(records)

    # 整理欄位順序與中文欄名，方便店家閱讀
    column_map = {
        "created_at": "建立時間",
        "name": "姓名",
        "phone": "電話",
        "email": "Email",
        "note": "備註",
        "amount": "金額",
        "order_id": "訂單編號",
        "status": "狀態",
        "transaction_id": "LinePay交易編號",
    }
    ordered_cols = [c for c in column_map if c in df.columns]
    df = df[ordered_cols].rename(columns=column_map)
    df["狀態"] = df["狀態"].map(lambda s: STATUS_LABEL.get(s, s))

    # 統計摘要
    col1, col2, col3 = st.columns(3)
    col1.metric("總報名數", len(df))
    paid_count = (df["狀態"] == STATUS_LABEL["paid"]).sum()
    col2.metric("已付款", int(paid_count))
    total_paid_amount = df.loc[df["狀態"] == STATUS_LABEL["paid"], "金額"].sum()
    col3.metric("已收金額", f"{int(total_paid_amount)} 元")

    st.divider()

    # 篩選狀態
    status_options = ["全部"] + sorted(df["狀態"].unique().tolist())
    selected_status = st.selectbox("篩選狀態", status_options)
    if selected_status != "全部":
        df_display = df[df["狀態"] == selected_status]
    else:
        df_display = df

    st.dataframe(df_display, use_container_width=True, hide_index=True)

    csv = df_display.to_csv(index=False).encode("utf-8-sig")
    st.download_button(
        "⬇️ 匯出目前列表為 CSV",
        data=csv,
        file_name="報名名單.csv",
        mime="text/csv",
    )

    if st.button("登出"):
        st.session_state["admin_authed"] = False
        st.rerun()


def main():
    if check_password():
        show_dashboard()


if __name__ == "__main__":
    main()
