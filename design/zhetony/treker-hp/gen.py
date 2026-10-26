"""Планшет здоровья врага (решение Никиты 2026-10-26) и его место на листе жетонов.

python gen.py <папка> — пишет plansht-1-k-1.svg (печать 100 %) и list-zhetonov.svg.
"""
import os
import sys

OUT = sys.argv[1] if len(sys.argv) > 1 else os.path.dirname(os.path.abspath(__file__))
FONT = 'font-family="Arial, sans-serif"'

# Лист A4 альбомом, 9 x 6 жетонов по 25 мм, зазор 5,5 мм (design/zhetony/zhetony.md)
W, H = 297, 210
D, G = 25, 5.5
P = D + G
X0, Y0 = (W - (9 * D + 8 * G)) / 2, (H - (6 * D + 5 * G)) / 2
# Планшет на месте блока 3 x 2 в правом нижнем углу: столбцы 7–9, ряды 5–6
PC, PR, PNC, PNR = 6, 4, 3, 2
PW, PH = PNC * D + (PNC - 1) * G, PNR * D + (PNR - 1) * G  # 86 x 55,5 мм


def plate(x, y):
    e = [f'<rect x="{x}" y="{y}" width="{PW}" height="{PH}" rx="3" fill="#f6efe0" stroke="#b03030" stroke-width="0.6" stroke-dasharray="2 1"/>',
         f'<text x="{x + PW / 2}" y="{y + 6.5}" {FONT} font-size="4.3" text-anchor="middle" font-weight="bold">ЗДОРОВЬЕ ВРАГА</text>']
    pad, top = 2.5, 9
    cw = (PW - 2 * pad) / 10
    rows = (("десятки", [10 * i for i in range(10)]),
            ("", [100 + 10 * i for i in range(10)]),
            ("единицы", list(range(10))))
    rh = (PH - top - pad - 3) / 3
    for i, (name, vals) in enumerate(rows):
        yy = y + top + i * rh + (3 if i == 2 else 0)
        for j, v in enumerate(vals):
            cx = x + pad + j * cw
            fill = "#e2cfa6" if i < 2 else ("#fff" if j % 2 == 0 else "#efe6d2")
            if i < 2 and j % 2:
                fill = "#ecdcb8"
            e.append(f'<rect x="{cx:.2f}" y="{yy:.2f}" width="{cw:.2f}" height="{rh:.2f}" fill="{fill}" stroke="#8a8170" stroke-width="0.25"/>')
            fs = 3.6 if v >= 100 else 4.4
            e.append(f'<text x="{cx + cw / 2:.2f}" y="{yy + rh / 2 + 1.5:.2f}" {FONT} font-size="{fs}" text-anchor="middle">{v}</text>')
    return e


def wrap(parts, w, h, name):
    with open(os.path.join(OUT, name), "w", encoding="utf8") as f:
        f.write(f'<svg xmlns="http://www.w3.org/2000/svg" width="{w}mm" height="{h}mm" viewBox="0 0 {w} {h}">\n'
                f'<rect width="{w}" height="{h}" fill="#fff"/>\n' + "\n".join(parts) + "\n</svg>\n")


# Печать 1:1
p = [f'<text x="5" y="6" {FONT} font-size="3.6">Печать 100 %. Красный пунктир — рез.</text><text x="5" y="10.5" {FONT} font-size="3.6">Метки: два кубика 7–8 мм (десятки и единицы).</text>']
p += plate(5, 14)
wrap(p, 120, 75, "plansht-1-k-1.svg")

# Лист жетонов
s = [f'<rect x="0.3" y="0.3" width="{W - 0.6}" height="{H - 0.6}" fill="#fff" stroke="#333" stroke-width="0.6"/>']
left = 0
for r in range(6):
    for c in range(9):
        if PC <= c < PC + PNC and PR <= r < PR + PNR:
            continue
        x, y = X0 + c * P, Y0 + r * P
        s.append(f'<circle cx="{x + D / 2}" cy="{y + D / 2}" r="{D / 2}" fill="#e8e3d8" stroke="#8a8170" stroke-width="0.5"/>')
        left += 1
s += plate(X0 + PC * P, Y0 + PR * P)
s.append(f'<text x="{X0}" y="{H - 4}" {FONT} font-size="5">Жетонов: {left} по 25 мм + планшет здоровья врага 86 × 55,5 мм на месте 6 жетонов</text>')
wrap(s, W, H, "list-zhetonov.svg")
print(left)
