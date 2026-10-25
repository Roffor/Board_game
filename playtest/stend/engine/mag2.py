# -*- coding: utf-8 -*-
"""Новые правила мага (решения Никиты 2026-10-24) и операции его банка идей (heroes/mag/idei-kart.md).

Правила включаются, если в колоде мага есть карты банка (nabor bank / legendarka) или в правилах
mag_pravila_2026_10_24: 1. Старые бои (золотые тесты) идут по прежним правилам.
  - Жетон Подношения: маг получает его, когда кто угодно сжёг 2+ карты за один розыгрыш; строки Подношения
    тратят жетон. Жетоны держатся весь бой (допущение Claude).
  - Порча — индикатор: на враге она есть или нет, каждое попадание сильнее на porcha_sila; снимается в конце
    раунда. Легендарка «Глубокий сглаз» — жетоны Порчи до porcha_maks_zhetonov.
  - Долг духам: мана или карты сейчас, плата в начале следующего хода из маны. Не хватило маны — остаток долга
    переходит дальше (дешёвого обхода нет).

Операции (регистрируются в effects.OPS):
  zheton: X / potrat_zheton: {n, v}         получить жетоны Подношения / потратить до n (в v — сколько)
  mana_v_dolg: X / dolg: X                  мана сейчас, долг столько же / просто долг
  otdaj_dolg: {n, v}                        отдать до n долга маной сейчас
  spisat_dolg: {n, v}                       списать до n долга без маны
  otlozhit_dolg: {rost}                     весь долг на ход позже, растёт на rost
  pri_oplate: [эффект]                      когда долг будет отдан полностью
  soderzhanie: {vid: uron|shchit, n}        «пока платишь»: в начале хода плата растёт, эффект каждый ход
  sbros_potom: {komu, n}                    в следующий ход сбросить n карт
  otlozhit_kartu: 1                         лучшая карта руки — в следующий ход в руку и бесплатно
  sygraj_v_dolg: {otkuda: ruka|verh}        сыграть карту бесплатно, её цена — в долг
  vklad: {n, plus}                          отдать n маны, в следующий ход n + plus
  zalog: {mana}                             карта из руки под планшет, мана в долг; долг отдан — карта вернётся
  skidka: X                                 в этом ходу карты стоят на X меньше
  snyat_porchu: {v} / porcha_derzhitsya: X  снять Порчу / Порча не снимается X концов раунда
  sygraj_szhzhennuyu: 1 / vernut_potom: 1   сыграть лучшую сожжённую бесплатно / вернуть её в руку в следующий ход
  szhech_kolodu: {v} / verh_iz_szhzhennyh / zameshaj_szhzhennye / snyat_shchit_vraga / uderzhat
  do_konca_raunda: {флаг: X}                флаги раунда (список в ROUND_FLAGS)"""
from .effects import op, X, compile_block, who, store, Ctx, EffectError

ROUND_FLAGS = {
    'osy': 'каждая следующая сыгранная магом карта наносит X урона',
    'udvoit_soyuznika': 'следующее попадание союзника вдвое',
    'soyuznik_nakladyvaet': 'следующее попадание союзника накладывает Порчу',
    'dvojnaya_porcha': 'бонус Порчи на следующем попадании мага дважды',
    'porcha_shchit': 'пока на враге Порча, щиты героев больше на X',
    'zloradstvo': 'когда Порча срабатывает, щит магу X',
    'bol_v_porchu': 'союзник получил урон — Порча в начале следующего раунда',
    'zerkalo': 'если на враге Порча, его атака бьёт и его',
    'zapertyj_shchit': 'пока на враге Порча, он не получает щит',
    'chuzhoj_shchit': 'если на враге Порча, его щит достаётся магу на следующий раунд',
    'pepel_dobor': 'когда сжигается любая карта, маг берёт карту',
    'teplyj_pepel': 'каждая карта, сожжённая союзником, даёт магу X щита',
    'goryashchaya_metka': 'пока на враге Порча, каждая сожжённая карта бьёт его на X',
    'topka': 'каждая сожжённая магом карта даёт ману',
    'poslednij_vzdoh': 'сжигаемая из руки карта мага сначала срабатывает',
    'smena_spisyvaet': 'смена благословений списывает жетон долга',
    'udar_soyuznika_platit': 'попадание союзника гасит жетон долга',
    'plechom': 'союзник получил щит — маг получает X щита',
}


