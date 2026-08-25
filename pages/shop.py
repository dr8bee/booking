"""
商城頁面（給顧客用）：瀏覽商品 → 加入購物車 → LINE Pay 結帳。
放在 pages/ 資料夾下，網址為 /shop。
"""
import uuid

import streamlit as st

import db
import promo_engine
from linepay import LinePayClient, LinePayError
from style import inject_theme, hero, BRAND_NAME

st.set_page_config(page_title=f"蜂蜜嚴選｜{BRAND_NAME}", page_icon="🍯", layout="wide")
inject_theme()

APP_CFG = st.secrets["app"]
LINEPAY_CFG = st.secrets.get("linepay")
BASE_URL = APP_CFG["base_url"].rstrip("/")
CURRENCY = APP_CFG.get("currency", "TWD")

if "cart" not in st.session_state:
    st.session_state.cart = {}  # {product_id: qty}
if "show_checkout" not in st.session_state:
    st.session_state.show_checkout = False


def get_linepay_client() -> LinePayClient | None:
    if not LINEPAY_CFG:
        return None
    return LinePayClient(
        channel_id=LINEPAY_CFG["channel_id"],
        channel_secret=LINEPAY_CFG["channel_secret"],
        env=LINEPAY_CFG.get("env", "sandbox"),
    )


def effective_price(p: dict) -> int:
    return int(p["price"])


def show_catalog(products: list[dict], promo_map: dict[int, list[dict]]):
    hero("蜂蜜嚴選", "一年一收．自家蜂場現採現裝．純淨不加糖")

    if not products:
        st.info("目前尚無上架商品，蜂蜜正在熟成中，敬請期待。")
        return

    cols = st.columns(3)
    for idx, p in enumerate(products):
        with cols[idx % 3]:
            with st.container(border=True):
                if p.get("image_url"):
                    st.image(p["image_url"], use_container_width=True)
                st.markdown(f"**{p['name']}**")
                if p.get("description"):
                    st.caption(p["description"])

                price = effective_price(p)
                st.markdown(f"**{price} {CURRENCY}**")

                promos = promo_map.get(p["id"], [])
                for promo in promos:
                    text = promo.get("display_text") or promo_engine.display_text_for(
                        promo["rule_type"], promo.get("params") or {}
                    )
                    st.caption(f"🎉 {text}")

                qty = st.number_input(
                    "數量", min_value=1, value=1, step=1, key=f"qty_{p['id']}"
                )

                if promos:
                    line_total, applied = promo_engine.calc_line_price(
                        price, int(qty), promos
                    )
                    if applied:
                        st.caption(f"→ 小計 **{line_total} {CURRENCY}**（已套用優惠）")

                if st.button("加入購物車", key=f"add_{p['id']}", use_container_width=True):
                    st.session_state.cart[p["id"]] = (
                        st.session_state.cart.get(p["id"], 0) + int(qty)
                    )
                    st.toast(f"已加入 {p['name']} x{int(qty)}")
                    st.rerun()

    show_cart_sidebar(products, promo_map)


def show_cart_sidebar(products: list[dict], promo_map: dict[int, list[dict]]):
    product_map = {p["id"]: p for p in products}
    with st.sidebar:
        st.header("🛒 購物車")
        if not st.session_state.cart:
            st.caption("購物車是空的")
            return

        total = 0
        for pid, qty in list(st.session_state.cart.items()):
            p = product_map.get(pid)
            if not p:
                continue
            price = effective_price(p)
            promos = promo_map.get(pid, [])
            subtotal, applied = promo_engine.calc_line_price(price, qty, promos)
            total += subtotal
            col1, col2 = st.columns([3, 1])
            with col1:
                st.write(f"{p['name']} x{qty}")
                if applied:
                    original = price * qty
                    st.caption(f"~~{original}~~ → {subtotal} {CURRENCY} 🎉")
                else:
                    st.caption(f"{subtotal} {CURRENCY}")
            with col2:
                if st.button("移除", key=f"remove_{pid}"):
                    del st.session_state.cart[pid]
                    st.rerun()

        st.divider()
        st.write(f"**總計：{total} {CURRENCY}**")

        if st.button("前往結帳", use_container_width=True, type="primary"):
            st.session_state.show_checkout = True
            st.rerun()


