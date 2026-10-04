# -*- coding: utf-8 -*-
"""Три билда мага (сжигание, Проклинатель, Медиум) — черновик v1, cards/mag/12. Поверх burn8.
Порядок в общей фазе: карты Медиума с тегом 'after' разыгрываются после карт союзника."""
import burn2
from burn2 import p
from burn import BCard, one
import burn8
from burn8 import B8Game, M_start as M_start8, M_bank as M_bank8, pools, CFG
from cards import ally

DEFAULTS = dict(burn8.DEFAULTS)
DEFAULTS.update({'echo0.b': 2, 'echo0.x': 3,           # Отголосок: 2 (−1 стартовая) / +3
                 'last.cost': 2, 'last.k': 1,           # Последнее пламя
                 'rot.n': 2, 'rot.cost': 1,              # Гниль
                 'rip.k': 3, 'rip.cost': 1,              # Разрыв проклятия
                 'wave.cost': 2,                         # Чёрная волна
                 'toad.d': 2, 'whisp.n': 3, 'cshield.k': 2,
                 'uni.b': 2, 'uni.x': 3, 'shoulder.sh': 3, 'retal.b': 1, 'echo.cost': 1,
                 'curse2.n': 2, 'hunt.x': 1, 'hunt.cost': 0, 'cshield.b': 0, 'toad.cost': 1})
# итерация 2 → 3 (запуск 2): принятые числа
DEFAULTS.update({'echo0.x': 1, 'rot.cost': 2, 'hunt.cost': 1, 'wrath.per': 3, 'last.cost': 1, 'retal.b': 2,
                 'shoulder.sh': 4, 'rag.b': 3, 'cshield.b': 3, 'rip.k': 4, 'pyre.per': 5, 'wave.cost': 1,
                 'toad.cost': 2, 'toad.d': 3,
                 'whisp.cost': 1, 'evil.cost': 0, 'mark.cost': 1, 'ans.b': 3, 'ans.per': 2})
# итерация 4 (запуск 4) → принятые числа по новой полосе +1,5…+2,5
DEFAULTS.update({'wave.cost': 2, 'echo.cost': 0, 'whisp.cost': 2, 'whisp.n': 4, 'evil.dr': 1})

# запуск 5: калибровка врагов под мага с 3/3/5 случайными апгрейдами (решение «б»)
CFG.update(sh0={'I': 4, 'II': 4}, rank_hp={'I': 20, 'II': 20}, r2_dmg=1.5, r2_cap=6,
           elite_hp=40, el_dmg=1.9, el_cap=10, boss_hp=58, boss_dmg=1.5, boss_cap=19)

KEEP = {'n_phoenix', 'a_ash2', 'a_pyre', 'n_rag', 'a_wrath', 'a_rite',                  # С
        'a_sacshield', 'n_shield2', 'a_spirit',                                            # М
        'a_blood', 'a_tar', 'a_ember', 'n_hands', 'n_alien', 'n_answer', 'n_mark'}         # мостики
BUILD = {}   # cid -> строка билдов, для отчёта


def M_start():
    D = [c for c in M_start8() if c.cid != 'whirl']
    D.append(BCard('echo0', 'Отголосок', 'атака',
                   '1 мана. 1 урон. Если союзник в этом раунде уже нанёс урон — 2 урона.',
                   one(lambda g, h, o: g.hit(h, p('echo0.b', 2) + (p('echo0.x', 3) if g.ally_hits_rnd else 0))),
                   cost=1, value=5, tags=('after',), cat='С'))
    assert len(D) == 15
    return D