class M2:
    """Состояние новых правил мага на бой."""
    def __init__(self):
        self.ptok = 0; self.debt = 0; self.debt2 = 0; self.paid = 0
        self.debt_disc = {}; self.upkeep = []; self.free_next = []; self.free_ids = set(); self.ret_next = []
        self.credit = 0; self.zalog = []; self.interest = False; self.on_pay = []; self.burnpay = False
        self.keep_porcha = 0; self.ptoks = 0; self.next_porcha = False
        self.ash = []; self.keep_cards = []; self.rf = {}; self.skidka = 0; self.osy_card = None

    def clone(self):
        m = M2.__new__(M2); m.__dict__ = dict(self.__dict__)
        for k in ('debt_disc', 'rf'):
            setattr(m, k, dict(getattr(self, k)))
        for k in ('upkeep', 'free_next', 'ret_next', 'zalog', 'on_pay', 'ash', 'keep_cards'):
            setattr(m, k, list(getattr(self, k)))
        m.upkeep = [list(u) for u in self.upkeep]; m.free_ids = set(self.free_ids)
        return m


def enabled(f, decks):
    if f.R.get('mag_pravila_2026_10_24', 0):
        return True
    return any(c.set in ('bank', 'legendarka') for c in decks.get(f.M, []))


# ================================================================ хуки движка
def cost_of(f, h, card):
    m = f.m2; d = card.d
    c = d.cost
    if d.cost_expr is not None:
        c = d.cost_expr(f, Ctx(h.id, card))
    if id(card) in m.free_ids:
        return 0
    c -= m.skidka
    lg = h.legend.get('pepelnyj_tron')
    if lg is not None and any(card is x for x in m.ash) and f.bl[h.id] == 'sol':
        c -= int(lg.get('sol_skidka', 1))
    if 'pozhiranie' in d.tags:
        c -= len(h.disc)
    return max(0, int(c))


def can_debt(f, h, card):
    d = card.d
    if d.debt_expr is None:
        return False
    return bool(d.debt_expr(f, Ctx(h.id, card)))


def pay_cost(f, h, card):
    """Оплатить цену: маной, а для карт «в долг» — долгом. False — сыграть нельзя."""
    m = f.m2; c = cost_of(f, h, card)
    if 'pozhiranie' in card.d.tags:
        need = max(0, card.d.cost - m.skidka) - c        # столько карт сброса сжечь вместо маны
        for _ in range(max(0, need)):
            if h.disc:
                x = min(h.disc, key=lambda y: y.value); h.disc = [y for y in h.disc if y is not x]; f._exile(h.id, x)
    if h.mana >= c:
        h.mana -= c
        return True
    if can_debt(f, h, card):
        m.debt += c; f.st('v_dolg')
        return True
    return False


def after_mage_play(f, h, card):
    m = f.m2
    m.free_ids.discard(id(card))
    if any(card is x for x in m.ash):              # сыграна из зоны сожжённых — возвращается туда
        m.ash = [x for x in m.ash if x is not card]
        if any(card is x for x in h.disc):
            h.disc = [x for x in h.disc if x is not card]; h.exiled.append(card)
        lg = h.legend.get('pepelnyj_tron')
        if lg is not None and f.bl[h.id] == 'lun':
            f.shield(h.id, int(lg.get('lun_shchit', 1)))
    if m.rf.get('osy') and card is not m.osy_card and f.E.hp > 0:
        f.hit(h.id, m.rf['osy'])


def porcha(f, n):
    e = f.E; m = f.m2
    if n <= 0:
        return
    lg = f.H[f.M].legend.get('glubokij_sglaz')
    if lg is not None:
        add = 2 if f.bl[f.M] == 'sol' else 1
        m.ptoks = min(int(f.R.get('porcha_maks_zhetonov', 6)), m.ptoks + add)
        e.porcha = m.ptoks * int(f.R.get('porcha_zheton', 1))
    else:
        e.porcha = max(e.porcha, int(f.R.get('porcha_sila', 2)))


def end_round_porcha(f):
    """Конец раунда: Порча снимается (кроме «держится» и Лунарис Глубокого сглаза)."""
    e = f.E; m = f.m2
    if m.keep_porcha > 0:
        m.keep_porcha -= 1
        return
    lg = f.H[f.M].legend.get('glubokij_sglaz')
    if lg is not None and f.bl[f.M] == 'lun' and m.ptoks > 0:
        m.ptoks -= 1; e.porcha = m.ptoks * int(f.R.get('porcha_zheton', 1))
        return
    e.porcha = 0; m.ptoks = 0


