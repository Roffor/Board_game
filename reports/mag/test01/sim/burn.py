# -*- coding: utf-8 -*-
"""Правило сжигания и зарядов подношения (cards/mag/02-sozhzhenie-idei.md, версия 3) поверх движка теста №1.
Эффект карты: fn(g, h, o), o — сколько раз оплачено Подношение (с Двойным подношением — вдвое)."""
import engine as E
from engine import Game, Hero
from cards import Card, ally, P_cards
import cards as C


class BCard(Card):
    def __init__(self, cid, name, kind, text, opts, cost=0, off=None, on_burn=None, pr=3, value=5,
                 tags=(), branch='Сжигание', grp=None, cat='А'):
        super().__init__(cid, name, 'M', kind, text, opts, cost=cost, offering=off is not None,
                         value=value, tags=tags, branch=branch)
        self.off = off            # None | '1' | '2' (стоит 2 заряда) | 'r' (сколько угодно раз)
        self.on_burn = on_burn    # fn(g) — эффект топлива
        self.pr = pr              # порядок в плане
        self.grp = grp; self.cat = cat


def one(fn):
    return [('', fn)]


# ---------------------------------------------------------------- стартовая колода под новое правило
def M_start():
    D = []
    def add(n, *a, **k):
        for _ in range(n):
            D.append(BCard(*a, **k))
    add(2, 'spark', 'Искра очага', 'атака', '1 мана. 2 урона. Подношение: +2 урона.',
        one(lambda g, h, o: g.hit(h, 2 + 2 * o)), cost=1, off='1', value=6, cat='С')
    add(1, 'swarm', 'Пепельный рой', 'атака', '1 мана. 2 попадания по 1.',
        one(lambda g, h, o: [g.hit(h, 1) for _ in range(2)]), cost=1, value=4, cat='С')
    add(1, 'whirl', 'Огненный вихрь', 'атака', '2 маны. 3 урона ИЛИ 1 урон и 3 щита себе.',
        [('3 урона', lambda g, h, o: g.hit(h, 3)),
         ('1 урон + 3 щита', lambda g, h, o: (g.hit(h, 1), g.shield(h, 3)))], cost=2, value=6, cat='С')
    add(1, 'flashs', 'Вспышка жертвы', 'атака', '1 мана. 1 урон. Сожги 1 карту из руки.',
        one(lambda g, h, o: (g.hit(h, 1), g.burn(h, 1))), cost=1, pr=1.2, value=5, tags=('burner',), cat='С')
    add(2, 'ward', 'Оберег', 'защита', '1 мана. 2 щита себе ИЛИ союзнику. Подношение: обоим.',
        [('себе', lambda g, h, o: (g.shield(h, 2), g.shield(ally(h), 2) if o else None)),
         ('союзнику', lambda g, h, o: (g.shield(ally(h), 2), g.shield(h, 2) if o else None))],
        cost=1, off='1', value=5, cat='С')
    add(1, 'mguard', 'Страж порога', 'защита', '1 мана. Авангард. 4 щита себе.',
        one(lambda g, h, o: (g.vanguard(h), g.shield(h, 4))), cost=1, value=5, tags=('vanguard',), cat='С')
    add(1, 'ashward', 'Пепельный оберег', 'топливо', '0 маны. 1 щит себе. Сожжена: 3 щита союзнику.',
        one(lambda g, h, o: g.shield(h, 1)), cost=0, on_burn=lambda g: g.shield('P', 3), value=2, cat='С')
    add(1, 'bonfire', 'Большой костёр', 'двигатель', '1 мана. Сожги 2 карты из руки.',
        one(lambda g, h, o: g.burn(h, 2)), cost=1, pr=1.2, value=5, tags=('burner',), cat='С')
    add(1, 'whisper', 'Шёпот костра', 'двигатель', '0 маны. Возьми 1 карту. Подношение: +1 мана.',
        one(lambda g, h, o: (g.draw(h, 1), g.gain_mana(h, o))), cost=0, off='1', pr=2, value=3,
        tags=('draw',), cat='С')
    add(1, 'fuel', 'Топливо', 'топливо', '0 маны. 1 щит себе. Сожжено: +1 мана.',
        one(lambda g, h, o: g.shield(h, 1)), cost=0, on_burn=lambda g: g.gain_mana('M', 1), value=2, cat='С')
    add(1, 'curse', 'Порча', 'связка', '1 мана. 1 Порча ИЛИ 3 щита союзнику.',
        [('1 Порча', lambda g, h, o: g.porcha(1)),
         ('3 щита союзнику', lambda g, h, o: g.shield(ally(h), 3))], cost=1, pr=1, value=5, tags=('porcha',), cat='С')
    add(1, 'altar', 'Жертвенник', 'связка', '1 мана. 1 Порча. Подношение: возьми 2 карты.',
        one(lambda g, h, o: (g.porcha(1), g.draw(h, 2 * o))), cost=1, off='1', pr=1.3, value=5,
        tags=('porcha', 'draw'), cat='С')
    add(1, 'flame', 'Пламя предков', 'визитка', '2 маны. 2 попадания по 2. Подношение (сколько угодно): +1 попадание по 2.',
        one(lambda g, h, o: [g.hit(h, 2) for _ in range(2 + o)]), cost=2, off='r', value=8, cat='С')
    assert len(D) == 15
    return D


