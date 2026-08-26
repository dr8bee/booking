"""
後台頁面（給店家用）：報名名單 + 活動管理。
放在 pages/ 資料夾下，Streamlit 會自動加到側邊欄選單，網址為 /admin。
"""
import datetime

import pandas as pd
import streamlit as st

import db
import promo_engine
from style import inject_theme, BRAND_NAME

st.set_page_config(page_title=f"後台｜{BRAND_NAME}", page_icon="🐝", layout="wide")
inject_theme()

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

    st.caption("勾選最左側的方框可選取要刪除的報名紀錄。")
    df_editable = df_display.copy()
    df_editable.insert(0, "刪除", False)
    edited_df = st.data_editor(
        df_editable,
        use_container_width=True,
        hide_index=True,
        disabled=[c for c in df_editable.columns if c != "刪除"],
        key="registrations_editor",
    )

    selected_order_ids = edited_df.loc[edited_df["刪除"], "訂單編號"].tolist()
    if selected_order_ids:
        st.warning(f"已勾選 {len(selected_order_ids)} 筆報名紀錄，刪除後無法復原。")
        if st.button("🗑️ 確認刪除勾選項目", type="primary"):
            errors = []
            for order_id in selected_order_ids:
                try:
                    db.delete_registration(order_id)
                except Exception as e:
                    errors.append(f"{order_id}：{e}")
            if errors:
                st.error("部分刪除失敗：\n" + "\n".join(errors))
            else:
                st.success(f"已刪除 {len(selected_order_ids)} 筆報名紀錄。")
            st.rerun()

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
# 商品管理頁籤
# ---------------------------------------------------------------------------


def show_product_form():
    st.subheader("➕ 上架新商品")
    with st.form("new_product_form", clear_on_submit=True):
        name = st.text_input("商品名稱 *")
        description = st.text_area("商品介紹", height=100)
        price = st.number_input("價格 *", min_value=0, step=10, value=0)
        uploaded_file = st.file_uploader(
            "商品圖片", type=["png", "jpg", "jpeg", "webp"]
        )
        submitted = st.form_submit_button("上架商品", use_container_width=True)

    if not submitted:
        return

    if not name.strip():
        st.error("請填寫商品名稱。")
        return
    if price <= 0:
        st.error("請填寫價格。")
        return

    image_url = ""
    if uploaded_file is not None:
        with st.spinner("上傳圖片中..."):
            try:
                image_url = db.upload_product_image(
                    file_bytes=uploaded_file.getvalue(),
                    filename=uploaded_file.name,
                    content_type=uploaded_file.type or "image/jpeg",
                )
            except Exception as e:
                st.error(f"圖片上傳失敗：{e}")
                return

    try:
        db.create_product(
            name=name.strip(),
            description=description.strip(),
            price=int(price),
            image_url=image_url,
        )
    except Exception as e:
        st.error(f"新增商品失敗：{e}")
        return

    st.success(f"商品「{name}」已上架！之後可以到「促銷管理」頁籤幫它設定優惠。")
    st.rerun()


def show_product_list():
    st.subheader("🛍️ 商品列表")
    try:
        products = db.get_all_products()
    except Exception as e:
        st.error(f"讀取商品列表失敗：{e}")
        return

    if not products:
        st.info("目前還沒有任何商品，請先在上方新增。")
        return

    try:
        all_promotions = db.get_all_promotions()
    except Exception as e:
        st.error(f"讀取促銷規則失敗：{e}")
        all_promotions = []

    promo_options = {p["name"]: p["id"] for p in all_promotions}
    promo_id_to_name = {p["id"]: p["name"] for p in all_promotions}

    for p in products:
        with st.container(border=True):
            col_img, col_info, col_action = st.columns([1, 3, 1])
            with col_img:
                if p.get("image_url"):
                    st.image(p["image_url"], use_container_width=True)
            with col_info:
                status_tag = "🟢 上架中" if p.get("is_active") else "🔴 已下架"
                st.markdown(f"**{p['name']}**　{status_tag}")
                st.caption(f"{p['price']} 元")
                if p.get("description"):
                    st.caption(p["description"])
            with col_action:
                if p.get("is_active"):
                    if st.button(
                        "下架", key=f"deactivate_{p['id']}", use_container_width=True
                    ):
                        db.set_product_active(p["id"], False)
                        st.rerun()
                else:
                    if st.button(
                        "重新上架", key=f"activate_{p['id']}", use_container_width=True
                    ):
                        db.set_product_active(p["id"], True)
                        st.rerun()
                if st.button(
                    "🗑️ 刪除",
                    key=f"delete_product_{p['id']}",
                    use_container_width=True,
                ):
                    db.delete_product(p["id"])
                    st.rerun()

            if promo_options:
                st.divider()
                try:
                    applied_promo_ids = db.get_product_promotions(p["id"])
                except Exception as e:
                    st.error(f"讀取套用規則失敗：{e}")
                    applied_promo_ids = []
                applied_promo_names = [
                    promo_id_to_name.get(pid, f"（規則 #{pid}）")
                    for pid in applied_promo_ids
                ]

                new_selection = st.multiselect(
                    "這個商品要套用哪些促銷規則",
                    list(promo_options.keys()),
                    default=applied_promo_names,
                    key=f"product_promos_{p['id']}",
                )
                if st.button("儲存套用規則", key=f"save_product_promos_{p['id']}"):
                    new_ids = [promo_options[n] for n in new_selection]
                    try:
                        db.set_product_promotions(p["id"], new_ids)
                    except Exception as e:
                        st.error(f"更新失敗：{e}")
                    else:
                        st.success("已更新。")
                        st.rerun()
            else:
                st.caption("目前還沒有促銷規則，可以到下方「促銷管理」頁籤新增。")


