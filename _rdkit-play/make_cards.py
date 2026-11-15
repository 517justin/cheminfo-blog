"""產生《用 RDKit 玩化學》各集的預覽圖（images/card.png，1200×630）。

版型：吉祥物「小電腦」。左邊是系列標記與標題，右邊是小電腦和這一集的畫面
（思考泡泡裡的球棒模型、漂浮的放大鏡或鉛筆）。畫面不放 SMILES 字串與結構式。
球棒模型的座標由 RDKit 計算，再畫成彩色圓球。

用法（需要 rdkit、pillow，以及 macOS 內建的 PingFang 字型）：
    python make_cards.py            # 全部
    python make_cards.py 01 02      # 指定集數
"""

import math
import sys
from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter, ImageFont
from rdkit import Chem
from rdkit.Chem import rdDepictor

POSTS = Path(__file__).resolve().parent.parent / "posts"
W, H = 1200, 630
PINGFANG = "/System/Library/AssetsV2/com_apple_MobileAsset_Font8/86ba2c91f017a3749571a82f2c6d890ac7ffb2fb.asset/AssetData/PingFang.ttc"
TC_REGULAR, TC_SEMIBOLD = 2, 10  # PingFang.ttc 裡 PingFang TC 的字重索引

ACCENT = (11, 114, 133)      # 系列主色
INK = (33, 37, 41)
MUTED = (134, 142, 150)
BUBBLE = (241, 243, 245)
SCREEN = (233, 250, 252)
STICK = (173, 181, 189)
ATOM_COLOR = {"C": (73, 80, 87), "O": (240, 62, 62), "N": (51, 154, 240), "H": (248, 249, 250), "Cl": (64, 192, 87), "Na": (151, 117, 250), "Ca": (130, 201, 30)}
ATOM_SIZE = {"H": 0.26, "C": 0.40, "N": 0.40, "O": 0.42, "Na": 0.5, "Cl": 0.5}


def font(size, weight=TC_REGULAR):
    return ImageFont.truetype(PINGFANG, size, index=weight)


# ---------- 版面 ----------

def base(ep, title):
    im = Image.new("RGB", (W, H), "white")
    d = ImageDraw.Draw(im)
    f_tag = font(24, TC_SEMIBOLD)
    tag = "用 RDKit 玩化學"
    tw = d.textlength(tag, font=f_tag)
    d.rounded_rectangle((60, 52, 60 + tw + 32, 96), radius=22, fill=ACCENT)
    d.text((76, 74), tag, font=f_tag, fill="white", anchor="lm")
    d.text((60 + tw + 50, 74), f"#{ep}", font=font(30, TC_SEMIBOLD), fill=ACCENT, anchor="lm")
    # 標題：用 \n 手動斷行，字級自動縮到每行都放得進 560 px
    parts = title.split("\n")
    for size in (64, 60, 56, 52, 48):
        f = font(size, TC_SEMIBOLD)
        if all(d.textlength(p, font=f) <= 560 for p in parts):
            break
    for i, p in enumerate(parts):
        d.text((60, 175 + i * int(size * 1.45)), p, font=f, fill=INK)
    d.text((60, H - 60), "電腦也會化學", font=font(24), fill=MUTED, anchor="lm")
    return im, d


# ---------- 吉祥物 ----------
# 造型：六角形螢幕（苯環，含淡內圈）、天線是單鍵頂端接原子（依每集主角更換；
# 苯環上的碳只能再接一個單鍵，所以一律用單鍵）、
# 尾巴是鋸齒碳鏈的電源線、尾端接氧原子球，尾巴姿勢配合表情。

O_RED = ATOM_COLOR["O"]


def hexagon(cx, cy, r, rot=90):
    """尖角朝上的正六邊形頂點（rot=90 時頂點在正上方）。"""
    return [(cx + r * math.cos(math.radians(rot + 60 * k)), cy - r * math.sin(math.radians(rot + 60 * k))) for k in range(6)]


# 尾巴（電源線）：沿著貝茲曲線排成鋸齒狀的碳鏈，形狀隨表情改變
TAIL_SHAPES = {  # 三個控制點，單位是像素（再乘縮放比例 s），相對於尾巴起點
    "happy": ((110, 10), (190, -40), (170, -150)),
    "curious": ((170, 10), (210, -170), (110, -170)),
    "surprised": ((60, 0), (70, -80), (70, -210)),
    "focused": ((70, 0), (140, 0), (200, 0)),
    "error": ((80, 10), (130, 60), (140, 95)),
    "computing": ((170, 60), (190, -150), (70, -90)),
    "proud": ((80, 0), (220, -30), (170, -190)),
}


def bezier(p0, p1, p2, p3, n=400):
    out = []
    for i in range(n + 1):
        t = i / n
        a, b, c, e = (1 - t) ** 3, 3 * (1 - t) ** 2 * t, 3 * (1 - t) * t ** 2, t ** 3
        out.append((a * p0[0] + b * p1[0] + c * p2[0] + e * p3[0], a * p0[1] + b * p1[1] + c * p2[1] + e * p3[1]))
    return out