def M_bank():
    U = [c for c in M_bank8() if c.cid in KEEP]
    def add(cid, name, kind, text, opts, grp, build, **k):
        c = BCard(cid, name, kind, text, opts, grp=grp, **k); U.append(c); BUILD[cid] = build; return c
    # --- сжигание
    add('x_last', 'Последнее пламя', 'атака', '1 мана. Урон, равный числу карт, сожжённых в этом бою (твоих и союзника).',
        one(lambda g, h, o: g.hit(h, p('last.k', 1) * (len(g.H['M'].exiled) + len(g.H['P'].exiled)))),
        'flame', 'С', cost=p('last.cost', 2), value=6)
    # --- Проклинатель
    add('x_rot', 'Гниль', 'связка', '2 маны. 2 Порчи. В конце этого раунда Порча на враге не снимается.',
        one(lambda g, h, o: (g.porcha(p('rot.n', 2)), g.set_rot())), 'curse', 'П', cost=p('rot.cost', 1), tags=('porcha',), value=6)
    add('x_rip', 'Разрыв проклятия', 'атака', '1 мана. Убери всю Порчу с врага: 4 урона за каждую убранную (одним ударом).',
        one(lambda g, h, o: g.rip()), 'spark', 'П', cost=p('rip.cost', 1), value=6, tags=('late',))
    add('x_wave', 'Чёрная волна', 'связка', '1 мана. 1 Порча, затем удвой Порчу на враге.',
        one(lambda g, h, o: (g.porcha(1), g.porcha(g.E.porcha))), 'ward', 'П', cost=p('wave.cost', 2), tags=('porcha2',), value=6)
    add('x_evil', 'Сглаз', 'связка', '0 маны. 1 Порча. Сбрось 1 карту из руки, возьми 1 карту.',
        one(lambda g, h, o: (g.porcha(1), g.discard_own(1), g.draw(h, p('evil.dr', 1)) if p('evil.dr', 1) else None)), 'whisper', 'П', cost=p('evil.cost', 0), tags=('porcha',), value=5)
    add('x_toad', 'Жабий яд', 'атака', '2 маны. 1 Порча, затем 3 урона.',
        one(lambda g, h, o: (g.porcha(1), g.hit(h, p('toad.d', 2)) if p('toad.d', 2) else None)), 'spark', 'П', cost=p('toad.cost', 1), tags=('porcha',), value=6)
    add('x_whisp', 'Шёпот проклятий', 'атака', '1 мана. 3 попадания по 1.',
        one(lambda g, h, o: [g.hit(h, 1) for _ in range(p('whisp.n', 3))]), 'swarm', 'П', cost=p('whisp.cost', 1), value=6)
    add('x_cshield', 'Проклятый щит', 'защита', '1 мана. 3 щита себе и ещё 2 за каждую Порчу на враге.',
        one(lambda g, h, o: g.shield(h, p('cshield.b', 0) + p('cshield.k', 2) * g.E.porcha)), 'ward', 'П', cost=1, value=5)
    # --- Медиум
    add('x_echo', 'Эхо', 'связка', '1 мана. Повтори эффект любой карты, сыгранной союзником в этом раунде (как будто он сыграл её ещё раз).',
        one(lambda g, h, o: g.echo()), 'echo0', 'М', cost=p('echo.cost', 1), tags=('after',), value=6)
    add('x_retal', 'Ответный огонь', 'атака', '1 мана. 2 урона и ещё урон, равный урону, который союзник получил в прошлом раунде.',
        one(lambda g, h, o: g.hit(h, p('retal.b', 1) + g.p_taken_last)), 'spark', 'М', cost=1, value=5)
    add('x_uni', 'Удар в унисон', 'атака', '1 мана. 2 урона. Если союзник в этом раунде уже нанёс урон — ещё 3 урона.',
        one(lambda g, h, o: g.hit(h, p('uni.b', 2) + (p('uni.x', 3) if g.ally_hits_rnd else 0))), 'echo0', 'М', cost=1, tags=('after',), value=6)
    add('x_shoulder', 'Плечом к плечу', 'защита', '1 мана. 4 щита себе. Если союзник в этом раунде получил щит или взял Авангард — ещё 4 щита ему.',
        one(lambda g, h, o: (g.shield(h, p('shoulder.sh', 3)),
                             g.shield('P', p('shoulder.sh', 3)) if (g.ally_shielded_rnd or g.H['P'].vanguard) else None)),
        'ward', 'М', cost=1, tags=('after',), value=5)
    # --- мостики П–М
    add('x_curse2', 'Проклятие на двоих', 'связка', '1 мана. Следующее попадание союзника в этом раунде вешает на врага 2 Порчи.',
        one(lambda g, h, o: g.set_curse_next(p('curse2.n', 2))), 'ward', 'П–М', cost=1, tags=('porcha',), value=5)
    add('x_hunt', 'Метка охотника', 'связка', '1 мана. 1 Порча. Если союзник в прошлом раунде нанёс урон — ещё 1 Порча.',
        one(lambda g, h, o: g.porcha(1 + (p('hunt.x', 1) if g.ally_hits_last else 0))), 'curse', 'П–М', cost=p('hunt.cost', 0), tags=('porcha',), value=5)
    for cid, b in {'n_phoenix': 'С', 'a_ash2': 'С', 'a_pyre': 'С', 'n_rag': 'С', 'a_wrath': 'С', 'a_greedy': 'С',
                   'a_sacshield': 'М', 'n_shield2': 'М', 'a_rite': 'С', 'a_spirit': 'М', 'a_blood': 'С–П', 'a_tar': 'С–П',
                   'a_ember': 'С–П', 'n_hands': 'С–М', 'n_alien': 'С–М', 'n_answer': 'С–М', 'n_mark': 'П–М'}.items():
        BUILD[cid] = b
    for c in U:
        if c.cid == 'n_mark':
            c.cost = p('mark.cost', 1)
        if c.cid == 'n_answer':
            c.opts = one(lambda g, h, o: g.hit(h, p('ans.b', 3) + p('ans.per', 2) * g.ally_burned_rnd))
    return U


