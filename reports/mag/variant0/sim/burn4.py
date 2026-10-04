# -*- coding: utf-8 -*-
"""Тест билда №4: принятые числовые правки теста №3 и пять новых карт (cards/mag/06, выбор Никиты 2026-09-29).
Поверх burn3.py. Числовые варианты — через P (burn2.P)."""
import burn2
from burn2 import p
from burn3 import B3Game, M_start, M_bank as M_bank3
from burn import BCard, one

# принятые правки (значения по умолчанию для теста №4)
DEFAULTS = {'spirits.cap': 99, 'heat.dmg': 1, 'common.sh': 0, 'blood.cost': 0, 'spirits.cost': 0}
REMOVED = {'a_forfriend', 'n_release', 'a_return', 'n_coal', 'n_last'}


def has(c, word):
    return word in c.text


def M_bank():
    U = [c for c in M_bank3() if c.cid not in REMOVED]
    by = {c.cid: c for c in U}
    pyre = by['a_pyre']
    pyre.text = '2 маны. Сожги сколько угодно карт из руки. 1 щит себе за каждую.'
    pyre.opts = [(f'сжечь {k}', (lambda k: lambda g, h, o: g.shield(h, g.burn(h, k)))(k)) for k in range(1, 6)]
    def add(*a, **k):
        c = BCard(*a, **k); U.append(c); return c
    add('n_embers', 'Угли до утра', 'двигатель',
        f"{p('emb.cost', 1)} мана. Сбрось любое число карт из руки. В начале следующего раунда получи {p('emb.per', 1)} заряд за каждую.",
        [(f'сбросить {k}', (lambda k: lambda g, h, o: g.embers(k))(k)) for k in range(0, 5)],
        cost=p('emb.cost', 1), pr=3.8, grp='whisper')
    add('n_deal', 'Сделка с духами', 'связка',
        f"{p('deal.cost', 0)} маны. Сними 1 статус с врага или героя. Если снял: следующее Подношение в этом раунде срабатывает дважды.",
        [('снять Порчу', lambda g, h, o: g.deal_spirits('porcha')),
         ('снять Благословение', lambda g, h, o: g.deal_spirits('bless'))],
        cost=p('deal.cost', 0), pr=2.9, grp='curse')
    add('n_alien', 'Чужое пламя', 'связка',
        f"{p('alien.cost', 1)} мана. Союзник может сжечь 1 карту из руки. Если на ней есть урон — {p('alien.n', 4)} урона врагу. "
        f"Если есть щит — {p('alien.n', 4)} щита союзнику. Если нет ни того, ни другого — возьми {p('alien.draw', 2)} карты.",
        [('атаку', lambda g, h, o: g.alien('урон')), ('защиту', lambda g, h, o: g.alien('щит')),
         ('другую', lambda g, h, o: g.alien(None))],
        cost=p('alien.cost', 1), pr=1.2, grp='hearth')
    ph = add('n_phoenix', 'Феникс', 'двигатель',
             f"{p('phx.cost', 0)} маны. {p('phx.dmg', 1)} урон. Сожги эту карту. Когда эта карта сгорает, в начале следующего раунда она возвращается тебе в руку.",
             one(lambda g, h, o: (g.hit(h, p('phx.dmg', 1)), g.phoenix_self())), cost=p('phx.cost', 0), pr=1.15, value=1, grp='whisper')
    ph.on_burn = lambda g, c=ph: g.phx_mark(c)
    add('n_rag', 'Масляная тряпка', 'топливо',
        '0 маны. Топливо. Сыграна: ничего. Сожжена: 1 урон за каждый заряд подношения, который у тебя сейчас есть.',
        one(lambda g, h, o: None), cost=0, value=2, grp='fuel',
        on_burn=lambda g: g.hit('M', p('rag.per', 1) * g.charges) if g.charges else None)
    return U


class B4Game(B3Game):
    def __init__(self, seed, mdeck, pdeck=None):
        super().__init__(seed, mdeck, pdeck)
        self.next_ch = 0; self.double_next = 0; self.phx = []; self.phx_play = None
        self.bstats.update(embers=0, deal=0, alien=0, phx_ret=0)

    # Угли до утра
    def embers(self, k):
        n = self.discard_own(k)
        self.next_ch += n * p('emb.per', 1)
        if self.sim:
            self.H['M'].pend += n        # в планировании заряды следующего раунда ценятся как добор
        self.bst('embers', n)

    # Сделка с духами
    def deal_spirits(self, what):
        ok = False
        if what == 'porcha' and self.E.porcha > 0:
            self.E.porcha = 0; ok = True
        elif what == 'bless':
            for k in 'MP':
                if self.H[k].blessed:
                    self.H[k].blessed = False; ok = True; break
        if ok:
            self.double_next = p('deal.n', 1); self.bst('deal')

    # Чужое пламя
    def alien(self, want):
        pz = self.H['P']
        if not pz.alive:
            return
        cands = [c for c in pz.hand if not any(c is r for r in self.reserved)]
        if want == 'урон':
            cands = [c for c in cands if has(c, 'урон')]
        elif want == 'щит':
            cands = [c for c in cands if has(c, 'щит')]
        else:
            cands = [c for c in cands if not has(c, 'урон') and not has(c, 'щит')]
        if not cands:
            return
        c = min(cands, key=lambda x: x.value)
        pz.hand.remove(c); pz.exiled.append(c)
        self.charges += 1; self.burned_rnd += 1; self.ally_burned_rnd += 1; self.bst('ally_burn'); self.bst('alien')
        if self.pyre_on:
            self.hit('M', p('spirits.dmg', 1))
        n = p('alien.n', 4)
        if has(c, 'урон'):
            self.hit('M', n)
        if has(c, 'щит'):
            self.shield('P', n)
        if not has(c, 'урон') and not has(c, 'щит'):
            self.draw('M', p('alien.draw', 2))

    # Феникс
    def phx_mark(self, c):
        self.phx.append(c)
        if self.sim:
            self.H['M'].pend += 1            # вернётся в следующем раунде: не считать потерей карты

    def phoenix_self(self):
        self.phx_play = True

    def play(self, hk, card, opt, want_off):
        dbl = hk == 'M' and self.double_next and getattr(card, 'off', None) and want_off
        m = self.H['M']
        if dbl:
            save = m.legend; m.legend = 'Двойное подношение'; ch0 = self.charges
        ok = super().play(hk, card, opt, want_off)
        if dbl:
            m.legend = save
            if ok and self.charges < ch0:
                self.double_next -= 1
        if ok and self.phx_play:
            self.phx_play = None
            if any(c is card for c in m.disc):
                m.disc = [c for c in m.disc if c is not card]; m.exiled.append(card); m.exiled_n += 1
                self.charges += 1; self.burned_rnd += 1; self.bst('burned')
                if self.pyre_on:
                    self.hit('M', p('spirits.dmg', 1))
                self.phx_mark(card)
        return ok

    def hero_phase(self):
        m = self.H['M']
        for c in self.phx:
            if any(x is c for x in m.exiled):
                m.exiled = [x for x in m.exiled if x is not c]; m.hand.append(c); self.bst('phx_ret')
        self.phx = []; self.double_next = 0
        if self.next_ch:
            self.charges = self.next_ch; self.keep = True
        self.next_ch = 0
        super().hero_phase()

    def fight(self, *a, **k):
        self.next_ch = 0; self.phx = []; self.double_next = 0
        return super().fight(*a, **k)

    def clone_sim(self):
        g = super().clone_sim()
        g.__class__ = B4Game
        g.phx = list(self.phx)
        return g