def tail(d, sx, sy, face, s):
    c1, c2, end = TAIL_SHAPES.get(face, TAIL_SHAPES["happy"])
    curve = bezier((sx, sy), (sx + c1[0] * s, sy + c1[1] * s), (sx + c2[0] * s, sy + c2[1] * s),
                   (sx + end[0] * s, sy + end[1] * s))
    # 依弧長等距取點，左右交替偏移，做成整齊的鋸齒
    step, amp = 30 * s, 11 * s
    cum = [0.0]
    for (x0, y0), (x1, y1) in zip(curve, curve[1:]):
        cum.append(cum[-1] + math.hypot(x1 - x0, y1 - y0))
    total = cum[-1]
    nseg = max(2, round(total / step))
    pts, j = [curve[0]], 0
    for k in range(1, nseg):
        target = total * k / nseg
        while cum[j + 1] < target:
            j += 1
        (x0, y0), (x1, y1) = curve[j], curve[j + 1]
        t = (target - cum[j]) / ((cum[j + 1] - cum[j]) or 1)
        x, y = x0 + (x1 - x0) * t, y0 + (y1 - y0) * t
        n = math.hypot(x1 - x0, y1 - y0) or 1
        nx, ny = -(y1 - y0) / n, (x1 - x0) / n
        sign = 1 if k % 2 else -1
        pts.append((x + nx * amp * sign, y + ny * amp * sign))
    d.line(pts, fill=INK, width=int(6 * s), joint="curve")
    # 最後一段鍵接到氧原子球，沿著曲線末端的方向
    (xa, ya), (xb, yb) = curve[-6], curve[-1]
    n = math.hypot(xb - xa, yb - ya) or 1
    ux, uy = (xb - xa) / n, (yb - ya) / n
    ex, ey = pts[-1]
    end_pt = (ex + ux * 30 * s, ey + uy * 30 * s)
    d.line((ex, ey, end_pt[0], end_pt[1]), fill=STICK, width=int(6 * s))
    return (end_pt[0] + ux * 8 * s, end_pt[1] + uy * 8 * s)