# ---------------------------------------------------------------- апгрейды банка (А)
# grp — какую стартовую карту заменяет апгрейд при тесте (замена по роли)
def M_bank():
    U = []
    def add(*a, **k):
        U.append(BCard(*a, **k))
    # сжигатели → вместо «Вспышки жертвы»
    add('a_ash2', 'Искра в пепел', 'двигатель', '0 маны. Сожги 1 карту из руки, возьми 2 карты.',
        one(lambda g, h, o: (g.burn(h, 1), g.draw(h, 2))), cost=0, pr=1.2, tags=('burner', 'draw'), grp='flashs')
    add('a_dig', 'Раскопать пепел', 'двигатель', '1 мана. Сожги до 2 карт из своего сброса. 1 щит себе.',
        one(lambda g, h, o: (g.burn(h, 2, 'disc'), g.shield(h, 1))), cost=1, pr=1.2, tags=('burner',), grp='flashs')
    add('a_delay', 'Отложенный костёр', 'двигатель', '0 маны. В начале следующего раунда, после добора, сожги до 2 карт из руки.',
        one(lambda g, h, o: g.set_delay(2)), cost=0, pr=1.2, grp='flashs')
    add('a_whirl', 'Пепельный вихрь', 'двигатель', '1 мана. Сожги 2 верхние карты своей колоды ИЛИ колоды союзника.',
        [('своей', lambda g, h, o: g.burn(h, 2, 'top')),
         ('союзника', lambda g, h, o: g.burn(h, 2, 'ally_top'))], cost=1, pr=1.2, tags=('burner',), grp='flashs')
    add('a_common', 'Общий костёр', 'двигатель', '1 мана. Сожги 1 карту из своей руки и 1 из руки союзника. Союзник берёт 1 карту и получает 1 щит.',
        one(lambda g, h, o: (g.burn(h, 1), g.burn(h, 1, 'ally_hand'), g.draw(ally(h), 1), g.shield(ally(h), 1))),
        cost=1, pr=1.2, tags=('burner',), grp='flashs')
    add('a_forfriend', 'Жертва за друга', 'связка', '1 мана. Союзник сбрасывает 1 карту и берёт 2.',
        one(lambda g, h, o: g.ally_discard_draw(1, 2)), cost=1, pr=1.1, grp='flashs')
    add('a_pyre', 'Погребальный костёр', 'двигатель', '2 маны. Сожги до 3 карт из руки. 1 щит себе за каждую.',
        one(lambda g, h, o: g.shield(h, g.burn(h, 3))), cost=2, pr=1.2, tags=('burner',), grp='flashs')
    add('a_greedy', 'Жадный огонь', 'двигатель', '2 маны. Сожги всю остальную руку. Возьми столько, сколько сжёг, минус 1.',
        one(lambda g, h, o: g.draw(h, max(0, g.burn(h, 99) - 1))), cost=2, pr=1.2, tags=('burner', 'draw'), grp='flashs')
    # топливо → вместо «Топлива»
    fuel = lambda cid, name, txt, fn: add(cid, name, 'топливо', '0 маны. 1 щит себе. Сожжена: ' + txt,
                                          one(lambda g, h, o: g.shield(h, 1)), cost=0, on_burn=fn, value=2, grp='fuel')
    fuel('a_brush', 'Сухой хворост', 'ещё 1 заряд и 1 щит себе.', lambda g: (g.add_charge(1), g.shield('M', 1)))
    fuel('a_bone', 'Кость предка', 'возьми 2 карты и 1 щит себе.', lambda g: (g.draw('M', 2), g.shield('M', 1)))
    fuel('a_tar', 'Смола', '1 Порча и 1 урон.', lambda g: (g.porcha(1), g.hit('M', 1)))
    fuel('a_ember', 'Тлеющий уголь', '3 попадания по 1.', lambda g: [g.hit('M', 1) for _ in range(3)])
    fuel('a_hero', 'Прах героя', 'союзник берёт 2 карты и получает 1 щит.', lambda g: (g.draw('P', 2), g.shield('P', 1)))
    fuel('a_palm', 'Уголёк в ладони', 'следующее попадание союзника в этом раунде +3.', lambda g: g.ally_bonus(3))
    # траты: атаки → вместо «Пепельного роя», защита → вместо «Оберега», связки → вместо «Порчи»
    add('a_rite', 'Обряд предков', 'атака', '2 маны. 4 урона и 2 щита себе. Подношение 2: ещё 3 урона, весь урон сквозь щит.',
        one(lambda g, h, o: (g.hit(h, 4 + (3 if o else 0) + (3 if o >= 2 else 0), pierce=bool(o)), g.shield(h, 2))),
        cost=2, off='2', grp='swarm')
    add('a_wrath', 'Гнев предков', 'атака', '0 маны. 2 щита себе. Подношение (сколько угодно): 3 урона.',
        one(lambda g, h, o: (g.shield(h, 2), g.hit(h, 3 * o) if o else None)), cost=0, off='r', grp='swarm')
    add('a_ashes', 'Пепел к пеплу', 'атака', '1 мана. 3 урона. Подношение (сколько угодно): попадание по 2.',
        one(lambda g, h, o: (g.hit(h, 3), [g.hit(h, 2) for _ in range(o)])), cost=1, off='r', grp='swarm')
    add('a_blood', 'Кровь на алтаре', 'связка', '1 мана. 1 Порча и 2 щита себе. Подношение: +1 Порча.',
        one(lambda g, h, o: (g.porcha(1 + o), g.shield(h, 2))), cost=1, off='1', pr=1.3, tags=('porcha',), grp='curse')
    add('a_spirit', 'Дух-хранитель', 'защита', '1 мана. 4 щита себе ИЛИ союзнику, 1 щит другому. Подношение: +3 щита другому.',
        [('себе', lambda g, h, o: (g.shield(h, 4), g.shield(ally(h), 1 + 3 * o))),
         ('союзнику', lambda g, h, o: (g.shield(ally(h), 4), g.shield(h, 1 + 3 * o)))], cost=1, off='1', grp='ward')
    add('a_gift', 'Дар огня', 'связка', '1 мана. Союзник берёт 1 карту и 3 щита. Подношение (сколько угодно): ещё 1 карту и 1 щит.',
        one(lambda g, h, o: (g.draw(ally(h), 1 + o), g.shield(ally(h), 3 + o))), cost=1, off='r', pr=2, grp='curse')
    add('a_blade', 'Угли на клинке', 'связка', '1 мана. Следующее попадание союзника +3. Подношение (сколько угодно): +2 к нему.',
        one(lambda g, h, o: g.ally_bonus(3 + 2 * o)), cost=1, off='r', pr=1.4, grp='curse')
    add('a_sacshield', 'Жертвенный щит', 'защита', '1 мана. Союзник получает Авангард и 4 щита. Подношение: +3 щита ему.',
        one(lambda g, h, o: (g.vanguard(ally(h)), g.shield(ally(h), 4 + 3 * o))), cost=1, off='1', grp='ward')
    # правила и реакции → вместо «Шёпота костра»
    add('a_spirits', 'Костёр духов', 'двигатель', '1 мана. 1 щит себе. До конца раунда каждое сжигание — попадание по 1 (не больше 3).',
        one(lambda g, h, o: (g.shield(h, 1), g.set_pyre())), cost=1, pr=0.5, grp='whisper')
    add('a_answer', 'Духи отвечают', 'двигатель', '1 мана. +1 заряд за каждую карту, сожжённую в этом раунде до этой (не больше 3).',
        one(lambda g, h, o: g.add_charge(min(3, g.burned_rnd))), cost=1, pr=1.25, grp='whisper')
    add('a_keeper', 'Хранитель углей', 'защита', '1 мана. 2 щита себе. Заряды не сгорают в конце этого раунда.',
        one(lambda g, h, o: (g.shield(h, 2), g.set_keep())), cost=1, pr=3.5, grp='whisper')
    add('a_return', 'Возврат из пепла', 'двигатель', '1 мана. Верни 1 сожжённую карту (свою или союзника) в руку владельца. +1 заряд.',
        one(lambda g, h, o: (g.return_burned(), g.add_charge(1))), cost=1, pr=1.25, tags=('draw',), grp='whisper')
    add('a_debt', 'Кровный долг', 'двигатель', '0 маны. +1 заряд; +2, если союзник в этом раунде получал урон или сбрасывал карту.',
        one(lambda g, h, o: g.add_charge(2 if (g.H['P'].discarded or g.lost_rnd) else 1)), cost=0, pr=1.25, grp='whisper')
    add('a_ritual', 'Ритуал на двоих', 'двигатель', '1 мана. Сожги 1 карту из руки. Если союзник уже сыграл карту в этом раунде, сожги ещё 1 и возьми 1.',
        one(lambda g, h, o: g.ritual()), cost=1, pr=4.5, tags=('burner', 'draw'), grp='whisper')
    return U


