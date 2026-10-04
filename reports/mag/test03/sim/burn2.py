# -*- coding: utf-8 -*-
"""Тест билда №2: новое «Берёт» (заряд за карту, сожжённую союзником), правки Никиты 2026-09-29,
13 новых карт из cards/mag/03-szhiganie-soyuznikom.md. Поверх burn.py (тест билда №1).
Числовые варианты для прогона 2 задаются через P (словарь параметров карт)."""
from burn import BCard, BGame, one, M_start as M_start1, M_bank as M_bank1
from cards import ally

# параметры карт, которые прогон 2 меняет на ±шаг
P = {}


def p(key, default):
    return P.get(key, default)


def M_start():
    D = [c for c in M_start1() if c.cid != 'flashs']
    D.append(BCard('hearth', 'Общий очаг', 'двигатель',
                   '1 мана. Ты и союзник можете сжечь по 1 карте из руки. Каждый, кто сжёг, берёт 1 карту.',
                   one(lambda g, h, o: (g.draw(h, g.burn(h, 1)), g.draw('P', g.ally_burn(1)))),
                   cost=1, pr=1.2, value=5, tags=('burner', 'draw'), cat='С'))
    assert len(D) == 15
    return D


REMOVED = {'a_dig', 'a_keeper', 'a_answer', 'a_ritual', 'a_delay'}
REGRP = {'flashs': 'bonfire'}   # Вспышки жертвы больше нет в стартовой колоде


def M_bank():
    U = []
    for c in M_bank1():
        if c.cid in REMOVED:
            continue
        c.grp = REGRP.get(c.grp, c.grp)
        U.append(c)
    by = {c.cid: c for c in U}
    def repl(cid, **kw):
        c = by[cid]
        for k, v in kw.items():
            setattr(c, k, v)
    # --- правки Никиты
    repl('a_ash2', cost=p('ash2.cost', 1), text=f"{p('ash2.cost', 1)} мана. Сожги 1 карту из руки, возьми {p('ash2.draw', 2)} карты.",
         opts=one(lambda g, h, o: (g.burn(h, 1), g.draw(h, p('ash2.draw', 2)))))
    repl('a_tar', text='0 маны. Сыграна: ничего. Сожжена: 1 Порча.', opts=one(lambda g, h, o: None),
         on_burn=lambda g: g.porcha(p('tar.porcha', 1)))
    repl('a_blood', text='1 мана. Подношение (сколько угодно раз): 1 Порча.', cost=p('blood.cost', 1),
         opts=one(lambda g, h, o: g.porcha(p('blood.per', 1) * o)))
    repl('a_wrath', text=f"0 маны. Подношение (сколько угодно раз): {p('wrath.per', 3)} урона.",
         opts=one(lambda g, h, o: g.hit(h, p('wrath.per', 3) * o) if o else None))
    repl('a_gift', grp='hearth', off='1', pr=1.15, cost=p('gift.cost', 1),
         text='1 мана. Союзник может сжечь любое число карт из руки и получает 1 щит за каждую. Подношение: ты тоже 1 щит за каждую.',
         opts=one(lambda g, h, o: g.gift(o)))
    repl('a_forfriend', grp='curse', off=p('ff.off', '2'), pr=4.8, cost=p('ff.cost', 1),
         text='1 мана. Без основного эффекта. Подношение 2: повтори эффект последней карты, разыгранной союзником в этом раунде.',
         opts=one(lambda g, h, o: g.copy_last(o)))
    repl('a_common', grp='hearth',
         text='1 мана. Сожги 1 карту из руки; союзник сжигает 1 карту из своей руки, берёт 1 карту и получает 1 щит.',
         cost=p('common.cost', 1),
         opts=one(lambda g, h, o: (g.burn(h, 1), g.draw('P', g.ally_burn(p('common.ally', 1))), g.shield('P', p('common.sh', 1)))))
    repl('a_debt', text='0 маны. +1 заряд; +2, если союзник в этом раунде получал урон или сжигал карту.',
         opts=one(lambda g, h, o: g.add_charge(2 if (g.ally_burned_rnd or g.lost_rnd) else 1)))
    repl('a_ashes', text=f"1 мана. {p('ashes.base', 3)} урона. Подношение (сколько угодно раз): попадание по {p('ashes.per', 2)}.",
         opts=one(lambda g, h, o: (g.hit(h, p('ashes.base', 3)), [g.hit(h, p('ashes.per', 2)) for _ in range(o)])))
    repl('a_spirits', cost=p('spirits.cost', 1))
    repl('a_return', cost=p('return.cost', 1),
         opts=one(lambda g, h, o: (g.return_burned(), g.add_charge(p('return.ch', 1)))))
    # --- 13 новых карт
    def add(*a, **k):
        U.append(BCard(*a, **k))
    add('n_swap', 'Обмен углями', 'двигатель', '0 маны. Союзник может сжечь 1 карту из руки и взять 1. Ты берёшь 1 карту.',
        one(lambda g, h, o: (g.draw('P', g.ally_burn(1)), g.draw(h, 1))), cost=0, pr=1.2, tags=('draw',), grp='hearth')
    add('n_hands', 'Костёр в его руках', 'связка', '1 мана. Союзник может сжечь 1 карту из руки; если сжёг, его следующее попадание +3.',
        one(lambda g, h, o: g.ally_bonus(3) if g.ally_burn(1) else None), cost=1, pr=1.2, grp='hearth')
    add('n_last', 'Последний дар', 'двигатель', '1 мана. Союзник может сжечь всю руку и взять на 1 карту меньше.',
        one(lambda g, h, o: g.draw('P', max(0, g.ally_burn(99) - p('last.minus', 1)))), cost=p('last.cost', 1), pr=1.2, grp='hearth')
    add('n_chain', 'Цепной костёр', 'двигатель', '1 мана. Сожги 1 карту из руки. Если это было топливо, союзник может сжечь 1 карту из руки и взять 1.',
        one(lambda g, h, o: g.chain()), cost=1, pr=1.2, tags=('burner',), grp='bonfire')
    add('n_mark', 'Огненная метка', 'связка', '1 мана. 1 Порча. Если союзник в этом раунде сжигал карту: ещё 1 Порча.',
        one(lambda g, h, o: g.porcha(1 + (1 if g.ally_burned_rnd else 0))), cost=1, pr=1.3, tags=('porcha',), grp='curse')
    add('n_ashshield', 'Щит из пепла', 'защита', '1 мана. Авангард. 1 щит себе за каждую карту, сожжённую в этом раунде (не больше 5).',
        one(lambda g, h, o: (g.vanguard(h), g.shield(h, min(5, g.burned_rnd)))), cost=1, pr=3.5, tags=('vanguard',), grp='ward')
    add('n_answer', 'Пламя в ответ', 'атака', '1 мана. 2 урона, +1 за каждую карту, сожжённую союзником в этом раунде.',
        one(lambda g, h, o: g.hit(h, 2 + g.ally_burned_rnd)), cost=1, pr=3.2, grp='swarm')
    add('n_heat', 'Жар общего костра', 'атака', '2 маны. Союзник может сжечь до 3 карт. 2 попадания по 2, +1 попадание по 2 за каждую его сожжённую.',
        one(lambda g, h, o: [g.hit(h, p('heat.dmg', 2)) for _ in range(2 + g.ally_burn(p('heat.max', 3)))]), cost=p('heat.cost', 2), pr=3, grp='whirl')
    add('n_armor', 'Пепельная броня', 'защита', '1 мана. 2 щита себе. Союзник может сжечь 1 карту; если сжёг, вы оба получаете по 3 щита.',
        one(lambda g, h, o: (g.shield(h, 2), (g.shield(h, 3), g.shield('P', 3)) if g.ally_burn(1) else None)),
        cost=1, pr=3, grp='ward')
    add('n_coal', 'Уголь в очаг', 'топливо', '0 маны. Сыграна: ничего. Сожжена: союзник может сжечь 1 карту и взять 1.',
        one(lambda g, h, o: None), cost=0, on_burn=lambda g: g.draw('P', g.ally_burn(p('coal.n', 1))), value=2, grp='fuel')
    add('n_sparks', 'Искры на двоих', 'связка', '0 маны. Подношение (сколько угодно раз): следующее попадание союзника +2.',
        one(lambda g, h, o: g.ally_bonus(p('sparks.per', 2) * o)), cost=0, off='r', pr=1.4, grp='curse')
    add('n_shield2', 'Щит для двоих', 'защита', '0 маны. Подношение (сколько угодно раз): 2 щита союзнику.',
        one(lambda g, h, o: g.shield('P', 2 * o)), cost=0, off='r', grp='ward')
    return U


