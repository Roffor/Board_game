# -*- coding: utf-8 -*-
"""Лог забега в формате обычного теста. Запуск: python3 report.py result.json > zabeg.md"""
import sys, json

ROOM = {'Б1': 'Бой I', 'Б2': 'Бой II', 'Эл': 'Элита', 'Отд': 'Отдых', 'Тай': 'Тайник', 'Соб': 'Событие',
        'Босс': 'Босс', 'Раскладка': 'Раскладка'}
TIER = {1: 'рядовой I', 2: 'рядовой II', 'elite': 'элита', 'boss': 'босс'}


def f1(x):
    return f'{x:.1f}'.replace('.', ',')


def main(path, title):
    d = json.load(open(path, encoding='utf-8'))
    F = d['fights']
    ordinary = [f for f in F if f['tier'] in (1, 2)]
    avg_ord = sum(f['sec'] for f in ordinary) / 60 / max(1, len(ordinary))
    mf = d['min_frac']
    low = min(mf, key=mf.get)
    rounds = sum(f['rounds'] for f in F)
    var = d['var_rounds']
    far = sum(1 for v in var if v[1]) / max(1, len(var))
    near = sum(v[0] for v in var) / max(1, len(var))
    print(f'# {title}\n')
    print(f'**Итог: {"победа" if d["won"] else "поражение"}, {f1(d["total_min"])} мин.** '
          f'Апгрейдов {d["n_up"]}, легендарок {d["n_leg"]}. '
          f'Среднее время убийства рядового врага {f1(avg_ord)} мин. '
          f'Самая низкая точка: {"Маг" if low == "M" else "Жрец"} {round(100 * mf[low])}% '
          f'(Маг {round(100 * mf["M"])}%, Жрец {round(100 * mf["P"])}%).\n')
    print(f'Боёв {len(F)}, раундов {rounds}, из них в темноте {d["stats"]["dark_rounds"]}. '
          f'Ошибок игроков (взят второй вариант) {d["bot_errors"]}.\n')
    print('## Бои\n')
    print('| # | Бой | Результат | Время, мин | Раундов | Потеряно здоровья М / Ж | Карт Маг: всего / разных | Карт Жрец: всего / разных | Раундов с другим путём |')
    print('|---|---|---|---|---|---|---|---|---|')
    for i, f in enumerate(F, 1):
        v = f['var']; vf = sum(1 for x in v if x[1])
        print(f"| {i} | {f['name']} ({TIER[f['tier']]}{', Угроза' if f['threat'] else ''}), «{f['loc']}» | "
              f"{'победа' if f['won'] else 'поражение'} | {f1(f['sec'] / 60)} | {f['rounds']} | "
              f"{f['taken']['M']} / {f['taken']['P']} | {len(f['plays']['M'])} / {len(set(f['plays']['M']))} | "
              f"{len(f['plays']['P'])} / {len(set(f['plays']['P']))} | {vf} из {len(v)} |")
    print(f'\nВариативность: в {round(100 * far)}% раундов был план, отличный от выбранного хотя бы двумя картами '
          f'и не хуже него больше чем на 1 здоровье; в среднем {f1(near)} близких по силе планов на раунд.\n')
    print('## Ход забега\n')
    print('| Этаж | Комната | Что произошло | Этап, мин | С начала, мин | После этапа |')
    print('|---|---|---|---|---|---|')
    for s in d['stages']:
        fl = '—' if s['floor'] == 0 else ('Босс' if s['floor'] == 13 else s['floor'])
        print(f"| {fl} | {ROOM.get(s['room'], s['room'])} | {s['text']} | {f1(s['min'])} | {round(s['total'])} | {s['state']} |")
    print(f"\nКолоды в конце: Маг — {d['decks']['M']}; Жрец — {d['decks']['P']}.")


if __name__ == '__main__':
    main(sys.argv[1], sys.argv[2])
