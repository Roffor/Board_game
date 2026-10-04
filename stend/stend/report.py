# -*- coding: utf-8 -*-
"""Отчёты в md: по каждой фазе и итоговый. Коротко: таблицы против коридоров соглашения и проблемные карты."""
import os

from . import metrics as M


def f1(x, nd=1):
    return '—' if x is None or x != x else f'{x:.{nd}f}'


def mark(x, k):
    if k is None or x != x:
        return ''
    return ' ✓' if k[0] <= x <= k[1] else (' ↑' if x > k[1] else ' ↓')


def sit_table(summ):
    out = ['| Ситуация | Боёв | Раунды (коридор) | Потери пары, % (коридор) | Победы | Застряли | Выбор в раунде | Карт за раунд | Урон мага, доля |',
           '|---|---|---|---|---|---|---|---|---|']
    for s, d in summ.items():
        rk, lk = d['rounds_k'], d['loss_k']
        out.append(f"| {s} | {d['n']} | {f1(d['rounds'], 2)}±{f1(d['rounds_se'], 2)}{mark(d['rounds'], rk)} ({rk[0]}–{rk[1]}) "
                   f"| {f1(d['loss'])}±{f1(d['loss_se'])}{mark(d['loss'], lk)} ({lk[0]}–{lk[1]}) | {f1(100 * d['won'], 0)}% "
                   f"| {d['stuck']} | {f1(100 * d['choice'], 0)}% | {f1(d['plays'])} | {f1(d['dmg_mag'], 2)} |")
    return '\n'.join(out)


def flags(summ, sog):
    """Что выходит за соглашение (по среднему)."""
    out = []
    for s, d in summ.items():
        if not M.in_k(d['rounds'], d['rounds_k']):
            out.append(f'{s}: раунды {f1(d["rounds"], 2)} вне {d["rounds_k"]} [С 2]')
        if not M.in_k(d['loss'], d['loss_k']):
            out.append(f'{s}: потери пары {f1(d["loss"])}% вне {d["loss_k"]} [С 3.2]')
        if d['won'] < sog['pobedy_min']:
            out.append(f'{s}: победы {f1(100 * d["won"], 0)}% меньше {int(100 * sog["pobedy_min"])}% [С 3.5]')
        if d.get('long') is not None and d['long'] > sog['zatyazhnye'][s]['dolya_maks']:
            out.append(f'{s}: затяжных боёв {f1(100 * d["long"], 0)}% [С 2.5]')
        if d.get('hero_over') is not None and d['hero_over'] > 0.5:
            out.append(f'{s}: в {f1(100 * d["hero_over"], 0)}% боёв один герой теряет больше нормы [С 3.2]')
        if d['choice'] < sog['vybor_v_raunde_min']:
            out.append(f'{s}: выбор в раунде {f1(100 * d["choice"], 0)}% < 50% [С 7.4]')
        if d['stuck']:
            out.append(f'{s}: {d["stuck"]} боёв упёрлись в предел раундов')
    return out


def card_md(tab, w, ref, sog):
    norm = sog['apgrejd_norma_proc']
    out = [f'Сила в % от средней силы эталонов; норма апгрейда {norm[0]}–{norm[1]}% [С 8.9]; погрешность ±1,5 σ. '
           f'Вес потерь w = {f1(w, 2)}, сила эталона = {f1(ref, 2)} очка.', '',
           '| Карта | Сила, % | Ранняя (I) | Поздняя | Δ побед | Разыграна за бой | Боёв | Итог |', '|---|---|---|---|---|---|---|---|']
    for r in tab:
        out.append(f"| {r['karta']} | {f1(r['pct'], 0)}±{f1(r['err'], 0)} | {f1(r.get('early'), 0)} | {f1(r.get('late'), 0)} "
                   f"| {f1(100 * r['d_won'], 1) if r.get('d_won') is not None else '—'} | {f1(r.get('plays'), 2)} | {r['n']} | {r['verdict']} |")
    return '\n'.join(out)