class B2Game(BGame):
    def __init__(self, seed, mdeck, pdeck=None):
        super().__init__(seed, mdeck, pdeck)
        self.ally_burned_rnd = 0; self.last_p = None
        self.bstats['ally_burn'] = 0
        self.pyre_cap = p('spirits.cap', 3); self.pyre_dmg = p('spirits.dmg', 1)

    # старое «Берёт» (сброс союзника → бесплатное Подношение) отключено
    def do_fdisc(self, hk):
        m = self.H['M']; fo, fg = m.free_off, m.free_given
        r = super().do_fdisc(hk)
        m.free_off, m.free_given = fo, fg
        return r

    def ally_burn(self, n):
        """Союзник сжигает до n карт из руки (не из плана). Новое «Берёт»: магу заряд за каждую."""
        pz = self.H['P']; done = 0
        if not pz.alive:
            return 0
        for _ in range(n):
            cands = [c for c in pz.hand if not any(c is r for r in self.reserved)]
            if not cands:
                break
            c = min(cands, key=lambda x: x.value); pz.hand.remove(c); pz.exiled.append(c)
            done += 1; self.charges += 1; self.burned_rnd += 1; self.ally_burned_rnd += 1
            self.bst('ally_burn')
            self.L(f'      союзник сжигает «{c.name}» → магу заряд ({self.charges})')
            if self.pyre < p('spirits.cap', 3) and self.pyre_on:
                self.pyre += 1; self.hit('M', p('spirits.dmg', 1))
        return done

    def gift(self, o):
        n = self.ally_burn(99)
        self.shield('P', n * p('gift.per', 1))
        if o:
            self.shield('M', n * o * p('gift.per', 1))

    def copy_last(self, o):
        if o and self.last_p:
            c, opt = self.last_p
            c.opts[opt][1](self, 'M', 0)

    def chain(self):
        m = self.H['M']
        cands = [c for c in m.hand if not any(c is r for r in self.reserved)]
        fuel = cands and getattr(min(cands, key=self._fuel_rank), 'on_burn', None)
        self.burn('M', 1)
        if fuel:
            self.draw('P', self.ally_burn(1))

    def play(self, hk, card, opt, want_off):
        ok = super().play(hk, card, opt, want_off)
        if ok and hk == 'P':
            self.last_p = (card, opt)
        return ok

    def clone_sim(self):
        g = super().clone_sim()
        g.__class__ = B2Game
        return g

    def hero_phase(self):
        self.ally_burned_rnd = 0; self.last_p = None
        super().hero_phase()
