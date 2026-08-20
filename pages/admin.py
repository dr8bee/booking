"""
後台頁面（給店家用）：報名名單 + 活動管理。
放在 pages/ 資料夾下，Streamlit 會自動加到側邊欄選單，網址為 /admin。
"""
import datetime

import pandas as pd
import streamlit as st

import db

st.set_page_config(page_title="報名名單後台", page_icon="📋", layout="wide")

STATUS_LABEL = {
    "registered": "已報名",
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


# ---------------------------------------------------------------------------
# 報名名單頁籤
# ---------------------------------------------------------------------------


def show_registrations_tab():
    with st.spinner("讀取報名資料中..."):
        try:
            records = db.get_all_registrations()
        except Exception as e:
            st.error(f"讀取報名資料失敗：{e}")
            return

    if not records:
        st.info("目前還沒有任何報名紀錄。")
        return

    df = pd.DataFrame(records)

    column_map = {
        "create_date": "建立時間",
        "event_name": "活動",
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

    col1, col2, col3 = st.columns(3)
    col1.metric("總報名數", len(df))
    paid_count = (df["狀態"] == STATUS_LABEL["paid"]).sum()
    col2.metric("已付款", int(paid_count))
    total_paid_amount = df.loc[df["狀態"] == STATUS_LABEL["paid"], "金額"].sum()
    col3.metric("已收金額", f"{int(total_paid_amount)} 元")

    st.divider()

    filter_col1, filter_col2 = st.columns(2)
    with filter_col1:
        status_options = ["全部"] + sorted(df["狀態"].unique().tolist())
        selected_status = st.selectbox("篩選狀態", status_options)
    with filter_col2:
        event_options = ["全部"] + sorted(df["活動"].dropna().unique().tolist())
        selected_event = st.selectbox("篩選活動", event_options)

    df_display = df
    if selected_status != "全部":
        df_display = df_display[df_display["狀態"] == selected_status]
    if selected_event != "全部":
        df_display = df_display[df_display["活動"] == selected_event]

    st.dataframe(df_display, use_container_width=True, hide_index=True)

    csv = df_display.to_csv(index=False).encode("utf-8-sig")
    st.download_button(
        "⬇️ 匯出目前列表為 CSV",
        data=csv,
        file_name="報名名單.csv",
        mime="text/csv",
    )


# ---------------------------------------------------------------------------
# 活動管理頁籤
# ---------------------------------------------------------------------------


def show_event_form():
    st.subheader("➕ 新增活動")
    with st.form("new_event_form", clear_on_submit=True):
        name = st.text_input("活動名稱 *")
        location = st.text_input("地點")
        col1, col2 = st.columns(2)
        with col1:
            event_date = st.date_input("活動日期", value=None)
        with col2:
            event_clock = st.time_input("活動時間", value=None)
        description = st.text_area("活動內容說明", height=100)
        amount = st.number_input("報名費金額", min_value=0, step=50, value=0)
        submitted = st.form_submit_button("新增活動", use_container_width=True)

    if not submitted:
        return

    if not name.strip():
        st.error("請填寫活動名稱。")
        return

    event_time_iso = ""
    if event_date and event_clock:
        event_time_iso = datetime.datetime.combine(event_date, event_clock).isoformat()
    elif event_date:
        event_time_iso = datetime.datetime.combine(
            event_date, datetime.time(0, 0)
        ).isoformat()

    try:
        db.create_event(
            name=name.strip(),
            location=location.strip(),
            event_time=event_time_iso,
            description=description.strip(),
            amount=int(amount),
        )
    except Exception as e:
        st.error(f"新增活動失敗：{e}")
        return

    st.success(f"活動「{name}」已新增！")
    st.rerun()


def format_event_time(iso_str: str | None) -> str:
    if not iso_str:
        return "時間未定"
    try:
        dt = datetime.datetime.fromisoformat(iso_str.replace("Z", "+00:00"))
        return dt.strftime("%Y/%m/%d (%a) %H:%M")
    except ValueError:
        return iso_str


def show_event_list():
    st.subheader("📅 活動列表")
    try:
        events = db.get_all_events()
    except Exception as e:
        st.error(f"讀取活動列表失敗：{e}")
        return

    if not events:
        st.info("目前還沒有任何活動，請先在上方新增。")
        return

    for e in events:
        with st.container(border=True):
            col_info, col_action = st.columns([4, 1])
            with col_info:
                status_tag = "🟢 開放報名中" if e.get("is_active") else "🔴 已關閉"
                st.markdown(f"**{e['name']}**　{status_tag}")
                st.caption(
                    f"📍 {e.get('location') or '未提供'}　"
                    f"🕒 {format_event_time(e.get('event_time'))}　"
                    f"💰 {e.get('amount', 0)} {e.get('currency', 'TWD')}"
                )
                if e.get("description"):
                    st.caption(f"📋 {e['description']}")
            with col_action:
                if e.get("is_active"):
                    if st.button("關閉報名", key=f"close_{e['id']}", use_container_width=True):
                        db.set_event_active(e["id"], False)
                        st.rerun()
                else:
                    if st.button("重新開放", key=f"open_{e['id']}", use_container_width=True):
                        db.set_event_active(e["id"], True)
                        st.rerun()


def show_events_tab():
    show_event_form()
    st.divider()
    show_event_list()


# ---------------------------------------------------------------------------
# 主流程
# ---------------------------------------------------------------------------


def show_dashboard():
    st.title("📋 報名系統後台")

    tab_registrations, tab_events = st.tabs(["報名名單", "活動管理"])
    with tab_registrations:
        show_registrations_tab()
    with tab_events:
        show_events_tab()

    st.divider()
    if st.button("登出"):
        st.session_state["admin_authed"] = False
        st.rerun()


def main():
    if check_password():
        show_dashboard()


if __name__ == "__main__":
    main()
