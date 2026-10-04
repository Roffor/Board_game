# -*- coding: utf-8 -*-
"""Тест билда №8 (решения Никиты 2026-09-29):
- возврат берёт любую сожжённую карту, и мага, и союзника (карта возвращается владельцу в руку);
- бот выбирает возвращаемую карту из 3 самых ценных под текущий ход;
- Пепельный вихрь: сожги 1 верхнюю карту своей колоды и 1 верхнюю карту колоды союзника;
- топливо с возвратом (Кость предка, Прах героя, Сухой хворост) и Угли до утра убраны до выбора новых идей;
- партнёр без лечения на картах: лечение с карт превращается в щит той же силы [С 8.7];
- 4-я ситуация — босс; калибровка врагов: dmg_k (урон), cap (предел одного удара), hp.
Поверх burn7 с числами теста №7 (cards/mag/10)."""
import copy, json, os
import burn2
from burn2 import p
import burn7
from burn7 import B7Game, M_start, M_bank as M_bank7, CFG as CFG7
import cards as C

HERE = os.path.dirname(os.path.abspath(__file__))
DEFAULTS = dict(burn7.DEFAULTS)
DEFAULTS.update(json.load(open(os.path.join(HERE, 'fix7.json'))))

REMOVED = {'a_bone', 'a_hero', 'a_brush', 'n_embers'}   # ждут новых идей (cards/mag/11)

CFG = dict(CFG7)
CFG.update(el_dmg=1.7, el_cap=10, boss_hp=45, boss_dmg=1.3, boss_cap=19)   # калибровка 2026-09-29: элита 5,6 р / 28%, босс 7,2 р / 39%


def M_bank():
    U = [c for c in M_bank7() if c.cid not in REMOVED]
    for c in U:
        if c.cid == 'a_whirl':
            c.text = f"{p('whirl.cost', 0)} маны. Сожги 1 верхнюю карту своей колоды и 1 верхнюю карту колоды союзника."
            c.opts = [('', lambda g, h, o: (g.burn(h, 1, 'top'), g.burn(h, 1, 'ally_top')))]
    return U


def _scale(ed, k, cap):
    ed = copy.deepcopy(ed)
    def fix(acts):
        return [('atk', min(cap, max(1, round(a[1] * k))), a[2], a[3]) if a[0] == 'atk' else a for a in acts]
    for key in ('deck', 'cycle'):
        if ed.get(key):
            for it in ed[key]:
                it['acts'] = fix(it['acts'])
    return ed


def pools(cfg=None):
    import burn6
    cfg = cfg or CFG
    P = burn6.pools(cfg)
    P['EL'] = [_scale(e, cfg['el_dmg'], cfg['el_cap']) for e in P['EL']]
    b = _scale(C.BOSS, cfg['boss_dmg'], cfg['boss_cap']); b['hp'] = cfg['boss_hp']
    P['BOSS'] = [b]
    return P


class B8Game(B7Game):
    def __init__(self, *a, **k):
        super().__init__(*a, **k)
        self.in_card = False
        self.bstats.setdefault('restored_ally', 0)

    # --- лечение с карт превращается в щит той же силы
    def play(self, hk, card, opt, want_off):
        prev = self.in_card; self.in_card = True
        try:
            return super().play(hk, card, opt, want_off)
        finally:
            self.in_card = prev

    def heal(self, h, n):
        if self.in_card:
            return self.shield(h, n)
        return super().heal(h, n)

    # --- возврат любой сожжённой карты, выбор под текущий ход
    def _danger(self, k):
        e = self.E; it = getattr(e, 'intent', None) if e else None
        if not it:
            return False
        dmg = sum(a[1] * a[3] for a in it['acts'] if a[0] == 'atk')
        return dmg > self.H[k].shield

    def _rscore(self, k, c):
        s = c.value
        if k == 'M' and getattr(c, 'cost', 0) <= self.H['M'].mana:
            s += 2
        if self._danger(k) and c.kind == 'защита':
            s += 3
        if not self._danger(k) and c.kind == 'атака':
            s += 2
        return s

    def restore(self, hk='M', skip_last=False, before=None):
        phx = getattr(self, 'phx', [])
        pool = []
        for k in 'MP':
            h = self.H[k]
            src = [c for c in (before[k] if before is not None else h.exiled)]
            if skip_last and k == 'M' and h.exiled:
                last = h.exiled[-1]; src = [c for c in src if c is not last]
            pool += [(k, c) for c in src if any(c is x for x in h.exiled) and not any(c is x for x in phx)]
        if not pool:
            return 0
        top = sorted(pool, key=lambda kc: -kc[1].value)[:3]
        k, c = max(top, key=lambda kc: self._rscore(*kc))
        h = self.H[k]
        h.exiled = [x for x in h.exiled if x is not c]
        if k == 'M':
            h.exiled_n = max(0, h.exiled_n - 1)
        if self.sim:
            h.pend += 1
        else:
            h.hand.append(c)
        self.bst('restored')
        if k == 'P':
            self.bst('restored_ally')
        self.L(f'      возвращена «{c.name}» ({k})')
        return 1

    def _snap(self):
        return {k: list(self.H[k].exiled) for k in 'MP'}

    def burn_restore(self, hk, nb, nr, nd):
        before = self._snap()
        self.burn(hk, nb)
        for _ in range(nr):
            self.restore(hk, before=before)
        self.draw(hk, nd)

    def pyre7(self, hk, k):
        before = self._snap()
        n = self.burn(hk, k)
        self.shield(hk, p('pyre.per', 3) * n)
        self.restore(hk, before=before)

    def clone_sim(self):
        g = super().clone_sim()
        g.__class__ = B8Game
        return g
