"""
品牌故事／活動花絮頁面（給顧客看）。
放在 pages/ 資料夾下，網址為 /story。
內容（理念文案、花絮照片）都由店家在 /admin 的「品牌故事」頁籤管理。
"""
import streamlit as st

import db
from style import inject_theme, hero, BRAND_NAME

st.set_page_config(page_title=f"品牌故事｜{BRAND_NAME}", page_icon="🐝", layout="wide")
inject_theme()


def show_philosophy():
    try:
        content = db.get_site_content()
    except Exception as e:
        st.error(f"讀取內容失敗：{e}")
        content = {}

    title = content.get("philosophy_title") or f"關於 {BRAND_NAME}"
    body = content.get("philosophy_body") or ""

    hero(title)

    if body:
        st.markdown(
            f'<div style="max-width:720px;margin:0 auto 1.6rem;text-align:center;'
            f'line-height:1.95;font-size:1.05rem;color:#4a3826;">{body}</div>',
            unsafe_allow_html=True,
        )

    stats = [
        (content.get("stat1_number"), content.get("stat1_label")),
        (content.get("stat2_number"), content.get("stat2_label")),
        (content.get("stat3_number"), content.get("stat3_label")),
    ]
    stats = [(n, l) for n, l in stats if n and l]
    if stats:
        cols = st.columns(len(stats))
        for col, (number, label) in zip(cols, stats):
            with col:
                st.markdown(
                    f'<div style="text-align:center;">'
                    f'<div style="font-family:\'Fraunces\',serif;font-size:2.3rem;'
                    f'color:var(--honey-gold-dark,#C9822A);font-weight:700;">{number}</div>'
                    f'<div style="color:#6b5642;font-size:0.9rem;">{label}</div>'
                    f"</div>",
                    unsafe_allow_html=True,
                )


def show_gallery():
    st.markdown(
        '<div class="brand-eyebrow" style="margin-top:2.6rem;">🎉 熱鬧花絮</div>'
        '<div class="brand-hero-title" style="font-size:1.8rem;">過去辦過的活動</div>',
        unsafe_allow_html=True,
    )

    try:
        photos = db.get_active_gallery_photos()
    except Exception as e:
        st.error(f"讀取花絮照片失敗：{e}")
        return

    if not photos:
        st.info("蜂農正在整理活動花絮照片，敬請期待。")
        return

    rotate_classes = ["gallery-rotate-a", "gallery-rotate-b", "gallery-rotate-c"]
    cards_html = []
    for idx, photo in enumerate(photos):
        rotate = rotate_classes[idx % len(rotate_classes)]
        caption_html = (
            f'<div class="gallery-caption">{photo["caption"]}</div>'
            if photo.get("caption")
            else ""
        )
        cards_html.append(
            f'<div class="gallery-photo-card {rotate}">'
            f'<img src="{photo["image_url"]}" />'
            f"{caption_html}"
            f"</div>"
        )

    st.markdown(
        f'<div class="gallery-grid">{"".join(cards_html)}</div>',
        unsafe_allow_html=True,
    )


def main():
    show_philosophy()
    hex_spans = "<span></span>" * 7
    st.markdown(
        f'<div class="honeycomb-divider">{hex_spans}</div>', unsafe_allow_html=True
    )
    show_gallery()


if __name__ == "__main__":
    main()