def show_products_tab():
    show_product_form()
    st.divider()
    show_product_list()


# ---------------------------------------------------------------------------
# 促銷管理頁籤
# ---------------------------------------------------------------------------


def show_promotion_form():
    st.subheader("➕ 新增促銷規則")

    rule_label_to_key = {v: k for k, v in promo_engine.RULE_TYPES.items()}
    rule_label = st.selectbox(
        "規則類型", list(promo_engine.RULE_TYPES.values()), key="new_promo_rule_type"
    )
    rule_type = rule_label_to_key[rule_label]

    with st.form("new_promo_form", clear_on_submit=True):
        name = st.text_input("規則名稱 *（給自己辨識用，例如：夏季買二送一）")

        params: dict = {}
        if rule_type == "percent_off":
            col1, col2 = st.columns(2)
            with col1:
                percent = st.number_input(
                    "折扣百分比（例如填 15 代表打 85 折）",
                    min_value=1,
                    max_value=99,
                    value=10,
                )
            with col2:
                min_qty = st.number_input("至少購買幾件才套用", min_value=1, value=1)
            params = {"percent": int(percent), "min_qty": int(min_qty)}
        elif rule_type == "amount_off":
            col1, col2 = st.columns(2)
            with col1:
                amount = st.number_input(
                    "折抵金額", min_value=1, value=50, step=10
                )
            with col2:
                min_qty = st.number_input("至少購買幾件才套用", min_value=1, value=1)
            params = {"amount": int(amount), "min_qty": int(min_qty)}
        elif rule_type == "buy_x_get_y":
            col1, col2 = st.columns(2)
            with col1:
                buy_qty = st.number_input("購買幾件", min_value=1, value=2)
            with col2:
                get_qty = st.number_input("加送幾件", min_value=1, value=1)
            params = {"buy_qty": int(buy_qty), "get_qty": int(get_qty)}
        elif rule_type == "bundle_price":
            col1, col2 = st.columns(2)
            with col1:
                bundle_qty = st.number_input("每幾件", min_value=1, value=3)
            with col2:
                bundle_price = st.number_input(
                    "優惠總價", min_value=1, value=250, step=10
                )
            params = {"bundle_qty": int(bundle_qty), "bundle_price": int(bundle_price)}

        display_text = st.text_input(
            "顯示文字（留空則自動產生，例如「買2送1」「85折」）"
        )

        submitted = st.form_submit_button("新增促銷規則", use_container_width=True)

    if not submitted:
        return

    if not name.strip():
        st.error("請填寫規則名稱。")
        return

    try:
        db.create_promotion(
            name=name.strip(),
            rule_type=rule_type,
            params=params,
            display_text=display_text.strip(),
        )
    except Exception as e:
        st.error(f"新增促銷規則失敗：{e}")
        return

    preview = promo_engine.display_text_for(rule_type, params, display_text.strip())
    st.success(
        f"促銷規則「{name}」已建立！套用效果：{preview}\n\n"
        "接下來請到「商品管理」頁籤，在要套用的商品上勾選這條規則。"
    )
    st.rerun()