class B9Game(B8Game):
    def __init__(self, *a, **k):
        super().__init__(*a, **k)
        self.ally_hits_rnd = 0; self.ally_hits_last = 0; self.ally_shielded_rnd = 0
        self.p_taken_last = 0; self._p_mark = 0; self.rot = False; self.rot_val = 0; self.curse_next = 0
        for k2 in ('rot', 'rip', 'echo', 'curse2'):
            self.bstats.setdefault(k2, 0)

    @staticmethod
    def prio(a):
        if a[0] == 'play' and a[1] == 'M':
            t = a[2].tags
            if 'after' in t: return 4.6
            if 'late' in t: return 4.7
        return B8Game.prio(a)

    def hero_phase(self):
        if not self.sim:
            self.ally_hits_last = self.ally_hits_rnd
            t = self.taken['P']; self.p_taken_last = t - self._p_mark; self._p_mark = t
            if self.rot_val and self.E:
                self.E.porcha += self.rot_val
            self.rot_val = 0; self.rot = False
            self.ally_hits_rnd = 0; self.ally_shielded_rnd = 0; self.curse_next = 0; self.p_plays_rnd = []
        super().hero_phase()

    def end_hero_phase(self):
        super().end_hero_phase()
        if self.rot and not self.sim:
            self.rot_val = self.E.porcha

    def hit(self, h, n, pierce=False):
        if h == 'P' and n > 0:
            self.ally_hits_rnd += 1
        super().hit(h, n, pierce)
        if h == 'P' and self.curse_next:
            self.porcha(self.curse_next); self.curse_next = 0; self.bst('curse2')

    def shield(self, h, n):
        if h == 'P' and n:
            self.ally_shielded_rnd += 1
        return super().shield(h, n)

    def play(self, hk, card, opt, want_off):
        ok = super().play(hk, card, opt, want_off)
        if ok and hk == 'P':
            self.p_plays_rnd = getattr(self, 'p_plays_rnd', []) + [(card, opt)]
        return ok

    def set_rot(self):
        self.rot = True; self.bst('rot')

    def set_curse_next(self, n):
        self.curse_next = n

    def rip(self):
        n = self.E.porcha
        if n <= 0:
            return
        self.E.porcha = 0; self.bst('rip')
        self.hit('M', p('rip.k', 3) * n)

    def echo(self):
        pl = getattr(self, 'p_plays_rnd', [])
        if not pl:
            return
        card, opt = max(pl, key=lambda co: co[0].value)
        self.bst('echo')
        card.opts[opt][1](self, 'P', 0)

    def clone_sim(self):
        g = super().clone_sim()
        g.__class__ = B9Game
        return g


def pools(cfg=None):
    """Как burn8, плюс урон рядовых II яруса ×r2_dmg (удар ≤ r2_cap, [С 3.6]: ≤1/3 здоровья героя)."""
    from burn8 import _scale
    cfg = cfg or CFG
    P = burn8.pools(cfg)
    k = cfg.get('r2_dmg', 1.0)
    if k != 1.0:
        P['II'] = [_scale(e, k, cfg.get('r2_cap', 6)) for e in P['II']]
    return P