def mascot(im, cx, cy, face="happy", atom="O", s=1.0, ion=None):
    """以螢幕中心 (cx, cy) 畫出吉祥物；atom 是天線原子的顏色，s 是縮放比例。

    ion 給 "+" 或 "−" 時，天線原子是離子：鍵畫成虛線（沒有共用電子的化學鍵），原子旁標上電荷。
    """
    # atom 是天線原子的元素符號；天線一律是單鍵（苯環上的碳只能再接一個單鍵）
    atom_color = ATOM_COLOR.get(atom, (174, 62, 201))
    d = ImageDraw.Draw(im)
    R = 120 * s
    top = (cx, cy - R)
    # 天線：一根化學鍵，頂端一顆原子
    ax, ay = cx, cy - R - 70 * s
    if ion:
        n = 5  # 虛線段數
        for k in range(n):
            y0 = top[1] - (ay - top[1]) * -k / n
            y1 = top[1] - (ay - top[1]) * -(k + 0.55) / n
            d.line((top[0], y0, ax, y1), fill=STICK, width=int(9 * s))
    else:
        d.line((top[0], top[1], ax, ay), fill=STICK, width=int(9 * s))
    # 底座與電源線（鋸齒碳鏈，尾端 OH）
    base_y = cy + R + 10 * s
    d.rectangle((cx - 18 * s, cy + R - 20 * s, cx + 18 * s, base_y + 18 * s), fill=ACCENT)
    d.rounded_rectangle((cx - 75 * s, base_y + 18 * s, cx + 75 * s, base_y + 38 * s), radius=int(8 * s), fill=ACCENT)
    sx, sy = cx + 75 * s, base_y + 28 * s
    cord_end = tail(d, sx, sy, face, s)
    # 六角形螢幕
    d.polygon(hexagon(cx, cy, R), fill=ACCENT)
    d.polygon(hexagon(cx, cy, R * 0.8), fill=SCREEN)
    # 淡淡的苯環內圈
    ri = R * 0.6
    d.ellipse((cx - ri, cy - ri, cx + ri, cy + ri), outline=(165, 216, 224), width=int(5 * s))
    ball(im, ax, ay, int(26 * s), atom_color)
    ball(im, cord_end[0], cord_end[1], int(14 * s), O_RED)
    d = ImageDraw.Draw(im)
    if ion:
        bx, by, br = ax + 26 * s, ay - 22 * s, 15 * s
        d.ellipse((bx - br, by - br, bx + br, by + br), fill="white", outline=INK, width=max(2, int(3 * s)))
        d.text((bx, by), ion, font=font(int(26 * s), TC_SEMIBOLD), fill=INK, anchor="mm")
    # 表情
    ex1, ex2, eyy = cx - 36 * s, cx + 36 * s, cy - 14 * s

    def shine(e, y):  # 眼睛的白色小反光
        d.ellipse((e - 7 * s, y - 8 * s, e - 1 * s, y - 2 * s), fill="white")
    if face == "surprised":
        for e in (ex1, ex2):
            d.ellipse((e - 14 * s, eyy - 16 * s, e + 14 * s, eyy + 16 * s), fill="white", outline=INK, width=int(5 * s))
            d.ellipse((e - 7 * s, eyy - 7 * s, e + 7 * s, eyy + 7 * s), fill=INK)
            d.ellipse((e - 4 * s, eyy - 5 * s, e - 1 * s, eyy - 2 * s), fill="white")
        d.ellipse((cx - 11 * s, cy + 22 * s, cx + 11 * s, cy + 46 * s), outline=INK, width=int(5 * s))
    elif face == "curious":
        for e in (ex1, ex2):
            d.ellipse((e - 12 * s, eyy - 12 * s, e + 12 * s, eyy + 12 * s), fill=INK)
            shine(e, eyy)
        d.line((ex2 - 16 * s, eyy - 28 * s, ex2 + 14 * s, eyy - 36 * s), fill=INK, width=int(5 * s))
        d.line((cx - 20 * s, cy + 36 * s, cx + 20 * s, cy + 30 * s), fill=INK, width=int(6 * s))
        d.text((cx + R * 0.95, cy - R * 0.7), "?", font=font(int(64 * s), TC_SEMIBOLD), fill=ACCENT, anchor="mm")
    elif face == "focused":
        for e in (ex1, ex2):
            d.line((e - 14 * s, eyy, e + 14 * s, eyy), fill=INK, width=int(7 * s))
        d.arc((cx - 18 * s, cy + 18 * s, cx + 18 * s, cy + 46 * s), 20, 160, fill=INK, width=int(6 * s))
    elif face == "error":
        for e in (ex1, ex2):
            k = 11 * s
            d.line((e - k, eyy - k, e + k, eyy + k), fill=INK, width=int(6 * s))
            d.line((e - k, eyy + k, e + k, eyy - k), fill=INK, width=int(6 * s))
        zig = [(cx - 28 * s + 14 * s * j, cy + 36 * s + (-7 * s if j % 2 else 7 * s)) for j in range(5)]
        d.line(zig, fill=INK, width=int(5 * s), joint="curve")
    elif face == "computing":
        for e in (ex1, ex2):
            d.ellipse((e - 10 * s, eyy - 18 * s, e + 10 * s, eyy + 2 * s), fill=INK)
            shine(e + 1 * s, eyy - 7 * s)
        bx0, bx1, by0, by1 = cx - 38 * s, cx + 38 * s, cy + 26 * s, cy + 42 * s
        d.rounded_rectangle((bx0, by0, bx1, by1), radius=int(8 * s), outline=INK, width=int(4 * s))
        d.rounded_rectangle((bx0 + 5 * s, by0 + 5 * s, bx0 + (bx1 - bx0) * 0.6, by1 - 5 * s), radius=int(4 * s), fill=ACCENT)
    elif face == "proud":
        for e in (ex1, ex2):
            d.arc((e - 14 * s, eyy - 8 * s, e + 14 * s, eyy + 18 * s), 200, 340, fill=INK, width=int(6 * s))
        d.chord((cx - 30 * s, cy + 2 * s, cx + 30 * s, cy + 50 * s), 0, 180, fill=INK)
        for (sx2, sy2, k) in ((cx + R * 0.95, cy - R * 0.75, 20 * s), (cx + R * 1.15, cy - R * 0.35, 12 * s)):
            d.polygon([(sx2, sy2 - k), (sx2 + k * 0.3, sy2 - k * 0.3), (sx2 + k, sy2), (sx2 + k * 0.3, sy2 + k * 0.3),
                       (sx2, sy2 + k), (sx2 - k * 0.3, sy2 + k * 0.3), (sx2 - k, sy2), (sx2 - k * 0.3, sy2 - k * 0.3)],
                      fill=(252, 196, 25))
    else:
        for e in (ex1, ex2):
            d.ellipse((e - 12 * s, eyy - 12 * s, e + 12 * s, eyy + 12 * s), fill=INK)
            shine(e, eyy)
        d.arc((cx - 30 * s, cy + 2 * s, cx + 30 * s, cy + 46 * s), 20, 160, fill=INK, width=int(6 * s))


def thought_bubble(d, box, toward):
    """思考泡泡：box 是大泡泡範圍，toward 是小泡泡最後指向的點（小電腦頭部）。"""
    d.rounded_rectangle(box, radius=60, fill=BUBBLE)
    bx, by = (box[0] + box[2]) / 2, box[3]
    tx, ty = toward
    for t, r in ((0.35, 16), (0.7, 10)):
        x, y = bx + (tx - bx) * t, by + (ty - by) * t
        d.ellipse((x - r, y - r, x + r, y + r), fill=BUBBLE)


# ---------- 球棒模型 ----------

