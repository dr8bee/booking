# 活動報名 + LINE Pay 收款系統

Streamlit + Supabase + LINE Pay 的輕量報名收款工具。無名額限制，純登記＋線上收款，
另外附一個密碼保護的後台頁面給店家看名單。

## 架構

```
顧客填表單 → 寫入 Supabase（狀態 pending）→ 導向 LINE Pay 付款
    → 付款完成後導回同一頁面 → 呼叫 LINE Pay confirm → 更新 Supabase 為 paid

店家開啟 /admin → 輸入密碼 → 看報名名單、篩選狀態、匯出 CSV
```

主程式是 `app.py`（顧客用的報名表單），`pages/admin.py` 是附屬的後台頁面，
Streamlit 偵測到 `pages/` 資料夾會自動把裡面的檔案變成側邊欄的子頁面，
不需要額外設定路由。部署時 Main file path 一律填 `app.py`。

## 檔案結構

```
booking_system/                    ← GitHub repo
├── app.py                         ← 主程式（報名表單 + LinePay 付款流程）
├── db.py                          ← Supabase 讀寫封裝
├── linepay.py                     ← LINE Pay API 封裝
├── requirements.txt               ← 套件清單（必須跟 app.py 同一層 root）
├── pages/
│   └── admin.py                   ← 後台名單頁面，自動變成 /admin
├── .gitignore                     ← 排除 secrets.toml 不上傳
├── supabase_schema.sql            ← 建表用 SQL（貼到 Supabase 執行，不影響部署）
└── README.md
```

`.streamlit/secrets.toml.example` 不需要上傳 GitHub，只是給你參考格式用；
真正的 secrets 要貼到 Streamlit Cloud 網站的 Secrets 設定裡。

## 事前準備

### 1. Supabase

1. 到 [supabase.com](https://supabase.com) 免費註冊，建立一個新專案（region 選
   Singapore 之類離台灣近的，速度較好）。
2. 進到專案的 **SQL Editor**，貼上 `supabase_schema.sql` 的內容並執行，會建立一張
   `registrations` 資料表。
3. 到專案的 **Settings → API**，記下兩個值：
   - **Project URL**（長得像 `https://xxxxxxxxxxxx.supabase.co`）
   - **service_role key**（在 "Project API keys" 底下，注意不是 anon/public key，
     這把 key 有完整讀寫權限，只能放在伺服器端 secrets，絕對不要放進前端程式碼）

> 免費方案：專案如果連續**兩週完全沒有 API 存取**會被自動暫停（pause），下次使用時
> 需要一點時間喚醒。如果報名有淡旺季、中間會停用很久，記得提醒店家第一次開啟可能
> 會稍微慢一點。

### 2. LINE Pay Online API

先用 `env = "sandbox"` 完整測過流程，確認沒問題再切成 `production`。
`confirmUrl` / `cancelUrl` 必須是正式部署後的網址，本機 `localhost` 無法讓 LINE Pay 導回。

### 3. 設定 secrets

複製 `.streamlit/secrets.toml.example` 為 `.streamlit/secrets.toml`（本機測試用），填入：

- `app.base_url`：Streamlit Cloud 部署後給你的網址
- `app.amount`：報名費金額
- `linepay.channel_id` / `linepay.channel_secret` / `linepay.env`
- `supabase.url` / `supabase.service_role_key`
- `admin.password`：給店家登入 `/admin` 用的密碼，自己取一組即可

`.streamlit/secrets.toml` 已被 `.gitignore` 排除，不會被推上 GitHub。

## 部署到 Streamlit Community Cloud

1. 把整個資料夾 push 到 GitHub repo，**確認 `requirements.txt` 跟 `app.py` 在同一層根目錄**，
   `admin.py` 必須放在 `pages/` 資料夾底下。
2. 到 [share.streamlit.io](https://share.streamlit.io) 選擇這個 repo，Main file path 填
   `app.py`，Deploy。
3. 部署完成後，到 App 右下角 **Settings → Secrets**，把 `.streamlit/secrets.toml`
   的內容整份貼進去存檔（Streamlit Cloud 會自動重啟套用）。
4. 把 `app.base_url` 改成 Streamlit Cloud 實際給你的網址後存檔重啟一次
   （這個網址要餵給 LINE Pay 當 `confirmUrl`/`cancelUrl`）。
5. 側邊欄選單會自動出現 "admin" 頁面，網址是 `https://你的app網址/admin`，
   把這個網址跟密碼給店家即可。

## 本機測試

```bash
pip install -r requirements.txt
streamlit run app.py
```

本機測試時 LINE Pay 無法導回 `localhost`，建議部署到 Streamlit Cloud 後用
sandbox 環境測試完整付款流程。Supabase 的讀寫本機就可以直接測。

## 資料表欄位（registrations）

| 欄位 | 說明 |
|---|---|
| created_at | 建立時間 |
| name / phone / email / note | 報名人資料 |
| amount | 金額 |
| order_id | 訂單編號（唯一） |
| status | pending / paid / cancelled / confirm_failed |
| transaction_id | LINE Pay 交易編號 |

## 之後可以擴充的方向

- 多場次/多方案不同金額 → 加下拉選單
- 名額上限 → 送出前先查 Supabase 算已報名人數，額滿擋掉
- 退款 → 用 `linepay.py` 加一支 `/v3/payments/{transactionId}/refund`
- 後台頁面加更多統計圖表（`pages/admin.py` 已有 pandas，可直接加 `st.bar_chart`）