def show_promotion_list(products: list[dict]):
    st.subheader("📋 促銷規則列表")
    try:
        promotions = db.get_all_promotions()
    except Exception as e:
        st.error(f"讀取促銷規則失敗：{e}")
        return

    if not promotions:
        st.info("目前還沒有任何促銷規則，請先在上方新增。")
        return

    product_options = {p["name"]: p["id"] for p in products}
    product_id_to_name = {p["id"]: p["name"] for p in products}

    for promo in promotions:
        try:
            applied_ids = db.get_promotion_products(promo["id"])
        except Exception as e:
            st.error(f"讀取「{promo['name']}」適用商品失敗：{e}")
            applied_ids = []
        applied_names = [
            product_id_to_name.get(pid, f"（商品 #{pid}）") for pid in applied_ids
        ]

        text = promo.get("display_text") or promo_engine.display_text_for(
            promo["rule_type"], promo.get("params") or {}
        )
        status_tag = "🟢 啟用中" if promo.get("is_active") else "🔴 已停用"

        with st.container(border=True):
            st.markdown(f"**{promo['name']}**　{status_tag}")
            st.caption(
                f"🎉 {text}　｜　套用商品："
                + ("、".join(applied_names) if applied_names else "（尚未指定商品）")
            )

            col1, col2, col3 = st.columns([2, 1, 1])
            with col1:
                new_selection = st.multiselect(
                    "調整套用商品",
                    list(product_options.keys()),
                    default=applied_names,
                    key=f"promo_products_{promo['id']}",
                )
                if st.button("儲存適用商品", key=f"save_promo_products_{promo['id']}"):
                    new_ids = [product_options[n] for n in new_selection]
                    try:
                        db.set_promotion_products(promo["id"], new_ids)
                    except Exception as e:
                        st.error(f"更新失敗：{e}")
                    else:
                        st.success("已更新。")
                        st.rerun()
            with col2:
                if promo.get("is_active"):
                    if st.button(
                        "停用",
                        key=f"deactivate_promo_{promo['id']}",
                        use_container_width=True,
                    ):
                        db.set_promotion_active(promo["id"], False)
                        st.rerun()
                else:
                    if st.button(
                        "啟用",
                        key=f"activate_promo_{promo['id']}",
                        use_container_width=True,
                    ):
                        db.set_promotion_active(promo["id"], True)
                        st.rerun()
            with col3:
                if st.button(
                    "🗑️ 刪除",
                    key=f"delete_promo_{promo['id']}",
                    use_container_width=True,
                ):
                    db.delete_promotion(promo["id"])
                    st.rerun()


def show_promotions_tab():
    try:
        products = db.get_all_products()
    except Exception as e:
        st.error(f"讀取商品列表失敗：{e}")
        return
    show_promotion_form()
    st.divider()
    show_promotion_list(products)


# ---------------------------------------------------------------------------
# 品牌故事頁籤
# ---------------------------------------------------------------------------


def show_philosophy_editor():
    st.subheader("✏️ 品牌理念文案")
    try:
        content = db.get_site_content()
    except Exception as e:
        st.error(f"讀取文案失敗：{e}")
        content = {}

    with st.form("philosophy_form"):
        title = st.text_input("標題", value=content.get("philosophy_title") or "")
        body = st.text_area(
            "理念內文", value=content.get("philosophy_body") or "", height=150
        )
        st.caption("三個亮點數字（例如年資、辦過幾場活動），留空就不會顯示在頁面上")
        c1, c2, c3 = st.columns(3)
        with c1:
            n1 = st.text_input("數字 1", value=content.get("stat1_number") or "")
            l1 = st.text_input("說明 1", value=content.get("stat1_label") or "")
        with c2:
            n2 = st.text_input("數字 2", value=content.get("stat2_number") or "")
            l2 = st.text_input("說明 2", value=content.get("stat2_label") or "")
        with c3:
            n3 = st.text_input("數字 3", value=content.get("stat3_number") or "")
            l3 = st.text_input("說明 3", value=content.get("stat3_label") or "")
        submitted = st.form_submit_button("儲存文案", use_container_width=True)

    if not submitted:
        return

    try:
        db.update_site_content(
            {
                "philosophy_title": title.strip(),
                "philosophy_body": body.strip(),
                "stat1_number": n1.strip(),
                "stat1_label": l1.strip(),
                "stat2_number": n2.strip(),
                "stat2_label": l2.strip(),
                "stat3_number": n3.strip(),
                "stat3_label": l3.strip(),
            }
        )
    except Exception as e:
        st.error(f"儲存失敗：{e}")
        return

    st.success("已儲存！")
    st.rerun()


def show_gallery_form():
    st.subheader("➕ 新增花絮照片")
    with st.form("new_gallery_form", clear_on_submit=True):
        caption = st.text_input("照片說明（例如：2024 秋季採蜜體驗）")
        uploaded_file = st.file_uploader(
            "照片", type=["png", "jpg", "jpeg", "webp"]
        )
        submitted = st.form_submit_button("上傳照片", use_container_width=True)

    if not submitted:
        return

    if uploaded_file is None:
        st.error("請選擇一張照片。")
        return

    with st.spinner("上傳照片中..."):
        try:
            image_url = db.upload_gallery_image(
                file_bytes=uploaded_file.getvalue(),
                filename=uploaded_file.name,
                content_type=uploaded_file.type or "image/jpeg",
            )
            db.create_gallery_photo(image_url=image_url, caption=caption.strip())
        except Exception as e:
            st.error(f"上傳失敗：{e}")
            return

    st.success("照片已新增！")
    st.rerun()


