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
# итерация 1 → 2: принятые числа (сила в % эталона при весе потерь 4,5)
DEFAULTS.update({'rot.cost': 1, 'rot.n': 1, 'phx.dmg': 1, 'shoulder.sh': 5, 'last.k': 2, 'whisp.n': 6, 'rip.k': 6,
                 'blood5.cost': 0, 'hunt.cost': 0, 'rite.d': 7, 'ash2.d': 3, 'pyre.per': 7, 'hands.b': 9})
# итерация 2 → 3 (объединение итераций 1–2, pool11.py)
DEFAULTS.update({'sac.sh': 6, 'retal.b': 6, 'ans.b': 6, 'uni.b': 3, 'mark.cost': 0, 'ember.n': 7, 'evil.n': 2, 'toad.cost': 1,
                 'wrath.per': 5, 'rag.b': 7, 'tar.porcha': 2, 'wave.cost': 1, 'cshield.b': 8, 'doom.k': 4, 'doom.n': 2, 'delay.d': 8})
# итерация 3 → 4 (якорь — объединённый эталон 5,15; см. журнал)
DEFAULTS.update({'doll.hp': 4, 'glass.x': 3, 'mad.cost': 1, 'rag.b': 6, 'nl.sh': 5, 'nl.d': 5, 'wisp.d': 4})
# итерация 4 → 5 (контрольная)
DEFAULTS.update({'doll.hp': 3, 'doll.porcha': 2, 'evil.dr': 0, 'ash2.d': 2, 'spirit.m': 6, 'pyre.per': 6, 'rag.b': 7})
# итерация 5 → 6: ожившие смелые идеи
DEFAULTS.update({'triple.need': 2, 'delay.cost': 0, 'kick.extra': 1, 'kick.big': 8, 'ashecho.cost': 0, 'ashecho.d': 5, 'glass.p': 0.5})
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
    # --- смелые идеи, партии 2–3
    add('x_storm', 'Буря искр', 'атака', '1 мана. 1 урон за каждую карту, сыгранную в этом раунде тобой и союзником (одним ударом).',
        one(lambda g, h, o: g.hit(h, p('storm.k', 1) * (g.m_plays_rnd + len(getattr(g, 'p_plays_rnd', []))))),
        'swarm', 'С–М', 3, cost=p('storm.cost', 1), tags=('late',), value=6)
    add('x_triple', 'Тройной обряд', 'атака', '1 мана. 2 урона. Если в этом раунде ты сжигал карту, на враге есть Порча и союзник получил щит — ещё 6 урона и возьми 1 карту.',
        one(lambda g, h, o: g.triple(h)), 'flame', 'С–П–М', 3, cost=1, tags=('late',), value=6)
    add('x_glass', 'Стеклянный огонь', 'связка', '0 маны. Твоё следующее попадание в этом раунде ×2. После розыгрыша брось кубик: на 1–2 карта сгорает.',
        one(lambda g, h, o: g.set_mmult()), 'whisper', 'С', 2, cost=0, tags=('porcha',), value=5)
    ae = add('x_ashecho', 'Пепельный отзвук', 'атака', '1 мана. 4 урона. Когда сгорает в первый раз — в начале следующего раунда возвращается в руку.',
        one(lambda g, h, o: g.hit(h, p('ashecho.d', 4))), 'spark', 'С', 2, cost=p('ashecho.cost', 1), value=6)
    ae.on_burn = lambda g, c=ae: g.ash_once(c)
    gr = add('x_grow', 'Растущее пламя', 'атака', '1 мана. 2 урона и ещё 2 за каждый раз, когда эта карта сгорала в этом бою.',
        one(lambda g, h, o: g.hit(h, 2 + p('grow.k', 2) * g.grow_n)), 'spark', 'С', 2, cost=1, value=6)
    gr.on_burn = lambda g: g.grow_up()
    add('x_wisp', 'Блуждающий огонёк', 'атака', '0 маны. 3 урона. Если в конце раунда она в руке — сгорает, и её заряд подношения сохраняется до следующего раунда.',
        one(lambda g, h, o: g.hit(h, p('wisp.d', 3))), 'fuel', 'С', 2, cost=0, value=5)
    add('x_prolif', 'Разрастание', 'связка', '0 маны. +1 Порча на враге, +1 заряд подношения, +1 щит каждому герою, у которого есть щит.',
        one(lambda g, h, o: g.prolif()), 'whisper', 'С–П', 2, cost=0, tags=('porcha',), value=5)
    # --- смелые идеи, партия 4
    add('x_doll', 'Кукла вуду', 'защита', '2 маны. Кукла с 6 здоровья: принимает на себя следующие удары по любому герою. Разрушена — в начале следующего раунда 3 Порчи на враге.',
        one(lambda g, h, o: g.make_doll()), 'ward', 'П', 3, cost=p('doll.cost', 2), value=6)
    md = add('x_madness', 'Шёпот безумия', 'связка', '2 маны. 2 Порчи. Если эту карту сжигают — её эффект срабатывает бесплатно.',
        one(lambda g, h, o: g.porcha(p('mad.n', 2))), 'curse', 'С–П', 2, cost=p('mad.cost', 2), value=3)
    md.on_burn = lambda g: (g.porcha(p('mad.n', 2)), g.bst('mad_burn') if not g.sim else None)
    add('x_xwall', 'Огненный вал', 'атака', 'X маны (не меньше 1). Потрать всю ману: X попаданий по 2 урона.',
        one(lambda g, h, o: g.xwall(h)), 'spark', 'С', 2, cost=1, tags=('late',), value=6)
    add('x_nowlater', 'Сейчас или после', 'связка', '1 мана. Выбери: 4 щита союзнику сразу ИЛИ 5 урона после всех карт союзника в этом раунде.',
        [('щит', lambda g, h, o: g.shield('P', p('nl.sh', 4))), ('после', lambda g, h, o: g.add_late(p('nl.d', 5)))],
        'echo0', 'М', 2, cost=1, value=6)
    # --- смелые идеи, партия 6 (StS: удержание и «силы» до конца боя)
    add('x_plans', 'Хранитель пламени', 'защита', '1 мана. 3 щита себе. В конце раунда оставь 1 карту из руки на следующий раунд.',
        one(lambda g, h, o: (g.shield(h, p('plans.sh', 3)), g.keep_more())), 'ward', 'С–М', 2, cost=1, value=5)
    add('x_embrace', 'Тёмные объятия', 'связка', '1 мана. До конца боя: в начале каждого раунда, если в прошлом раунде ты сжигал карту, возьми 1 карту.',
        one(lambda g, h, o: g.embrace_on()), 'whisper', 'С', 3, cost=p('emb2.cost', 1), value=5)
    # --- смелые идеи, партия 7 (StS: Feel No Pain; MTG: Affinity)
    add('x_ashskin', 'Пепельная кожа', 'защита', '1 мана. До конца боя: каждый раз, когда сгорает карта (твоя или союзника), 2 щита себе.',
        one(lambda g, h, o: g.skin_on()), 'ward', 'С', 3, cost=p('skin.cost', 1), value=5)
    add('x_affin', 'Общий круг', 'атака', '3 маны. 10 урона. Стоит на 1 ману меньше за каждую карту, сыгранную союзником в этом раунде.',
        one(lambda g, h, o: g.affinity(h)), 'flame', 'С–М', 2, cost=3, tags=('late',), value=6)
    # --- смелые идеи, партия 8 (Balatro: красная печать; StS: жетоны-заточки)
    add('x_twice', 'Двойной отблеск', 'связка', '1 мана. Следующая карта, которую ты разыграешь в этом раунде, срабатывает дважды (подношение — один раз).',
        one(lambda g, h, o: g.twice_on()), 'whisper', 'С', 2, cost=p('twice.cost', 1), tags=('porcha',), value=5)
    add('x_shards', 'Искры-осколки', 'атака', '1 мана. Возьми в руку 2 Осколка (0 маны, 2 урона; сгорает после розыгрыша или в конце раунда).',
        one(lambda g, h, o: g.make_shards()), 'spark', 'С', 2, cost=1, tags=('draw',), value=6)
    # --- смелые идеи, партия 9 (MTG: Тёмный ритуал; StS 2: общая цель)
    add('x_ritual', 'Тёмный ритуал', 'связка', '0 маны. +2 маны. После розыгрыша сгорает.',
        one(lambda g, h, o: g.gain_mana('M', p('ritual.m', 2))), 'fuel', 'С', 1, cost=0, value=5)
    add('x_aim', 'Общая цель', 'атака', '1 мана. Твоё следующее попадание в этом раунде +4 и следующее попадание союзника +4.',
        one(lambda g, h, o: g.aim_on()), 'echo0', 'С–М', 2, cost=1, tags=('porcha',), value=6)
    # --- смелые идеи, партия 10 (Balatro: стальная карта, джокеры «за карты в руке»)
    add('x_steel', 'Стальной оберег', 'защита', '1 мана. 4 щита себе. Если в конце раунда эта карта у тебя в руке — 2 щита себе.',
        one(lambda g, h, o: g.shield('M', p('steel.sh', 4))), 'ward', 'М', 2, cost=1, value=4)
    add('x_fist', 'Полная горсть', 'атака', '0 маны. 1 урон за каждую карту, оставшуюся у тебя в руке (одним ударом).',
        one(lambda g, h, o: g.hit(h, p('fist.k', 1) * len(g.H['M'].hand))), 'spark', 'С', 2, cost=0, value=5)
    # --- смелые идеи, партия 11 (Balatro: последняя рука; Остров духов: страх)
    add('x_final', 'Последний аккорд', 'атака', '1 мана. 4 урона. Если после неё у тебя в руке не осталось карт — 12 урона.',
        one(lambda g, h, o: g.hit(h, p('final.big', 12) if not g.H['M'].hand else p('final.d', 4))), 'spark', 'С', 2, cost=1, tags=('late',), value=6)
    add('x_fear', 'Ужас', 'связка', '1 мана. 2 Порчи. Если у врага осталось не больше половины здоровья — ещё 2 Порчи.',
        one(lambda g, h, o: g.porcha(p('fear.n', 2) + (p('fear.n', 2) if g.E.hp * 2 <= g.E.maxhp else 0))), 'curse', 'П', 2, cost=1, value=5)
    # --- смелые идеи, партия 12 (StS: Clash; MTG: Cycling)
    add('x_clash', 'Чистое пламя', 'атака', '0 маны. 8 урона, если в руке у тебя нет защитных карт; иначе 2 урона.',
        one(lambda g, h, o: g.hit(h, p('clash.d', 8) if not any(c.kind == 'защита' for c in g.H['M'].hand) else p('clash.low', 2))), 'spark', 'С', 2, cost=0, tags=('late',), value=6)
    add('x_cycle', 'Искра-перевёртыш', 'атака', '1 мана. Выбери: 6 урона ИЛИ верни 1 ману и возьми 1 карту.',
        [('удар', lambda g, h, o: g.hit(h, p('cycle.d', 6))), ('цикл', lambda g, h, o: (g.gain_mana('M', 1), g.draw('M', 1)))],
        'spark', 'С', 1, cost=1, tags=('draw',), value=6)
    # --- смелые идеи, партия 5 (MTG: доплата и каскад)
    add('x_kick', 'Искра с доплатой', 'атака', '1 мана. 4 урона. Доплата: потрать ещё 2 маны — вместо этого 10 урона и 1 Порча.',
        [('обычно', lambda g, h, o: g.hit(h, p('kick.d', 4))), ('с доплатой', lambda g, h, o: g.kicker(h))],
        'spark', 'С–П', 2, cost=1, value=6)
    add('x_cascade', 'Каскад', 'атака', '1 мана. 3 урона. Открой верхнюю карту колоды: если она стоит 0–1 маны, сыграй её бесплатно.',
        one(lambda g, h, o: g.cascade(h)), 'spark', 'С', 3, cost=p('casc.cost', 1), value=6)
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


