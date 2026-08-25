"""
報名系統 - 主程式（目前版本：純登記，尚未串接付款）
顧客先選擇活動場次，再填寫報名資料。
之後要加 LINE Pay 付款時，把 linepay.py 接回本檔案的送出流程即可。
"""
import datetime
import uuid

import streamlit as st

import db
from style import inject_theme, hero, BRAND_NAME

st.set_page_config(page_title=f"活動報名｜{BRAND_NAME}", page_icon="🐝", layout="centered")
inject_theme()


def format_event_time(iso_str: str | None) -> str:
    if not iso_str:
        return "時間未定"
    try:
        dt = datetime.datetime.fromisoformat(iso_str.replace("Z", "+00:00"))
        return dt.strftime("%Y/%m/%d (%a) %H:%M")
    except ValueError:
        return iso_str


def registration_form():
    hero("蜂場活動報名", "跟著蜂農走進蜂場，看蜜蜂如何釀出一年一收的甜")

    with st.spinner("載入活動列表中..."):
        try:
            events = db.get_active_events()
        except Exception as e:
            st.error(f"讀取活動列表失敗，請稍後再試。\n\n錯誤訊息：{e}")
            return

    if not events:
        st.info("目前尚無開放報名的蜂場活動，關注我們，下一梯採蜜體驗開放時第一時間通知您。")
        return

    def label_for(e: dict) -> str:
        return f"{e['name']}｜{format_event_time(e.get('event_time'))}"

    options = {label_for(e): e for e in events}
    selected_label = st.selectbox("選擇要報名的活動", list(options.keys()))
    selected_event = options[selected_label]

    st.divider()
    st.write(f"📍 **地點**：{selected_event.get('location') or '未提供'}")
    st.write(f"🕒 **時間**：{format_event_time(selected_event.get('event_time'))}")
    if selected_event.get("description"):
        st.write(f"📋 **內容**：{selected_event['description']}")
    amount = int(selected_event.get("amount") or 0)
    currency = selected_event.get("currency") or "TWD"
    st.write(f"💰 **報名費**：{amount} {currency}")
    st.divider()

    with st.form("registration_form", clear_on_submit=True):
        name = st.text_input("姓名 *")
        phone = st.text_input("聯絡電話 *")
        email = st.text_input("Email")
        note = st.text_area("備註（例如：飲食禁忌、特殊需求）", height=80)
        submitted = st.form_submit_button("送出報名", use_container_width=True)

    if not submitted:
        return

    if not name.strip() or not phone.strip():
        st.error("請填寫姓名與聯絡電話。")
        return

    order_id = f"REG{uuid.uuid4().hex[:12].upper()}"

    with st.spinner("送出報名中..."):
        try:
            db.append_registration(
                name=name.strip(),
                phone=phone.strip(),
                email=email.strip(),
                note=note.strip(),
                amount=amount,
                order_id=order_id,
                event_id=selected_event["id"],
                event_name=selected_event["name"],
            )
        except Exception as e:
            st.error(f"報名送出失敗，請稍後再試或聯絡工作人員。\n\n錯誤訊息：{e}")
            return

    st.success("報名成功！🐝🎉")
    st.write(f"活動：{selected_event['name']}")
    st.write(f"訂單編號：`{order_id}`")
    if amount > 0:
        st.caption("蜂農將會收到您的報名紀錄，如需付款會另行通知，期待在蜂場見到您。")
    else:
        st.caption("蜂農將會收到您的報名紀錄，期待在蜂場見到您。")


if __name__ == "__main__":
    registration_form()