def show_gallery_list():
    st.subheader("🖼️ 花絮照片列表")
    try:
        photos = db.get_all_gallery_photos()
    except Exception as e:
        st.error(f"讀取花絮照片失敗：{e}")
        return

    if not photos:
        st.info("目前還沒有任何花絮照片，請先在上方新增。")
        return

    cols = st.columns(4)
    for idx, photo in enumerate(photos):
        with cols[idx % 4]:
            with st.container(border=True):
                st.image(photo["image_url"], use_container_width=True)
                if photo.get("caption"):
                    st.caption(photo["caption"])
                status_tag = "🟢 顯示中" if photo.get("is_active") else "🔴 已隱藏"
                st.caption(status_tag)
                if photo.get("is_active"):
                    if st.button(
                        "隱藏",
                        key=f"hide_gallery_{photo['id']}",
                        use_container_width=True,
                    ):
                        db.set_gallery_photo_active(photo["id"], False)
                        st.rerun()
                else:
                    if st.button(
                        "顯示",
                        key=f"show_gallery_{photo['id']}",
                        use_container_width=True,
                    ):
                        db.set_gallery_photo_active(photo["id"], True)
                        st.rerun()
                if st.button(
                    "🗑️ 刪除",
                    key=f"delete_gallery_{photo['id']}",
                    use_container_width=True,
                ):
                    db.delete_gallery_photo(photo["id"])
                    st.rerun()


def show_story_tab():
    show_philosophy_editor()
    st.divider()
    show_gallery_form()
    st.divider()
    show_gallery_list()


# ---------------------------------------------------------------------------
# 商城訂單頁籤
# ---------------------------------------------------------------------------


def show_shop_orders_tab():
    try:
        orders = db.get_all_shop_orders()
    except Exception as e:
        st.error(f"讀取商城訂單失敗：{e}")
        return

    if not orders:
        st.info("目前還沒有任何商城訂單。")
        return

    df = pd.DataFrame(orders)
    column_map = {
        "create_date": "建立時間",
        "name": "姓名",
        "phone": "電話",
        "email": "Email",
        "total_amount": "總金額",
        "order_id": "訂單編號",
        "status": "狀態",
        "transaction_id": "LinePay交易編號",
    }
    ordered_cols = [c for c in column_map if c in df.columns]
    df_display = df[ordered_cols].rename(columns=column_map)
    df_display["狀態"] = df_display["狀態"].map(lambda s: STATUS_LABEL.get(s, s))

    col1, col2, col3 = st.columns(3)
    col1.metric("總訂單數", len(df_display))
    paid_count = (df_display["狀態"] == STATUS_LABEL["paid"]).sum()
    col2.metric("已付款", int(paid_count))
    total_paid = df_display.loc[df_display["狀態"] == STATUS_LABEL["paid"], "總金額"].sum()
    col3.metric("已收金額", f"{int(total_paid)} 元")

    st.dataframe(df_display, use_container_width=True, hide_index=True)

    st.divider()
    st.caption("展開查看訂單明細")
    for o in orders:
        status_label = STATUS_LABEL.get(o["status"], o["status"])
        with st.expander(
            f"{o['order_id']}｜{o['name']}｜{o['total_amount']} 元｜{status_label}"
        ):
            for item in o.get("items", []):
                line = f"- {item['name']} x{item['qty']}"
                if item.get("promo_name"):
                    line += f"　🎉 {item['promo_name']}"
                line += f"　小計 {item.get('line_total', item.get('price', 0) * item.get('qty', 0))} 元"
                st.write(line)

    csv = df_display.to_csv(index=False).encode("utf-8-sig")
    st.download_button(
        "⬇️ 匯出商城訂單 CSV",
        data=csv,
        file_name="商城訂單.csv",
        mime="text/csv",
    )


# ---------------------------------------------------------------------------
# 主流程
# ---------------------------------------------------------------------------


def show_dashboard():
    st.title(f"🐝 {BRAND_NAME}後台")

    tab_registrations, tab_events, tab_shop_orders, tab_products, tab_promotions, tab_story = st.tabs(
        ["活動報名名單", "活動管理", "商城訂單", "商品管理", "促銷管理", "品牌故事"]
    )
    with tab_registrations:
        show_registrations_tab()
    with tab_events:
        show_events_tab()
    with tab_shop_orders:
        show_shop_orders_tab()
    with tab_products:
        show_products_tab()
    with tab_promotions:
        show_promotions_tab()
    with tab_story:
        show_story_tab()

    st.divider()
    if st.button("登出"):
        st.session_state["admin_authed"] = False
        st.rerun()


def main():
    if check_password():
        show_dashboard()


if __name__ == "__main__":
    main()
