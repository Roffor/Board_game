# -*- coding: utf-8 -*-
"""Длинный тест мага (серия №10): поверх burn9.
- эталоны: стартовая карта + бюджет апгрейда (+3): e_dmg (Искра +3 урона), e_sh (Оберег +3 щита);
- смелые идеи (cards/mag/16): Рок, Отложенное заклинание, Резонанс и др.;
- подсказки бота о ценности будущего: перенос Порчи (Гниль), отложенный урон."""
import burn2
from burn2 import p
from burn import BCard, one
import burn9
from burn9 import B9Game, M_start, M_bank as M_bank9, CFG, pools

DEFAULTS = dict(burn9.DEFAULTS)
DEFAULTS.update({'doom.k': 3, 'doom.cost': 1, 'delay.d': 7, 'delay.cost': 1, 'reso.cost': 1,
                 'fut.rot': 1.5, 'fut.delay': 0.9})
BUILD = burn9.BUILD
BOLD = {'n_phoenix', 'x_last', 'x_rot', 'x_rip', 'x_wave', 'x_echo', 'x_retal', 'x_curse2'}
ETALON = {'e_dmg', 'e_sh'}
# сложность: 1 — одно действие; 2 — условие или выбор; 3 — отложенный эффект, счёт по игре, связка с союзником
CX = {}
NEW = {}   # cid -> функция, создающая карту (для добавления смелых идей по итерациям)


def M_bank(extra=None):
    U = M_bank9()
    def add(cid, name, kind, text, opts, grp, build, cx, bold=True, **k):
        c = BCard(cid, name, kind, text, opts, grp=grp, **k); U.append(c); BUILD[cid] = build; CX[cid] = cx
        if bold:
            BOLD.add(cid)
        return c
    # эталоны: не входят в банк случайных апгрейдов базы
    add('e_dmg', 'Эталон: Искра +3', 'атака', '1 мана. 5 урона. Подношение: +2 урона.',
        one(lambda g, h, o: g.hit(h, 5 + 2 * o)), 'spark', 'эталон', 1, bold=False, cost=1, off='1', value=7)
    add('e_sh', 'Эталон: Оберег +3', 'защита', '1 мана. 5 щитов себе ИЛИ союзнику. Подношение: обоим.',
        [('себе', lambda g, h, o: (g.shield('M', 5), g.shield('P', 5) if o else None)),
         ('союзнику', lambda g, h, o: (g.shield('P', 5), g.shield('M', 5) if o else None))],
        'ward', 'эталон', 1, bold=False, cost=1, off='1', value=7)
    # --- смелые идеи, итерация 1 (ресёрч cards/mag/16)
    add('x_doom', 'Рок', 'связка', '1 мана. 1 Порча. Затем, если Порча на враге ×3 не меньше его здоровья, враг погибает.',
        one(lambda g, h, o: g.doom()), 'curse', 'П', 2, cost=p('doom.cost', 2), tags=('late',), value=6)
    add('x_delay', 'Отложенное заклинание', 'атака', '1 мана. Положи на стол. В начале следующего раунда: 7 урона.',
        one(lambda g, h, o: g.add_delay(p('delay.d', 7))), 'spark', 'С–М', 3, cost=p('delay.cost', 1), value=6)
    add('x_reso', 'Резонанс', 'связка', '1 мана. Следующее попадание союзника в этом раунде наносит двойной урон.',
        one(lambda g, h, o: g.set_mult()), 'echo0', 'М', 2, cost=p('reso.cost', 2), tags=('porcha',), value=6)
    for f in (extra or []):
        f(add)
    for c in U:
        CX.setdefault(c.cid, 2 if c.cid in BOLD else 1)
    return U


# сложность карт серии №9 (ручная оценка)
CX.update({'n_phoenix': 3, 'a_ash2': 2, 'a_pyre': 2, 'n_rag': 2, 'a_wrath': 2, 'a_rite': 2, 'x_last': 3,
           'a_blood': 2, 'a_tar': 2, 'a_ember': 2, 'x_rot': 3, 'x_rip': 2, 'x_wave': 2, 'x_evil': 2, 'x_toad': 1,
           'x_whisp': 1, 'x_cshield': 2, 'x_echo': 3, 'x_retal': 2, 'x_uni': 2, 'x_shoulder': 2, 'a_sacshield': 1,
           'n_shield2': 1, 'a_spirit': 2, 'n_hands': 3, 'n_alien': 3, 'n_answer': 2, 'n_mark': 2, 'x_curse2': 3,
           'x_hunt': 2})