def on_exile(f, owner, c):
    m = f.m2; rf = m.rf
    if rf.get('pepel_dobor'):
        f.draw(f.M, 1)
    if rf.get('teplyj_pepel') and owner == f.P:
        f.shield(f.M, rf['teplyj_pepel'])
    if rf.get('goryashchaya_metka') and f.E.porcha > 0 and f.E.hp > 0:
        f._raw_hit(f.M, rf['goryashchaya_metka'])
    if rf.get('topka') and owner == f.M:
        f.H[f.M].mana += 1


def hit_mod(f, hid, n):
    """Изменить попадание до брони и щита врага. Возвращает новое n."""
    m = f.m2; rf = m.rf
    if hid == f.P and n > 0:
        if rf.get('udvoit_soyuznika'):
            n *= 2; rf['udvoit_soyuznika'] = 0
        if rf.get('udar_soyuznika_platit') and m.debt > 0:
            m.debt -= 1
    if hid == f.M and n > 0 and m.debt + m.debt2 > 0:
        lg = f.H[f.M].legend.get('plata_duham')
        if lg is not None and f.bl[f.M] == 'sol' and f.E.hp > n + f.E.porcha:
            k = min(m.debt + m.debt2, n); _write_off(f, k); n -= k; f.H[f.M].mana += k; f.st('plata_duham', k)
    return n


def after_hit(f, hid):
    rf = f.m2.rf
    if hid == f.P and rf.get('soyuznik_nakladyvaet'):
        rf['soyuznik_nakladyvaet'] = 0; porcha(f, 1)


def raw_hit_mod(f, hid, dmg):
    rf = f.m2.rf; e = f.E
    if e.porcha > 0:
        if hid == f.M and rf.get('dvojnaya_porcha'):
            dmg += e.porcha; rf['dvojnaya_porcha'] = 0
        if rf.get('zloradstvo'):
            f.shield(f.M, rf['zloradstvo'])
    return dmg


def shield_mod(f, hid, n):
    m = f.m2; rf = m.rf
    if rf.get('porcha_shchit') and f.E.porcha > 0:
        n += rf['porcha_shchit']
    if hid == f.M and m.debt + m.debt2 > 0:
        lg = f.H[f.M].legend.get('plata_duham')
        if lg is not None and f.bl[f.M] == 'lun':
            k = min(m.debt + m.debt2, n); _write_off(f, k); n -= k; f.H[f.M].mana += k; f.st('plata_duham', k)
    return n


def after_shield(f, hid, n):
    rf = f.m2.rf
    if hid == f.P and n > 0 and rf.get('plechom'):
        f.H[f.M].shield += rf['plechom']


def on_deal(f, k, n):
    if k == f.P and n > 0 and f.m2.rf.get('bol_v_porchu'):
        f.m2.next_porcha = True


def enemy_shield(f, n):
    """Сколько щита враг получает на самом деле."""
    rf = f.m2.rf
    if f.E.porcha > 0 and rf.get('chuzhoj_shchit'):
        f.next_shields[f.M] = f.next_shields.get(f.M, 0) + n
        return 0
    if f.E.porcha > 0 and rf.get('zapertyj_shchit'):
        return 0
    return n


def enemy_attack(f, n):
    rf = f.m2.rf
    if rf.get('zerkalo') and f.E.porcha > 0 and f.E.hp > 0:
        rf['zerkalo'] = 0; f.E.hp = max(0, f.E.hp - n); f.st('zerkalo', n)


def on_swap(f):
    m = f.m2
    if m.rf.get('smena_spisyvaet') and m.debt + m.debt2 > 0:
        _write_off(f, 1)


def _write_off(f, k):
    m = f.m2
    a = min(m.debt, k); m.debt -= a; k -= a
    m.debt2 = max(0, m.debt2 - k)
    _check_paid(f)


def _check_paid(f):
    m = f.m2
    if m.debt + m.debt2 == 0:
        if m.zalog:
            f.H[f.M].hand += m.zalog; m.zalog = []
        effs = m.on_pay; m.on_pay = []
        for eff, me, card in effs:
            if f.E.hp > 0:
                eff(f, Ctx(me, card))


