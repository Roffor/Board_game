"""Схемы пути (design/06 §3.2–3.3): генерация 18 схем и проверка требований.
SOSTAV — копия таблицы design/06 §2.1 (карты пути); при смене состава правь здесь и перезапусти.
Буквы: В I, В II — враг яруса, Э — элита, С — событие, К — костёр, М — мастерская, Т — тайник."""
import itertools, random
SOSTAV = {'В I': 14, 'В II': 12, 'Э': 5, 'С': 20, 'К': 6, 'М': 6, 'Т': 6}   # design/06 §2.1
BOI = ('В I', 'В II', 'Э')
TIHIE = ('С', 'К', 'М', 'Т')
# Потолок каждой категории в одной схеме акта. Сумма по актам ≤ SOSTAV — любой бросок трёх d6 раскладывается.
POTOLOK = {1: {'В I': 4, 'В II': 2, 'Э': 0, 'С': 4, 'К': 2, 'М': 2, 'Т': 2},
           2: {'В I': 3, 'В II': 3, 'Э': 1, 'С': 4, 'К': 2, 'М': 2, 'Т': 2},
           3: {'В I': 1, 'В II': 4, 'Э': 2, 'С': 4, 'К': 2, 'М': 2, 'Т': 2}}
ELIT_MIN = {1: 0, 2: 0, 3: 1}            # решение Никиты: 0 / 0–1 / 1–2
ETAZHI = [tuple(sorted(c)) for c in itertools.combinations(BOI + TIHIE, 3)]

def boevoj(et): return any(c in BOI for c in et)

def goditsya(akt, s):
    cnt = {k: sum(et.count(k) for et in s) for k in SOSTAV}
    if any(cnt[k] > POTOLOK[akt][k] for k in SOSTAV) or cnt['Э'] < ELIT_MIN[akt]: return False
    boj = sum(boevoj(et) for et in s)
    if not 2 <= boj <= 3: return False                    # 1–2 тихих этажа: жадный маршрут ≤ 9 боёв + Хранитель
    if akt == 1 and 'Э' in s[0]: return False
    if akt == 3 and (boevoj(s[3]) or 'К' not in s[3]): return False   # перед боссом — тихий этаж с костром
    if 'В II' in s[0] and akt == 1: return False          # первый этаж забега — только ярус I
    return True

def vybrat(akt, n=6, seed=11):
    rnd = random.Random(seed * 10 + akt)
    out, vidy = [], set()
    for _ in range(200000):
        s = tuple(rnd.choice(ETAZHI) for _ in range(4))
        if not goditsya(akt, s): continue
        vid = tuple(sorted(sum(s, ())))                     # разнообразие по составу
        if vid in vidy: continue
        vidy.add(vid); out.append(s)
        if len(out) == n: break
    while len(out) < n:                                     # добор: другой порядок этажей
        s = tuple(rnd.choice(ETAZHI) for _ in range(4))
        if goditsya(akt, s) and s not in out: out.append(s)
    return [tuple(tuple(rnd.sample(et, 3)) for et in s) for s in out]

def proverka(shemy):
    for k, n in SOSTAV.items():
        hud = sum(max(sum(et.count(k) for et in s) for s in lst) for lst in shemy.values())
        print(f'{k}: худшее {hud} из {n} — ' + ('ok' if hud <= n else 'НЕ ХВАТАЕТ'))
    boi = [sum(boevoj(et) for et in s) for lst in shemy.values() for s in lst]
    print('боевых этажей на схеме:', sorted(set(boi)), '; жадный маршрут за забег + Хранитель ≤', 3 * max(boi) + 1)

if __name__ == '__main__':
    shemy = {a: vybrat(a) for a in (1, 2, 3)}
    proverka(shemy)
    for a, lst in shemy.items():
        print(f'\n## Акт {a}')
        for i, s in enumerate(lst, 1):
            print(f'\n**{a}.{i}** (d6 = {i})\n\n| этаж | | | |\n|---|---|---|---|')
            for e in range(4, 0, -1):
                print(f'| {e} | ' + ' | '.join(s[e - 1]) + ' |')
