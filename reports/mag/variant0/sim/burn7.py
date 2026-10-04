# -*- coding: utf-8 -*-
"""Тест билда №7: у мага меньше сжигания и появляется возврат сожжённых карт (Никита 2026-09-29).
Тексты — cards/mag/09. Поверх burn6 с числами теста №6 (cards/mag/08)."""
import json, os
import burn2
from burn2 import p
from burn import one
import burn6
from burn6 import B6Game, M_start as M_start6, M_bank as M_bank6, pools, CFG, START_P

DEFAULTS = dict(burn6.DEFAULTS)
DEFAULTS.update(json.load(open(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'fix6.json'))))
DEFAULTS.update({'ashes.base': 1,
                 # новое в тесте №7
                 'bonf.n': 1, 'bonf.cost': 0, 'common.n': 1, 'whirl.n': 1,
                 'pyre.n': 2, 'pyre.per': 3, 'pyre.cost': 1, 'ash2.d': 1, 'ash2.cost': 1,
                 'bone.sh': 3, 'hero.sh': 5, 'brush.ch': 2, 'ashsh.per': 2})

RESTORE = {'whisper', 'a_ash2', 'a_pyre', 'a_bone', 'a_hero', 'n_ashshield', 'n_embers', 'a_brush'}


def M_start():
    D = M_start6()
    for c in D:
        if c.cid == 'whisper':
            c.text = '0 маны. Возьми 1 карту ИЛИ верни 1 сожжённую карту в руку. Подношение: +1 мана.'
            c.opts = [('возьми 1', lambda g, h, o: (g.draw(h, 1), g.gain_mana(h, o))),
                      ('верни 1', lambda g, h, o: (g.restore(h), g.gain_mana(h, o)))]
        elif c.cid == 'bonfire':
            c.cost = p('bonf.cost', 0)
            c.text = f"{c.cost} маны. Сожги {p('bonf.n', 1)} карту из руки."
            c.opts = one(lambda g, h, o: g.burn(h, p('bonf.n', 1)))
    return D


def M_bank():
    U = M_bank6()
    by = {c.cid: c for c in U}
    def r(cid, text, opts=None, **kw):
        c = by[cid]; c.text = text
        if opts is not None:
            c.opts = opts
        for k, v in kw.items():
            setattr(c, k, v)
    F = '0 маны. Топливо. 1 щит себе. '
    r('a_ash2', '1 мана. Сожги 1 карту из руки. Верни в руку 1 карту, сожжённую раньше. Возьми 1 карту.',
      one(lambda g, h, o: g.burn_restore(h, 1, 1, p('ash2.d', 1))), cost=p('ash2.cost', 1))
    r('a_pyre', '1 мана. Сожги до 2 карт из руки, 3 щита себе за каждую. Верни в руку 1 карту, сожжённую раньше.',
      [(f'сжечь {k}', (lambda k: lambda g, h, o: g.pyre7(h, k))(k)) for k in range(1, p('pyre.n', 2) + 1)],
      cost=p('pyre.cost', 1))
    r('a_bone', F + 'Сожжена: верни в руку 1 другую сожжённую карту и получи 3 щита.',
      on_burn=lambda g: (g.restore('M', skip_last=True), g.shield('M', p('bone.sh', 3)), g.gain_mana('M', p('bone.mana', 0))))
    r('a_hero', F + 'Сожжена: верни в руку 1 другую сожжённую карту, союзник получает 5 щитов.',
      on_burn=lambda g: (g.restore('M', skip_last=True), g.shield('P', p('hero.sh', 5)), g.gain_mana('M', p('hero.mana', 0))))
    r('a_brush', F + 'Сожжена: ещё 2 заряда и верни в руку 1 другую сожжённую карту.',
      on_burn=lambda g: (g.add_charge(p('brush.ch', 2)), g.restore('M', skip_last=True), g.gain_mana('M', p('brush.mana', 0))))
    r('n_ashshield', '1 мана. 2 щита себе за каждую карту, сожжённую в этом раунде. Верни в руку 1 сожжённую карту.',
      one(lambda g, h, o: (g.shield(h, p('ashsh.per', 2) * g.burned_rnd), g.restore(h))))
    r('n_embers', '0 маны. Верни в руку 1 сожжённую карту. Сбрось любое число карт из руки. '
                  'В начале следующего раунда получи 2 заряда за каждую.',
      [(f'сбросить {k}', (lambda k: lambda g, h, o: (g.restore(h), g.embers(k)))(k)) for k in range(0, 5)])
    r('a_common', f"1 мана. Ты и союзник сжигаете до {p('common.n', 1)} карты из руки, берёте столько же и получаете по {p('common.sh', 1)} щиту.",
      [(f'сжечь {k}', (lambda k: lambda g, h, o: g.common2(k))(k)) for k in range(1, p('common.n', 1) + 1)])
    r('a_whirl', f"{p('whirl.cost', 0)} маны. Сожги {p('whirl.n', 1)} верхнюю карту своей колоды ИЛИ колоды союзника.",
      [('своей', lambda g, h, o: g.burn(h, p('whirl.n', 1), 'top')),
       ('союзника', lambda g, h, o: g.burn(h, p('whirl.n', 1), 'ally_top'))])
    return U


class B7Game(B6Game):
    def __init__(self, *a, **k):
        super().__init__(*a, **k)
        self.bstats.setdefault('restored', 0)

    def restore(self, hk='M', skip_last=False, before=None):
        """Вернуть в руку мага 1 сожжённую карту (самую ценную). skip_last — не саму сгоревшую карту;
        before — только из карт, сожжённых до розыгрыша."""
        m = self.H['M']
        pool = list(before) if before is not None else list(m.exiled)
        if skip_last and m.exiled:
            last = m.exiled[-1]; pool = [c for c in pool if c is not last]
        pool = [c for c in pool if any(c is x for x in m.exiled) and not any(c is x for x in getattr(self, 'phx', []))]
        if not pool:
            return 0
        c = max(pool, key=lambda x: x.value)
        m.exiled = [x for x in m.exiled if x is not c]; m.exiled_n = max(0, m.exiled_n - 1)
        if self.sim:
            m.pend += 1
        else:
            m.hand.append(c)
        self.bst('restored')
        self.L(f'      возвращена «{c.name}»')
        return 1

    def burn_restore(self, hk, nb, nr, nd):
        before = list(self.H['M'].exiled)
        self.burn(hk, nb)
        for _ in range(nr):
            if self.restore(hk, before=before):
                before = [c for c in before if any(c is x for x in self.H['M'].exiled)]
        self.draw(hk, nd)

    def pyre7(self, hk, k):
        before = list(self.H['M'].exiled)
        n = self.burn(hk, k)
        self.shield(hk, p('pyre.per', 3) * n)
        self.restore(hk, before=before)

    def clone_sim(self):
        g = super().clone_sim()
        g.__class__ = B7Game
        return g
