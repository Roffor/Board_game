# -*- coding: utf-8 -*-
"""Движок прогона «Двое во тьме». Настоящая тасовка (random.Random с записанным сидом),
все трекеры ведутся по правилам из design/. Бой разыгрывает перебор вариантов на раунд
(обе руки открыты, карты по одной); решения вне боя (путь, награды, отдых, события)
принимаются вручную и читаются из decisions.json."""
import random, json, sys, os
from cards import *

HERO_NAMES = {'M': 'Маг', 'P': 'Жрец'}
MAXHP = {'M': 16, 'P': 18}
REST_HEAL = 6
FALLEN_HP = 3
OIL_V = 2.5
POTION_V = 3.0
EST = {1: 4, 2: 5, 'elite': 6, 'boss': 7}

# ---- нормы времени для двух живых игроков (секунды)
T = dict(setup=360, map=30, layout=15, fight_setup=60, elite_setup=30, round_overhead=45,
         discuss_base=15, discuss_per_card=2, card=10, choice=5, offering=6, replan=10,
         enemy=10, enemy_act=5, reshuffle=15, fight_end=30, upgrade=90, legend=100,
         event=110, rest=60, forge=60, cache=40, flash=15, potion=15, fallen=20)


class NeedDecision(Exception):
    pass


class Hero:
    def __init__(self, key, deck):
        self.key, self.name = key, HERO_NAMES[key]
        self.maxhp = MAXHP[key]; self.hp = self.maxhp
        self.deck = list(deck)      # постоянная колода 15 карт
        self.draw, self.hand, self.disc, self.exiled = [], [], [], []
        self.shield = 0; self.vanguard = False; self.blessed = False; self.alive = True
        self.mana = 0; self.carry = 0; self.plays = 0; self.maxplays = 3; self.faith = 0
        self.discarded = False; self.free_off = False; self.free_given = False
        self.lost_hp_fight = False; self.last_hit = 0; self.exiled_n = 0; self.pend = 0
        self.legend = None

    def clone(self):
        h = Hero.__new__(Hero)
        h.__dict__ = dict(self.__dict__)
        h.hand = list(self.hand); h.disc = list(self.disc); h.exiled = list(self.exiled)
        return h


class Enemy:
    def __init__(self, data, tier, threat=False):
        self.name = data['name']; self.tier = tier
        self.maxhp = data['hp'] + (3 if threat else 0); self.hp = self.maxhp
        self.traits = data.get('traits', {}); self.shield = 0; self.porcha = 0
        self.buff = 1 if threat else 0
        self.cycle = data.get('cycle'); self.idx = 0
        self.deckmode = 'deck' in data
        self.dpile = list(data['deck']) if self.deckmode else None; self.ddisc = []
        self.intent = None
        self.stone = 0; self.cracks = 0; self.knocked = False; self.hitters = []

    def clone(self):
        e = Enemy.__new__(Enemy)
        e.__dict__ = dict(self.__dict__)
        e.hitters = list(self.hitters)
        return e