def start_round(f):
    """Начало раунда (после добора и маны): долг, содержание, отложенные карты."""
    m = f.m2; M = f.H[f.M]
    m.rf = {}; m.skidka = 0; m.osy_card = None
    m.free_ids = set()
    if m.credit:
        M.mana += m.credit; m.credit = 0
    due = m.debt; m.paid = 0
    if due:
        if m.burnpay:
            for _ in range(2):
                if f._top(f.M) is not None:
                    f._exile(f.M, M.draw.pop())
            pay = due; m.burnpay = False
        else:
            pay = min(due, M.mana); M.mana -= pay
        m.debt -= pay; m.paid = pay; f.st('dolg_otdan', pay)
        if m.interest and m.debt > 0:
            porcha(f, 1); m.debt += 1
    m.interest = False
    m.debt += m.debt2; m.debt2 = 0
    if due:
        _check_paid(f)
    for u in list(m.upkeep):
        vid, n, cost, card = u
        if M.mana >= cost and M.alive:
            M.mana -= cost; u[2] = cost + 1
            if vid == 'uron':
                f.hit(f.M, n)
            else:
                f.shield(f.M, n); f.shield(f.P, n)
        else:
            m.upkeep = [x for x in m.upkeep if x is not u]
            if card is not None:
                M.disc.append(card)
    for hid, n in m.debt_disc.items():
        f.discard(hid, n)
    m.debt_disc = {}
    if m.next_porcha:
        m.next_porcha = False; porcha(f, 1)
    for c in m.free_next:
        M.hand.append(c); m.free_ids.add(id(c))
    m.free_next = []
    for c in m.ret_next:
        if any(c is x for x in M.exiled):
            M.exiled = [x for x in M.exiled if x is not c]; M.hand.append(c)
    m.ret_next = []
    ash_open(f)


def ash_open(f):
    """Карты, которые можно играть из зоны сожжённых, на время фазы героев кладутся в руку (бот видит до 4 лучших)."""
    m = f.m2; M = f.H[f.M]
    lg = M.legend.get('pepelnyj_tron')
    cands = [c for c in M.exiled if lg is not None or 'iz_pepla' in c.tags]
    cands = sorted(cands, key=lambda c: -c.value)[:4]
    if cands:
        M.exiled = [x for x in M.exiled if not any(x is c for c in cands)]
        M.hand += cands; m.ash = list(cands)


def finish_round(f):
    """Перед сбросом руки: карты из зоны сожжённых возвращаются туда, удержанные остаются в руке."""
    m = f.m2; M = f.H[f.M]
    if m.ash:
        back = [c for c in M.hand if any(c is x for x in m.ash)]
        M.hand = [c for c in M.hand if not any(c is x for x in back)]; M.exiled += back; m.ash = []
    keep = [c for c in M.hand if any(c is x for x in m.keep_cards)]
    m.keep_cards = []
    return keep


# ================================================================ операции
def _n(arg, w, key='n', default=1):
    if isinstance(arg, dict):
        return X(arg.get(key, default), w)
    return X(arg if arg is not None else default, w)


@op('zheton')
def _tok(arg, w):
    n = X(arg, w)
    def run(f, ctx):
        k = int(n(f, ctx)); f.m2.ptok += k; f.st('zhetonov_polucheno', k)
    return run


@op('potrat_zheton')
def _spend_tok(arg, w):
    n = _n(arg, w); v = (arg or {}).get('v') if isinstance(arg, dict) else None
    def run(f, ctx):
        k = min(f.m2.ptok, max(0, int(n(f, ctx)))); f.m2.ptok -= k; store(ctx, v, k)
    return run


@op('mana_v_dolg')
def _loan(arg, w):
    n = X(arg, w)
    def run(f, ctx):
        k = int(n(f, ctx)); f.H[f.M].mana += k; f.m2.debt += k
    return run


@op('dolg')
def _debt(arg, w):
    n = X(arg, w)
    def run(f, ctx):
        f.m2.debt += int(n(f, ctx))
    return run


@op('otdaj_dolg')
def _pay(arg, w):
    n = _n(arg, w, default='dolg'); v = arg.get('v') if isinstance(arg, dict) else None
    def run(f, ctx):
        M = f.H[f.M]; m = f.m2
        k = min(m.debt + m.debt2, M.mana, max(0, int(n(f, ctx))))
        M.mana -= k; _write_off(f, k); store(ctx, v, k)
    return run


@op('spisat_dolg')
def _writeoff(arg, w):
    n = _n(arg, w, default='dolg'); v = arg.get('v') if isinstance(arg, dict) else None
    def run(f, ctx):
        m = f.m2; k = min(m.debt + m.debt2, max(0, int(n(f, ctx)))); _write_off(f, k); store(ctx, v, k)
    return run


