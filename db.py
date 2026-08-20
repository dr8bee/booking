"""
Supabase 讀寫封裝。
改用 requests 直接呼叫 Supabase 的 PostgREST API，不透過 supabase-py 套件，
避免該套件在部分雲端環境下處理中文字時發生編碼問題。
資料表結構請見 supabase_schema.sql。
"""
import datetime

import requests
import streamlit as st

TABLE_NAME = "registrations"


def _headers() -> dict:
    key = st.secrets["supabase"]["service_role_key"]
    return {
        "apikey": key,
        "Authorization": f"Bearer {key}",
        "Content-Type": "application/json; charset=utf-8",
        "Prefer": "return=representation",
    }


def _table_url() -> str:
    base = st.secrets["supabase"]["url"].rstrip("/")
    return f"{base}/rest/v1/{TABLE_NAME}"


def append_registration(
    name: str,
    phone: str,
    email: str,
    note: str,
    amount: int,
    order_id: str,
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
    }
    body = _json_dumps(payload)
    resp = requests.post(
        _table_url(), headers=_headers(), data=body, timeout=20
    )
    if resp.status_code >= 300:
        raise RuntimeError(f"Supabase 寫入失敗（{resp.status_code}）：{resp.text}")


def update_status(order_id: str, status: str, transaction_id: str = "") -> bool:
    """依訂單編號更新狀態（paid / cancelled / confirm_failed）。"""
    payload = {"status": status}
    if transaction_id:
        payload["transaction_id"] = transaction_id

    body = _json_dumps(payload)
    resp = requests.patch(
        _table_url(),
        headers=_headers(),
        params={"order_id": f"eq.{order_id}"},
        data=body,
        timeout=20,
    )
    if resp.status_code >= 300:
        raise RuntimeError(f"Supabase 更新失敗（{resp.status_code}）：{resp.text}")
    return len(resp.json()) > 0


def get_registration_amount(order_id: str) -> int | None:
    """依訂單編號取回金額，付款確認時用來核對金額。"""
    resp = requests.get(
        _table_url(),
        headers=_headers(),
        params={"order_id": f"eq.{order_id}", "select": "amount"},
        timeout=20,
    )
    if resp.status_code >= 300:
        raise RuntimeError(f"Supabase 查詢失敗（{resp.status_code}）：{resp.text}")
    data = resp.json()
    if not data:
        return None
    return data[0]["amount"]


def get_all_registrations() -> list[dict]:
    """取得所有報名紀錄，依建立時間新到舊排序，給後台頁面使用。"""
    resp = requests.get(
        _table_url(),
        headers=_headers(),
        params={"select": "*", "order": "create_date.desc"},
        timeout=20,
    )
    if resp.status_code >= 300:
        raise RuntimeError(f"Supabase 查詢失敗（{resp.status_code}）：{resp.text}")
    return resp.json()


def _json_dumps(payload: dict) -> bytes:
    """明確用 UTF-8 編碼成 bytes 再送出，避免任何隱含編碼猜測造成問題。"""
    import json

    return json.dumps(payload, ensure_ascii=False).encode("utf-8")