class Game:
    def __init__(self, seed, decisions):
        self.seed = seed; self.rng = random.Random(seed)
        self.decisions = list(decisions); self.dec_i = 0
        self.sim = False; self.t = 0; self.log = []; self.stages = []
        self.oil = 6; self.potions = []; self.keys = 0; self.traces = []; self.threat_next = None
        self.H = {'M': Hero('M', M_cards()), 'P': Hero('P', P_cards())}
        self.E = None; self.stats = dict(rounds=0, fights=0, free_off=0, exiles=0, faith_gain=0,
                                        porcha_trig=0, flashes=0, potions_used=0, falls=0,
                                        fight_rounds=[], dark_rounds=0, discards=0, plans=0)
        self.reserved = []
        self.feats = []; self.feat_used = []; self.fdisc_round = []
        self.rnd = 0; self.target = None; self.flash_weak = False; self.flasher = None
        self.revealed = False; self.porcha_trig = False; self.dmg_phase = 0; self.mercy_used = False
        self.fight_kind = None

    # ------------------------------------------------ служебное
    def L(self, s):
        if not self.sim:
            self.log.append(s)

    def tick(self, sec):
        if not self.sim:
            self.t += sec

    def clone_sim(self):
        g = Game.__new__(Game)
        g.__dict__ = dict(self.__dict__)
        g.sim = True
        g.H = {k: h.clone() for k, h in self.H.items()}
        g.E = self.E.clone()
        g.potions = list(self.potions); g.feat_used = list(self.feat_used)
        g.fdisc_round = list(self.fdisc_round); g.reserved = list(self.reserved)
        g.stats = None
        return g

    def st(self, k, n=1):
        if not self.sim:
            self.stats[k] += n

    @property
    def dark(self):
        return self.oil <= 0

    def hidden(self):
        return self.dark or (self.E.traits.get('hidden') and not self.revealed)

    def decide(self, kind, prompt):
        if self.dec_i < len(self.decisions):
            d = self.decisions[self.dec_i]; self.dec_i += 1
            self.L(f'   [решение: {d}]')
            return d
        print('=' * 70); print('НУЖНО РЕШЕНИЕ #%d (%s)' % (self.dec_i, kind)); print(prompt)
        raise NeedDecision()

    def hs(self):
        m, p = self.H['M'], self.H['P']
        return f"Маг {m.hp}/{m.maxhp}, Жрец {p.hp}/{p.maxhp}, масло {self.oil}, зелья {self.potions or '—'}"

    # ------------------------------------------------ колоды
    def start_fight_decks(self):
        for h in self.H.values():
            h.draw = list(h.deck); self.rng.shuffle(h.draw)
            h.hand, h.disc, h.exiled = [], [], []
            h.exiled_n = 0; h.lost_hp_fight = False; h.shield = 0; h.vanguard = False; h.carry = 0
            keep = 0
            if h.key == 'P' and h.legend == 'Неугасимая вера':
                keep = min(3, h.faith)
            h.faith = keep if h.key == 'P' else 0

    def draw_cards(self, k, n):
        h = self.H[k]
        for _ in range(n):
            if not h.draw:
                if not h.disc:
                    return
                h.draw = h.disc; h.disc = []; self.rng.shuffle(h.draw)
                self.L(f'   {h.name}: колода кончилась, сброс перетасован ({len(h.draw)} карт).')
                self.tick(T['reshuffle'])
            h.hand.append(h.draw.pop())

    # ------------------------------------------------ операции карт
    def gain_faith(self, n, why):
        p = self.H['P']
        if n <= 0:
            return
        old = p.faith; p.faith = min(6, p.faith + n)
        if p.faith > old:
            self.st('faith_gain', p.faith - old)
            self.L(f'      +{p.faith - old} вера Жрецу ({why}) → {p.faith}')

    def hit(self, h, n):
        e = self.E
        if e.hp <= 0:
            return
        dmg = n + e.porcha
        if e.porcha > 0 and not self.porcha_trig:
            self.porcha_trig = True; self.st('porcha_trig')
            self.gain_faith(1, 'сработал статус союзника: Порча')
        self.H[h].last_hit = dmg
        if e.traits.get('golem'):
            if h not in e.hitters:
                e.hitters.append(h)
            if len(e.hitters) == 2 and e.stone > 0:
                e.stone = 0; e.knocked = True; e.cracks += 1
                self.L(f'      Каменный щит голема сбит (оба попали)! Трещин: {e.cracks}')
            if e.stone > 0:
                self.L(f'      Каменный щит держит удар ({dmg}): нужно попадание второго героя')
                dmg = 0
        a = min(e.shield, dmg); e.shield -= a; dmg -= a
        e.hp -= dmg; self.dmg_phase += dmg
        if e.hp <= 0:
            e.hp = 0
            self.L(f'      {e.name} повержен ({HERO_NAMES[h]})!')
            if h == 'M':
                self.gain_faith(1, 'союзник убил врага')

    def shield(self, h, n):
        if n and self.H[h].alive:
            self.H[h].shield += n

    def heal(self, h, n):
        x = self.H[h]
        if n and x.alive:
            x.hp = min(x.maxhp, x.hp + n)

    def porcha(self, n):
        self.E.porcha += n

    def bless(self, h):
        if self.H[h].alive:
            self.H[h].blessed = True
        if self.H['P'].legend == 'Двойное благословение' and self.H['P'].alive:
            self.H['P'].blessed = True

    def vanguard(self, h):
        self.H[h].vanguard = True
        if any(f[1] == 'narrow' for f in self.feats):
            self.shield(h, 1)

    def draw(self, h, n):
        if n <= 0:
            return
        if self.sim:
            self.H[h].pend += n
        else:
            self.draw_cards(h, n)

    def gain_mana(self, h, n):
        self.H[h].mana += n

    def burn_faith(self):
        p = self.H['P']; f = p.faith
        if p.legend == 'Милость бога' and not self.mercy_used and f > 0:
            self.mercy_used = True
            self.L('      Милость бога: вера не сжигается')
            return f
        p.faith = 0
        return f

    def spend_faith_shift(self, k):
        p = self.H['P']
        if p.faith >= k:
            p.faith -= k; self.shift()

    def extra_play(self, h):
        self.H[h].maxplays += 1

    def shift(self):
        e = self.E
        if e.deckmode:
            e.ddisc.append(e.intent); e.intent = self.draw_intent()
        else:
            e.idx += 1; e.intent = e.cycle[e.idx % len(e.cycle)]
        self.L(f'      Сдвиг намерения → {self.intent_str()}')
        self.roll_target()

    # ------------------------------------------------ враг
    def draw_intent(self):
        e = self.E
        if not e.dpile:
            e.dpile = e.ddisc; e.ddisc = []
            if not self.sim:
                self.rng.shuffle(e.dpile)
            self.L('   Колода намерений перетасована.')
        if self.sim:
            return e.dpile[-1] if e.dpile else e.intent
        return e.dpile.pop()

    def intent_str(self, full=True):
        i = self.E.intent
        if self.hidden() and not full:
            return f"[скрыто: {i['type']}]"
        return i['text'] + (f" (+{self.E.buff} усиление)" if self.E.buff else '')

    def roll_target(self):
        alive = [k for k in 'MP' if self.H[k].alive]
        need = any(a[0] == 'atk' and a[2] in ('single', 'moth') for a in self.E.intent['acts'])
        self.target = None
        if need and alive:
            self.target = self.rng.choice(alive) if (not self.sim and len(alive) > 1) else alive[0]

    def plan_intent(self):
        """Что пара знает о намерении при планировании."""
        if not self.hidden():
            return self.E.intent
        t = self.E.intent['type']; e = self.E
        est = EST['boss'] if e.tier == 'boss' else EST['elite'] if e.tier == 'elite' else EST[e.tier]
        if t == 'удар':
            return I('удар', [A(est)], '?')
        if t == 'защита':
            return I('защита', [('shield', 10), A(est // 2)], '?')
        return I('усиление', [('buff', 2)], '?')

    def choose(self, cands, n):
        # игроки выбирают, кто примет удар: минимизируем потерю здоровья
        def loss(k):
            h = self.H[k]; x = max(0, n - (BLESS if h.blessed else 0) - h.shield)
            return (x >= h.hp, x, -h.hp)
        return min(cands, key=loss)

    def targets(self, tgt, n):
        alive = [k for k in 'MP' if self.H[k].alive]
        if not alive:
            return []
        if tgt == 'all':
            return alive
        if tgt == 'moth':
            c = [k for k in alive if self.H[k].vanguard or self.flasher == k]
            if c:
                return [self.choose(c, n)]
            tgt = 'single'
        if tgt == 'single':
            van = [k for k in alive if self.H[k].vanguard]
            if van:
                return [self.choose(van, n)]
            return [self.target if self.target in alive else alive[0]]
        if tgt == 'weakest':
            m = min(self.H[k].hp for k in alive)
            return [self.choose([k for k in alive if self.H[k].hp == m], n)]
        if tgt == 'unshielded':
            c = [k for k in alive if self.H[k].shield == 0] or alive
            return [self.choose(c, n)]
        return [alive[0]]

    def deal(self, k, n, src='удар'):
        h = self.H[k]
        if not h.alive:
            return
        if h.blessed and n > 0:
            n = max(0, n - BLESS); h.blessed = False
            self.L(f'      Благословение на {h.name}: удар слабее на {BLESS}')
        a = min(h.shield, n); h.shield -= a; n -= a
        if n > 0:
            h.hp -= n; h.lost_hp_fight = True
            self.L(f'      {h.name} теряет {n} ({src}) → {max(0, h.hp)}')
            if k == 'M':
                self.gain_faith(1, 'союзник получил урон')
            if h.hp <= 0:
                h.hp = 0; h.alive = False; h.shield = 0
                self.L(f'      *** {h.name} падает! ***'); self.st('falls')

    def enemy_act(self, intent):
        e = self.E
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

    # ------------------------------------------------ особенности комнат
    def feat_available(self, hk):
        if hk in self.fdisc_round:
            return None
        for f in self.feats:
            if f[0] == 'discard':
                if f[1] == 'altar' and ('altar' in self.feat_used or self.oil >= 6):
                    continue
                return f
        for f in self.feats:
            if f[0] == 'double' and f[1] not in self.feat_used:
                return f
        return None

    def lowest_free(self, hk):
        h = self.H[hk]
        cands = [c for c in h.hand if not any(c is r for r in self.reserved)]
        if not cands:
            return None
        return min(cands, key=lambda c: c.value)

    def do_fdisc(self, hk):
        f = self.feat_available(hk)
        c = self.lowest_free(hk)
        if f is None or c is None:
            return False
        h = self.H[hk]
        h.hand.remove(c); h.disc.append(c); h.discarded = True; self.fdisc_round.append(hk)
        self.st('discards')
        self.L(f'   {h.name} сбрасывает «{c.name}» ради особенности комнаты')
        self.tick(T['card'])
        if f[0] == 'discard':
            if f[1] == 'altar':
                self.feat_used.append('altar'); self.oil = min(6, self.oil + 1); self.L(f'      Алтарь: +1 масло → {self.oil}')
            elif f[1] == 'bones':
                e = self.E; a = min(e.shield, 1); e.shield -= a; e.hp = max(0, e.hp - (1 - a)); self.dmg_phase += 1 - a
                self.L(f'      Костница: 1 урон → враг {e.hp}')
            elif f[1] == 'pillar':
                self.shield(hk, 1)
            elif f[1] == 'sealheal':
                self.heal(hk, 1)
            elif f[1] == 'draftshield':
                self.shield(ally(hk), 1)
        if hk == 'P' and not self.H['M'].free_given:
            self.H['M'].free_off = True; self.H['M'].free_given = True
            self.L('      Маг «берёт»: союзник сбросил карту → одно Подношение без изгнания в этом раунде')
        if (any(x[1] == 'seals' for x in self.feats) and 'seals' not in self.feat_used
                and 'M' in self.fdisc_round and 'P' in self.fdisc_round):
            self.feat_used.append('seals'); self.L('      Печати предков (оба сбросили): сдвиг намерения'); self.shift()
        return True

    def end_hero_phase(self):
        if any(f[1] == 'pit' for f in self.feats) and self.dmg_phase >= 6 and self.E.hp > 0:
            self.E.hp = max(0, self.E.hp - 2); self.L(f'      Провал в полу: враг теряет ещё 2 → {self.E.hp}')

    # ------------------------------------------------ розыгрыш карты
    def play(self, hk, card, opt, want_off):
        h = self.H[hk]
        if not h.alive or not any(c is card for c in h.hand):
            return False
        if hk == 'M' and h.mana < card.cost:
            return False
        if hk == 'P' and h.plays >= h.maxplays:
            return False
        h.hand.remove(card)
        self.reserved = [r for r in self.reserved if r is not card]
        if hk == 'M':
            h.mana -= card.cost
        h.plays += 1
        off = 0; offtxt = ''
        if card.offering and want_off:
            if h.free_off:
                h.free_off = False; off = 1; offtxt = ' [Подношение без изгнания]'; self.st('free_off')
            else:
                x = self.lowest_free(hk)
                if x is not None:
                    h.hand.remove(x); h.exiled.append(x); h.exiled_n += 1; off = 1
                    offtxt = f' [Подношение: изгнана «{x.name}»]'; self.st('exiles')
            if off and h.legend == 'Двойное подношение':
                off = 2
        e0 = self.E.hp
        label = card.opts[opt][0]
        if not self.sim:
            self.L(f'   {h.name}: «{card.name}»' + (f' ({label})' if label else '') + offtxt)
        card.opts[opt][1](self, hk, off)
        h.disc.append(card)
        if not self.sim:
            self.tick(T['card'] + (T['choice'] if len(card.opts) > 1 else 0) + (T['offering'] if off else 0))
            if self.E.hp != e0:
                self.L(f'      враг {e0} → {self.E.hp}' + (f' (Порча {self.E.porcha})' if self.E.porcha else ''))
        return True

    def apply(self, act):
        if act[0] == 'play':
            return self.play(act[1], act[2], act[3], act[4])
        if act[0] == 'fdisc':
            return self.do_fdisc(act[1])
        return False

    # ------------------------------------------------ планирование раунда
    def gen_mage(self):
        h = self.H['M']
        if not h.alive:
            return [[]]
        hand = h.hand; out = []
        def rec(i, mana, cur, offs):
            if i == len(hand):
                left = len(hand) - len(cur)
                if offs <= left + (1 if (h.free_off or not h.free_given) else 0):
                    out.append(list(cur))
                return
            rec(i + 1, mana, cur, offs)
            c = hand[i]
            if c.cost <= mana:
                for oi in range(len(c.opts)):
                    for off in ((0, 1) if c.offering else (0,)):
                        extra = 1 if (c.cid == 'whisper' and off) else 0
                        cur.append(('play', 'M', c, oi, off))
                        rec(i + 1, mana - c.cost + extra, cur, offs + off)
                        cur.pop()
        rec(0, h.mana, [], 0)
        return out

    def gen_priest(self):
        h = self.H['P']
        if not h.alive:
            return [[]]
        hand = h.hand; n = h.maxplays - h.plays; out = []
        def rec(i, left, cur):
            if i == len(hand):
                out.append(list(cur)); return
            rec(i + 1, left, cur)
            if left > 0:
                c = hand[i]
                for oi in range(len(c.opts)):
                    cur.append(('play', 'P', c, oi, 0)); rec(i + 1, left - 1, cur); cur.pop()
        rec(0, n, [])
        return out

    @staticmethod
    def prio(a):
        if a[0] == 'fdisc':
            return 0 if a[1] == 'P' else 6
        c = a[2]
        if a[1] == 'M':
            if 'porcha' in c.tags: return 1
            if 'porcha2' in c.tags: return 1.5
            if 'draw' in c.tags: return 2
            if c.cid == 'u_ehit': return 4.5
            return 3
        if 'draw' in c.tags: return 3.5
        if 'miracle' in c.tags: return 5
        return 4

    def evaluate(self, base, seq):
        g = self.clone_sim()
        g.reserved = [a[2] for a in seq if a[0] == 'play']
        for a in seq:
            g.apply(a)
            if g.E.hp <= 0:
                break
        if g.E.hp > 0:
            g.end_hero_phase()
        killed = g.E.hp <= 0
        if not killed:
            g.enemy_act(g.plan_intent())
        s = (base.E.hp - g.E.hp) * 1.0
        if killed:
            s += 12
        for k in 'MP':
            h0, h1 = base.H[k], g.H[k]
            w = 2.2 if h0.hp > 7 else 3.2
            s += w * (h1.hp - h0.hp)
            if h0.alive and not h1.alive:
                s -= 20
            if h1.alive and h1.blessed and not killed:
                s += 1.5
            s += 1.0 * h1.pend
        if not any(g.H[k].alive for k in 'MP'):
            s -= 1000
        if not killed:
            s += 0.6 * (g.H['P'].faith - base.H['P'].faith)
            s -= 1.5 * (g.E.buff - base.E.buff) + 0.3 * g.E.shield
        s -= 0.6 * (g.H['M'].exiled_n - base.H['M'].exiled_n)
        s -= OIL_V * (base.oil - g.oil)
        return s

    def best_plan(self, base=None, K=18):
        base = base or self
        mp = self.gen_mage(); pp = self.gen_priest()
        def top(plans):
            sc = []
            for p in plans:
                seq = sorted(p, key=self.prio)
                sc.append((self.evaluate(base, seq), len(sc), p))
            sc.sort(key=lambda x: (-x[0], x[1]))
            return [x[2] for x in sc[:K]]
        tm, tp = top(mp), top(pp)
        dv = [()]
        for hk in 'MP':
            if self.feat_available(hk) is not None and self.H[hk].hand:
                dv = dv + [d + (hk,) for d in dv]
        best = (-1e9, [])
        for m in tm:
            for p in tp:
                for d in dv:
                    seq = sorted(m + p + [('fdisc', hk) for hk in d], key=self.prio)
                    s = self.evaluate(base, seq)
                    if s > best[0] + 1e-9:
                        best = (s, seq)
        return best

    # ------------------------------------------------ фаза героев (исполнение)
    def apply_pre(self, pre):
        for p in pre:
            if p[0] == 'flash':
                self.oil -= 1; self.flash_weak = True; self.flasher = p[1]
                self.L(f'   Вспышка ({HERO_NAMES[p[1]]}): −1 масло → {self.oil}; враг бьёт на 1 слабее')
                self.tick(T['flash']); self.st('flashes')
            elif p[0] == 'potion':
                self.potions.remove(p[1]); self.st('potions_used'); self.tick(T['potion'])
                self.L(f'   Зелье «{p[1]}»' + (f' → {HERO_NAMES[p[2]]}' if p[2] else ''))
                if p[1] == 'щит':
                    self.shield(p[2], 4)
                elif p[1] == 'урон':
                    e = self.E; a = min(e.shield, 4); e.shield -= a; e.hp = max(0, e.hp - (4 - a))
                elif p[1] == 'сдвиг':
                    self.shift()

    def hero_phase(self):
        # правила-эвристики для зелий, которые не зависят от плана
        for k in 'MP':
            h = self.H[k]
            if h.alive and h.hp <= 5 and 'лечение' in self.potions:
                self.potions.remove('лечение'); self.heal(k, 4); self.st('potions_used'); self.tick(T['potion'])
                self.L(f'   Зелье «лечение» → {h.name} ({h.hp})')
        if self.oil == 0 and 'масло' in self.potions and (self.E.tier in ('elite', 'boss') or self.E.traits.get('dark')):
            self.potions.remove('масло'); self.oil = 2; self.st('potions_used'); self.tick(T['potion'])
            self.L('   Зелье «масло»: масло 0 → 2, фонарь снова горит')
            self.L(f'   Намерение теперь видно: {self.intent_str()}')
        if self.rnd == 1 and self.E.tier in ('elite', 'boss') and 'добор' in self.potions and self.H['P'].alive:
            self.potions.remove('добор'); self.draw_cards('P', 2); self.st('potions_used'); self.tick(T['potion'])
            self.L('   Зелье «добор»: Жрец берёт 2 карты')
        if self.E.traits.get('hidden') and not self.dark and not self.revealed and self.oil >= 2 \
                and self.E.intent['type'] == 'удар':
            self.oil -= 1; self.revealed = True; self.flasher = 'P' if self.H['P'].alive else 'M'
            self.st('flashes'); self.tick(T['flash'])
            self.L(f'   Вспышка: открыть намерение Скрытня (−1 масло → {self.oil}): {self.intent_str()}')
        # варианты «до плана»: вспышка-ослабление и зелья
        variants = [[]]
        vis = not self.hidden()
        incoming = sum(a[1] * a[3] for a in self.E.intent['acts'] if a[0] == 'atk')
        if self.oil >= 1 and vis and incoming >= 4 and not self.flash_weak:
            variants += [[('flash', k)] for k in 'MP' if self.H[k].alive]
        for pt in sorted(set(self.potions)):
            if pt == 'щит':
                variants += [[('potion', 'щит', k)] for k in 'MP' if self.H[k].alive]
            elif pt in ('урон', 'сдвиг'):
                variants.append([('potion', pt, None)])
        self.st('plans')
        best = None
        for v in variants:
            g = self.clone_sim(); g.apply_pre(v)
            s, seq = g.best_plan(base=self)
            s -= POTION_V * sum(1 for x in v if x[0] == 'potion')
            if best is None or s > best[0] + 1e-9:
                best = (s, v, seq)
        cards = len(self.H['M'].hand) + len(self.H['P'].hand)
        self.tick(T['discuss_base'] + T['discuss_per_card'] * cards)
        self.apply_pre(best[1])
        seq = best[2]
        while True:
            if self.E.hp <= 0 or not any(self.H[k].alive for k in 'MP'):
                return
            if not seq:
                break
            self.reserved = [a[2] for a in seq if a[0] == 'play']
            replan = False
            for a in seq:
                drew0 = sum(len(self.H[k].hand) for k in 'MP')
                ok = self.apply(a)
                if self.E.hp <= 0:
                    self.reserved = []; return
                if ok and a[0] == 'play' and 'draw' in a[2].tags:
                    replan = True; break
            self.reserved = []
            if not replan:
                break
            self.tick(T['replan'])
            s, seq = self.best_plan()

    # ------------------------------------------------ бой
    def fight(self, edata, tier, loc, threat=False):
        self.E = Enemy(edata, tier, threat)
        e = self.E
        self.feats = loc['feats']; self.feat_used = []; self.mercy_used = False
        self.fight_kind = tier
        self.start_fight_decks()
        for h in self.H.values():
            h.maxplays = 3
        t0 = self.t
        self.tick(T['fight_setup'] + (T['elite_setup'] if tier in ('elite', 'boss') else 0))
        if e.deckmode:
            self.rng.shuffle(e.dpile)
        self.L(f'БОЙ: {e.name} ({e.hp} здоровья) в локации «{loc["name"]}». ' +
               '; '.join(f[2] for f in loc['feats']) + (' [Угроза: +3 здоровья, +1 к атакам]' if threat else ''))
        self.L(f'   Старт: {self.hs()}; вера {self.H["P"].faith}')
        self.rnd = 0; start_hp = {k: self.H[k].hp for k in 'MP'}
        oil0 = self.oil
        while True:
            self.rnd += 1; self.st('rounds')
            if self.dark:
                self.st('dark_rounds')
            # 1. намерение
            if e.deckmode:
                e.intent = self.draw_intent()
            else:
                e.intent = e.cycle[e.idx % len(e.cycle)]
            self.flash_weak = False; self.flasher = None; self.revealed = False; self.porcha_trig = False
            self.dmg_phase = 0; self.fdisc_round = []
            if e.traits.get('golem'):
                e.stone = e.traits['golem']; e.knocked = False; e.hitters = []
            self.roll_target()
            nxt = ''
            if e.deckmode and e.dpile:
                nxt = f"; следующее: {e.dpile[-1]['type']}"
            tg = f"; цель броском: {HERO_NAMES[self.target]}" if self.target else ''
            self.L(f' Раунд {self.rnd}. Намерение: {self.intent_str(full=False)}{tg}{nxt}. '
                   f'{e.name} {e.hp}/{e.maxhp}' + (f', щит {e.shield}' if e.shield else '') +
                   (f', каменный щит {e.stone}, трещин {e.cracks}' if e.traits.get("golem") else '') +
                   (' | ТЕМНОТА' if self.dark else ''))
            self.tick(T['round_overhead'])
            # опасности начала раунда
            if any(f[1] == 'drip' for f in self.feats):
                for k in 'MP':
                    if self.H[k].alive:
                        self.H[k].hp -= 1; self.H[k].lost_hp_fight = True
                        self.L(f'      Капель: {self.H[k].name} −1 → {self.H[k].hp}')
                        if k == 'M':
                            self.gain_faith(1, 'союзник получил урон')
                        if self.H[k].hp <= 0:
                            self.H[k].hp = 0; self.H[k].alive = False; self.L(f'      *** {self.H[k].name} падает! ***')
            # 2. добор
            for k in 'MP':
                h = self.H[k]
                self.draw_cards(k, max(0, 6 - len(h.hand)))
                h.mana = 3 + h.carry if k == 'M' else 0; h.carry = 0
                h.plays = 0; h.maxplays = 3; h.discarded = False; h.free_off = False; h.free_given = False
                h.last_hit = 0; h.pend = 0
            m, p = self.H['M'], self.H['P']
            self.L(f'   Рука Мага: {", ".join(c.name for c in m.hand)} (мана {m.mana})')
            self.L(f'   Рука Жреца: {", ".join(c.name for c in p.hand)} (вера {p.faith})')
            # 3. общая фаза
            self.hero_phase()
            if e.hp > 0 and any(self.H[k].alive for k in 'MP'):
                self.end_hero_phase()
            if e.hp <= 0:
                break
            # 4. враг
            it = e.intent
            self.L(f'   Враг: {it["text"]}' + (f' (+{e.buff})' if e.buff else '') +
                   (f' (+{e.traits["dark"]} в темноте)' if self.dark and e.traits.get('dark') else '') +
                   (' (−1 Вспышка)' if self.flash_weak else '') +
                   f' | щиты: Маг {m.shield}, Жрец {p.shield}' +
                   (' | Авангард: ' + ','.join(HERO_NAMES[k] for k in 'MP' if self.H[k].vanguard) if (m.vanguard or p.vanguard) else ''))
            self.enemy_act(it)
            self.tick(T['enemy'] + T['enemy_act'] * len(it['acts']))
            if e.traits.get('golem'):
                if not e.knocked and e.cracks:
                    e.cracks = 0; self.L('      Раунд без сбитого щита: трещины голема затянулись')
            # 5. конец раунда
            if any(f[1] == 'draft' for f in self.feats):
                al = [k for k in 'MP' if self.H[k].alive]
                if al:
                    k = max(al, key=lambda x: self.H[x].hp)
                    self.H[k].hp -= 1; self.H[k].lost_hp_fight = True; self.L(f'      Сквозняк: {self.H[k].name} −1 → {self.H[k].hp}')
                    if k == 'M':
                        self.gain_faith(1, 'союзник получил урон')
                    if self.H[k].hp <= 0:
                        self.H[k].hp = 0; self.H[k].alive = False; self.L(f'      *** {self.H[k].name} падает! ***')
            for k in 'MP':
                h = self.H[k]
                h.shield = 0; h.vanguard = False
                if k == 'M' and h.legend == 'Негаснущий очаг':
                    h.carry = min(2, h.mana)
                h.disc += h.hand; h.hand = []
            if self.H['M'].legend != 'Вечная Порча':
                e.porcha = 0
            if e.deckmode:
                e.ddisc.append(e.intent)
            else:
                e.idx += 1
            self.L(f'   Итог раунда: {e.name} {e.hp}/{e.maxhp}; {self.hs()}; вера {p.faith}')
            if not any(self.H[k].alive for k in 'MP'):
                break
        won = e.hp <= 0
        self.stats['fights'] += 1; self.stats['fight_rounds'].append((e.name, self.rnd))
        self.tick(T['fight_end'])
        for k in 'MP':
            h = self.H[k]; h.shield = 0; h.vanguard = False; h.blessed = False
            if won and not h.alive:
                h.alive = True; h.hp = FALLEN_HP; self.L(f'   {h.name} встаёт после боя с {FALLEN_HP} здоровья.')
                self.tick(T['fallen'])
        if won and e.traits.get('golem') and e.cracks:
            o = self.oil; self.oil = min(6, self.oil + min(2, e.cracks))
            self.L(f'   Трещины голема: +{self.oil - o} масла')
        res = dict(won=won, rounds=self.rnd, sec=self.t - t0,
                   hp_loss={k: start_hp[k] - self.H[k].hp for k in 'MP'})
        self.L(f'   ИТОГ БОЯ: {"победа" if won else "поражение"} за {self.rnd} р., ~{(self.t - t0) / 60:.1f} мин. {self.hs()}')
        return res
