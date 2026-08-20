"""
報名系統 - 主程式（目前版本：純登記，尚未串接付款）
之後要加 LINE Pay 付款時，把 linepay.py 接回本檔案的送出流程即可。
"""
import uuid

import streamlit as st

import db

st.set_page_config(page_title="活動報名", page_icon="📝", layout="centered")

APP_CFG = st.secrets["app"]
ITEM_NAME = APP_CFG.get("item_name", "活動報名")
AMOUNT = int(APP_CFG.get("amount", 0))
CURRENCY = APP_CFG.get("currency", "TWD")


def registration_form():
    st.title("📝 活動報名")
    if AMOUNT > 0:
        st.caption(f"{ITEM_NAME}｜費用 {AMOUNT} {CURRENCY}（目前先不用線上付款，現場付款或另行通知）")
    else:
        st.caption(ITEM_NAME)

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
                amount=AMOUNT,
                order_id=order_id,
            )
        except Exception as e:
            st.error(f"報名送出失敗，請稍後再試或聯絡工作人員。\n\n錯誤訊息：{e}")
            return

    st.success("報名成功！🎉")
    st.write(f"訂單編號：`{order_id}`")
    st.caption("工作人員將會收到您的報名紀錄，如需付款會另行通知。")


if __name__ == "__main__":
    registration_form()