def ball(im, cx, cy, r, color, hidden=False):
    """有立體感的圓球；hidden=True 時畫成虛線輪廓的「隱形球」。"""
    d = ImageDraw.Draw(im)
    if hidden:
        n = 16
        for k in range(0, n, 2):
            d.arc((cx - r, cy - r, cx + r, cy + r), 360 * k / n, 360 * (k + 1) / n, fill=MUTED, width=3)
        return
    layer = Image.new("RGBA", im.size, (0, 0, 0, 0))
    ImageDraw.Draw(layer).ellipse((cx - r, cy - r, cx + r, cy + r), fill=color + (255,))
    hl = Image.new("RGBA", im.size, (0, 0, 0, 0))
    ImageDraw.Draw(hl).ellipse((cx - r * 0.55, cy - r * 0.6, cx - r * 0.05, cy - r * 0.15), fill=(255, 255, 255, 140))
    hl = hl.filter(ImageFilter.GaussianBlur(max(1, r * 0.12)))
    mask = Image.new("L", im.size, 0)
    ImageDraw.Draw(mask).ellipse((cx - r, cy - r, cx + r, cy + r), fill=255)
    layer.paste(hl, (0, 0), Image.composite(hl, Image.new("RGBA", im.size), mask).split()[3])
    im.paste(layer, (0, 0), layer)
    if color == ATOM_COLOR["H"]:
        d.ellipse((cx - r, cy - r, cx + r, cy + r), outline=STICK, width=2)


def ball_model(im, smiles, cx, cy, size, add_hs=False, rotate=0.0, hide_h=False, hide_atoms=(), halo_atoms=(),
               kekulize=False, ring_circle=False):
    """把分子畫成球棒模型，置中在 (cx, cy)，最大寬度約 size。回傳各原子的像素座標。

    hide_atoms：畫成虛線「隱形球」的原子編號；halo_atoms：加上主色光暈的原子編號。
    kekulize：芳香環畫成單雙鍵交替；ring_circle：芳香環中間畫一個圓圈。
    """
    mol = Chem.MolFromSmiles(smiles)
    if kekulize:
        Chem.Kekulize(mol, clearAromaticFlags=True)
    if add_hs:
        mol = Chem.AddHs(mol)
    rdDepictor.Compute2DCoords(mol)
    conf = mol.GetConformer()
    pts = [(conf.GetAtomPosition(i).x, -conf.GetAtomPosition(i).y) for i in range(mol.GetNumAtoms())]
    mx = sum(p[0] for p in pts) / len(pts)
    my = sum(p[1] for p in pts) / len(pts)
    a = math.radians(rotate)
    pts = [((x - mx) * math.cos(a) - (y - my) * math.sin(a), (x - mx) * math.sin(a) + (y - my) * math.cos(a)) for x, y in pts]
    extent = max(max(abs(x), abs(y)) for x, y in pts) + 0.6
    s = size / 2 / extent  # 1 個 RDKit 長度單位（約一個鍵長）對應的像素
    xy = [(cx + x * s, cy + y * s) for x, y in pts]
    d = ImageDraw.Draw(im)
    for b in mol.GetBonds():
        (x1, y1), (x2, y2) = xy[b.GetBeginAtomIdx()], xy[b.GetEndAtomIdx()]
        ends = (b.GetBeginAtomIdx(), b.GetEndAtomIdx())
        hidden = (hide_h and "H" in (b.GetBeginAtom().GetSymbol(), b.GetEndAtom().GetSymbol())) or any(e in hide_atoms for e in ends)
        order = b.GetBondTypeAsDouble()
        if order in (2, 3):
            nx, ny = -(y2 - y1), x2 - x1
            L = math.hypot(nx, ny) or 1
            off = s * (0.09 if order == 2 else 0.13)
            for k in ((-1, 1) if order == 2 else (-1, 0, 1)):
                d.line((x1 + nx / L * off * k, y1 + ny / L * off * k, x2 + nx / L * off * k, y2 + ny / L * off * k),
                       fill=STICK, width=max(3, int(s * 0.08)))
        else:
            d.line((x1, y1, x2, y2), fill=(222, 226, 230) if hidden else STICK, width=max(3, int(s * 0.1)))
    if ring_circle:
        for ring in mol.GetRingInfo().AtomRings():
            rx = sum(xy[i][0] for i in ring) / len(ring)
            ry = sum(xy[i][1] for i in ring) / len(ring)
            rr = 0.55 * s
            d.ellipse((rx - rr, ry - rr, rx + rr, ry + rr), outline=STICK, width=max(3, int(s * 0.08)))
    if halo_atoms:
        glow = Image.new("RGBA", im.size, (0, 0, 0, 0))
        gd = ImageDraw.Draw(glow)
        for i in halo_atoms:
            r = ATOM_SIZE.get(mol.GetAtomWithIdx(i).GetSymbol(), 0.42) * s * 1.9
            gd.ellipse((xy[i][0] - r, xy[i][1] - r, xy[i][0] + r, xy[i][1] + r), fill=ACCENT + (90,))
        im.paste(glow, (0, 0), glow)
    order = sorted(range(mol.GetNumAtoms()), key=lambda i: mol.GetAtomWithIdx(i).GetSymbol() != "H")
    for i in order:
        sym = mol.GetAtomWithIdx(i).GetSymbol()
        r = ATOM_SIZE.get(sym, 0.42) * s
        ball(im, xy[i][0], xy[i][1], r, ATOM_COLOR.get(sym, (174, 62, 201)),
             hidden=(hide_h and sym == "H") or i in hide_atoms)
    return xy


