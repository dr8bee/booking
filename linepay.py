"""
LINE Pay Online API v3 封裝
文件參考：https://developers-pay.line.me/online/
"""
import base64
import hashlib
import hmac
import json
import uuid

import requests

SANDBOX_BASE_URL = "https://sandbox-api-pay.line.me"
PRODUCTION_BASE_URL = "https://api-pay.line.me"


class LinePayError(Exception):
    """LINE Pay API 回傳非成功狀態時拋出"""

    def __init__(self, return_code: str, return_message: str, raw: dict):
        self.return_code = return_code
        self.return_message = return_message
        self.raw = raw
        super().__init__(f"[LinePay {return_code}] {return_message}")


class LinePayClient:
    def __init__(self, channel_id: str, channel_secret: str, env: str = "sandbox"):
        """
        env: "sandbox" 或 "production"
        """
        self.channel_id = channel_id
        self.channel_secret = channel_secret
        self.base_url = (
            SANDBOX_BASE_URL if env == "sandbox" else PRODUCTION_BASE_URL
        )

    def _signature(self, uri_path: str, body_str: str, nonce: str) -> str:
        """
        LINE Pay 簽章規則：
        Base64( HMAC-SHA256( channelSecret, channelSecret + uriPath + body + nonce ) )
        """
        message = f"{self.channel_secret}{uri_path}{body_str}{nonce}"
        digest = hmac.new(
            self.channel_secret.encode("utf-8"),
            message.encode("utf-8"),
            hashlib.sha256,
        ).digest()
        return base64.b64encode(digest).decode("utf-8")

    def _post(self, uri_path: str, payload: dict) -> dict:
        body_str = json.dumps(payload, ensure_ascii=False, separators=(",", ":"))
        nonce = str(uuid.uuid4())
        signature = self._signature(uri_path, body_str, nonce)

        headers = {
            "Content-Type": "application/json",
            "X-LINE-ChannelId": self.channel_id,
            "X-LINE-Authorization-Nonce": nonce,
            "X-LINE-Authorization": signature,
        }

        resp = requests.post(
            self.base_url + uri_path,
            headers=headers,
            data=body_str.encode("utf-8"),
            timeout=20,
        )
        resp.raise_for_status()
        data = resp.json()

        return_code = data.get("returnCode")
        if return_code != "0000":
            raise LinePayError(
                return_code, data.get("returnMessage", "unknown error"), data
            )
        return data

    def request_payment(
        self,
        order_id: str,
        amount: int,
        product_name: str,
        confirm_url: str,
        cancel_url: str,
        currency: str = "TWD",
    ) -> dict:
        """
        呼叫 POST /v3/payments/request
        回傳 info 內含 paymentUrl.web（導引顧客付款用）與 transactionId
        """
        uri_path = "/v3/payments/request"
        payload = {
            "amount": amount,
            "currency": currency,
            "orderId": order_id,
            "packages": [
                {
                    "id": "package-1",
                    "amount": amount,
                    "products": [
                        {
                            "name": product_name,
                            "quantity": 1,
                            "price": amount,
                        }
                    ],
                }
            ],
            "redirectUrls": {
                "confirmUrl": confirm_url,
                "cancelUrl": cancel_url,
            },
        }
        data = self._post(uri_path, payload)
        return data["info"]

    def confirm_payment(
        self, transaction_id: str, amount: int, currency: str = "TWD"
    ) -> dict:
        """
        呼叫 POST /v3/payments/{transactionId}/confirm
        顧客從 LINE Pay 導回 confirmUrl 後，用這支 API 完成收單
        """
        uri_path = f"/v3/payments/{transaction_id}/confirm"
        payload = {"amount": amount, "currency": currency}
        data = self._post(uri_path, payload)
        return data["info"]
