# -*- coding: utf-8 -*-
"""Бой: правила «Двое во тьме» для одного боя пары героев (Маг + Жрец) против одного врага.

Движок ничего не знает о тестах и боте. Снаружи им управляет «игрок» (стенд, бот или человек):
    f = Fight(game, decks, enemy, location, seed, choices)
    while not f.over:
        f.start_round()                # намерение врага, добор, эффекты начала раунда
        ... игрок делает действия: f.apply(('play', герой, карта, вариант, подношений)),
            f.apply(('fdisc', герой)), f.flash(герой), f.reveal()
        f.finish_round()               # конец фазы героев, ход врага, конец раунда
Для планирования игрок берёт копию f.plan_copy(): в ней колоды закрыты (добор не тянет карты,
а копится в pend), случайностей нет, журнал не пишется.

Решения внутри эффектов (какую карту сжечь, что вернуть, что сыграть Молитвой, кто примет удар)
движок спрашивает у объекта choices (см. engine/choices.py)."""
import random
from .data import CardInst
from .effects import Ctx

ALIVE_HAND = 6


class Hero:
    def __init__(self, hid, mech, name, maxhp, deck):
        self.id = hid; self.mech = mech; self.name = name
        self.maxhp = maxhp; self.hp = maxhp
        self.deck = list(deck)
        self.draw, self.hand, self.disc, self.exiled = [], [], [], []
        self.shield = 0; self.vanguard = False; self.blessed = False; self.alive = True
        self.mana = 0; self.plays = 0; self.maxplays = 3; self.faith = 0
        self.discarded = False; self.pend = 0; self.lost_hp_fight = False; self.last_hit = 0; self.exiled_n = 0
        self.next_bonus = 0
        # счётчики раунда (для условий карт)
        self.plays_rnd = 0; self.hand_plays_rnd = 0; self.hits_rnd = 0; self.hits_last = 0
        self.shielded_rnd = 0; self.drew_rnd = 0; self.disc_rnd = 0; self.burned_by_ally_rnd = 0
        self.taken = 0; self.taken_mark = 0; self.taken_last = 0
        self.played = []            # [(карта, вариант)] за раунд

    def clone(self):
        h = Hero.__new__(Hero)
        h.__dict__ = dict(self.__dict__)
        h.draw = list(self.draw); h.hand = list(self.hand); h.disc = list(self.disc); h.exiled = list(self.exiled)
        h.played = list(self.played)
        return h


class Enemy:
    def __init__(self, ed):
        self.d = ed; self.name = ed.name; self.tier = ed.tier
        self.maxhp = ed.hp; self.hp = ed.hp
        self.traits = dict(ed.traits); self.shield = ed.shield0; self.porcha = 0; self.buff = 0
        self.deckmode = ed.mode == 'koloda'
        self.cycle = None if self.deckmode else list(ed.intents); self.idx = 0
        self.dpile = list(ed.intents) if self.deckmode else None; self.ddisc = []
        self.intent = None
        self.stone = 0; self.cracks = 0; self.knocked = False; self.hitters = []
        self.threat = ed.threat

    def clone(self):
        e = Enemy.__new__(Enemy)
        e.__dict__ = dict(self.__dict__)
        e.hitters = list(self.hitters)
        if self.dpile is not None:
            e.dpile = list(self.dpile); e.ddisc = list(self.ddisc)
        return e


