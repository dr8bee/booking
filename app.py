"""
報名 + LINE Pay 收款系統 - 主程式
Streamlit 單頁應用：同一個網址同時負責「報名表單」與「LINE Pay 付款回導確認」。
這是給顧客使用的頁面。後台名單頁面在 pages/admin.py。
"""
import uuid

import streamlit as st

import db
from linepay import LinePayClient, LinePayError

st.set_page_config(page_title="8博士農場 活動報名", page_icon="📝", layout="centered")

# ---------- 讀取設定 ----------
APP_CFG = st.secrets["app"]
LINEPAY_CFG = st.secrets["linepay"]

BASE_URL = APP_CFG["base_url"].rstrip("/")  # 例如 https://your-app.streamlit.app
ITEM_NAME = APP_CFG.get("item_name", "活動報名費")
AMOUNT = int(APP_CFG.get("amount", 0))
CURRENCY = APP_CFG.get("currency", "TWD")

client = LinePayClient(
    channel_id=LINEPAY_CFG["channel_id"],
    channel_secret=LINEPAY_CFG["channel_secret"],
    env=LINEPAY_CFG.get("env", "sandbox"),
)


def registration_form():
    st.title("📝 活動報名")
    st.write(f"報名費用：**{AMOUNT} {CURRENCY}**")

    with st.form("registration_form", clear_on_submit=False):
        name = st.text_input("姓名 *")
        phone = st.text_input("聯絡電話 *")
        email = st.text_input("Email")
        note = st.text_area("備註（例如：飲食禁忌、特殊需求）", height=80)
        submitted = st.form_submit_button("送出並前往付款", use_container_width=True)

    if not submitted:
        return

    if not name.strip() or not phone.strip():
        st.error("請填寫姓名與聯絡電話。")
        return

    order_id = f"REG{uuid.uuid4().hex[:12].upper()}"

    with st.spinner("建立報名紀錄中..."):
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
            st.error(f"寫入報名紀錄失敗，請稍後再試或聯絡工作人員。\n\n錯誤訊息：{e}")
            return

    confirm_url = f"{BASE_URL}/?orderId={order_id}"
    cancel_url = f"{BASE_URL}/?cancelled=1&orderId={order_id}"

    with st.spinner("建立付款連結中..."):
        try:
            info = client.request_payment(
                order_id=order_id,
                amount=AMOUNT,
                product_name=ITEM_NAME,
                confirm_url=confirm_url,
                cancel_url=cancel_url,
                currency=CURRENCY,
            )
        except LinePayError as e:
            st.error(f"建立 LINE Pay 付款連結失敗：{e.return_message}")
            return
        except Exception as e:
            st.error(f"建立 LINE Pay 付款連結失敗，請稍後再試。\n\n錯誤訊息：{e}")
            return

    payment_url = info["paymentUrl"]["web"]

    st.success("報名已登記，請完成付款！")
    st.write(f"訂單編號：`{order_id}`")
    st.link_button("👉 前往 LINE Pay 付款", payment_url, use_container_width=True)

    # 沒有自動跳轉點擊按鈕的環境，提供自動導轉作為備援
    st.markdown(
        f'<meta http-equiv="refresh" content="3;url={payment_url}">',
        unsafe_allow_html=True,
    )
    st.caption("若 3 秒後沒有自動跳轉，請點擊上方按鈕。")


def handle_payment_confirm(order_id: str, transaction_id: str):
    st.title("💳 付款確認中")

    amount = db.get_registration_amount(order_id)
    if amount is None:
        st.error("找不到對應的報名紀錄，請聯絡工作人員確認。")
        return

    with st.spinner("正在向 LINE Pay 確認付款結果..."):
        try:
            client.confirm_payment(
                transaction_id=transaction_id, amount=amount, currency=CURRENCY
            )
        except LinePayError as e:
            db.update_status(order_id, "confirm_failed", transaction_id)
            st.error(f"付款確認失敗：{e.return_message}")
            st.caption("若已扣款請保留付款截圖，並聯絡工作人員協助核對。")
            return
        except Exception as e:
            st.error(f"付款確認過程發生錯誤，請聯絡工作人員。\n\n錯誤訊息：{e}")
            return

    db.update_status(order_id, "paid", transaction_id)

    st.success("付款完成，報名成功！🎉")
    st.write(f"訂單編號：`{order_id}`")
    st.write(f"金額：{amount} {CURRENCY}")
    st.caption("此頁面可直接關閉，工作人員將會收到您的報名紀錄。")


def handle_payment_cancelled(order_id: str):
    st.title("已取消付款")
    db.update_status(order_id, "cancelled")
    st.warning("您已取消本次付款，報名紀錄將標記為未完成。")
    st.write(f"訂單編號：`{order_id}`")
    if st.button("重新報名"):
        st.query_params.clear()
        st.rerun()


def main():
    params = st.query_params

    order_id = params.get("orderId")
    transaction_id = params.get("transactionId")
    cancelled = params.get("cancelled")

    if order_id and transaction_id:
        handle_payment_confirm(order_id, transaction_id)
    elif order_id and cancelled:
        handle_payment_cancelled(order_id)
    else:
        registration_form()


if __name__ == "__main__":
    main()
