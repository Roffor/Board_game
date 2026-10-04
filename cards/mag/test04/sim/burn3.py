# -*- coding: utf-8 -*-
"""Тест билда №3: правки Никиты 2026-09-29 (cards/mag/04, 05): без ограничений на картах,
новые Отпустить духа / Жертва за друга / Уголь в очаг, Щит из пепла без Авангарда.
Поверх burn2.py. Числовые варианты прогона 2 — через P."""
import burn2
from burn2 import B2Game, M_start, M_bank as M_bank2, p, P
from burn import BCard, one
from cards import ally

REMOVED = {'n_sparks'}


def M_bank():
    U = [c for c in M_bank2() if c.cid not in REMOVED]
    by = {c.cid: c for c in U}
    def repl(cid, **kw):
        for k, v in kw.items():
            setattr(by[cid], k, v)
    repl('n_heat', cost=p('heat.cost', 2),
         text=f"{p('heat.cost', 2)} маны. Союзник может сжечь сколько угодно карт. 1 попадание по {p('heat.dmg', 2)} за каждую его сожжённую.",
         opts=one(lambda g, h, o: [g.hit(h, p('heat.dmg', 2)) for _ in range(p('heat.base', 0) + g.ally_burn(99))]))
    repl('n_last', cost=p('last.cost', 1),
         text=f"{p('last.cost', 1)} мана. Союзник может сжечь сколько угодно карт из руки и взять на {p('last.plus', 1)} больше.",
         opts=one(lambda g, h, o: g.draw('P', g.ally_burn(99) + p('last.plus', 1))))
    repl('a_spirits', cost=p('spirits.cost', 1),
         text=f"{p('spirits.cost', 1)} мана. 1 щит себе. До конца раунда каждое сжигание — попадание по {p('spirits.dmg', 1)}.")
    repl('a_return', cost=p('return.cost', 0),
         text=f"{p('return.cost', 0)} маны. Верни {p('ret.n', 1)} сожжённую карту себе в руку и {p('ret.n', 1)} союзнику.",
         opts=one(lambda g, h, o: [(g.return_one('M'), g.return_one('P')) for _ in range(p('ret.n', 1))]))
    repl('a_gift', text=f"1 мана. Союзник может сжечь любое число карт из руки и получает {p('gift.per', 2)} щита за каждую. Подношение: ты тоже.")
    repl('a_common', cost=p('common.cost', 1),
         text=f"1 мана. Ты и союзник сжигаете до {p('common.n', 2)} карт из руки, берёте столько же и получаете по {p('common.sh', 2)} щита.",
         opts=[(f'сжечь {k}', (lambda k: lambda g, h, o: g.common2(k))(k)) for k in range(1, p('common.n', 2) + 1)])
    repl('n_ashshield', text='1 мана. 1 щит себе за каждую карту, сожжённую в этом раунде.', tags=(),
         opts=one(lambda g, h, o: g.shield(h, p('ashsh.per', 1) * g.burned_rnd)))
    # --- три новые карты (cards/mag/05)
    ff = by['a_forfriend']
    ff.name = 'Жертва за друга'; ff.off = None; ff.offering = False; ff.cost = p('ff.cost', 1); ff.pr = 1.1
    ff.text = f"{p('ff.cost', 1)} мана. Сбрось любое число карт из руки. Союзник берёт столько же и ещё {p('ff.plus', 1)}."
    ff.opts = [(f'сбросить {k}', (lambda k: lambda g, h, o: g.draw('P', g.discard_own(k) + p('ff.plus', 1)))(k)) for k in range(0, 4)]
    U.append(BCard('n_release', 'Отпустить духа', 'связка',
                   f"0 маны. Сними 1 статус с врага или союзника. Если снял: {p('rel.ch', 2)} заряда подношения.",
                   [('снять Порчу', lambda g, h, o: g.release('porcha')),
                    ('снять Благословение', lambda g, h, o: g.release('bless'))],
                   cost=0, pr=p('rel.pr', 2.9), grp='curse'))
    coal = by['n_coal']
    coal.text = f"0 маны. Топливо. Сыграна: ничего. Сожжена: сожги {p('coal.disc', 2)} карты из своего сброса."
    coal.on_burn = lambda g: g.burn('M', p('coal.disc', 2), 'disc')
    return U


class B3Game(B2Game):
    def discard_own(self, n):
        m = self.H['M']; done = 0
        for _ in range(n):
            cands = [c for c in m.hand if not any(c is r for r in self.reserved)]
            if not cands:
                break
            c = min(cands, key=lambda x: x.value); m.hand.remove(c); m.disc.append(c); done += 1
        return done

    def common2(self, k):
        n = self.burn('M', k); self.draw('M', n)
        a = self.ally_burn(p('common.n', 2)); self.draw('P', a)
        self.shield('M', p('common.sh', 2)); self.shield('P', p('common.sh', 2))

    def release(self, what):
        ok = False
        if what == 'porcha' and self.E.porcha > 0:
            self.E.porcha = 0; ok = True
        elif what == 'bless':
            for k in 'MP':
                if self.H[k].blessed:
                    self.H[k].blessed = False; ok = True; break
        if ok:
            self.add_charge(p('rel.ch', 2)); self.bst('released')

    def return_one(self, k):
        h = self.H[k]
        if not h.exiled:
            return
        c = max(h.exiled, key=lambda x: x.value); h.exiled.remove(c)
        if self.sim:
            h.pend += 1
        else:
            h.hand.append(c)

    def gift(self, o):
        n = self.ally_burn(99)
        self.shield('P', n * p('gift.per', 2))
        if o:
            self.shield('M', n * o * p('gift.per', 2))

    def __init__(self, seed, mdeck, pdeck=None):
        super().__init__(seed, mdeck, pdeck)
        self.bstats['released'] = 0
        self.pyre_cap = 99

    def clone_sim(self):
        g = super().clone_sim()
        g.__class__ = B3Game
        return g