class Fight:
    def __init__(self, game, decks, enemy, location, seed, choices, log=False):
        """decks: {id героя: [CardDef, ...]} — ровно один Маг и один Жрец."""
        R = game.rules
        self.game = game; self.R = R; self.choices = choices
        self.seed = seed; self.rng = random.Random(seed)
        self.planning = False; self.logging = log; self.log = []
        self.H = {}
        for hid, cards in decks.items():
            hd = game.heroes[hid]
            self.H[hid] = Hero(hid, hd['mehanika'], hd['imya'], hd['zdorove'], [CardInst(c, hid) for c in cards])
        mech = {h.mech: h.id for h in self.H.values()}
        if set(mech) != {'mag', 'zhrec'}:
            raise ValueError('в версии 1 движок знает пару Маг + Жрец')
        self.M = mech['mag']; self.P = mech['zhrec']
        self.order = [self.M, self.P]
        self.E = Enemy(enemy)
        self.loc = location; self.feats = list(location.feats) if location else []
        self.oil = R['maslo_na_starte']; self.bless_n = R['blagoslovenie']; self.faith_max = R['vera_maks']
        self.rnd = 0; self.over = False; self.won = False; self.stuck = False
        self.target = None; self.flash_weak = False; self.flasher = None; self.revealed = False
        self.porcha_trig = False; self.dmg_phase = 0; self.fdisc_round = []; self.feat_used = []
        self.reserved = []
        self.ignore_stone = False
        # Маг
        self.charges = 0; self.keep = False; self.burned_rnd = 0; self.mmult = False
        self.rot = False; self.rot_val = 0; self.rot_cap = 0; self.late_dmg = 0
        self.phx = []; self.ash_used = frozenset(); self.doll = 0; self.doll_dmg = 0
        self._after = []              # что сделать с картой после розыгрыша (сгореть и т.п.)
        # Жрец
        self.vows = []; self.bless_riders = []; self.inspired = []
        self.bless_trig_rnd = 0; self.bless_trig_last = 0; self.bless_trig_fight = 0
        self.kinds_rnd = set(); self.pray_rnd = 0; self.mir_rnd = 0; self.weak = 0; self.brand = 0
        self.martyr = 0; self.bless_big = False; self.pray_bonus = 0; self.mir_plus = 0; self.news = False
        self.vigil = False; self.banner = False; self.banner_keep = 0; self.cover = False
        self._free = 0
        # оценки будущего для бота (копятся только в копии для планирования)
        self.est = 0.0; self.est_f = 0.0
        self.stats = {}; self.min_frac = 1.0
        self.start_hp = {k: h.hp for k, h in self.H.items()}
        self._start_fight()

    # ================================================================ служебное
    def L(self, s):
        if self.logging and not self.planning:
            self.log.append(s)

    def st(self, k, n=1):
        if not self.planning:
            self.stats[k] = self.stats.get(k, 0) + n

    def ally(self, hid):
        return self.P if hid == self.M else self.M

    def hn(self, hid):
        return self.H[hid].name

    @property
    def dark(self):
        return self.oil <= 0

    def hidden(self):
        return self.dark or (self.E.traits.get('hidden') and not self.revealed)

    def alive_ids(self):
        return [k for k in self.order if self.H[k].alive]

    def plan_copy(self):
        g = Fight.__new__(Fight)
        g.__dict__ = dict(self.__dict__)
        g.planning = True
        g.H = {k: h.clone() for k, h in self.H.items()}
        g.E = self.E.clone()
        g.fdisc_round = list(self.fdisc_round); g.feat_used = list(self.feat_used); g.reserved = list(self.reserved)
        g.phx = list(self.phx); g.vows = list(self.vows); g.bless_riders = list(self.bless_riders)
        g.inspired = list(self.inspired); g.kinds_rnd = set(self.kinds_rnd); g._after = []
        g.stats = None; g.log = []
        return g

    # ================================================================ переменные для выражений карт
    def var(self, name, me):
        fn = VARS.get(name)
        if fn is None:
            raise KeyError(f'неизвестное имя «{name}» в выражении карты. Есть: {", ".join(sorted(VARS))}')
        return fn(self, self.H[me], self.H[self.ally(me)])

    # ================================================================ колоды
    def _start_fight(self):
        R = self.R
        for h in self.H.values():
            h.draw = list(h.deck); self.rng.shuffle(h.draw)
            h.hand, h.disc, h.exiled = [], [], []
            h.faith = 0; h.maxplays = R['limit_kart_zhreca'] if h.mech == 'zhrec' else 99
        if self.E.deckmode:
            self.rng.shuffle(self.E.dpile)
        self.L(f'БОЙ: {self.E.name} ({self.E.hp} здоровья)' + (f' в локации «{self.loc.name}»' if self.loc else '') +
               (('. ' + '; '.join(f[2] for f in self.feats)) if self.feats else ''))

    def draw_cards(self, hid, n):
        h = self.H[hid]
        for _ in range(n):
            if not h.draw:
                if not h.disc:
                    return
                h.draw = h.disc; h.disc = []; self.rng.shuffle(h.draw)
                self.L(f'   {h.name}: колода кончилась, сброс перетасован ({len(h.draw)} карт).')
            h.hand.append(h.draw.pop())

    def draw(self, hid, n):
        if n <= 0:
            return
        self.H[hid].drew_rnd += 1
        if self.planning:
            self.H[hid].pend += n
        else:
            self.draw_cards(hid, n)

    def _top(self, hid):
        h = self.H[hid]
        if not h.draw:
            if not h.disc:
                return None
            h.draw = h.disc; h.disc = []
            if not self.planning:
                self.rng.shuffle(h.draw)
        return h.draw[-1]

    # ================================================================ вера и ресурсы
    def gain_faith(self, n, why):
        P = self.H[self.P]
        if n <= 0:
            return
        old = P.faith; P.faith = min(self.faith_max, P.faith + n)
        if P.faith > old:
            self.st('vera_poluchena', P.faith - old)
            self.st('vera_ot_kart' if why == 'карта' else 'vera_ot_soyuznika', P.faith - old)

    def own_faith(self, n):
        self.gain_faith(int(n), 'карта')

    def spend_faith(self, n):
        P = self.H[self.P]
        n = min(n, P.faith); P.faith -= n
        self.st('vera_potrachena', n)

    def miracle(self):
        P = self.H[self.P]; f = P.faith; P.faith = 0
        f += self.mir_plus; self.mir_plus = 0
        self.mir_rnd += 1
        self.st('chudes'); self.st('vera_v_chudo', f)
        return f

    def gain_mana(self, hid, n):
        self.H[hid].mana += n

    def add_charge(self, n):
        self.charges += n

    def add_next_bonus(self, hid, n):
        self.H[hid].next_bonus += n

    def weaken(self, n):
        self.weak += n

    # ================================================================ урон по врагу
    def hit(self, hid, n, armor_pierce=False):
        e = self.E
        if e.hp <= 0:
            return
        M, P = self.M, self.P
        if hid == M and n > 0:
            if self.cover and self.H[M].blessed:
                n += self.R['pokrov_bonus']
            if self.brand > 0:
                self.brand -= 1; self.gain_faith(1, 'союзник')
        a = e.traits.get('armor', 0)
        if a and n > 0 and not armor_pierce:
            n = max(0, n - a); self.st('bronya_srezala')
        h = self.H[hid]
        if hid == M and n > 0:
            if h.next_bonus:
                n += h.next_bonus; h.next_bonus = 0
            if self.mmult:
                x = self.R['steklo_mnozhitel']; n = x * n + (x - 1) * e.porcha; self.mmult = False
        if n > 0:
            h.hits_rnd += 1
        if hid == P and n > 0 and h.next_bonus:
            n += h.next_bonus; h.next_bonus = 0
        self._raw_hit(hid, n)

    def _raw_hit(self, hid, n, ignore_shield=False):
        e = self.E
        if e.hp <= 0:
            return
        dmg = n + e.porcha
        if e.porcha > 0 and not self.porcha_trig:
            self.porcha_trig = True; self.st('porcha_srabotala')
            self.gain_faith(1, 'союзник')
        self.H[hid].last_hit = dmg
        if e.traits.get('golem'):
            if hid not in e.hitters:
                e.hitters.append(hid)
            if self.ignore_stone:
                e.stone = 0
            if (len(e.hitters) == 2 or len(self.alive_ids()) == 1) and e.stone > 0:
                e.stone = 0; e.knocked = True; e.cracks += 1
                self.L(f'      Каменный щит голема сбит (оба попали)! Трещин: {e.cracks}')
            if e.stone > 0:
                self.L(f'      Каменный щит держит удар ({dmg}): нужно попадание второго героя')
                dmg = 0
        if not ignore_shield:
            a = min(e.shield, dmg); e.shield -= a; dmg -= a
        e.hp -= dmg; self.dmg_phase += dmg
        self.st('uron_' + hid, max(0, dmg))
        if e.hp <= 0:
            e.hp = 0
            self.L(f'      {e.name} повержен ({self.hn(hid)})!')
            if hid == self.M:
                self.gain_faith(1, 'союзник')

    def kill_enemy(self, hid):
        """Враг погибает сразу (Рок): удар, равный его здоровью, мимо щита."""
        self._raw_hit(hid, self.E.hp, ignore_shield=True)

    # ================================================================ защита и статусы
    def shield(self, hid, n):
        h = self.H[hid]
        if n and h.alive:
            h.shield += n
            if n > 0:
                h.shielded_rnd += 1

    def add_porcha(self, n):
        self.E.porcha += n

    def bless(self, hid):
        if self.H[hid].alive:
            self.H[hid].blessed = True

    def vanguard(self, hid):
        self.H[hid].vanguard = True
        if any(f[1] == 'narrow' for f in self.feats):
            self.shield(hid, 1)

    # ================================================================ сжигание, сброс, возврат
    def _free_cards(self, cards):
        return [c for c in cards if not any(c is r for r in self.reserved)]

    def _exile(self, owner, c, charge=True):
        self.H[owner].exiled.append(c)
        if owner == self.M:
            self.H[owner].exiled_n += 1
        if charge:
            self.charges += 1
        self.burned_rnd += 1
        self.st('szhzheno')

    def burn(self, me, n, src='ruka'):
        """Сжечь до n карт. Маг получает заряд подношения за каждую. Возвращает число сожжённых."""
        done = 0
        own = self.H[me]; al = self.H[self.ally(me)]
        for _ in range(n):
            if src == 'ruka':
                cands = self._free_cards(own.hand)
                if not cands:
                    break
                c = self.choices.burn_pick(self, me, cands); own.hand.remove(c); owner = me
            elif src == 'sbros':
                if not own.disc:
                    break
                c = self.choices.burn_pick(self, me, own.disc); own.disc.remove(c); owner = me
            elif src == 'verh':
                if not own.draw:
                    break
                c = own.draw.pop(); owner = me
            elif src == 'verh_soyuznika':
                if not al.draw:
                    break
                c = al.draw.pop(); owner = al.id; self.st('szhzheno_u_soyuznika')
            else:   # ruka_soyuznika
                cands = self._free_cards(al.hand)
                if not cands:
                    break
                c = min(cands, key=lambda x: x.value); al.hand.remove(c); owner = al.id; self.st('szhzheno_u_soyuznika')
            done += 1
            self._exile(owner, c)
            self.L(f'      сожжена «{c.name}» → заряд ({self.charges})')
            if owner == me and c.d.on_burn is not None:
                c.d.on_burn(self, Ctx(me, c))
        return done

    def ally_burn(self, me, n):
        """Союзник может сжечь до n карт из своей руки (маг получает заряд за каждую)."""
        a = self.H[self.ally(me)]
        if not a.alive:
            return 0
        done = 0
        for _ in range(n):
            cands = self._free_cards(a.hand)
            if not cands:
                break
            c = self.choices.ally_burn_pick(self, a.id, cands)
            if c is None:
                break
            a.hand.remove(c); self._exile(a.id, c); a.burned_by_ally_rnd += 1; done += 1
            self.st('soyuznik_szheg')
            self.L(f'      {a.name} сжигает «{c.name}» → магу заряд ({self.charges})')
        return done

    def discard(self, hid, n):
        h = self.H[hid]; done = 0
        for _ in range(n):
            cands = self._free_cards(h.hand)
            if not cands:
                break
            c = self.choices.discard_pick(self, hid, cands); h.hand.remove(c); h.disc.append(c); done += 1
        if done:
            h.discarded = True; h.disc_rnd += done
            self.st('sbrosheno_' + hid, done)
        return done

    def burned_snapshot(self):
        return {k: list(h.exiled) for k, h in self.H.items()}

    def restore(self, before=None, skip_card=None):
        """Вернуть в руку владельца 1 сожжённую карту (свою или союзника)."""
        pool = []
        for k, h in self.H.items():
            src = before[k] if before is not None else h.exiled
            pool += [(k, c) for c in src if any(c is x for x in h.exiled) and c is not skip_card
                     and not any(c is x for x in self.phx)]
        if not pool:
            return 0
        k, c = self.choices.restore_pick(self, pool)
        h = self.H[k]
        h.exiled = [x for x in h.exiled if x is not c]
        if k == self.M:
            h.exiled_n = max(0, h.exiled_n - 1)
        if self.planning:
            h.pend += 1
        else:
            h.hand.append(c)
        self.st('vozvrascheno')
        self.L(f'      возвращена «{c.name}» ({h.name})')
        return 1

    def phx_mark(self, c):
        self.phx.append(c)
        if self.planning:
            self.H[self.M].pend += 1

    # ================================================================ Жрец: Молитва, Обет, Благословение
    def pray(self, ctx, n_open=None, n_play=1, uselimit=False, kind_filter=None, then=None, est=0.0):
        P = self.H[self.P]
        n_open = (n_open or self.R['molitva_otkryt']) + self.pray_bonus; self.pray_bonus = 0
        if self.planning:
            B = self.R['bot']
            k = n_play if kind_filter is None else 0.45 * n_open
            w = B['ocenka_molitvy'] + est
            if uselimit:
                k = min(k, max(0, P.maxplays - P.plays)); w = B['ocenka_molitvy_v_limit']
            self.est += w * k
            self.pray_rnd += 1
            return []
        opened = []
        for _ in range(n_open):
            if self._top(self.P) is None:
                break
            opened.append(P.draw.pop())
        self.st('molitv'); played = []
        rounds = n_play if kind_filter is None else len(opened)
        for _ in range(rounds):
            cands = [c for c in opened if kind_filter is None or c.kind == kind_filter]
            if not cands or self.E.hp <= 0 or not P.alive:
                break
            pick = self.choices.pray_pick(self, cands, uselimit)
            if pick is None:
                break
            c, oi = pick
            opened = [x for x in opened if x is not c]
            P.hand.append(c)
            if not uselimit:
                P.maxplays += 1
            self._free += 1
            try:
                ok = self.play(self.P, c, oi, 0)
            finally:
                self._free -= 1
            if not ok:
                P.hand = [x for x in P.hand if x is not c]; P.disc.append(c)
                if not uselimit:
                    P.maxplays -= 1
                continue
            played.append(c); self.pray_rnd += 1; self.st('molitvoj_sygrano')
            if then is not None:
                c2 = Ctx(self.P, ctx.card); c2.loc['sygrana_ataka'] = int(c.kind == 'атака')
                then(self, c2)
        P.disc += opened
        return played

    def threat_k(self):
        return 1.0 + 2.2 * self.E.threat / max(1, self.E.maxhp)

    def vow(self, ctx, eff, kind, est, when):
        if self.planning:
            self.est_f += self.R['bot']['ocenka_obeta'] * est * (self.threat_k() if kind == 'dmg' else 1.0)
            return
        self.vows.append((when, eff, self.rnd, ctx.me, ctx.card)); self.st('obetov')

    def bless_rider(self, ctx, eff):
        self.bless(self.ally(ctx.me))
        self.bless_riders = self.bless_riders + [(eff, ctx.me, ctx.card)]

    # ================================================================ враг
    def draw_intent(self):
        e = self.E
        if not e.dpile:
            e.dpile = e.ddisc; e.ddisc = []
            if not self.planning:
                self.rng.shuffle(e.dpile)
            self.L('   Колода намерений перетасована.')
        if self.planning:
            return e.dpile[-1] if e.dpile else e.intent
        return e.dpile.pop()

    def intent_str(self, full=True):
        i = self.E.intent
        if self.hidden() and not full:
            return f"[скрыто: {i['type']}]"
        return i['text'] + (f" (+{self.E.buff} усиление)" if self.E.buff else '')

    def roll_target(self):
        alive = self.alive_ids()
        need = any(a[0] == 'atk' and a[2] in ('single', 'moth') for a in self.E.intent['acts'])
        self.target = None
        if need and alive:
            self.target = self.rng.choice(alive) if (not self.planning and len(alive) > 1) else alive[0]

    def shift(self):
        e = self.E
        if e.deckmode:
            e.ddisc.append(e.intent); e.intent = self.draw_intent()
        else:
            e.idx += 1; e.intent = e.cycle[e.idx % len(e.cycle)]
        self.L(f'      Сдвиг намерения → {self.intent_str()}')
        self.roll_target()

    def plan_intent(self):
        """Что пара знает о намерении врага при планировании."""
        if not self.hidden():
            return self.E.intent
        t = self.E.intent['type']; est = self.R['skrytoe_namerenie'][self.E.tier]
        if t == 'удар':
            return {'type': 'удар', 'acts': [('atk', est, 'single', 1)], 'text': '?'}
        if t == 'защита':
            return {'type': 'защита', 'acts': [('shield', 10), ('atk', est // 2, 'single', 1)], 'text': '?'}
        return {'type': 'усиление', 'acts': [('buff', 2)], 'text': '?'}

    def targets(self, tgt, n):
        alive = self.alive_ids()
        if not alive:
            return []
        if tgt == 'all':
            return alive
        if tgt == 'moth':
            c = [k for k in alive if self.H[k].vanguard or self.flasher == k]
            if c:
                return [self.choices.take_hit(self, c, n)]
            tgt = 'single'
        if tgt == 'single':
            van = [k for k in alive if self.H[k].vanguard]
            if van:
                return [self.choices.take_hit(self, van, n)]
            return [self.target if self.target in alive else alive[0]]
        if tgt == 'weakest':
            m = min(self.H[k].hp for k in alive)
            return [self.choices.take_hit(self, [k for k in alive if self.H[k].hp == m], n)]
        if tgt == 'unshielded':
            c = [k for k in alive if self.H[k].shield == 0] or alive
            return [self.choices.take_hit(self, c, n)]
        return [alive[0]]

    def deal(self, k, n, src='удар'):
        """Удар по герою."""
        h = self.H[k]
        if not h.alive:
            return
        if self.doll > 0 and n > 0:
            a = min(self.doll, n); self.doll -= a; n -= a; self.doll_dmg += a
            self.L(f'      Кукла вуду принимает {a}')
        if k == self.P and n > 0 and self.martyr > 0:
            self.martyr -= 1; self.own_faith(1)
        trig = h.blessed and n > 0
        if h.blessed and n > 0:
            b = self.R['blagoslovenie_bolshoe'] if (k == self.M and self.bless_big) else self.bless_n
            n = max(0, n - b); h.blessed = False
            self.L(f'      Благословение на {h.name}: удар слабее на {b}')
        a = min(h.shield, n); h.shield -= a; n -= a
        if n > 0:
            if not self.planning:
                h.taken += min(n, h.hp)
            h.hp -= n; h.lost_hp_fight = True
            self.L(f'      {h.name} теряет {n} ({src}) → {max(0, h.hp)}')
            if k == self.M:
                self.gain_faith(1, 'союзник')
            if h.hp <= 0:
                h.hp = 0; h.alive = False; h.shield = 0
                self.L(f'      *** {h.name} падает! ***'); self.st('padenij')
        if trig and k == self.M:
            self.bless_trig_rnd += 1; self.bless_trig_fight += 1; self.cover = False; self.st('blagoslovenie_srabotalo')
            rs = self.bless_riders; self.bless_riders = []
            for eff, me, card in rs:
                if self.E.hp > 0:
                    eff(self, Ctx(me, card))

    def enemy_act(self, intent):
        e = self.E
        e.buff -= self.weak
        try:
            e.shield = 0
            for act in intent['acts']:
                k = act[0]
                if k == 'atk':
                    n = act[1] + e.buff + (e.traits.get('dark', 0) if self.dark else 0) - (1 if self.flash_weak else 0)
                    n = max(0, n)
                    for _ in range(act[3]):
                        for tk in self.targets(act[2], n):
                            self.deal(tk, n)
                elif k == 'shield':
                    e.shield += act[1]
                elif k == 'buff':
                    e.buff += act[1]
                elif k == 'heal':
                    e.hp = min(e.maxhp, e.hp + act[1])
                elif k == 'oil':
                    o = self.oil; self.oil = max(0, self.oil - act[1])
                    if o != self.oil:
                        self.L(f'      Враг крадёт масло: {o} → {self.oil}')
        finally:
            e.buff += self.weak
        if self.banner and not self.planning:
            self.banner_keep = self.H[self.P].shield

    # ================================================================ особенности комнат
    def feat_available(self, hid):
        if hid in self.fdisc_round:
            return None
        for f in self.feats:
            if f[0] == 'discard':
                if f[1] == 'altar' and ('altar' in self.feat_used or self.oil >= self.R['maslo_maks']):
                    continue
                return f
        for f in self.feats:
            if f[0] == 'double' and f[1] not in self.feat_used:
                return f
        return None

    def lowest_free(self, hid):
        cands = self._free_cards(self.H[hid].hand)
        return min(cands, key=lambda c: c.value) if cands else None

    def do_fdisc(self, hid):
        f = self.feat_available(hid)
        c = self.lowest_free(hid)
        if f is None or c is None:
            return False
        h = self.H[hid]
        h.hand.remove(c); h.disc.append(c); h.discarded = True; self.fdisc_round.append(hid)
        self.st('sbros_dlya_komnaty')
        self.L(f'   {h.name} сбрасывает «{c.name}» ради особенности комнаты')
        if f[0] == 'discard':
            if f[1] == 'altar':
                self.feat_used.append('altar'); self.oil = min(self.R['maslo_maks'], self.oil + 1)
            elif f[1] == 'bones':
                e = self.E; a = min(e.shield, 1); e.shield -= a; e.hp = max(0, e.hp - (1 - a)); self.dmg_phase += 1 - a
            elif f[1] == 'pillar':
                self.shield(hid, 1)
            elif f[1] == 'sealheal':
                h.hp = min(h.maxhp, h.hp + 1) if h.alive else h.hp
            elif f[1] == 'draftshield':
                self.shield(self.ally(hid), 1)
        if (any(x[1] == 'seals' for x in self.feats) and 'seals' not in self.feat_used
                and all(k in self.fdisc_round for k in self.order)):
            self.feat_used.append('seals'); self.L('      Печати предков (оба сбросили): сдвиг намерения'); self.shift()
        return True

    # ================================================================ розыгрыш карты
    def play(self, hid, card, opt, want_off):
        h = self.H[hid]
        if not h.alive or not any(c is card for c in h.hand):
            return False
        if h.mech == 'mag':
            return self._play_mage(h, card, opt, want_off)
        return self._play_priest(h, card, opt)

    def _play_mage(self, h, card, opt, want_off):
        d = card.d
        if h.mana < d.cost:
            return False
        h.hand.remove(card)
        self.reserved = [r for r in self.reserved if r is not card]
        h.mana -= d.cost; h.plays += 1
        o = 0
        if d.offering:
            price = 2 if d.offering == '2' else 1
            for _ in range(want_off):
                if self.charges >= price:
                    self.charges -= price; o += 1; self.st('zaryadov_potracheno', price)
                else:
                    break
        v = d.variants[opt]
        self.L(f'   {h.name}: «{d.name}»' + (f' ({v.name})' if v.name else '') + (f' [Подношение ×{o}]' if o else ''))
        self.st('sygrano_' + h.id)
        if not self.planning:
            self.stats.setdefault('karty', {}).setdefault(d.cid, 0)
            self.stats['karty'][d.cid] += 1
        e0 = self.E.hp
        self._after = []
        v.effect(self, Ctx(h.id, card, o, False, opt))
        h.disc.append(card)
        self._after_play(h, card)
        h.plays_rnd += 1; h.played.append((card, opt))
        if any(card is x for x in self.inspired):
            self.inspired = [x for x in self.inspired if x is not card]
            self.own_faith(self.R['vdohnovenie_vera'])
        if self.E.hp != e0:
            self.L(f'      враг {e0} → {self.E.hp}' + (f' (Порча {self.E.porcha})' if self.E.porcha else ''))
        return True

    def _after_play(self, h, card):
        """Что происходит с картой после розыгрыша: сгорает (Феникс, Осколок), бросок Стеклянного огня."""
        todo = self._after; self._after = []
        burn_after = 'sgoraet_posle' in card.tags
        for what, arg in todo:
            if what == 'burn_self':
                burn_after = True
            elif what == 'glass' and not self.planning and self.rng.random() < arg[0]:
                if any(c is card for c in h.disc):
                    h.disc = [c for c in h.disc if c is not card]
                    self._exile(h.id, card, charge=arg[1] > 0)
                    if arg[1] > 1:
                        self.charges += arg[1] - 1
                    self.st('steklo_sgorelo')
                    self.L(f'      «{card.name}» сгорает (бросок кубика)')
        if burn_after and any(c is card for c in h.disc):
            h.disc = [c for c in h.disc if c is not card]
            self._exile(h.id, card)
            if card.d.on_burn is not None:
                card.d.on_burn(self, Ctx(h.id, card))

    def _play_priest(self, h, card, opt):
        d = card.d
        if h.plays >= h.maxplays:
            return False
        v = d.variants[opt]
        if not self._free:
            h.hand_plays_rnd += 1
        self.kinds_rnd = self.kinds_rnd | {d.kind}
        h.hand.remove(card)
        self.reserved = [r for r in self.reserved if r is not card]
        h.plays += 1
        paid = False
        if v.pay_faith and h.faith >= v.pay_faith:
            h.faith -= v.pay_faith; paid = True; self.st('vera_potrachena', v.pay_faith); self.st('doplat')
        self.L(f'   {h.name}: «{d.name}»' + (f' ({v.name})' if v.name else '') + (' [доплата]' if paid else ''))
        self.st('sygrano_' + h.id)
        if not self.planning:
            self.stats.setdefault('karty', {}).setdefault(d.cid, 0)
            self.stats['karty'][d.cid] += 1
        e0 = self.E.hp
        v.effect(self, Ctx(h.id, card, 0, paid, opt))
        h.disc.append(card)
        h.plays_rnd += 1; h.played.append((card, opt))
        if self.E.hp != e0:
            self.L(f'      враг {e0} → {self.E.hp}' + (f' (Порча {self.E.porcha})' if self.E.porcha else ''))
        return True

    def apply(self, act):
        if act[0] == 'play':
            return self.play(act[1], act[2], act[3], act[4])
        if act[0] == 'fdisc':
            return self.do_fdisc(act[1])
        return False

    # ================================================================ действия до плана: Вспышка
    def flash(self, hid):
        """Вспышка фонаря: −1 масло, враг в этом раунде бьёт на 1 слабее, мотылёк бьёт вспыхнувшего."""
        self.oil -= 1; self.flash_weak = True; self.flasher = hid
        self.L(f'   Вспышка ({self.hn(hid)}): −1 масло → {self.oil}; враг бьёт на 1 слабее'); self.st('vspyshek')

    def reveal(self):
        """Вспышка, чтобы открыть намерение Скрытня."""
        self.oil -= 1; self.revealed = True; self.flasher = self.P if self.H[self.P].alive else self.M
        self.st('vspyshek')
        self.L(f'   Вспышка: открыть намерение (−1 масло → {self.oil}): {self.intent_str()}')

    # ================================================================ ход раунда
    def start_round(self):
        """Начало раунда: намерение, добор, эффекты начала раунда. Дальше ходит игрок."""
        R = self.R; e = self.E; M, P = self.H[self.M], self.H[self.P]
        self.rnd += 1; self.st('raundov')
        if self.dark:
            self.st('raundov_v_temnote')
        e.intent = self.draw_intent() if e.deckmode else e.cycle[e.idx % len(e.cycle)]
        self.flash_weak = False; self.flasher = None; self.revealed = False; self.porcha_trig = False
        self.dmg_phase = 0; self.fdisc_round = []
        if e.traits.get('golem'):
            e.stone = e.traits['golem']; e.knocked = False; e.hitters = []
        self.roll_target()
        nxt = f"; следующее: {e.dpile[-1]['type']}" if (e.deckmode and e.dpile) else ''
        tg = f"; цель броском: {self.hn(self.target)}" if self.target else ''
        self.L(f' Раунд {self.rnd}. Намерение: {self.intent_str(full=False)}{tg}{nxt}. {e.name} {e.hp}/{e.maxhp}' +
               (f', щит {e.shield}' if e.shield else '') + (f', каменный щит {e.stone}' if e.traits.get('golem') else '') +
               (' | ТЕМНОТА' if self.dark else ''))
        if any(f[1] == 'drip' for f in self.feats):
            for k in self.order:
                self._hazard(k, 'Капель')
        for h in self.H.values():
            self.draw_cards(h.id, max(0, R['ruka'] - len(h.hand)))
            h.mana = R['mana_maga'] if h.mech == 'mag' else 0
            h.plays = 0; h.maxplays = R['limit_kart_zhreca'] if h.mech == 'zhrec' else 99
            h.discarded = False; h.last_hit = 0; h.pend = 0
            h.hits_last = h.hits_rnd
            h.taken_last = h.taken - h.taken_mark; h.taken_mark = h.taken
            h.plays_rnd = 0; h.hand_plays_rnd = 0; h.hits_rnd = 0; h.shielded_rnd = 0; h.drew_rnd = 0
            h.disc_rnd = 0; h.burned_by_ally_rnd = 0; h.played = []; h.next_bonus = 0
        self.bless_trig_last = self.bless_trig_rnd
        self.bless_trig_rnd = 0; self.kinds_rnd = set(); self.pray_rnd = 0; self.mir_rnd = 0; self.weak = 0
        self.brand = 0; self.martyr = 0; self.bless_big = False; self.pray_bonus = 0; self.mir_plus = 0
        self.inspired = []; self.news = False; self.mmult = False; self.burned_rnd = 0
        if self.rnd > R['predel_raundov']:
            self.stuck = True
            for h in self.H.values():
                h.alive = False; h.hp = 0
            self.L('   Предел раундов: бой засчитан поражением')
            self.over = True; self.won = False
            return
        # эффекты начала раунда
        if self.vigil:
            if P.faith >= R['bdenie_porog']:
                self.draw_cards(self.P, 1)
            self.vigil = False
        if self.banner_keep:
            P.shield += self.banner_keep; self.banner_keep = 0
        self.banner = False
        if self.doll_dmg > 0 and e.hp > 0:
            d = self.doll_dmg; self.doll_dmg = 0; self.doll = 0
            self.L(f'   Кукла вуду бьёт врага на {d} и разрушается'); self.hit(self.M, d); self.st('kukla_udarila', d)
        vs = [v for v in self.vows if v[0] == 'start']
        self.vows = [v for v in self.vows if v[0] != 'start']
        for _, eff, _, me, card in vs:
            if e.hp > 0:
                self.L(f'   Обет «{card.name}» срабатывает'); eff(self, Ctx(me, card))
        if self.rot_val and e.hp > 0:
            e.porcha += self.rot_val
        self.rot_val = 0; self.rot = False
        for c in self.phx:
            if any(x is c for x in M.exiled):
                M.exiled = [x for x in M.exiled if x is not c]; M.hand.append(c); self.st('feniks_vernulsya')
                self.L(f'   «{c.name}» возвращается в руку')
        self.phx = []
        if not self.keep:
            self.charges = 0
        self.keep = False
        if e.hp <= 0:
            self.over = True; self.won = True
        self.L(f'   Рука {M.name}: {", ".join(c.name for c in M.hand)} (мана {M.mana}, заряды {self.charges})')
        self.L(f'   Рука {P.name}: {", ".join(c.name for c in P.hand)} (вера {P.faith})')

    def _hazard(self, k, why):
        h = self.H[k]
        if not h.alive:
            return
        h.hp -= 1; h.lost_hp_fight = True
        if not self.planning:
            h.taken += 1
        self.L(f'      {why}: {h.name} −1 → {h.hp}')
        if k == self.M:
            self.gain_faith(1, 'союзник')
        if h.hp <= 0:
            h.hp = 0; h.alive = False; self.L(f'      *** {h.name} падает! ***')

    def end_hero_phase(self):
        """Конец фазы героев (вызывается, только если враг жив)."""
        e = self.E; M = self.H[self.M]
        if not self.planning and e.hp > 0:
            vs = [v for v in self.vows if v[0] == 'endhp' and v[2] < self.rnd]
            self.vows = [v for v in self.vows if not (v[0] == 'endhp' and v[2] < self.rnd)]
            for _, eff, _, me, card in vs:
                if e.hp > 0:
                    self.L(f'   Обет «{card.name}» срабатывает'); eff(self, Ctx(me, card))
            if self.news and M.plays_rnd >= self.R['blagaya_vest_kart']:
                self.own_faith(self.R['blagaya_vest_vera'])
            self.news = False
        if self.late_dmg and e.hp > 0:
            d = self.late_dmg; self.late_dmg = 0; self.hit(self.M, d)
        self.late_dmg = 0
        M.next_bonus = 0
        for c in [c for c in M.hand if 'sgoraet_v_ruke' in c.tags]:
            M.hand = [x for x in M.hand if x is not c]
            self._exile(self.M, c)
            if 'hranit_zaryady' in c.tags:
                self.keep = True
        self.rot_cap = e.porcha if self.rot else 0
        if any(f[1] == 'pit' for f in self.feats) and self.dmg_phase >= 6 and e.hp > 0:
            e.hp = max(0, e.hp - 2); self.L(f'      Провал в полу: враг теряет ещё 2 → {e.hp}')
        if self.rot and not self.planning:
            self.rot_val = e.porcha
        if not self.planning:
            self.st('vera_summa', self.H[self.P].faith); self.st('vera_zamerov')

    def track_hp(self):
        if self.planning:
            return
        for h in self.H.values():
            self.min_frac = min(self.min_frac, max(0, h.hp) / h.maxhp)

    def finish_round(self):
        """Конец фазы героев, ход врага, конец раунда."""
        e = self.E
        if self.over:
            return
        alive = lambda: any(h.alive for h in self.H.values())
        if e.hp > 0 and alive():
            self.end_hero_phase()
        if e.hp <= 0:
            self._end(True); return
        it = e.intent
        M, P = self.H[self.M], self.H[self.P]
        self.L(f'   Враг: {it["text"]}' + (f' (+{e.buff})' if e.buff else '') + (' (−1 Вспышка)' if self.flash_weak else '') +
               f' | щиты: {M.name} {M.shield}, {P.name} {P.shield}')
        self.enemy_act(it)
        self.track_hp()
        if e.traits.get('golem') and not e.knocked and e.cracks:
            e.cracks = 0
        if any(f[1] == 'draft' for f in self.feats):
            al = self.alive_ids()
            if al:
                self._hazard(max(al, key=lambda x: self.H[x].hp), 'Сквозняк')
        for h in self.H.values():
            h.shield = 0; h.vanguard = False
            h.disc += h.hand; h.hand = []
        e.porcha = 0
        self.track_hp()
        if e.deckmode:
            e.ddisc.append(e.intent)
        else:
            e.idx += 1
        self.L(f'   Итог раунда: {e.name} {e.hp}/{e.maxhp}; {M.name} {M.hp}, {P.name} {P.hp}; вера {P.faith}')
        if not alive():
            self._end(False)

    def _end(self, won):
        self.over = True; self.won = won
        self.L(f'   ИТОГ БОЯ: {"победа" if won else "поражение"} за {self.rnd} р.')

    def check_over(self):
        if self.E.hp <= 0 and not self.over:
            self._end(True)
        elif not any(h.alive for h in self.H.values()) and not self.over:
            self._end(False)
        return self.over

    def result(self):
        return dict(won=self.won, rounds=self.rnd, stuck=self.stuck,
                    taken={k: h.taken for k, h in self.H.items()},
                    hp_loss={k: self.start_hp[k] - h.hp for k, h in self.H.items()},
                    end_hp={k: h.hp for k, h in self.H.items()},
                    min_frac=self.min_frac, enemy=self.E.d.eid, stats=dict(self.stats))


# ---------------------------------------------------------------- имена для выражений в картах (с точки зрения владельца карты)
VARS = {
    'vera': lambda f, h, a: f.H[f.P].faith,
    'mana': lambda f, h, a: h.mana,
    'zaryady': lambda f, h, a: f.charges,
    'porcha': lambda f, h, a: f.E.porcha,
    'vrag_zdorove': lambda f, h, a: f.E.hp,
    'vrag_maks_zdorove': lambda f, h, a: f.E.maxhp,
    'ruka': lambda f, h, a: len(h.hand),
    'zashchita_v_ruke': lambda f, h, a: int(any(c.kind == 'защита' for c in h.hand)),
    'shchit': lambda f, h, a: h.shield,
    'shchit_soyuznika': lambda f, h, a: a.shield,
    'szhzheno_v_raunde': lambda f, h, a: f.burned_rnd,
    'soyuznik_szheg': lambda f, h, a: a.burned_by_ally_rnd,
    'soyuznik_popadal': lambda f, h, a: a.hits_rnd,
    'soyuznik_popadal_proshlyj': lambda f, h, a: a.hits_last,
    'soyuznik_poluchil_shchit': lambda f, h, a: a.shielded_rnd,
    'soyuznik_avangard': lambda f, h, a: int(a.vanguard),
    'soyuznik_blagoslovlen': lambda f, h, a: int(a.blessed),
    'soyuznik_vzyal': lambda f, h, a: a.drew_rnd,
    'soyuznik_sbrosil': lambda f, h, a: int(a.discarded),
    'soyuznik_poteryal_proshlyj': lambda f, h, a: a.taken_last,
    'ja_sbrosil': lambda f, h, a: h.disc_rnd,
    'sygrano_mnoj_do': lambda f, h, a: h.plays_rnd,
    'kart_iz_ruki': lambda f, h, a: h.hand_plays_rnd,
    'sygrano_soyuznikom': lambda f, h, a: a.plays_rnd,
    'vidov_kart': lambda f, h, a: len(f.kinds_rnd & {'атака', 'защита', 'вера', 'молитва'}),
    'molitv_v_raunde': lambda f, h, a: f.pray_rnd,
    'ranenyh': lambda f, h, a: sum(1 for x in f.H.values() if x.alive and x.hp < x.maxhp),
    'blagoslovenij_v_boyu': lambda f, h, a: f.bless_trig_fight,
    'blagoslovenie_srabotalo_proshlyj': lambda f, h, a: f.bless_trig_last,
}