def show_checkout(products: list[dict], promo_map: dict[int, list[dict]]):
    hero("結帳", "確認訂購內容，蜂農會盡快為您裝罐出貨")
    product_map = {p["id"]: p for p in products}

    if not st.session_state.cart:
        st.info("購物車是空的，請先選購商品。")
        if st.button("回到商品頁"):
            st.session_state.show_checkout = False
            st.rerun()
        return

    if st.button("← 返回購物"):
        st.session_state.show_checkout = False
        st.rerun()

    items = []
    total = 0
    for pid, qty in st.session_state.cart.items():
        p = product_map.get(pid)
        if not p:
            continue
        price = effective_price(p)
        promos = promo_map.get(pid, [])
        line_total, applied = promo_engine.calc_line_price(price, qty, promos)
        total += line_total
        items.append(
            {
                "product_id": pid,
                "name": p["name"],
                "qty": qty,
                "unit_price": price,
                "line_total": line_total,
                "promo_name": applied["name"] if applied else None,
            }
        )
        if applied:
            original = price * qty
            st.write(f"{p['name']} x{qty}　→　~~{original}~~ **{line_total} {CURRENCY}** 🎉 {applied['name']}")
        else:
            st.write(f"{p['name']} x{qty}　→　{line_total} {CURRENCY}")

    st.write(f"### 總計：{total} {CURRENCY}")
    st.divider()

    client = get_linepay_client()
    if client is None:
        st.info(
            "🚧 商城線上付款尚未開放，敬請期待。若想選購以上商品，"
            "請直接私訊或到店洽詢，謝謝！"
        )
        return

    with st.form("checkout_form"):
        name = st.text_input("姓名 *")
        phone = st.text_input("聯絡電話 *")
        email = st.text_input("Email")
        submitted = st.form_submit_button(
            "送出並前往 LINE Pay 付款", use_container_width=True
        )

    if not submitted:
        return

    if not name.strip() or not phone.strip():
        st.error("請填寫姓名與聯絡電話。")
        return

    order_id = f"SHOP{uuid.uuid4().hex[:12].upper()}"

    with st.spinner("建立訂單中..."):
        try:
            db.create_shop_order(
                order_id=order_id,
                name=name.strip(),
                phone=phone.strip(),
                email=email.strip(),
                items=items,
                total_amount=total,
            )
        except Exception as e:
            st.error(f"建立訂單失敗，請稍後再試。\n\n錯誤訊息：{e}")
            return

    confirm_url = f"{BASE_URL}/shop?orderId={order_id}"
    cancel_url = f"{BASE_URL}/shop?cancelled=1&orderId={order_id}"

    with st.spinner("建立付款連結中..."):
        try:
            info = client.request_payment(
                order_id=order_id,
                amount=total,
                product_name="商城訂單",
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
    st.success("訂單已建立，請完成付款！")
    st.write(f"訂單編號：`{order_id}`")
    st.link_button("👉 前往 LINE Pay 付款", payment_url, use_container_width=True)
    st.markdown(
        f'<meta http-equiv="refresh" content="3;url={payment_url}">',
        unsafe_allow_html=True,
    )
    st.caption("若 3 秒後沒有自動跳轉，請點擊上方按鈕。")


def handle_payment_confirm(order_id: str, transaction_id: str):
    st.title("💳 付款確認中")

    order = db.get_shop_order(order_id)
    if order is None:
        st.error("找不到對應的訂單，請聯絡工作人員確認。")
        return

    client = get_linepay_client()
    if client is None:
        st.error("尚未設定 LINE Pay，請聯絡店家管理員。")
        return

    with st.spinner("正在向 LINE Pay 確認付款結果..."):
        try:
            client.confirm_payment(
                transaction_id=transaction_id,
                amount=order["total_amount"],
                currency=CURRENCY,
            )
        except LinePayError as e:
            db.update_shop_order_status(order_id, "confirm_failed", transaction_id)
            st.error(f"付款確認失敗：{e.return_message}")
            st.caption("若已扣款請保留付款截圖，並聯絡工作人員協助核對。")
            return
        except Exception as e:
            st.error(f"付款確認過程發生錯誤，請聯絡工作人員。\n\n錯誤訊息：{e}")
            return

    db.update_shop_order_status(order_id, "paid", transaction_id)
    st.session_state.cart = {}
    st.session_state.show_checkout = False

    st.success("付款完成，訂單成立！🐝🍯")
    st.write(f"訂單編號：`{order_id}`")
    st.write(f"金額：{order['total_amount']} {CURRENCY}")
    st.caption("此頁面可直接關閉，蜂農將會收到您的訂單，盡快為您裝罐出貨。")


def handle_payment_cancelled(order_id: str):
    st.title("已取消付款")
    db.update_shop_order_status(order_id, "cancelled")
    st.warning("您已取消本次付款，訂單將標記為未完成。")
    st.write(f"訂單編號：`{order_id}`")
    if st.button("回到商品頁"):
        st.query_params.clear()
        st.session_state.show_checkout = False
        st.rerun()


def main():
    params = st.query_params
    order_id = params.get("orderId")
    transaction_id = params.get("transactionId")
    cancelled = params.get("cancelled")

    if order_id and transaction_id:
        handle_payment_confirm(order_id, transaction_id)
        return
    if order_id and cancelled:
        handle_payment_cancelled(order_id)
        return

    with st.spinner("載入商品中..."):
        try:
            products = db.get_active_products()
            promo_map = db.get_active_product_promotion_map()
        except Exception as e:
            st.error(f"讀取商品失敗，請稍後再試。\n\n錯誤訊息：{e}")
            return

    if st.session_state.show_checkout:
        show_checkout(products, promo_map)
    else:
        show_catalog(products, promo_map)


if __name__ == "__main__":
    main()