# ---------- 各集 ----------

S = 0.8                     # 吉祥物縮放比例
MX, MY = 800, 430           # 吉祥物螢幕中心
HEAD = (MX, MY - 96 - 80)   # 天線頂端附近，思考泡泡的小泡泡指向這裡


def card_01():
    im, d = base("01", "電腦怎麼讀懂\n二氧化碳？")
    thought_bubble(d, (870, 50, 1160, 250), HEAD)
    ball_model(im, "O=C=O", 1015, 150, 250)
    mascot(im, MX, MY, "happy", "C", S)
    return im


def card_02():
    im, d = base("02", "同一個分子，\n為什麼有好幾種寫法？")
    thought_bubble(d, (760, 40, 1170, 220), HEAD)
    for i, rot in enumerate((0, 120, 240)):
        ball_model(im, "CCO", 835 + i * 130, 130, 125, rotate=rot)
    mascot(im, MX, MY + 20, "curious", "O", S)
    return im


def card_04():
    im, d = base("04", "氫原子\n躲到哪裡去了？")
    thought_bubble(d, (850, 40, 1170, 250), HEAD)
    ball_model(im, "CCO", 1010, 145, 280, add_hs=True, hide_h=True)
    mascot(im, MX, MY, "surprised", "H", S)
    return im


def card_13():
    im, d = base("13", "電腦會畫\n結構式嗎？")
    thought_bubble(d, (850, 40, 1170, 260), HEAD)
    ball_model(im, "CN1C=NC2=C1C(=O)N(C(=O)N2C)C", 1010, 150, 230)
    # 漂浮的鉛筆
    px, py = 1060, 420
    d = ImageDraw.Draw(im)
    d.polygon([(px, py), (px + 90, py - 90), (px + 106, py - 74), (px + 16, py + 16)], fill=(252, 196, 25))
    d.polygon([(px, py), (px + 16, py + 16), (px - 10, py + 26)], fill=(248, 215, 160))
    d.polygon([(px - 4, py + 17), (px - 10, py + 26), (px + 2, py + 21)], fill=INK)
    d.polygon([(px + 90, py - 90), (px + 106, py - 74), (px + 115, py - 83), (px + 99, py - 99)], fill=(250, 82, 82))
    mascot(im, MX - 40, MY, "happy", "N", S)
    return im


def card_17():
    im, d = base("17", "這個分子\n有沒有 OH？")
    xy = ball_model(im, "CCO", 1000, 200, 300, add_hs=True)
    # 漂浮的放大鏡圈住 OH：O 是 2 號原子，再找它身上的 H
    mol = Chem.AddHs(Chem.MolFromSmiles("CCO"))
    h_on_o = [n.GetIdx() for n in mol.GetAtomWithIdx(2).GetNeighbors() if n.GetSymbol() == "H"][0]
    ox = (xy[2][0] + xy[h_on_o][0]) / 2
    oy = (xy[2][1] + xy[h_on_o][1]) / 2
    r = 70
    d = ImageDraw.Draw(im)
    d.ellipse((ox - r, oy - r, ox + r, oy + r), outline=INK, width=9)
    ang = math.radians(135)
    hx, hy = ox + r * math.cos(ang), oy + r * math.sin(ang)
    d.line((hx, hy, hx + 80 * math.cos(ang), hy + 80 * math.sin(ang)), fill=INK, width=18)
    mascot(im, MX - 60, MY + 20, "focused", "O", S)
    return im



GLUCOSE = "OC[C@H]1OC(O)[C@H](O)[C@@H](O)[C@@H]1O"


def card_03():
    im, d = base("03", "打錯字，\n電腦會發現嗎？")
    thought_bubble(d, (870, 50, 1160, 250), HEAD)
    ball_model(im, "O=C=O", 1015, 150, 250, hide_atoms={2})  # 少打的那個 O 變成隱形球
    mascot(im, MX, MY - 50, "error", "O", S)  # 失敗表情的尾巴往下垂，整體往上移才不會超出畫面
    return im


def card_05():
    im, d = base("05", "分子裡有幾個\n原子、幾個鍵？")
    thought_bubble(d, (850, 40, 1170, 260), HEAD)
    ball_model(im, CAFFEINE_SMI, 1010, 150, 230)
    mascot(im, MX, MY, "computing", "C", S)
    return im


def card_10():
    im, d = base("10", "分子裡\n有沒有環？")
    thought_bubble(d, (850, 40, 1170, 260), HEAD)
    glucose = Chem.MolFromSmiles(GLUCOSE)  # 先存成變數，環資訊才不會隨暫時物件一起消失
    ring_atoms = set(glucose.GetRingInfo().AtomRings()[0])
    ball_model(im, GLUCOSE, 1010, 150, 240, halo_atoms=ring_atoms)
    mascot(im, MX, MY, "happy", "O", S)
    return im