SHARD = BCard('t_shard', 'Осколок', 'атака', '0 маны. 2 урона. Сгорает после розыгрыша или в конце раунда.',
              one(lambda g, h, o: g.hit(h, p('shard.d', 2))), cost=0, value=4, grp='spark')


class B10Game(B9Game):
    def __init__(self, *a, **k):
        super().__init__(*a, **k)
        self.delay_dmg = 0; self.delay_now = 0; self.mult_next = False
        self.m_plays_rnd = 0; self.mmult = False; self.ash_used = frozenset(); self.grow_n = 0
        for k2 in ('doom', 'delay', 'reso', 'triple', 'ashecho', 'glass_broke', 'doll', 'mad_burn', 'cascade', 'embrace', 'kept', 'skin', 'affin', 'twice', 'shards', 'aim', 'steel'):
            self.bstats.setdefault(k2, 0)

    def hero_phase(self):
        if not self.sim:
            self.mult_next = False; self.m_plays_rnd = 0; self.mmult = False
            if self.delay_dmg and self.E and self.E.hp > 0:
                d = self.delay_dmg; self.delay_dmg = 0
                self.hit('M', d); self.bst('delay')
            if getattr(self, 'doll_porcha', 0) and self.E:
                self.E.porcha += self.doll_porcha
            self.doll_porcha = 0
            m = self.H['M']
            if getattr(self, 'retained', None):
                m.hand += self.retained; self.retained = []
            if getattr(self, 'embrace', 0) and getattr(self, 'burned_last', 0):
                self.draw_cards('M', p('emb2.n', 1) * self.embrace); self.bst('embrace')
        self.keep_n = 0
        super().hero_phase()

    def hit(self, h, n, pierce=False):
        if h == 'M' and getattr(self, 'mbonus', 0) and n > 0:
            n += self.mbonus; self.mbonus = 0; self.bst('aim')
        if h == 'M' and self.mmult and n > 0:
            x = p('glass.x', 2); n = x * n + (x - 1) * self.E.porcha; self.mmult = False
        if h == 'P' and self.mult_next and n > 0:
            if p('reso.add', 0):
                n = n + p('reso.add', 0)
            else:
                n = 2 * n + self.E.porcha; self.mult_next = False
            if not self.sim:
                self.bst('reso')
        keep = self.curse_next if (h == 'P' and n > 0 and p('curse2.all', 0)) else 0
        super().hit(h, n, pierce)
        if keep and self.E and self.E.hp > 0:
            self.curse_next = keep

    def play(self, hk, card, opt, want_off):
        ok = super().play(hk, card, opt, want_off)
        if ok and hk == 'M':
            self.m_plays_rnd += 1
            if getattr(self, 'twice', 0) and card.cid != 'x_twice' and self.E.hp > 0:
                self.twice -= 1; card.opts[opt][1](self, 'M', 0); self.bst('twice')
            if card.cid in ('t_shard', 'x_ritual'):
                m = self.H['M']
                for i, c in enumerate(m.disc):
                    if c is card:
                        del m.disc[i]; break
                m.exiled.append(card); m.exiled_n += 1
                self.charges += 1; self.burned_rnd += 1; self.bst('burned')
            if card.cid == 'x_glass' and not self.sim and self.rng.random() < p('glass.p', 1 / 3):
                m = self.H['M']
                if any(c is card for c in m.disc):
                    m.disc = [c for c in m.disc if c is not card]; m.exiled.append(card); m.exiled_n += 1
                    self.charges += 1; self.burned_rnd += 1; self.bst('burned'); self.bst('glass_broke')
        return ok

    def set_mmult(self):
        self.mmult = True

    def triple(self, h):
        full = (int(self.burned_rnd > 0) + int(self.E.porcha > 0) + int(self.ally_shielded_rnd > 0)) >= p('triple.need', 3)
        self.hit(h, 2 + (6 if full else 0))
        if full:
            self.draw(h, 1); self.bst('triple')

    def ash_once(self, c):
        if id(c) not in self.ash_used:
            self.ash_used = self.ash_used | {id(c)}
            self.phx_mark(c); self.bst('ashecho')

    def grow_up(self):
        self.grow_n += 1

    def prolif(self):
        self.porcha(p('prolif.n', 1)); self.charges += 1
        for k in 'MP':
            if self.H[k].shield > 0:
                self.shield(k, 1)

    # --- партия 9
    def aim_on(self):
        self.ally_bonus(p('aim.b', 4)); self.mbonus = getattr(self, 'mbonus', 0) + p('aim.b', 4)

    # --- партия 8
    def twice_on(self):
        self.twice = getattr(self, 'twice', 0) + 1

    def make_shards(self):
        m = self.H['M']
        if self.sim:   # оценка бота: осколки будут сыграны после переплана (как у Каскада)
            for _ in range(p('shard.n', 2)):
                self.hit('M', p('shard.d', 2)); self.charges += 1; self.burned_rnd += 1
            return
        for _ in range(p('shard.n', 2)):
            m.hand.append(SHARD)
        self.bst('shards', p('shard.n', 2))

    # --- партия 7
    def skin_on(self):
        self.ashskin = getattr(self, 'ashskin', 0) + 1

    @property
    def burned_rnd(self):
        return self.__dict__.get('_brnd', 0)

    @burned_rnd.setter
    def burned_rnd(self, v):
        old = self.__dict__.get('_brnd', 0); self.__dict__['_brnd'] = v
        k = self.__dict__.get('ashskin', 0)
        if v > old and k and self.H['M'].alive:
            self.shield('M', k * p('skin.sh', 2) * (v - old)); self.bst('skin')

    def affinity(self, h):
        self.hit(h, p('affin.d', 10))
        n = len(getattr(self, 'p_plays_rnd', []))
        self.H['M'].mana += min(3, n)
        if n and not self.sim:
            self.bst('affin', min(3, n))

    # --- партия 6
    def keep_more(self):
        self.keep_n = getattr(self, 'keep_n', 0) + 1

    def embrace_on(self):
        self.embrace = getattr(self, 'embrace', 0) + 1

    # --- партия 5
    def kicker(self, h):
        m = self.H['M']
        if m.mana >= p('kick.extra', 2):
            m.mana -= p('kick.extra', 2); self.hit(h, p('kick.big', 10)); self.porcha(1)
        else:
            self.hit(h, p('kick.d', 4))

    def cascade(self, h):
        self.hit(h, p('casc.d', 3))
        m = self.H['M']
        if self.sim:
            self.hit(h, p('casc.sim', 3))   # оценка бота: в среднем открытая карта даёт около 3 урона
            return
        if not m.draw or self.E.hp <= 0:
            return
        c = m.draw[-1]
        if c.cost <= 1 and c.cid != 'x_cascade':
            m.draw.pop(); m.hand.append(c); m.mana += c.cost
            if self.play('M', c, 0, False):
                self.bst('cascade')

    # --- партия 4
    def make_doll(self):
        self.doll = getattr(self, 'doll', 0) + p('doll.hp', 6)

    def deal(self, k, n, src='удар'):
        d = getattr(self, 'doll', 0)
        if d > 0 and n > 0 and self.H[k].alive:
            a = min(d, n); self.doll = d - a; n -= a
            if self.doll <= 0:
                self.doll_porcha = getattr(self, 'doll_porcha', 0) + p('doll.porcha', 3)
                if not self.sim:
                    self.bst('doll')
        super().deal(k, n, src)

    def xwall(self, h):
        m = self.H['M']; x = 1 + m.mana; m.mana = 0
        for _ in range(x + p('xwall.plus', 0)):
            self.hit(h, p('xwall.d', 2))

    def add_late(self, n):
        self.late_dmg = getattr(self, 'late_dmg', 0) + n

    def end_hero_phase(self):
        if getattr(self, 'late_dmg', 0) and self.E.hp > 0:
            d = self.late_dmg; self.late_dmg = 0; self.hit('M', d)
        self.late_dmg = 0
        m = self.H['M']
        if not self.sim:
            self.burned_last = self.burned_rnd
            if getattr(self, 'keep_n', 0) and m.hand:
                keep = sorted(m.hand, key=lambda c: -c.value)[:self.keep_n]
                m.hand = [c for c in m.hand if not any(c is k for k in keep)]
                self.retained = keep; self.bst('kept')
        self.twice = 0; self.mbonus = 0
        for c in m.hand:
            if c.cid == 'x_steel' and m.alive:
                self.shield('M', p('steel.held', 2)); self.bst('steel')
        w = [c for c in m.hand if c.cid in ('x_wisp', 't_shard')]
        for c in w:
            m.hand = [x for x in m.hand if x is not c]; m.exiled.append(c); m.exiled_n += 1
            self.charges += 1; self.burned_rnd += 1; self.bst('burned')
            if c.cid == 'x_wisp':
                self.keep = True
        self.rot_cap = self.E.porcha if (self.rot and self.E) else 0
        super().end_hero_phase()

    def doom(self):
        e = self.E
        self.porcha(p('doom.n', 1))
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
            if g.E.hp > 0:
                s += p('fut.doll', 1.2) * (getattr(g, 'doll', 0) - getattr(base, 'doll', 0))
                s += p('fut.dollp', 1.0) * k * (getattr(g, 'doll_porcha', 0) - getattr(base, 'doll_porcha', 0))
                s += p('fut.keep', 2.0) * (getattr(g, 'keep_n', 0) - getattr(base, 'keep_n', 0))
                s += p('fut.emb', 3.0) * (getattr(g, 'embrace', 0) - getattr(base, 'embrace', 0))
                s += p('fut.skin', 3.0) * (getattr(g, 'ashskin', 0) - getattr(base, 'ashskin', 0))
                s += p('fut.steel', 1.2) * p('steel.held', 2) * sum(1 for c in g.H['M'].hand if c.cid == 'x_steel')
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
