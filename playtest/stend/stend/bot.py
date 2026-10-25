# -*- coding: utf-8 -*-
"""Бот пары игроков: перебирает планы на раунд и выбирает лучший по оценке.
Перенос бота из старого симулятора (engine.py best_plan/evaluate + burn10 + priest.py) без изменения логики.

Движок про бота ничего не знает: бот — это объект Choices плюс функция play_round(fight)."""
import random
from collections import Counter

from engine import Choices

OIL_V = 2.5          # цена одного масла в оценке плана
K_TOP = 18           # сколько лучших планов каждого героя скрещивать
K_ALLY = 6           # сколько ещё планов мага с картами «от союзника» добавить
NEAR = 2.2           # «равноценный» план: хуже лучшего меньше чем на одно здоровье героя
ERR_P = 0.25         # шанс выбрать второй по качеству план (живые игроки ошибаются)


def plan_key(seq):
    return tuple(sorted((a[1], a[2].cid, a[3], a[4]) for a in seq if a[0] == 'play'))


class Bot(Choices):
    def __init__(self, seed, err_p=ERR_P):
        self.rng = random.Random(seed * 7919 + 17)
        self.err_p = err_p
        self.errors = 0
        self.var_rounds = []      # (сколько равноценных планов, сколько из них отличаются 2+ картами)
        self.plans = 0

    # ------------------------------------------------ решения внутри эффектов
    def pray_pick(self, f, cards, uselimit):
        """Молитва: сыграть ту открытую карту и тот вариант, что дают лучшую оценку хода."""
        best = None
        for c in cards:
            for oi in range(len(c.d.variants)):
                g = f.plan_copy()
                P = g.H[g.P]
                P.hand.append(c)
                if uselimit:
                    if P.plays >= P.maxplays:
                        continue
                else:
                    P.maxplays += 1
                s = self.evaluate(f, [('play', f.P, c, oi, 0)], start=g)
                if best is None or s > best[0]:
                    best = (s, c, oi)
        return None if best is None else (best[1], best[2])

    @staticmethod
    def wants_blessing(f):
        if f.bl_swapped:
            return False
        if any('blag' in c.tags for h in f.H.values() for c in h.hand):
            return True
        return any(name in ('neugasimaya_vera', 'dvojnaya_molitva', 'shipy_zaslona') for name in f.H[f.P].legend)

    # ------------------------------------------------ оценка плана
    def evaluate(self, base, seq, start=None):
        g = (start or base).plan_copy()
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
        k = base.threat_k()
        s = (base.E.hp - g.E.hp) * k
        if killed:
            s += 12
        for hid in base.order:
            h0, h1 = base.H[hid], g.H[hid]
            w = 2.2 if h0.hp > 7 else 3.2
            s += w * (h1.hp - h0.hp)
            if h0.alive and not h1.alive:
                s -= 20
            if h1.alive and h1.blessed and not killed:
                s += 1.5
            s += 1.0 * h1.pend
        if not any(h.alive for h in g.H.values()):
            s -= 1000
        if not killed:
            s += 0.6 * (g.H[g.P].faith - base.H[base.P].faith)
            s -= 1.5 * (g.E.buff - base.E.buff) + 0.3 * g.E.shield
        s -= 0.6 * (g.H[g.M].exiled_n - base.H[base.M].exiled_n)
        if base.nm:          # новые правила мага: жетон Подношения — ценность, долг — будущая мана
            s += 1.8 * (g.m2.ptok - base.m2.ptok)
            s -= 1.6 * ((g.m2.debt + g.m2.debt2) - (base.m2.debt + base.m2.debt2))
        s -= OIL_V * (base.oil - g.oil)
        # подсказки ценности будущего
        alive_e = g.E.hp > 0
        if g.rot and alive_e:
            s += 1.5 * g.rot_cap
        if alive_e:
            s += 1.2 * (g.doll - base.doll)
        s += g.est - base.est
        if alive_e:
            s += g.est_f - base.est_f
            s += 0.9 * k * (g.doll_dmg - base.doll_dmg)
            if g.banner:
                s += 0.8 * g.H[g.P].shield
        return s

    # ------------------------------------------------ перебор планов
    @staticmethod
    def order_key(f):
        def key(a):
            if a[0] == 'fdisc':
                return 0 if a[1] == f.P else 6
            return a[2].d.order
        return key

    def gen_mage(self, f):
        h = f.H[f.M]
        if not h.alive:
            return [[]]
        hand = h.hand; out = []
        # карты, которые могут дать ману (Топливо при сжигании, Шёпот с Подношением), расширяют бюджет плана;
        # невыполнимые планы отсеет розыгрыш на копии
        bonus = sum(int(c.d.bot.get('mana_v_plane', 0)) for c in hand)
        def rec(i, mana, cur):
            if i == len(hand):
                out.append(list(cur)); return
            rec(i + 1, mana, cur)
            c = hand[i]
            cc = self.mage_cost(f, h, c)
            if cc <= mana:
                pays = {'1': (0, 1), '2': (0, 1), 'r': (0, 1, 2, 3)}.get(c.d.offering, (0,))
                for oi in range(len(c.d.variants)):
                    for off in pays:
                        cur.append(('play', f.M, c, oi, off))
                        rec(i + 1, mana - cc, cur)
                        cur.pop()
        rec(0, h.mana + bonus, [])
        return out

    @staticmethod
    def mage_cost(f, h, c):
        """Цена карты для перебора планов: по новым правилам мага — с выражением цены, скидками и «в долг»."""
        if not f.nm:
            return c.cost
        from engine import mag2
        if mag2.can_debt(f, h, c):
            return 0
        return mag2.cost_of(f, h, c)

    def gen_priest(self, f):
        h = f.H[f.P]
        if not h.alive:
            return [[]]
        hand = h.hand; out = []
        def rec(i, left, cur):
            if i == len(hand):
                out.append(list(cur)); return
            rec(i + 1, left, cur)
            c = hand[i]
            w = 2 if 'dve_karty' in c.tags else (0 if 'mozhet_vne_limita' in c.tags else 1)
            if left >= max(1, w) or (w == 0 and left >= 0):
                for oi in range(len(c.d.variants)):
                    cur.append(('play', f.P, c, oi, 0)); rec(i + 1, left - w, cur); cur.pop()
        rec(0, h.maxplays - h.plays, [])
        return out

    def best_plan(self, f, base=None):
        base = base or f
        key = self.order_key(f)
        def top(plans, extra=0):
            sc = []
            f.ignore_stone = bool(f.E.traits.get('golem'))
            for pl in plans:
                sc.append((self.evaluate(base, sorted(pl, key=key), start=f), len(sc), pl))
            f.ignore_stone = False
            sc.sort(key=lambda x: (-x[0], x[1]))
            out = [x[2] for x in sc[:K_TOP]]
            if extra:
                more = [x[2] for x in sc[K_TOP:] if any(a[0] == 'play' and a[2].d.bot.get('soyuznaya') for a in x[2])]
                out += more[:extra]
            return out
        tm, tp = top(self.gen_mage(f), extra=K_ALLY), top(self.gen_priest(f))
        dv = [()]
        for hid in f.order:
            if f.feat_available(hid) is not None and f.H[hid].hand:
                dv = dv + [d + (hid,) for d in dv]
        best = (-1e9, []); ranked = {}
        for m in tm:
            for p in tp:
                for d in dv:
                    seq = sorted(m + p + [('fdisc', hid) for hid in d], key=key)
                    s = self.evaluate(base, seq, start=f)
                    if s > best[0] + 1e-9:
                        best = (s, seq)
                    pk = plan_key(seq)
                    if pk not in ranked or s > ranked[pk][0]:
                        ranked[pk] = (s, seq)
        return best, sorted(ranked.values(), key=lambda x: -x[0])

    # ------------------------------------------------ раунд
    def play_round(self, f):
        """Фаза героев: решения до плана (вспышки), выбор плана, розыгрыш с перепланом после добора."""
        e = f.E
        if e.traits.get('hidden') and not f.dark and not f.revealed and f.oil >= 2 and e.intent['type'] == 'удар':
            f.reveal()
        variants = [None]
        incoming = sum(a[1] * a[3] for a in e.intent['acts'] if a[0] == 'atk')
        if f.oil >= 1 and not f.hidden() and incoming >= 4 and not f.flash_weak:
            variants += [hid for hid in f.order if f.H[hid].alive]
        self.plans += 1
        best = None; allp = {}
        # смена благословений — только если в руках или легендарках есть что-то про Лунарис/Соларис
        swaps = [False, True] if self.wants_blessing(f) else [False]
        variants = [(v, sw) for sw in swaps for v in variants]
        for v in variants:
            g = f.plan_copy()
            if v[1]:
                g.swap_blessings()
            if v[0] is not None:
                g.flash(v[0])
            (s, seq), ranked = self.best_plan(g, base=f)
            if best is None or s > best[0] + 1e-9:
                best = (s, v, seq)
            for s2, seq2 in ranked[:8]:
                pk = (v, plan_key(seq2))
                if pk not in allp or s2 > allp[pk][0]:
                    allp[pk] = (s2, v, seq2)
        cand = sorted(allp.values(), key=lambda x: -x[0])
        s_pass = self.evaluate(f, [])
        gain = best[0] - s_pass
        near = [c for c in cand if c[0] >= best[0] - NEAR]
        bk = Counter(plan_key(best[2]))
        def diff(c):
            ck = Counter(plan_key(c[2])); return sum(((bk - ck) + (ck - bk)).values())
        self.var_rounds.append((max(1, len(near)), sum(1 for c in near if diff(c) >= 3)))
        if len(cand) > 1 and gain > 0 and self.rng.random() < self.err_p:
            sec = cand[1]
            if sec[0] - s_pass >= 0.5 * gain:
                best = sec; self.errors += 1
                f.L('   [игроки выбирают не лучший, а второй по качеству вариант]')
        if best[1][1]:
            f.swap_blessings()
        if best[1][0] is not None:
            f.flash(best[1][0])
        seq = best[2]
        while seq:
            if f.E.hp <= 0 or not any(h.alive for h in f.H.values()):
                break
            f.reserved = [a[2] for a in seq if a[0] == 'play']
            replan = False
            for a in seq:
                ok = f.apply(a)
                if f.E.hp <= 0:
                    break
                if ok and a[0] == 'play' and a[2].d.replan:
                    replan = True; break
            f.reserved = []
            if not replan or f.E.hp <= 0:
                break
            (s, seq), _ = self.best_plan(f)


def run_fight(game, decks, enemy, location, seed, log=False, err_p=ERR_P):
    """Сыграть один бой ботом. Возвращает (результат движка, бот, бой)."""
    from engine import Fight
    bot = Bot(seed, err_p)
    f = Fight(game, decks, enemy, location, seed, bot, log=log)
    while not f.over:
        f.start_round()
        if f.over:
            break
        bot.play_round(f)
        f.check_over()
        f.finish_round()
    return f.result(), bot, f