def errors_md(rows):
    bad = [r for r in rows if 'error' in r]
    if not bad:
        return ''
    out = [f'\n**Ошибки:** {len(bad)} боёв. Первые:']
    for r in bad[:3]:
        out.append(f"- {r['v']} {r['sit']} сид {r['seed']}: {r['error']}")
    return '\n'.join(out)


def phase_report(run, ph):
    rows = run.phase_rows(ph); sog = run.sog
    L = [f'# Фаза «{ph["id"]}» ({ph["tip"]})', '',
         f'План «{run.plan["nazvanie"]}», сид {run.state["seed0"]}, боёв {len(rows)}, '
         f'время {run.state["potracheno"].get(ph["id"], 0) / 60:.0f} мин.', '']
    if ph.get('opisanie'):
        L += [ph['opisanie'], '']
    if ph['tip'] == 'progon':
        for v in ph['varianty']:
            vr = [r for r in rows if r['v'] == v['metka']]
            summ = M.summary(vr, sog)
            L += [f'## {v["metka"]}', '', sit_table(summ), '']
            fl = flags(summ, sog)
            L += (['Вне соглашения:'] + [f'- {x}' for x in fl] if fl else ['Всё в коридорах соглашения.']) + ['']
    elif ph['tip'] == 'test_bilda':
        summ = M.summary([r for r in rows if r['v'] == 'baza'], sog)
        L += ['## База', '', sit_table(summ), '']
        tab, w, ref = M.card_table(rows, 'baza', ph['karty'], sog['etalony'], ph['situacii'], sog)
        L += ['## Карты', '', card_md(tab, w, ref, sog), '']
        bad = [r for r in tab if r['karta'] in ph['karty'] and r['verdict'].startswith('точно вне')]
        if bad:
            L += ['Вне нормы: ' + ', '.join(f"{r['karta']} ({f1(r['pct'], 0)}%)" for r in bad), '']
    elif ph['tip'] == 'podbor':
        cur = run.podbor_cur(ph)
        L += ['## Найденные числа', '', '| Число | Было | Стало |', '|---|---|---|']
        for x in ph['parametry']:
            L.append(f"| {x['chislo']} | {run.current_value(x['chislo']) if not ph.get('zapisyvat') else '(см. журнал)'} | {cur[x['chislo']]} |")
        L.append('')
        if ph['cel'] == 'koridory':
            name = run.sig(cur)
            summ = M.summary([r for r in rows if r['v'] == name], sog)
            if summ:
                L += ['## С найденными числами', '', sit_table(summ), '']
        else:
            names = sorted({r['v'] for r in rows} - {'baza'} - set(sog['etalony']))
            tab, w, ref = M.card_table(rows, 'baza', names, sog['etalony'], ph['situacii'], sog)
            L += ['## Все проверенные значения', '', card_md(tab, w, ref, sog), '']
    L.append(errors_md(rows))
    with open(os.path.join(run.dir, f'otchet-{ph["id"]}.md'), 'w', encoding='utf-8') as f:
        f.write('\n'.join(L) + '\n')


def final_report(run):
    L = [f'# Итог: {run.plan["nazvanie"]}', '',
         f'Старт {run.state["start"]}, срок {run.plan["srok_chasov"]} ч, потрачено {sum(run.state["potracheno"].values()) / 3600:.2f} ч, '
         f'боёв {len(run.rows)}, ошибок {sum(1 for r in run.rows if "error" in r)}, сид {run.state["seed0"]}.', '',
         '| Фаза | Тип | Боёв | Мин | Отчёт |', '|---|---|---|---|---|']
    for ph in run.plan['fazy']:
        L.append(f"| {ph['id']} | {ph['tip']} | {len(run.phase_rows(ph))} | {run.state['potracheno'].get(ph['id'], 0) / 60:.0f} "
                 f"| [otchet-{ph['id']}.md](otchet-{ph['id']}.md) |")
    L += ['', 'Журнал событий и правок файлов: [zhurnal.md](zhurnal.md).']
    with open(os.path.join(run.dir, 'itog.md'), 'w', encoding='utf-8') as f:
        f.write('\n'.join(L) + '\n')
