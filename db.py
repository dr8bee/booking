"""
Supabase 讀寫封裝。
改用 requests 直接呼叫 Supabase 的 PostgREST API，不透過 supabase-py 套件，
避免該套件在部分雲端環境下處理中文字時發生編碼問題。
資料表結構請見 supabase_schema.sql。
"""
import datetime
import json
import uuid

import requests
import streamlit as st

REGISTRATIONS_TABLE = "registrations"
EVENTS_TABLE = "events"
PRODUCTS_TABLE = "products"
SHOP_ORDERS_TABLE = "shop_orders"
STORAGE_BUCKET = "product-images"


def _headers() -> dict:
    key = st.secrets["supabase"]["service_role_key"]
    return {
        "apikey": key,
        "Authorization": f"Bearer {key}",
        "Content-Type": "application/json; charset=utf-8",
        "Prefer": "return=representation",
    }


def _table_url(table_name: str) -> str:
    base = st.secrets["supabase"]["url"].rstrip("/")
    return f"{base}/rest/v1/{table_name}"


def _json_dumps(payload: dict) -> bytes:
    """明確用 UTF-8 編碼成 bytes 再送出，避免任何隱含編碼猜測造成問題。"""
    return json.dumps(payload, ensure_ascii=False).encode("utf-8")


def _raise_if_error(resp: requests.Response, action: str) -> None:
    if resp.status_code >= 300:
        raise RuntimeError(f"Supabase {action}失敗（{resp.status_code}）：{resp.text}")


# ---------------------------------------------------------------------------
# 報名紀錄 registrations
# ---------------------------------------------------------------------------


def append_registration(
    name: str,
    phone: str,
    email: str,
    note: str,
    amount: int,
    order_id: str,
    event_id: int | None = None,
    event_name: str = "",
    status: str = "registered",
) -> None:
    """
    新增一筆報名紀錄。
    目前版本尚未串接付款，狀態預設為 registered（已報名）。
    之後接上 LINE Pay 時，可以把預設值改回 pending，並在付款流程中呼叫
    update_status() 轉成 paid / cancelled / confirm_failed。
    """
    payload = {
        "create_date": datetime.datetime.now().isoformat(),
        "name": name,
        "phone": phone,
        "email": email,
        "note": note,
        "amount": amount,
        "order_id": order_id,
        "status": status,
        "transaction_id": "",
        "event_id": event_id,
        "event_name": event_name,
    }
    resp = requests.post(
        _table_url(REGISTRATIONS_TABLE),
        headers=_headers(),
        data=_json_dumps(payload),
        timeout=20,
    )
    _raise_if_error(resp, "寫入報名紀錄")


def update_status(order_id: str, status: str, transaction_id: str = "") -> bool:
    """依訂單編號更新狀態（paid / cancelled / confirm_failed）。"""
    payload = {"status": status}
    if transaction_id:
        payload["transaction_id"] = transaction_id

    resp = requests.patch(
        _table_url(REGISTRATIONS_TABLE),
        headers=_headers(),
        params={"order_id": f"eq.{order_id}"},
        data=_json_dumps(payload),
        timeout=20,
    )
    _raise_if_error(resp, "更新報名狀態")
    return len(resp.json()) > 0


def get_registration_amount(order_id: str) -> int | None:
    """依訂單編號取回金額，付款確認時用來核對金額。"""
    resp = requests.get(
        _table_url(REGISTRATIONS_TABLE),
        headers=_headers(),
        params={"order_id": f"eq.{order_id}", "select": "amount"},
        timeout=20,
    )
    _raise_if_error(resp, "查詢報名紀錄")
    data = resp.json()
    if not data:
        return None
    return data[0]["amount"]


def get_all_registrations() -> list[dict]:
    """取得所有報名紀錄，依建立時間新到舊排序，給後台頁面使用。"""
    resp = requests.get(
        _table_url(REGISTRATIONS_TABLE),
        headers=_headers(),
        params={"select": "*", "order": "create_date.desc"},
        timeout=20,
    )
    _raise_if_error(resp, "查詢報名名單")
    return resp.json()


def delete_registration(order_id: str) -> None:
    """依訂單編號刪除一筆報名紀錄，用於後台的刪除功能。"""
    resp = requests.delete(
        _table_url(REGISTRATIONS_TABLE),
        headers=_headers(),
        params={"order_id": f"eq.{order_id}"},
        timeout=20,
    )
    _raise_if_error(resp, "刪除報名紀錄")