@op('otlozhit_dolg')
def _postpone(arg, w):
    r = X((arg or {}).get('rost', 0), w)
    def run(f, ctx):
        m = f.m2
        if m.debt:
            m.debt2 += m.debt + int(r(f, ctx)); m.debt = 0
    return run


@op('pri_oplate')
def _onpay(arg, w):
    eff, sub = compile_block(arg, w + ' (pri_oplate)')
    def run(f, ctx):
        if f.planning:
            f.est_f += 2.0
            return
        f.m2.on_pay = f.m2.on_pay + [(eff, ctx.me, ctx.card)]
    return run, sub


@op('soderzhanie')
def _upkeep(arg, w):
    n = X(arg['n'], w); vid = arg.get('vid', 'uron'); c0 = X(arg.get('plata', 1), w)
    def run(f, ctx):
        if f.planning:
            f.est_f += 1.5 * n(f, ctx)
            return
        f.m2.upkeep = f.m2.upkeep + [[vid, int(n(f, ctx)), int(c0(f, ctx)), ctx.card]]
        f._post.append('ubrat')
    return run


@op('sbros_potom')
def _disc_later(arg, w):
    n = X(arg.get('n', 1), w); komu = arg.get('komu', 'ja')
    def run(f, ctx):
        for h in who(f, ctx, komu):
            f.m2.debt_disc[h] = f.m2.debt_disc.get(h, 0) + int(n(f, ctx))
        if f.planning:
            f.est_f -= 1.0 * int(n(f, ctx)) * len(who(f, ctx, komu))
    return run


@op('otlozhit_kartu')
def _setaside(arg, w):
    def run(f, ctx):
        h = f.H[ctx.me]
        cands = [c for c in f._free_cards(h.hand) if c is not ctx.card]
        if not cands:
            return
        c = max(cands, key=lambda x: (x.cost, x.value))
        h.hand = [x for x in h.hand if x is not c]
        if f.planning:
            f.est_f += 0.8 * c.value
        else:
            f.m2.free_next = f.m2.free_next + [c]
    return run


@op('sygraj_v_dolg')
def _iou(arg, w):
    src = (arg or {}).get('otkuda', 'ruka')
    def run(f, ctx):
        h = f.H[ctx.me]
        if src == 'verh':
            c = f._top(ctx.me)
            if c is None:
                return
            if f.planning:
                f.est += 3.0; f.m2.debt += 1
                return
            h.draw.pop()
        else:
            cands = [c for c in f._free_cards(h.hand) if c is not ctx.card]
            if not cands:
                return
            c = max(cands, key=lambda x: (x.cost, x.value))
            h.hand = [x for x in h.hand if x is not c]
        f.m2.debt += c.cost
        h.hand.append(c); f.m2.free_ids.add(id(c))
        f.play(ctx.me, c, 0, 0)
    return run


@op('vklad')
def _deposit(arg, w):
    n = X(arg.get('n', 1), w); plus = X(arg.get('plus', 1), w)
    def run(f, ctx):
        M = f.H[f.M]; k = min(M.mana, int(n(f, ctx))); M.mana -= k
        if f.planning:
            f.est_f += 1.3 * (k + plus(f, ctx))
        else:
            f.m2.credit += k + int(plus(f, ctx))
    return run


@op('zalog')
def _pledge(arg, w):
    mana = X(arg.get('mana', 2), w)
    def run(f, ctx):
        h = f.H[ctx.me]
        cands = [c for c in f._free_cards(h.hand) if c is not ctx.card]
        if not cands:
            return
        c = min(cands, key=lambda x: x.value)
        h.hand = [x for x in h.hand if x is not c]; f.m2.zalog = f.m2.zalog + [c]
        k = int(mana(f, ctx)); h.mana += k; f.m2.debt += k
    return run


@op('skidka')
def _discount(arg, w):
    n = X(arg, w)
    def run(f, ctx):
        f.m2.skidka += int(n(f, ctx))
    return run


@op('snyat_porchu')
def _unporcha(arg, w):
    v = (arg or {}).get('v') if isinstance(arg, dict) else None
    def run(f, ctx):
        had = int(f.E.porcha > 0); f.E.porcha = 0; f.m2.ptoks = 0; store(ctx, v, had)
    return run


@op('porcha_derzhitsya')
def _keepporcha(arg, w):
    n = X(arg, w)
    def run(f, ctx):
        f.m2.keep_porcha = max(f.m2.keep_porcha, int(n(f, ctx)))
    return run