class B10Game(B9Game):
    def __init__(self, *a, **k):
        super().__init__(*a, **k)
        self.delay_dmg = 0; self.delay_now = 0; self.mult_next = False
        for k2 in ('doom', 'delay', 'reso'):
            self.bstats.setdefault(k2, 0)

    def hero_phase(self):
        if not self.sim:
            self.mult_next = False
            if self.delay_dmg and self.E and self.E.hp > 0:
                d = self.delay_dmg; self.delay_dmg = 0
                self.hit('M', d); self.bst('delay')
        super().hero_phase()

    def hit(self, h, n, pierce=False):
        if h == 'P' and self.mult_next and n > 0:
            n = 2 * n + self.E.porcha; self.mult_next = False
            if not self.sim:
                self.bst('reso')
        super().hit(h, n, pierce)

    def end_hero_phase(self):
        self.rot_cap = self.E.porcha if (self.rot and self.E) else 0
        super().end_hero_phase()

    def doom(self):
        e = self.E
        self.porcha(1)
        if e.hp > 0 and e.porcha * p('doom.k', 3) >= e.hp:
            self.bst('doom')
            s = e.shield; e.shield = 0
            B9Game.hit(self, 'M', e.hp)
            e.shield = s

    def add_delay(self, n):
        self.delay_dmg += n

    def set_mult(self):
        self.mult_next = True

    def evaluate(self, base, seq):
        s = super().evaluate(base, seq)
        # подсказки «ценности будущего» [ответ Никиты 17]: оцениваем по состоянию после плана
        g = self._last_eval
        if g is not None:
            k = 1.0 + 2.2 * self.E.threat / max(1, self.E.maxhp)
            if g.rot and g.E.hp > 0:
                s += p('fut.rot', 1.5) * getattr(g, 'rot_cap', 0)
            if g.delay_dmg > base.delay_dmg and g.E.hp > 0:
                s += p('fut.delay', 0.9) * k * (g.delay_dmg - base.delay_dmg)
        return s

    def clone_sim(self):
        g = super().clone_sim()
        g.__class__ = B10Game
        return g


# evaluate движка создаёт клон внутри; перехватываем его, чтобы подсказки видели состояние после плана
_orig_clone = B10Game.clone_sim
def _clone_track(self):
    g = _orig_clone(self)
    B10Game._last_eval = g
    return g
B10Game.clone_sim = _clone_track
B10Game._last_eval = None


# ---- бот: планы мага, где есть карты «от союзника», оцениваются вместе с планами Жреца
# (раньше их отсекал отбор 18 лучших планов мага, посчитанных без союзника — так Проклятие на двоих почти не игралось)
ALLY = {'x_reso', 'x_curse2', 'x_doom', 'x_echo', 'x_uni', 'x_shoulder'}
from engine import plan_key


def _best_plan(self, base=None, K=18):
    base = base or self
    mp = self.gen_mage(); pp = self.gen_priest()
    def top(plans, extra=0):
        sc = []
        self.ignore_stone = bool(self.E.traits.get('golem'))
        for pl in plans:
            seq = sorted(pl, key=self.prio)
            sc.append((self.evaluate(base, seq), len(sc), pl))
        self.ignore_stone = False
        sc.sort(key=lambda x: (-x[0], x[1]))
        out = [x[2] for x in sc[:K]]
        if extra:
            more = [x[2] for x in sc[K:] if any(a[0] == 'play' and a[2].cid in ALLY for a in x[2])]
            out += more[:extra]
        return out
    tm, tp = top(mp, extra=6), top(pp)
    dv = [()]
    for hk in 'MP':
        if self.feat_available(hk) is not None and self.H[hk].hand:
            dv = dv + [d + (hk,) for d in dv]
    best = (-1e9, []); ranked = {}
    for m in tm:
        for pl in tp:
            for d in dv:
                seq = sorted(m + pl + [('fdisc', hk) for hk in d], key=self.prio)
                s = self.evaluate(base, seq)
                if s > best[0] + 1e-9:
                    best = (s, seq)
                key = plan_key(seq)
                if key not in ranked or s > ranked[key][0]:
                    ranked[key] = (s, seq)
    self.ranked = sorted(ranked.values(), key=lambda x: -x[0])
    return best


B10Game.best_plan = _best_plan