# ---------------------------------------------------------------------------
# 活動 events
# ---------------------------------------------------------------------------


def create_event(
    name: str,
    location: str,
    event_time: str,
    description: str,
    amount: int,
    currency: str = "TWD",
) -> dict:
    """
    新增一個活動。
    event_time 請傳 ISO 格式字串（例如 datetime.isoformat()）。
    """
    payload = {
        "name": name,
        "location": location,
        "event_time": event_time,
        "description": description,
        "amount": amount,
        "currency": currency,
        "is_active": True,
    }
    resp = requests.post(
        _table_url(EVENTS_TABLE),
        headers=_headers(),
        data=_json_dumps(payload),
        timeout=20,
    )
    _raise_if_error(resp, "新增活動")
    data = resp.json()
    return data[0] if data else {}


def update_event(
    event_id: int,
    name: str,
    location: str,
    event_time: str,
    description: str,
    amount: int,
    currency: str = "TWD",
) -> None:
    """編輯既有活動的內容。"""
    payload = {
        "name": name,
        "location": location,
        "event_time": event_time,
        "description": description,
        "amount": amount,
        "currency": currency,
    }
    resp = requests.patch(
        _table_url(EVENTS_TABLE),
        headers=_headers(),
        params={"id": f"eq.{event_id}"},
        data=_json_dumps(payload),
        timeout=20,
    )
    _raise_if_error(resp, "更新活動")


def set_event_active(event_id: int, is_active: bool) -> None:
    """開放／關閉活動報名（軟刪除，保留歷史報名紀錄的關聯）。"""
    payload = {"is_active": is_active}
    resp = requests.patch(
        _table_url(EVENTS_TABLE),
        headers=_headers(),
        params={"id": f"eq.{event_id}"},
        data=_json_dumps(payload),
        timeout=20,
    )
    _raise_if_error(resp, "更新活動狀態")


def get_active_events() -> list[dict]:
    """取得目前開放報名的活動，依活動時間排序，給顧客報名表單使用。"""
    resp = requests.get(
        _table_url(EVENTS_TABLE),
        headers=_headers(),
        params={
            "select": "*",
            "is_active": "eq.true",
            "order": "event_time.asc.nullslast",
        },
        timeout=20,
    )
    _raise_if_error(resp, "查詢開放活動")
    return resp.json()


def get_all_events() -> list[dict]:
    """取得所有活動（不論開放或關閉），給後台管理頁面使用。"""
    resp = requests.get(
        _table_url(EVENTS_TABLE),
        headers=_headers(),
        params={"select": "*", "order": "create_date.desc"},
        timeout=20,
    )
    _raise_if_error(resp, "查詢活動列表")
    return resp.json()


# ---------------------------------------------------------------------------
# 商品圖片上傳 (Supabase Storage)
# ---------------------------------------------------------------------------


def upload_product_image(file_bytes: bytes, filename: str, content_type: str) -> str:
    """
    上傳商品圖片到 Supabase Storage 的 product-images bucket（需先在 Supabase
    建立這個 public bucket，見 supabase_schema.sql），回傳可公開瀏覽的圖片網址。
    """
    ext = filename.rsplit(".", 1)[-1].lower() if "." in filename else "jpg"
    path = f"{uuid.uuid4().hex}.{ext}"
    base = st.secrets["supabase"]["url"].rstrip("/")
    key = st.secrets["supabase"]["service_role_key"]
    upload_url = f"{base}/storage/v1/object/{STORAGE_BUCKET}/{path}"
    headers = {
        "apikey": key,
        "Authorization": f"Bearer {key}",
        "Content-Type": content_type or "application/octet-stream",
    }
    resp = requests.post(upload_url, headers=headers, data=file_bytes, timeout=30)
    if resp.status_code >= 300:
        raise RuntimeError(f"Supabase 圖片上傳失敗（{resp.status_code}）：{resp.text}")
    return f"{base}/storage/v1/object/public/{STORAGE_BUCKET}/{path}"


# ---------------------------------------------------------------------------
# 商品 products
# ---------------------------------------------------------------------------


