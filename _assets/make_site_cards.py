"""產生網站本身的預覽圖（1200×630）：首頁用 images/site-card.png，系列介紹頁用 images/series-card.png。

畫法沿用 _rdkit-play/make_cards.py 的吉祥物、思考泡泡與球棒模型（只匯入，不修改那支程式）。

用法（需要 rdkit、pillow，以及 macOS 內建的 PingFang 字型）：
    python _assets/make_site_cards.py
"""

import sys
from pathlib import Path

SITE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(SITE / "_rdkit-play"))

from PIL import Image, ImageDraw  # noqa: E402

import make_cards as mc  # noqa: E402

OUT = SITE / "images"


def layout(title_lines, sub, tag=None):
    im = Image.new("RGB", (mc.W, mc.H), "white")
    d = ImageDraw.Draw(im)
    if tag:
        f_tag = mc.font(24, mc.TC_SEMIBOLD)
        tw = d.textlength(tag, font=f_tag)
        d.rounded_rectangle((60, 52, 60 + tw + 32, 96), radius=22, fill=mc.ACCENT)
        d.text((76, 74), tag, font=f_tag, fill="white", anchor="lm")
    f = mc.font(72, mc.TC_SEMIBOLD)
    for i, line in enumerate(title_lines):
        d.text((60, 170 + i * 100), line, font=f, fill=mc.INK)
    y = 170 + len(title_lines) * 100 + 30
    for i, line in enumerate(sub):
        d.text((60, y + i * 48), line, font=mc.font(32), fill=mc.MUTED)
    return im, d


def site_card():
    im, d = layout(["電腦也會化學"], ["在網頁上動手玩，", "看電腦怎麼認識分子。"])
    mc.thought_bubble(d, (850, 40, 1170, 260), mc.HEAD)
    mc.ball_model(im, "CN1C=NC2=C1C(=O)N(C(=O)N2C)C", 1010, 150, 240)  # 咖啡因
    mc.mascot(im, mc.MX, mc.MY, "happy", "C", mc.S)
    return im


def series_card():
    im, d = layout(["用 RDKit", "玩化學"], ["電腦不只會選花生，", "還會化學。"], tag="系列介紹")
    mc.thought_bubble(d, (850, 40, 1170, 260), mc.HEAD)
    mc.ball_model(im, "O=C=O", 1015, 150, 250)
    mc.mascot(im, mc.MX, mc.MY, "proud", "C", mc.S)
    return im


if __name__ == "__main__":
    OUT.mkdir(exist_ok=True)
    for name, make in (("site-card.png", site_card), ("series-card.png", series_card)):
        make().save(OUT / name)
        print("saved", OUT / name)
