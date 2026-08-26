"""
共用視覺主題：蜂場品牌風格。
每個頁面（app.py / pages/shop.py / pages/admin.py）在最上方呼叫 inject_theme()
即可套用一致的字體、配色與元件樣式。

如果之後要換品牌名稱／標語，只要改這裡的 BRAND_NAME / BRAND_TAGLINE 即可，
所有頁面都會自動同步。
"""
import streamlit as st

BRAND_NAME = "8博士農場"
BRAND_TAGLINE = "自家蜂場．小批現採．蜂農直送"


def inject_theme():
    st.markdown(
        """
        <style>
        @import url('https://fonts.googleapis.com/css2?family=Fraunces:opsz,wght@9..144,400;9..144,500;9..144,600;9..144,700&family=Noto+Sans+TC:wght@400;500;700&display=swap');

        :root {
            --honey-gold: #E8A33D;
            --honey-gold-dark: #C9822A;
            --hive-brown: #3D2817;
            --wax-cream: #FBF3E3;
            --meadow-sage: #7C8B5E;
            --comb-charcoal: #2A1D12;
        }

        html, body, [class*="css"] {
            font-family: 'Noto Sans TC', sans-serif;
        }

        .stApp {
            background-color: var(--wax-cream);
            background-image: radial-gradient(circle at 1px 1px, rgba(61,40,23,0.05) 1px, transparent 0);
            background-size: 22px 22px;
        }

        h1, h2, h3 {
            font-family: 'Fraunces', 'Noto Sans TC', serif !important;
            color: var(--hive-brown) !important;
            letter-spacing: 0.01em;
        }

        p, span, label, div {
            color: var(--hive-brown);
        }

        /* 蜂巢六角形分隔線：這個系統的簽名元素 */
        .honeycomb-divider {
            display: flex;
            justify-content: center;
            gap: 6px;
            margin: 0.6rem 0 1.6rem;
            opacity: 0.55;
        }
        .honeycomb-divider span {
            width: 14px;
            height: 16px;
            background: var(--honey-gold);
            clip-path: polygon(25% 0%, 75% 0%, 100% 50%, 75% 100%, 25% 100%, 0% 50%);
        }

        .brand-eyebrow {
            text-align: center;
            font-size: 0.8rem;
            letter-spacing: 0.28em;
            color: var(--meadow-sage);
            font-weight: 700;
            margin-bottom: 0.2rem;
        }
        .brand-hero-title {
            text-align: center;
            font-size: 2.3rem;
            margin: 0.2rem 0 0.15rem;
            color: var(--hive-brown);
        }
        .brand-hero-subtitle {
            text-align: center;
            color: #6b5642;
            font-size: 0.98rem;
            margin-bottom: 0.4rem;
        }

        /* 按鈕：蜂蜜金底色 */
        .stButton > button,
        .stFormSubmitButton > button,
        .stLinkButton > a,
        .stDownloadButton > button {
            background-color: var(--honey-gold) !important;
            color: var(--comb-charcoal) !important;
            border: none !important;
            border-radius: 6px !important;
            font-weight: 700 !important;
            transition: transform 0.15s ease, box-shadow 0.15s ease;
        }
        .stButton > button:hover,
        .stFormSubmitButton > button:hover,
        .stLinkButton > a:hover,
        .stDownloadButton > button:hover {
            background-color: var(--honey-gold-dark) !important;
            transform: translateY(-1px);
            box-shadow: 0 4px 10px rgba(201,130,42,0.35);
        }

        /* 卡片容器（活動卡片／商品卡片／border容器） */
        div[data-testid="stVerticalBlockBorderWrapper"] {
            background: #FFFDF8 !important;
            border: 1px solid rgba(61,40,23,0.14) !important;
            border-radius: 10px !important;
        }

        /* 輸入框 */
        .stTextInput input, .stTextArea textarea, .stNumberInput input {
            border-radius: 6px !important;
            border-color: rgba(61,40,23,0.25) !important;
        }

        /* 購物車側邊欄：巢心炭深色 */
        section[data-testid="stSidebar"] {
            background-color: var(--comb-charcoal) !important;
        }
        section[data-testid="stSidebar"] * {
            color: var(--wax-cream) !important;
        }
        section[data-testid="stSidebar"] .stButton > button {
            background-color: var(--honey-gold) !important;
            color: var(--comb-charcoal) !important;
        }

        /* info/促銷提示框：草地綠 */
        div[data-testid="stAlertContentInfo"] {
            background-color: rgba(124,139,94,0.14) !important;
            border-left: 4px solid var(--meadow-sage) !important;
        }

        /* success 提示框：蜂蜜金 */
        div[data-testid="stAlertContentSuccess"] {
            background-color: rgba(232,163,61,0.16) !important;
            border-left: 4px solid var(--honey-gold-dark) !important;
        }

        /* 活動花絮照片牆：拍立得散落風格，比整齊網格更有熱鬧感 */
        .gallery-grid {
            display: flex;
            flex-wrap: wrap;
            justify-content: center;
            gap: 1.8rem 1.3rem;
            padding: 1rem 0 2.5rem;
        }
        .gallery-photo-card {
            background: #FFFDF8;
            padding: 10px 10px 16px;
            box-shadow: 0 6px 16px rgba(61,40,23,0.16);
            border-radius: 4px;
            width: 230px;
            transition: transform 0.2s ease, box-shadow 0.2s ease;
        }
        .gallery-photo-card:hover {
            transform: translateY(-4px) rotate(0deg) !important;
            box-shadow: 0 10px 24px rgba(61,40,23,0.24);
            z-index: 2;
        }
        .gallery-photo-card img {
            width: 100%;
            height: 200px;
            object-fit: cover;
            border-radius: 2px;
            display: block;
        }
        .gallery-caption {
            margin-top: 10px;
            font-family: 'Fraunces', 'Noto Sans TC', serif;
            font-size: 0.92rem;
            color: var(--hive-brown);
            text-align: center;
        }
        .gallery-rotate-a { transform: rotate(-2.5deg); }
        .gallery-rotate-b { transform: rotate(2deg); }
        .gallery-rotate-c { transform: rotate(-1deg); }
        </style>
        """,
        unsafe_allow_html=True,
    )


def hero(title: str, subtitle: str = ""):
    """統一風格的頁首：品牌眉標 + 標題 + 副標 + 蜂巢分隔線。"""
    hex_spans = "<span></span>" * 7
    st.markdown(
        f"""
        <div class="brand-eyebrow">🍯 {BRAND_NAME}</div>
        <div class="brand-hero-title">{title}</div>
        {f'<div class="brand-hero-subtitle">{subtitle}</div>' if subtitle else ''}
        <div class="honeycomb-divider">{hex_spans}</div>
        """,
        unsafe_allow_html=True,
    )
