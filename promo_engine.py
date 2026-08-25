"""
促銷規則計算引擎。
規則資料存在 Supabase 的 promotions 資料表，商品與規則的對應存在
product_promotions 資料表（見 supabase_schema.sql）。

這個檔案只負責「給定商品原價、購買數量、適用的規則列表，算出最優惠的
價格與套用哪條規則」，不直接碰資料庫，方便商品卡片、購物車、結帳頁面
共用同一套計算邏輯，不會算出兜不起來的價錢。
"""

RULE_TYPES = {
    "percent_off": "折扣（打幾折）",
    "amount_off": "折抵金額",
    "buy_x_get_y": "買X送Y",
    "bundle_price": "N件優惠價",
}


def display_text_for(rule_type: str, params: dict, custom_text: str = "") -> str:
    """
    店家在後台如果有填自訂顯示文字就優先使用，
    否則依規則類型與參數自動產生一段簡短說明文字。
    """
    if custom_text:
        return custom_text

    params = params or {}

    if rule_type == "percent_off":
        percent = params.get("percent", 0)
        keep = 100 - percent
        min_qty = params.get("min_qty", 1)
        prefix = f"滿{min_qty}件" if min_qty > 1 else ""
        if keep % 10 == 0:
            return f"{prefix}{keep // 10}折"
        return f"{prefix}{keep / 10:.1f}折"

    if rule_type == "amount_off":
        amount = params.get("amount", 0)
        min_qty = params.get("min_qty", 1)
        prefix = f"滿{min_qty}件" if min_qty > 1 else "每筆"
        return f"{prefix}折抵 {amount} 元"

    if rule_type == "buy_x_get_y":
        buy_qty = params.get("buy_qty", 1)
        get_qty = params.get("get_qty", 0)
        return f"買{buy_qty}送{get_qty}"

    if rule_type == "bundle_price":
        bundle_qty = params.get("bundle_qty", 1)
        bundle_price = params.get("bundle_price", 0)
        return f"{bundle_qty}件只要 {bundle_price} 元"

    return ""


def _apply_rule(unit_price: int, qty: int, rule_type: str, params: dict) -> float:
    params = params or {}

    if rule_type == "percent_off":
        percent = params.get("percent", 0)
        min_qty = params.get("min_qty", 1)
        if qty < min_qty:
            return unit_price * qty
        return unit_price * qty * (1 - percent / 100)

    if rule_type == "amount_off":
        amount = params.get("amount", 0)
        min_qty = params.get("min_qty", 1)
        if qty < min_qty:
            return unit_price * qty
        return max(0, unit_price * qty - amount)

    if rule_type == "buy_x_get_y":
        buy_qty = max(1, params.get("buy_qty", 1))
        get_qty = max(0, params.get("get_qty", 0))
        group = buy_qty + get_qty
        full_groups, remainder = divmod(qty, group)
        payable_units = full_groups * buy_qty + min(remainder, buy_qty)
        return unit_price * payable_units

    if rule_type == "bundle_price":
        bundle_qty = max(1, params.get("bundle_qty", 1))
        bundle_price = params.get("bundle_price", 0)
        full_bundles, remainder = divmod(qty, bundle_qty)
        return full_bundles * bundle_price + remainder * unit_price

    return unit_price * qty


def calc_line_price(unit_price: int, qty: int, promotions: list[dict]) -> tuple[int, dict | None]:
    """
    給定單價、購買數量、適用的促銷規則列表，
    回傳 (最優惠的小計金額, 套用的規則字典或 None)。
    如果沒有任何規則比原價更划算（例如數量不到門檻），回傳原價與 None。
    多條規則都適用時，自動挑選對顧客最划算的那一條，不會疊加計算。
    """
    original_total = unit_price * qty
    best_total = original_total
    best_promo = None

    for promo in promotions:
        total = _apply_rule(unit_price, qty, promo["rule_type"], promo.get("params") or {})
        if total < best_total:
            best_total = total
            best_promo = promo

    return round(best_total), best_promo