@op('sygraj_szhzhennuyu')
def _play_burned(arg, w):
    def run(f, ctx):
        h = f.H[ctx.me]
        cands = [c for c in h.exiled if c is not ctx.card]
        if not cands:
            return
        if f.planning:
            f.est += 0.9 * max(c.value for c in cands)
            return
        c = max(cands, key=lambda x: x.value)
        h.exiled = [x for x in h.exiled if x is not c]
        h.hand.append(c); f.m2.free_ids.add(id(c))
        if not f.play(ctx.me, c, 0, 0):
            h.hand = [x for x in h.hand if x is not c]; h.exiled.append(c)
    return run


@op('vernut_potom')
def _return_later(arg, w):
    def run(f, ctx):
        h = f.H[ctx.me]
        cands = [c for c in h.exiled if c is not ctx.card and not any(c is x for x in f.m2.ret_next)]
        if not cands:
            return
        c = max(cands, key=lambda x: x.value)
        if f.planning:
            f.est_f += 0.7 * c.value
        else:
            f.m2.ret_next = f.m2.ret_next + [c]
    return run


@op('szhech_kolodu')
def _burn_deck(arg, w):
    v = (arg or {}).get('v') if isinstance(arg, dict) else None
    def run(f, ctx):
        h = f.H[ctx.me]; k = 0
        while h.draw:
            f._exile(ctx.me, h.draw.pop()); k += 1
        store(ctx, v, k)
    return run


@op('verh_iz_szhzhennyh')
def _burned_top(arg, w):
    def run(f, ctx):
        h = f.H[ctx.me]
        if not h.exiled:
            return
        c = max(h.exiled, key=lambda x: x.value)
        h.exiled = [x for x in h.exiled if x is not c]; h.draw.append(c)
    return run


@op('zameshaj_szhzhennye')
def _reshuffle_burned(arg, w):
    def run(f, ctx):
        h = f.H[ctx.me]
        back = [c for c in h.exiled if not any(c is x for x in f.m2.ash)]
        h.exiled = [c for c in h.exiled if any(c is x for x in f.m2.ash)]
        h.draw = back + h.draw
        if not f.planning:
            f.rng.shuffle(h.draw)
    return run


@op('snyat_shchit_vraga')
def _unshield(arg, w):
    return lambda f, ctx: setattr(f.E, 'shield', 0)


@op('uderzhat')
def _retain(arg, w):
    def run(f, ctx):
        h = f.H[ctx.me]
        cands = [c for c in h.hand if c is not ctx.card]
        if cands:
            c = max(cands, key=lambda x: x.value); f.m2.keep_cards = f.m2.keep_cards + [c]
            if f.planning:
                f.est_f += 0.5 * c.value
    return run


@op('do_konca_raunda')
def _round_flags(arg, w):
    fs = {}
    for k, v in arg.items():
        if k not in ROUND_FLAGS:
            raise EffectError(f'{w}: флаг раунда «{k}» не из {sorted(ROUND_FLAGS)}')
        fs[k] = X(v, w)
    def run(f, ctx):
        for k, fn in fs.items():
            f.m2.rf[k] = fn(f, ctx)
            if k == 'osy':
                f.m2.osy_card = ctx.card
    return run


@op('zhech_po_rozygryshu')
def _burnpay(arg, w):
    return lambda f, ctx: setattr(f.m2, 'burnpay', True)


@op('procenty')
def _interest(arg, w):
    return lambda f, ctx: setattr(f.m2, 'interest', True)


@op('uslovnyj_zheton')
def _cond_tok(arg, w):
    """«Считается, что сжёг две»: жетон Подношения сразу."""
    return lambda f, ctx: setattr(f.m2, 'ptok', f.m2.ptok + 1)


@op('effekt_kart_ruki')
def _fire_burned(arg, w):
    """Голод пламени: сжечь карту из руки; если у неё есть строка Подношения, она срабатывает без жетона."""
    def run(f, ctx):
        h = f.H[ctx.me]
        cands = [c for c in f._free_cards(h.hand) if c is not ctx.card]
        if not cands:
            return
        off = [c for c in cands if c.d.offering]
        c = max(off, key=lambda x: x.value) if off else min(cands, key=lambda x: x.value)
        h.hand = [x for x in h.hand if x is not c]; f._exile(ctx.me, c)
        if c.d.offering and c.d.variants:
            c.d.variants[0].effect(f, Ctx(ctx.me, c, 1))
    return run
