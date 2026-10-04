# -*- coding: utf-8 -*-
"""Таблица карт героя для его дизайн-документа (heroes/<герой>/<герой>.md).

Числа карт живут только в YAML карт; таблица в документе собирается отсюда, чтобы документ и карты
не расходились. Таблица стоит между метками НАЧАЛО и КОНЕЦ; если меток в документе нет, раздел
дописывается в конец. Руками внутри меток не править: следующий запуск всё перезапишет."""
import os

НАЧАЛО = '<!-- karty:nachalo — раздел собирается командой `python run.py tablica` из YAML карт, руками не править -->'
КОНЕЦ = '<!-- karty:konec -->'
НАБОРЫ = {'start': 'стартовая', 'zheton': 'жетон', 'apgrejd': 'апгрейд', 'zapas': 'запас', 'otkaz': 'отказ'}


def _table(cards):
    rows = ['| Карта | Набор | Билд | Копий | Цена | Текст |', '|---|---|---|---|---|---|']
    for c in cards:
        text = c.text.replace('|', '/').replace('\n', ' ')
        rows.append(f'| {c.name} | {НАБОРЫ.get(c.set, c.set)} | {c.build or "—"} | {c.copies} | {c.cost} | {text} |')
    return '\n'.join(rows)


def section(cards):
    order = {'start': 0, 'zheton': 1, 'apgrejd': 2, 'zapas': 3, 'otkaz': 4}
    key = lambda c: (order.get(c.set, 9), c.build, c.name)
    osn = sorted((c for c in cards if '/karty/osnovnye/' in c.path.replace(os.sep, '/')), key=key)
    zap = sorted((c for c in cards if '/karty/zapas/' in c.path.replace(os.sep, '/')), key=key)
    out = [НАЧАЛО, '', '## Карты (числа из YAML)', '',
           f'### Основные: {len(osn)} (`karty/osnovnye/`)', '', _table(osn) if osn else 'Пока нет.', '',
           f'### Запас: {len(zap)} (`karty/zapas/`)', '', _table(zap) if zap else 'Пока нет.', '', КОНЕЦ]
    return '\n'.join(out)


def update(game, root):
    """Обновить таблицы во всех документах героев. Возвращает список обновлённых файлов."""
    by_dir = {}
    for c in game.cards.values():
        parts = c.path.replace(os.sep, '/').split('/')
        if parts[0] == 'heroes':
            by_dir.setdefault(parts[1], []).append(c)
    done = []
    for folder in sorted(os.listdir(os.path.join(root, 'heroes'))):
        doc = os.path.join(root, 'heroes', folder, folder + '.md')
        if not os.path.exists(doc):
            continue
        with open(doc, encoding='utf-8') as f:
            s = f.read()
        new = section(by_dir.get(folder, []))
        if НАЧАЛО in s and КОНЕЦ in s:
            a = s.index(НАЧАЛО); b = s.index(КОНЕЦ) + len(КОНЕЦ)
            s2 = s[:a] + new + s[b:]
        else:
            s2 = s.rstrip('\n') + '\n\n' + new + '\n'
        if s2 != s:
            with open(doc, 'w', encoding='utf-8') as f:
                f.write(s2)
            done.append(os.path.relpath(doc, root))
    return done
