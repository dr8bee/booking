"""
Supabase 讀寫封裝。
資料表結構請見 supabase_schema.sql。
"""
import datetime
import locale

# 部分雲端環境預設語系編碼較保守，遇到中文字容易觸發編碼錯誤，
# 這裡強制指定 UTF-8，降低底層套件處理中文時出錯的機會。
try:
    locale.setlocale(locale.LC_ALL, "C.UTF-8")
except locale.Error:
    pass

import streamlit as st
from supabase import create_client, Client

TABLE_NAME = "registrations"


@st.cache_resource(show_spinner=False)
def _get_client() -> Client:
    """建立一次 Supabase client 並快取。"""
    url = st.secrets["supabase"]["url"]
    # 這裡用 service_role key，因為所有存取都是從 Streamlit 伺服器端發出，
    # 不會暴露給瀏覽器，所以可以繞過 RLS 直接讀寫。
    # 千萬不要把 service_role key 用在前端 / 瀏覽器程式碼裡。
    key = st.secrets["supabase"]["service_role_key"]
    return create_client(url, key)


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
    client = _get_client()
    client.table(TABLE_NAME).insert(
        {
            "created_at": datetime.datetime.now().isoformat(),
            "name": name,
            "phone": phone,
            "email": email,
            "note": note,
            "amount": amount,
            "order_id": order_id,
            "status": status,
            "transaction_id": "",
        }
    ).execute()


def update_status(order_id: str, status: str, transaction_id: str = "") -> bool:
    """依訂單編號更新狀態（paid / cancelled / confirm_failed）。"""
    client = _get_client()
    payload = {"status": status}
    if transaction_id:
        payload["transaction_id"] = transaction_id

    result = (
        client.table(TABLE_NAME)
        .update(payload)
        .eq("order_id", order_id)
        .execute()
    )
    return len(result.data) > 0


def get_registration_amount(order_id: str) -> int | None:
    """依訂單編號取回金額，付款確認時用來核對金額。"""
    client = _get_client()
    result = (
        client.table(TABLE_NAME)
        .select("amount")
        .eq("order_id", order_id)
        .limit(1)
        .execute()
    )
    if not result.data:
        return None
    return result.data[0]["amount"]


def get_all_registrations() -> list[dict]:
    """取得所有報名紀錄，依建立時間新到舊排序，給後台頁面使用。"""
    client = _get_client()
    result = (
        client.table(TABLE_NAME)
        .select("*")
        .order("created_at", desc=True)
        .execute()
    )
    return result.data