def no_heal_priest(deck):
    """Лечения на картах нет (решение Никиты): у Жреца лечение заменено тем же числом щита."""
    for c in deck:
        if c.cid == 'healc':
            c.text = '3 щита себе или союзнику. Вера 4+: 5 щита.'
            c.opts = [('себе', lambda g, h, o: g.shield(h, 5 if C.f4(g) else 3)),
                      ('союзнику', lambda g, h, o: g.shield(ally(h), 5 if C.f4(g) else 3))]
        if c.cid == 'bless':
            c.opts = [c.opts[0], ('2 щита союзнику', lambda g, h, o: g.shield(ally(h), 2))]
        if c.cid == 'u_gbless':
            c.opts = [('', lambda g, h, o: (g.bless(ally(h)), g.shield(ally(h), 5 if C.f4(g) else 3)))]
        if c.cid == 'u_hlight':
            c.opts = [('4 щита союзнику', lambda g, h, o: g.shield(ally(h), 4))]
        if c.cid == 'u_mheal':
            c.opts = [('всё союзнику', lambda g, h, o: g.shield(ally(h), 2 * g.burn_faith()))]
    return deck


class BGame(Game):
    def __init__(self, seed, mdeck, pdeck=None):
        super().__init__(seed, [])
        self.H['M'] = Hero('M', mdeck)
        self.H['P'] = Hero('P', no_heal_priest(pdeck or P_cards()))
        self.charges = 0; self.burned_rnd = 0; self.pyre = 0; self.keep = False; self.delay = 0
        self.bonus = 0; self.lost_rnd = False; self.pyre_on = False; self.delay_next = 0
        self.bstats = dict(burned=0, spent=0, free=0, burned_ally=0)

    def clone_sim(self):
        g = BGame.__new__(BGame)
        g.__dict__ = dict(self.__dict__)
        g.sim = True
        g.H = {k: h.clone() for k, h in self.H.items()}
        for h in g.H.values():
            h.draw = list(h.draw)   # сжигание верха колоды в планировании не должно трогать настоящую колоду
        g.E = self.E.clone()
        g.potions = list(self.potions); g.feat_used = list(self.feat_used)
        g.fdisc_round = list(self.fdisc_round); g.reserved = list(self.reserved)
        g.stats = None; g.bstats = None
        return g

    def fight(self, *a, **k):
        self.charges = 0; self.keep = False; self.delay_next = 0
        return super().fight(*a, **k)

    def bst(self, k, n=1):
        if not self.sim and self.bstats is not None:
            self.bstats[k] += n

    # ---------- операции нового правила
    def add_charge(self, n):
        self.charges += n

    def _fuel_rank(self, c):
        # топливо жгут первым, потом самые слабые карты
        return (0 if getattr(c, 'on_burn', None) else 1, c.value)

    def burn(self, hk, n, src='hand'):
        """Сжигает до n карт, возвращает сколько сожжено. Каждая даёт заряд магу."""
        m = self.H['M']; done = 0
        for _ in range(n):
            if src == 'hand':
                cands = [c for c in m.hand if not any(c is r for r in self.reserved)]
                if not cands:
                    break
                c = min(cands, key=self._fuel_rank); m.hand.remove(c); m.exiled.append(c)
            elif src == 'disc':
                if not m.disc:
                    break
                c = min(m.disc, key=self._fuel_rank); m.disc.remove(c); m.exiled.append(c)
            elif src == 'top':
                if not m.draw:
                    break
                c = m.draw.pop(); m.exiled.append(c)
            elif src == 'ally_top':
                p = self.H['P']
                if not p.draw:
                    break
                c = p.draw.pop(); p.exiled.append(c); self.bst('burned_ally')
            elif src == 'ally_hand':
                p = self.H['P']
                cands = [c for c in p.hand if not any(c is r for r in self.reserved)]
                if not cands:
                    break
                c = min(cands, key=lambda x: x.value); p.hand.remove(c); p.exiled.append(c); self.bst('burned_ally')
            done += 1; self.charges += 1; self.burned_rnd += 1; self.bst('burned')
            m.exiled_n += 1
            self.L(f'      сожжена «{c.name}» → заряд ({self.charges})')
            if src in ('hand', 'disc', 'top') and getattr(c, 'on_burn', None):
                c.on_burn(self)
            if self.pyre < 3 and self.pyre_on:
                self.pyre += 1; self.hit('M', 1)
        return done

    def set_pyre(self):
        self.pyre_on = True

    def set_keep(self):
        self.keep = True

    def set_delay(self, n):
        self.delay_next = n

    def ally_bonus(self, n):
        self.bonus += n

    def ally_discard_draw(self, nd, ndraw):
        p = self.H['P']
        cands = [c for c in p.hand if not any(c is r for r in self.reserved)]
        if cands:
            c = min(cands, key=lambda x: x.value); p.hand.remove(c); p.disc.append(c); p.discarded = True
            m = self.H['M']
            if not m.free_given:
                m.free_off = True; m.free_given = True
        self.draw('P', ndraw)

    def return_burned(self):
        best = None
        for k in 'MP':
            for c in self.H[k].exiled:
                if best is None or c.value > best[1].value:
                    best = (k, c)
        if best:
            k, c = best; self.H[k].exiled.remove(c)
            if self.sim:
                self.H[k].pend += 1
            else:
                self.H[k].hand.append(c)

    def ritual(self):
        self.burn('M', 1)
        if self.H['P'].plays > 0:
            self.burn('M', 1); self.draw('M', 1)

    def hit(self, h, n, pierce=False):
        if h == 'P' and self.bonus and n > 0:
            n += self.bonus; self.bonus = 0
        if pierce:
            s = self.E.shield; self.E.shield = 0
            super().hit(h, n)
            self.E.shield = s
        else:
            super().hit(h, n)

    def deal(self, k, n, src='удар'):
        hp0 = self.H[k].hp
        super().deal(k, n, src)
        if k == 'P' and self.H[k].hp < hp0:
            self.lost_rnd = True

    # ---------- розыгрыш
    def play(self, hk, card, opt, want_off):
        if hk == 'P':
            return super().play(hk, card, opt, 0)
        h = self.H['M']
        if not h.alive or not any(c is card for c in h.hand):
            return False
        if h.mana < card.cost:
            return False
        h.hand.remove(card)
        self.reserved = [r for r in self.reserved if r is not card]
        h.mana -= card.cost; h.plays += 1
        o = 0
        if card.off:
            price = 2 if card.off == '2' else 1
            for _ in range(want_off):
                if price == 1 and h.free_off:
                    h.free_off = False; o += 1; self.bst('free')
                elif self.charges >= price:
                    self.charges -= price; o += 1; self.bst('spent', price)
                else:
                    break
            if o and h.legend == 'Двойное подношение':
                o *= 2
        if not self.sim:
            self.L(f'   Маг: «{card.name}»' + (f' ({card.opts[opt][0]})' if card.opts[opt][0] else '') +
                   (f' [Подношение ×{o}]' if o else ''))
            self.fplays['M'].append(card.name)
            self.cardplays[card.name] = self.cardplays.get(card.name, 0) + 1
            self.tick(E.T['card'] + (E.T['choice'] if len(card.opts) > 1 else 0) + (E.T['offering'] if o else 0))
        card.opts[opt][1](self, 'M', o)
        h.disc.append(card)
        return True

    def gen_mage(self):
        h = self.H['M']
        if not h.alive:
            return [[]]
        hand = h.hand; out = []
        bonus = sum(1 for c in hand if c.cid in ('fuel', 'whisper'))
        def rec(i, mana, cur):
            if i == len(hand):
                out.append(list(cur)); return
            rec(i + 1, mana, cur)
            c = hand[i]
            if c.cost <= mana:
                pays = {None: (0,), '1': (0, 1), '2': (0, 1), 'r': (0, 1, 2, 3)}[getattr(c, 'off', None)]
                for oi in range(len(c.opts)):
                    for p in pays:
                        cur.append(('play', 'M', c, oi, p))
                        rec(i + 1, mana - c.cost, cur)
                        cur.pop()
        rec(0, h.mana + bonus, [])
        return out

    @staticmethod
    def prio(a):
        if a[0] == 'play' and a[1] == 'M':
            return getattr(a[2], 'pr', 3)
        return Game.prio(a)

    def evaluate(self, base, seq):
        s = super().evaluate(base, seq)
        # super() уже вычитает 0,6 за изгнанную карту; сожжённая карта теряется на бой — оставляем 0,3
        return s + 0.3 * 0  # (штраф 0,6 из движка оставлен как цена сужения колоды)

    def hero_phase(self):
        if self.rnd > 25 and not self.sim:
            # защита от бесконечного боя: считаем поражением и отмечаем
            self.stuck = True
            for k in 'MP':
                self.H[k].alive = False; self.H[k].hp = 0
            return
        if not self.keep:
            self.charges = 0
        self.keep = False
        self.burned_rnd = 0; self.pyre = 0; self.pyre_on = False; self.bonus = 0
        self.lost_rnd = False
        if getattr(self, 'delay_next', 0):
            n = self.delay_next; self.delay_next = 0
            m = self.H['M']
            k = min(n, max(0, len(m.hand) - 3))
            self.burn('M', k)
        super().hero_phase()


def P_start():
    return P_cards()