def create_product(
    name: str,
    description: str,
    price: int,
    sale_price: int | None,
    promo_text: str,
    image_url: str,
) -> dict:
    payload = {
        "name": name,
        "description": description,
        "price": price,
        "sale_price": sale_price,
        "promo_text": promo_text,
        "image_url": image_url,
        "is_active": True,
    }
    resp = requests.post(
        _table_url(PRODUCTS_TABLE),
        headers=_headers(),
        data=_json_dumps(payload),
        timeout=20,
    )
    _raise_if_error(resp, "新增商品")
    data = resp.json()
    return data[0] if data else {}


def update_product(
    product_id: int,
    name: str,
    description: str,
    price: int,
    sale_price: int | None,
    promo_text: str,
    image_url: str | None = None,
) -> None:
    payload = {
        "name": name,
        "description": description,
        "price": price,
        "sale_price": sale_price,
        "promo_text": promo_text,
    }
    if image_url:
        payload["image_url"] = image_url
    resp = requests.patch(
        _table_url(PRODUCTS_TABLE),
        headers=_headers(),
        params={"id": f"eq.{product_id}"},
        data=_json_dumps(payload),
        timeout=20,
    )
    _raise_if_error(resp, "更新商品")


def set_product_active(product_id: int, is_active: bool) -> None:
    resp = requests.patch(
        _table_url(PRODUCTS_TABLE),
        headers=_headers(),
        params={"id": f"eq.{product_id}"},
        data=_json_dumps({"is_active": is_active}),
        timeout=20,
    )
    _raise_if_error(resp, "更新商品狀態")


def delete_product(product_id: int) -> None:
    resp = requests.delete(
        _table_url(PRODUCTS_TABLE),
        headers=_headers(),
        params={"id": f"eq.{product_id}"},
        timeout=20,
    )
    _raise_if_error(resp, "刪除商品")


def get_active_products() -> list[dict]:
    """取得目前上架中的商品，給顧客商城頁面使用。"""
    resp = requests.get(
        _table_url(PRODUCTS_TABLE),
        headers=_headers(),
        params={"select": "*", "is_active": "eq.true", "order": "create_date.desc"},
        timeout=20,
    )
    _raise_if_error(resp, "查詢商品")
    return resp.json()


def get_all_products() -> list[dict]:
    """取得所有商品（不論上架或下架），給後台管理頁面使用。"""
    resp = requests.get(
        _table_url(PRODUCTS_TABLE),
        headers=_headers(),
        params={"select": "*", "order": "create_date.desc"},
        timeout=20,
    )
    _raise_if_error(resp, "查詢商品列表")
    return resp.json()


# ---------------------------------------------------------------------------
# 商城訂單 shop_orders
# ---------------------------------------------------------------------------


def create_shop_order(
    order_id: str,
    name: str,
    phone: str,
    email: str,
    items: list[dict],
    total_amount: int,
    status: str = "pending",
) -> None:
    payload = {
        "create_date": datetime.datetime.now().isoformat(),
        "order_id": order_id,
        "name": name,
        "phone": phone,
        "email": email,
        "items": items,
        "total_amount": total_amount,
        "status": status,
        "transaction_id": "",
    }
    resp = requests.post(
        _table_url(SHOP_ORDERS_TABLE),
        headers=_headers(),
        data=_json_dumps(payload),
        timeout=20,
    )
    _raise_if_error(resp, "建立商城訂單")


def update_shop_order_status(order_id: str, status: str, transaction_id: str = "") -> None:
    payload = {"status": status}
    if transaction_id:
        payload["transaction_id"] = transaction_id
    resp = requests.patch(
        _table_url(SHOP_ORDERS_TABLE),
        headers=_headers(),
        params={"order_id": f"eq.{order_id}"},
        data=_json_dumps(payload),
        timeout=20,
    )
    _raise_if_error(resp, "更新商城訂單狀態")


def get_shop_order(order_id: str) -> dict | None:
    resp = requests.get(
        _table_url(SHOP_ORDERS_TABLE),
        headers=_headers(),
        params={"order_id": f"eq.{order_id}", "select": "*"},
        timeout=20,
    )
    _raise_if_error(resp, "查詢商城訂單")
    data = resp.json()
    return data[0] if data else None


def get_all_shop_orders() -> list[dict]:
    """取得所有商城訂單，依建立時間新到舊排序，給後台頁面使用。"""
    resp = requests.get(
        _table_url(SHOP_ORDERS_TABLE),
        headers=_headers(),
        params={"select": "*", "order": "create_date.desc"},
        timeout=20,
    )
    _raise_if_error(resp, "查詢商城訂單列表")
    return resp.json()