def card_18():
    im, d = base("18", "葡萄糖\n有幾個 OH？")
    thought_bubble(d, (850, 40, 1170, 260), HEAD)
    mol = Chem.MolFromSmiles(GLUCOSE)
    oh_oxygens = {m[0] for m in mol.GetSubstructMatches(Chem.MolFromSmarts("[OX2H]"))}
    ball_model(im, GLUCOSE, 1010, 150, 240, halo_atoms=oh_oxygens)
    mascot(im, MX, MY, "computing", "O", S)
    return im


def card_21():
    im, d = base("21", "分子\n也有身分證？")
    # 漂浮的身分證卡：左邊是分子照片，右邊是幾行資料
    x0, y0, x1, y1 = 880, 70, 1150, 250
    d.rounded_rectangle((x0, y0, x1, y1), radius=18, fill="white", outline=ACCENT, width=6)
    d.rectangle((x0 + 3, y0 + 3, x1 - 3, y0 + 34), fill=ACCENT)
    d.rounded_rectangle((x0 + 20, y0 + 52, x0 + 120, y1 - 20), radius=10, fill=BUBBLE)
    ball_model(im, "CCO", x0 + 70, (y0 + 52 + y1 - 20) // 2, 95)
    d = ImageDraw.Draw(im)
    for k, w in enumerate((100, 80, 110, 60)):
        yy = y0 + 62 + k * 34
        d.rounded_rectangle((x0 + 138, yy, x0 + 138 + w, yy + 14), radius=7, fill=(206, 212, 218))
    mascot(im, MX - 30, MY, "proud", "C", S)
    return im


def card_06():
    im, d = base("06", "電腦會算\n分子量嗎？")
    thought_bubble(d, (880, 50, 1150, 240), HEAD)
    ball_model(im, "O", 1015, 150, 170, add_hs=True)
    # 漂浮的天平
    d = ImageDraw.Draw(im)
    bx, by = 1095, 330
    d.polygon([(bx - 34, by + 90), (bx + 34, by + 90), (bx, by + 60)], fill=MUTED)
    d.line((bx, by + 70, bx, by - 10), fill=MUTED, width=8)
    d.line((bx - 70, by, bx + 70, by), fill=MUTED, width=8)
    for px in (bx - 70, bx + 70):
        d.line((px, by, px - 24, by + 46), fill=MUTED, width=3)
        d.line((px, by, px + 24, by + 46), fill=MUTED, width=3)
        d.chord((px - 32, by + 30, px + 32, by + 62), 0, 180, fill=(252, 196, 25))
    mascot(im, MX - 40, MY, "computing", "O", S)
    return im


def card_07():
    im, d = base("07", "這個原子\n旁邊接了誰？")
    thought_bubble(d, (850, 40, 1170, 260), HEAD)
    ball_model(im, "CC(C)O", 1010, 150, 220, halo_atoms={1})  # 中間的碳有光暈，三個鄰居圍著它
    mascot(im, MX, MY + 20, "curious", "C", S)
    return im


def card_08():
    im, d = base("08", "每個原子\n是什麼元素？")
    thought_bubble(d, (850, 40, 1170, 260), HEAD)
    ball_model(im, "CC(=O)O", 1010, 150, 230)
    mascot(im, MX, MY, "focused", "C", S)
    return im


def card_09():
    im, d = base("09", "單鍵、雙鍵、\n三鍵怎麼分？")
    thought_bubble(d, (800, 40, 1170, 240), HEAD)
    ball_model(im, "O=C=O", 900, 140, 200)
    ball_model(im, "C#C", 1085, 140, 150)  # 不畫氫，三鍵才看得清楚
    mascot(im, MX, MY, "surprised", "C", S)
    return im


def card_11():
    im, d = base("11", "苯為什麼\n有兩種寫法？")
    thought_bubble(d, (790, 40, 1170, 240), HEAD)
    ball_model(im, "c1ccccc1", 890, 140, 170, ring_circle=True)
    ball_model(im, "c1ccccc1", 1070, 140, 170, kekulize=True)
    mascot(im, MX, MY + 20, "curious", "H", S)  # 天線是氫：小電腦自己就是一個苯
    return im


def card_12():
    im, d = base("12", "電腦看得懂\n食鹽嗎？")
    thought_bubble(d, (850, 50, 1170, 240), HEAD)
    for x, sym, sign in ((945, "Na", "+"), (1080, "Cl", "−")):
        ball(im, x, 150, 52, ATOM_COLOR[sym])
        d = ImageDraw.Draw(im)
        d.ellipse((x + 26, 82, x + 66, 122), fill="white", outline=INK, width=4)
        d.text((x + 46, 101), sign, font=font(34, TC_SEMIBOLD), fill=INK, anchor="mm")
    mascot(im, MX, MY, "surprised", "Cl", S, ion="−")  # 天線是氯離子：虛線的鍵、帶負電
    return im


def card_14():
    im, d = base("14", "廚房裡的分子\n排排站")
    thought_bubble(d, (760, 40, 1170, 230), HEAD)
    ball_model(im, "O", 840, 135, 100, add_hs=True)
    for i, smi in enumerate(("CCO", "CC(=O)O")):
        ball_model(im, smi, 970 + i * 130, 135, 115)
    mascot(im, MX, MY + 20, "proud", "O", S)
    return im


def card_15():
    im, d = base("15", "幫原子編號")
    thought_bubble(d, (850, 40, 1170, 260), HEAD)
    xy = ball_model(im, "CC(=O)O", 1010, 150, 220)
    d = ImageDraw.Draw(im)
    for i, (x, y) in enumerate(xy):  # 每顆球旁邊的小編號
        d.ellipse((x + 14, y - 46, x + 46, y - 14), fill="white", outline=ACCENT, width=3)
        d.text((x + 30, y - 30), str(i), font=font(22, TC_SEMIBOLD), fill=ACCENT, anchor="mm")
    mascot(im, MX, MY, "focused", "C", S)
    return im


def card_16():
    im, d = base("16", "幫一塊結構\n塗顏色")
    thought_bubble(d, (850, 40, 1170, 260), HEAD)
    ball_model(im, "CCO", 1010, 150, 260, halo_atoms={2})
    mascot(im, MX, MY, "happy", "O", S)
    return im


def card_19():
    im, d = base("19", "把酒精的 OH\n拿掉會怎樣？")
    thought_bubble(d, (830, 40, 1170, 250), HEAD)
    xy = ball_model(im, "CCO", 975, 165, 230, hide_atoms={2})  # 原本 OH 的位置變成隱形球
    ball(im, xy[2][0] + 75, xy[2][1] - 70, 26, ATOM_COLOR["O"])  # 氧飄走了
    ball(im, xy[2][0] + 105, xy[2][1] - 92, 15, ATOM_COLOR["H"])
    d = ImageDraw.Draw(im)
    d.line((xy[2][0] + 88, xy[2][1] - 80, xy[2][0] + 96, xy[2][1] - 86), fill=STICK, width=6)
    mascot(im, MX, MY, "surprised", "O", S)
    return im


def card_20():
    im, d = base("20", "酒為什麼\n會變醋？")
    thought_bubble(d, (760, 40, 1170, 240), HEAD)
    ball_model(im, "CCO", 850, 145, 150)
    d = ImageDraw.Draw(im)
    d.line((935, 145, 985, 145), fill=ACCENT, width=8)
    d.polygon([(1000, 145), (980, 130), (980, 160)], fill=ACCENT)
    ball_model(im, "CC(=O)O", 1080, 145, 150)
    mascot(im, MX, MY, "proud", "O", S)
    return im


def drop(d, cx, cy, r, color):
    """水滴形：上尖下圓。"""
    d.ellipse((cx - r, cy - r, cx + r, cy + r), fill=color)
    d.polygon([(cx - r * 0.87, cy - r * 0.5), (cx, cy - r * 2.1), (cx + r * 0.87, cy - r * 0.5)], fill=color)
    d.ellipse((cx - r * 0.55, cy - r * 0.35, cx - r * 0.2, cy + r * 0.1), fill=(255, 255, 255))


def card_22():
    im, d = base("22", "喜歡水\n還是喜歡油？")
    thought_bubble(d, (850, 50, 1170, 250), HEAD)
    drop(d, 945, 175, 48, (77, 171, 247))    # 水
    drop(d, 1080, 175, 48, (252, 196, 25))   # 油
    mascot(im, MX, MY, "curious", "O", S)
    return im


def card_23():
    im, d = base("23", "分子的條碼")
    thought_bubble(d, (820, 40, 1170, 260), HEAD)
    ball_model(im, "CCO", 995, 105, 150)
    from rdkit.Chem import rdFingerprintGenerator
    bits = rdFingerprintGenerator.GetMorganGenerator(radius=2, fpSize=64).GetFingerprint(Chem.MolFromSmiles("CCO")).ToBitString()
    d = ImageDraw.Draw(im)
    x0, w = 850, 9
    for i, b in enumerate(bits[:32]):   # 前 32 格
        d.rectangle((x0 + i * w, 180, x0 + i * w + w - 2, 230), fill=INK if b == "1" else (206, 212, 218))
    mascot(im, MX, MY, "computing", "C", S)
    return im


def card_24():
    im, d = base("24", "兩個分子\n有多像？")
    thought_bubble(d, (800, 40, 1170, 240), HEAD)
    ball_model(im, "CCO", 900, 140, 170)
    ball_model(im, "CO", 1075, 140, 120)
    mascot(im, MX, MY + 20, "curious", "O", S)
    return im


def card_25():
    im, d = base("25", "咖啡因和巧克力裡的\n可可鹼差在哪？")
    thought_bubble(d, (770, 30, 1175, 260), HEAD)
    from rdkit.Chem import rdFMCS
    theo = "Cn1cnc2c1c(=O)[nH]c(=O)n2C"
    caf, tb = Chem.MolFromSmiles(CAFFEINE_SMI), Chem.MolFromSmiles(theo)
    q = Chem.MolFromSmarts(rdFMCS.FindMCS([caf, tb]).smartsString)
    ball_model(im, CAFFEINE_SMI, 875, 145, 165, halo_atoms=set(caf.GetSubstructMatch(q)))
    ball_model(im, theo, 1070, 145, 165, halo_atoms=set(tb.GetSubstructMatch(q)))
    mascot(im, MX, MY + 30, "surprised", "N", S)
    return im


def card_26():
    im, d = base("26", "分子其實\n是立體的")
    thought_bubble(d, (850, 40, 1170, 270), HEAD)
    from rdkit.Chem import AllChem
    m = Chem.AddHs(Chem.MolFromSmiles("CCO"))
    AllChem.EmbedMolecule(m, randomSeed=42)
    c = m.GetConformer()
    pts = [tuple(c.GetAtomPosition(i)) for i in range(m.GetNumAtoms())]
    cen = [sum(p[k] for p in pts) / len(pts) for k in range(3)]
    rx, ry = -0.4, 0.6
    P = []
    for x, y, z in ((p[0] - cen[0], p[1] - cen[1], p[2] - cen[2]) for p in pts):
        x1, z1 = x * math.cos(ry) + z * math.sin(ry), -x * math.sin(ry) + z * math.cos(ry)
        y1, z2 = y * math.cos(rx) - z1 * math.sin(rx), y * math.sin(rx) + z1 * math.cos(rx)
        f = 6 / (6 - z2)
        P.append((1010 + x1 * 62 * f, 155 - y1 * 62 * f, z2, f))
    d = ImageDraw.Draw(im)
    items = [((P[b.GetBeginAtomIdx()][2] + P[b.GetEndAtomIdx()][2]) / 2 - 0.01, "b", (b.GetBeginAtomIdx(), b.GetEndAtomIdx()))
             for b in m.GetBonds()] + [(P[i][2], "a", i) for i in range(len(P))]
    for _, kind, v in sorted(items, key=lambda t: t[0]):
        if kind == "b":
            i, j = v
            d.line((P[i][0], P[i][1], P[j][0], P[j][1]), fill=STICK, width=8)
        else:
            sym = m.GetAtomWithIdx(v).GetSymbol()
            ball(im, P[v][0], P[v][1], int(ATOM_SIZE.get(sym, 0.42) * 62 * P[v][3]), ATOM_COLOR[sym])
            d = ImageDraw.Draw(im)
    mascot(im, MX, MY + 20, "proud", "C", S)
    return im


CAFFEINE_SMI = "CN1C=NC2=C1C(=O)N(C(=O)N2C)C"

CARDS = {
    "01": ("2026-11-rdkit-01-molfromsmiles", card_01),
    "02": ("2026-11-rdkit-02-moltosmiles", card_02),
    "04": ("2026-11-rdkit-04-addhs", card_04),
    "13": ("2026-11-rdkit-13-moltoimage", card_13),
    "17": ("2026-11-rdkit-17-hassubstructmatch", card_17),
    "03": ("2026-11-rdkit-03-smiles-errors", card_03),
    "05": ("2026-11-rdkit-05-getnumatoms", card_05),
    "10": ("2026-11-rdkit-10-getringinfo", card_10),
    "18": ("2026-11-rdkit-18-getsubstructmatches", card_18),
    "21": ("2026-11-rdkit-21-moltoinchikey", card_21),
    "06": ("2026-11-rdkit-06-molwt", card_06),
    "07": ("2026-11-rdkit-07-getneighbors", card_07),
    "08": ("2026-11-rdkit-08-getatoms", card_08),
    "09": ("2026-11-rdkit-09-getbonds", card_09),
    "11": ("2026-11-rdkit-11-kekulize", card_11),
    "12": ("2026-11-rdkit-12-getmolfrags", card_12),
    "14": ("2026-11-rdkit-14-molstogridimage", card_14),
    "15": ("2026-11-rdkit-15-addatomindices", card_15),
    "16": ("2026-11-rdkit-16-highlightatoms", card_16),
    "19": ("2026-11-rdkit-19-deletesubstructs", card_19),
    "20": ("2026-11-rdkit-20-reactionfromsmarts", card_20),
    "22": ("2026-11-rdkit-22-mollogp", card_22),
    "23": ("2026-11-rdkit-23-morganfingerprint", card_23),
    "24": ("2026-11-rdkit-24-tanimotosimilarity", card_24),
    "25": ("2026-11-rdkit-25-findmcs", card_25),
    "26": ("2026-11-rdkit-26-embedmolecule", card_26),
}


def main(selected):
    for ep, (folder, make) in CARDS.items():
        if selected and ep not in selected:
            continue
        out = POSTS / folder / "images" / "card.png"
        make().save(out)
        print("saved", out)


if __name__ == "__main__":
    main(set(sys.argv[1:]))
