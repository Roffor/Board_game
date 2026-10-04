# -*- coding: utf-8 -*-
"""Забег целиком. Запуск: python3 run.py decisions.json
Если очередного решения нет в файле, печатает ситуацию и выходит с кодом 3."""
import sys, json
from engine import *


def card_list(h):
    names = {}
    for c in h.deck:
        names[c.name] = names.get(c.name, 0) + 1
    return ', '.join(f'{n}×{k}' if n > 1 else k for k, n in names.items())


class Run:
    def __init__(self, path):
        cfg = json.load(open(path, encoding='utf-8'))
        self.g = g = Game(cfg['seed'], cfg['decisions'])
        r = g.rng
        self.t1 = list(TIER1); r.shuffle(self.t1)
        self.t2 = list(TIER2); r.shuffle(self.t2)
        self.el = list(ELITES); r.shuffle(self.el)
        self.locs = list(LOCATIONS); r.shuffle(self.locs); self.loc_disc = []
        self.events = list(EVENTS); r.shuffle(self.events)
        self.pots = list(POTIONS); r.shuffle(self.pots)
        self.caches = list(CACHES); r.shuffle(self.caches)
        self.up = {'M': M_upgrades(), 'P': P_upgrades()}
        for k in 'MP':
            r.shuffle(self.up[k])
        self.legs = {'M': list(M_LEGENDS), 'P': list(P_LEGENDS)}
        self.col = None; self.threat_cell = None
        self.boss_hp_mod = 0; self.boss_oil_bonus = 0

    # ---------------------------------------------------------- помощники
    def stage(self, floor, room, t0, text):
        g = self.g
        g.stages.append(dict(floor=floor, room=room, min=(g.t - t0) / 60, total=g.t / 60, text=text, state=g.hs()))

    def loc(self):
        if not self.locs:
            self.locs = self.loc_disc; self.loc_disc = []; self.g.rng.shuffle(self.locs)
        l = self.locs.pop(); self.loc_disc.append(l); return l

    def potion(self, n=1):
        got = []
        for _ in range(n):
            if not self.pots:
                break
            p = self.pots.pop()
            if len(self.g.potions) < 3:
                self.g.potions.append(p); got.append(p)
            else:
                got.append(p + ' (не влезло, сумка полна)')
        return got

    def deck_prompt(self, k):
        h = self.g.H[k]
        return f'{h.name} ({h.hp}/{h.maxhp}), колода: {card_list(h)}' + (f'; легендарка: {h.legend}' if h.legend else '')

    def upgrade(self, k, n=3, label='Апгрейд'):
        g = self.g; stack = self.up[k]
        offer = [stack.pop(0) for _ in range(min(n, len(stack)))]
        txt = '\n'.join(f'  {i}: {c.name} [{c.branch}] — {c.text}' for i, c in enumerate(offer))
        d = g.decide(f'{label} {k}', f'{label} для героя {HERO_NAMES[k]}. Варианты:\n{txt}\n{self.deck_prompt(k)}\n'
                     'Формат: "i:Имя заменяемой карты" или "нет"')
        taken = None
        if d != 'нет':
            i, rep = d.split(':', 1); i = int(i); taken = offer[i]
            h = g.H[k]; old = next(c for c in h.deck if c.name == rep)
            h.deck.remove(old); h.deck.append(taken)
            g.L(f'   {h.name}: берёт «{taken.name}» вместо «{rep}»')
        for c in offer:
            if c is not taken:
                stack.append(c)
        g.tick(0)
        return f'{HERO_NAMES[k]}: ' + (f'«{taken.name}» вместо «{rep}»' if taken else 'ничего') + \
               f' (из: {", ".join(c.name for c in offer)})'

    def legend(self, k):
        g = self.g; h = g.H[k]
        offer = g.rng.sample(self.legs[k], 2)
        txt = '\n'.join(f'  {i}: {n} — {t}' for i, (n, t) in enumerate(offer))
        d = g.decide(f'Легендарка {k}', f'Легендарка для {h.name}: \n{txt}\n{self.deck_prompt(k)}\n'
                     'Формат: "i:Имя заменяемой карты" или "нет"')
        if d == 'нет':
            return f'{h.name}: легендарку не взял (из: {", ".join(n for n, _ in offer)})'
        i, rep = d.split(':', 1); n, t = offer[int(i)]
        old = next(c for c in h.deck if c.name == rep)
        h.deck.remove(old)
        if h.legend:
            oldl = next(c for c in h.deck if c.cid == 'leg'); h.deck.remove(oldl); h.deck.append(old)
        h.deck.append(legend_card(k, n, t)); h.legend = n
        g.L(f'   {h.name}: легендарка «{n}» вместо «{rep}»')
        return f'{h.name}: легендарка «{n}» вместо «{rep}» (из: {", ".join(x for x, _ in offer)})'

    # ---------------------------------------------------------- комнаты
    def room_fight(self, fl, kind):
        g = self.g; t0 = g.t
        threat = self.threat_cell == (fl, self.col)
        if kind == 'Б1':
            if not self.t1: self.t1 = list(TIER1); g.rng.shuffle(self.t1)
            ed, tier = self.t1.pop(), 1
        elif kind == 'Б2':
            if not self.t2: self.t2 = list(TIER2); g.rng.shuffle(self.t2)
            ed, tier = self.t2.pop(), 2
        else:
            ed, tier = self.el.pop(), 'elite'
        loc = self.loc()
        res = g.fight(ed, tier, loc, threat)
        if not res['won']:
            self.stage(fl, kind, t0, f'{ed["name"]} ({loc["name"]}): ПОРАЖЕНИЕ за {res["rounds"]} р.')
            return False
        fmin = res['sec'] / 60
        rew = []
        tr = g.t
        if tier == 'elite':
            for k in 'MP':
                rew.append(self.legend(k))
            g.tick(T['legend'])
            for k in 'MP':
                rew.append(self.upgrade(k))
            g.tick(T['upgrade'])
        else:
            for k in 'MP':
                rew.append(self.upgrade(k))
            g.tick(T['upgrade'])
        self.stage(fl, kind, t0, f'{ed["name"]}' + (' [Угроза]' if threat else '') + f' в «{loc["name"]}»: победа за {res["rounds"]} р. '
                   f'(бой ~{fmin:.1f} мин, награда ~{(g.t - tr) / 60:.1f} мин); потери: Маг {res["hp_loss"]["M"]}, '
                   f'Жрец {res["hp_loss"]["P"]}. Награда: ' + '; '.join(rew))
        return True

    def room_rest(self, fl):
        g = self.g; t0 = g.t; g.tick(T['rest']); out = []
        choices = {}
        for k in 'MP':
            d = g.decide(f'Отдых {k}', f'Отдых, выбор {HERO_NAMES[k]}. {g.hs()}\n{self.deck_prompt(k)}\n'
                         'Варианты: лечение (6) / закалка (5→1) / дежурство (партнёр выбирает дважды) / фонарь (+3 масла)')
            choices[k] = d
        acts = []
        for k in 'MP':
            if choices[k] == 'дежурство':
                continue
            acts.append((k, choices[k]))
            if choices[ally(k)] == 'дежурство':
                d2 = g.decide(f'Отдых {k} (второй выбор)', f'Второй выбор {HERO_NAMES[k]} (партнёр на дежурстве). {g.hs()}')
                acts.append((k, d2))
        for k, c in acts:
            h = g.H[k]
            if c == 'лечение':
                o = h.hp; h.hp = min(h.maxhp, h.hp + REST_HEAL); out.append(f'{h.name} лечится {o}→{h.hp}')
            elif c == 'фонарь':
                o = g.oil; g.oil = min(6, g.oil + 3); out.append(f'{h.name} заправляет фонарь {o}→{g.oil}')
            elif c.startswith('закалка'):
                g.tick(T['forge']); out.append('закалка: ' + self.upgrade(k, 5, 'Закалка'))
            elif c.startswith('лечение2'):
                pass
        g.L('ОТДЫХ: ' + '; '.join(out))
        self.stage(fl, 'Отд', t0, 'Отдых: ' + '; '.join(out) + (' (дежурство)' if 'дежурство' in choices.values() else ''))

    def room_cache(self, fl):
        g = self.g; t0 = g.t; g.tick(T['cache'])
        if not self.caches: self.caches = list(CACHES); g.rng.shuffle(self.caches)
        name, np, oil, dmg = self.caches.pop()
        got = self.potion(np)
        o = g.oil; g.oil = min(6, g.oil + oil)
        for k in 'MP':
            if dmg:
                g.H[k].hp = max(1, g.H[k].hp - dmg)
        txt = f'Тайник «{name}»: зелья {got or "—"}' + (f', масло {o}→{g.oil}' if oil else '')
        g.L('ТАЙНИК: ' + txt)
        self.stage(fl, 'Тай', t0, txt)

    def room_event(self, fl):
        g = self.g; t0 = g.t; g.tick(T['event'])
        ev = self.events.pop()
        prompt = f'СОБЫТИЕ «{ev["name"]}»: {ev["text"]}\n' + '\n'.join(ev['opts']) + \
                 f'\n{g.hs()}; Ключей {g.keys}; {self.deck_prompt("M")}; {self.deck_prompt("P")}'
        d = g.decide('Событие', prompt + '\nФормат: буква[:герой M/P]')
        ch = d.split(':'); o = ch[0]; who = ch[1] if len(ch) > 1 else None
        res = ''
        e = ev['id']
        if e == 'watch':
            if o == 'а':
                g.oil = min(6, g.oil + 2); self.threat_cell = 'next'; res = f'+2 масла ({g.oil}), Угроза на следующую клетку'
            elif o == 'б':
                for k in 'MP': g.heal(k, 2)
                res = 'оба лечат 2'
            elif o == 'в':
                g.H[who].hp -= 3; res = f'{HERO_NAMES[who]} теряет 3; ' + self.upgrade(ally(who))
        elif e == 'keeper':
            if o == 'а':
                g.keys += 1; res = 'получен Ключ'
            else:
                res = f'зелье {self.potion(1)}'
        elif e == 'well':
            if o == 'а':
                for k in 'MP': g.H[k].hp -= 2
                self.boss_hp_mod -= 8; res = 'оба −2, След на Гасителе: −8 здоровья'
            else:
                res = 'ушли'
        elif e == 'trader':
            if o == 'а':
                g.oil -= 2; res = f'−2 масла ({g.oil}); ' + '; '.join(self.upgrade(k) for k in 'MP')
            elif o == 'б':
                g.H[who].hp -= 4; res = f'{HERO_NAMES[who]} −4, зелья {self.potion(2)}'
            elif o == 'в':
                res = self.legend(who)
            else:
                res = 'ушли'
        elif e == 'pilgrim':
            if o == 'а':
                p = ch[1]; g.potions.remove(p); g.oil = min(6, g.oil + 2); res = f'отдали зелье {p}, масло {g.oil}'
            elif o == 'б':
                g.oil -= 1; self.boss_oil_bonus += 2; res = f'−1 масло ({g.oil}), След: +2 масла в бою с Гасителем'
            else:
                res = 'прошли мимо'
        elif e == 'bridge':
            if o == 'а':
                rr = []
                for k in 'MP':
                    x = g.rng.randint(1, 6); rr.append(f'{HERO_NAMES[k]} d6={x}')
                    if x <= 2: g.H[k].hp -= 3
                res = 'порознь: ' + ', '.join(rr)
            elif o == 'б':
                g.H[who].hp -= 3; res = f'{HERO_NAMES[who]} держит верёвку, −3'
            else:
                res = f'Ключ: потайная дверь, зелье {self.potion(1)}'
        elif e == 'mirror':
            if o == 'а':
                rr = []
                for k in 'MP':
                    rr.append(self.upgrade(k, 1, 'Зеркало'))
                res = '; '.join(rr)
            else:
                res = 'ушли'
        elif e == 'sleeper':
            if o == 'а':
                g.oil -= 1; res = f'прокрались, масло {g.oil}'
            elif o == 'б':
                res = 'напали: ' + ('победа' if self.room_fight(fl, 'Б1') else 'поражение')
            else:
                x = g.rng.randint(1, 6)
                if x <= 3:
                    self.threat_cell = 'next'; res = f'd6={x}: Угроза на следующий бой'
                else:
                    g.keys += 1; res = f'd6={x}: Ключ'
        for k in 'MP':
            g.H[k].hp = max(1, g.H[k].hp)
        g.oil = max(0, g.oil)
        g.L(f'СОБЫТИЕ «{ev["name"]}»: {d} → {res}')
        self.stage(fl, 'Соб', t0, f'Событие «{ev["name"]}»: выбор {d} → {res}')

    # ---------------------------------------------------------- забег
    def run(self):
        g = self.g
        g.L(f'Сид тасовки: {g.seed}')
        g.tick(T['setup'])
        self.stage(0, 'Раскладка', 0, 'Раскладка: планшеты, колоды по 15, стопки врагов/локаций/событий, 4 этажа карты пути')
        for fl in range(12):
            t0 = g.t
            if fl == 0:
                allowed = [0, 1, 2]
            else:
                allowed = [c for c in (self.col - 1, self.col, self.col + 1) if 0 <= c <= 2]
            view = '\n'.join(f'  этаж {i + 1}: ' + ' | '.join(SCHEMA[i]) for i in range(fl, min(12, fl + 4)))
            d = g.decide('Путь', f'Этаж {fl + 1}. Допустимые столбцы {allowed} (0..2). Видно:\n{view}\n'
                         f'{g.hs()}; Ключей {g.keys}\n{self.deck_prompt("M")}\n{self.deck_prompt("P")}')
            self.col = int(d)
            if self.threat_cell == 'next':
                self.threat_cell = (fl + 1, self.col)
            g.tick(T['map'] + T['layout'])
            kind = SCHEMA[fl][self.col]
            g.L(f'\n===== ЭТАЖ {fl + 1}, столбец {self.col}: {kind} =====  (время {g.t / 60:.0f} мин)')
            if kind in ('Б1', 'Б2', 'Эл'):
                if not self.room_fight(fl + 1, kind):
                    return self.finish(False, fl + 1)
            elif kind == 'Отд':
                self.room_rest(fl + 1)
            elif kind == 'Тай':
                self.room_cache(fl + 1)
            elif kind == 'Соб':
                self.room_event(fl + 1)
            o = g.oil; g.oil = max(0, g.oil - 1)
            g.L(f'   Этаж пройден: масло {o} → {g.oil}' + ('  — ФОНАРЬ ПОГАС, ТЕМНОТА' if g.oil == 0 and o > 0 else ''))
            if g.stages and g.stages[-1]['floor'] == fl + 1:
                g.stages[-1]['min'] = (g.t - t0) / 60; g.stages[-1]['total'] = g.t / 60
                g.stages[-1]['state'] = g.hs()
        # босс
        t0 = g.t
        boss = dict(BOSS); boss['hp'] = BOSS['hp'] + self.boss_hp_mod
        g.oil = min(6, g.oil + self.boss_oil_bonus)
        g.L(f'\n===== БОСС: Гаситель (здоровье {boss["hp"]}, масло {g.oil}) =====  (время {g.t / 60:.0f} мин)')
        res = g.fight(boss, 'boss', dict(name='Сердце катакомб', feats=[('discard', 'bones', 'Сброс карты: 1 урон врагу.')]))
        self.stage(13, 'Босс', t0, f'Гаситель: {"ПОБЕДА" if res["won"] else "ПОРАЖЕНИЕ"} за {res["rounds"]} р.; потери Маг {res["hp_loss"]["M"]}, Жрец {res["hp_loss"]["P"]}')
        return self.finish(res['won'], 13)

    def finish(self, won, fl):
        g = self.g
        g.L(f'\nИТОГ ЗАБЕГА: {"ПОБЕДА" if won else "ПОРАЖЕНИЕ"} (этаж {fl}), время {g.t / 60:.0f} мин')
        return won


if __name__ == '__main__':
    path = sys.argv[1]
    R = Run(path)
    try:
        won = R.run()
    except NeedDecision:
        open(path + '.log.txt', 'w', encoding='utf-8').write('\n'.join(R.g.log))
        sys.exit(3)
    g = R.g
    open(path + '.log.txt', 'w', encoding='utf-8').write('\n'.join(g.log))
    json.dump(dict(stages=g.stages, stats=g.stats, won=won, total_min=g.t / 60,
                   decks={k: card_list(g.H[k]) for k in 'MP'}), open(path + '.result.json', 'w', encoding='utf-8'),
              ensure_ascii=False, indent=1)
    print('ГОТОВО', 'победа' if won else 'поражение', f'{g.t / 60:.0f} мин')
