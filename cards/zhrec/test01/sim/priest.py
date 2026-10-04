# -*- coding: utf-8 -*-
"""Длинный тест Жреца (2026-09-30), черновик колоды cards/zhrec/03. Поверх burn11 (маг заморожен на серии №11).
Механики Жреца:
- вера 0–6 от союзника (движок) и от своих карт (pf, множитель src.own — вариант В1 = 0), стартовая вера src.start;
- лимит 3 карты из руки; Молитва: открой pray.open верхних, сыграй одну бесплатно (лимит не тратит), остальные в сброс;
- Благословение: следующий удар по союзнику слабее на bless.n, не копится; «сработало» — сняло урон (наездники карт);
- доплата = сожги N веры (вариант опции с меткой PAY); Чудо = сожги всю веру;
- Обет: эффект в начале следующего раунда (или в конце следующей фазы героев);
- «вера-строка» карт F()/FB() переписывается режимом fmode: 1 порог, 2 линейно, 3 трата, 4 Чудо, 5 смесь по билдам.
Новая Кукла вуду мага: урон, принятый куклой, бьёт врага в начале следующего хода, потом кукла умирает."""
import engine as E
import cards as C
from cards import Card
import burn2
from burn2 import p
import burn11
from burn11 import B11Game, CFG, pools, CONCEPT as M_CONCEPT
from burn10 import B10Game
from burn9 import B9Game

DEFAULTS = dict(burn11.DEFAULTS)
DEFAULTS.update({
    'fmode': 6, 'f.thr': 4, 'f.lin': 4, 'f.cost': 2, 'f.mir': 3,
    'src.own': 1, 'src.start': 0,
    'bless.n': 3, 'bless.big': 5, 'pray.open': 2,
    'fut.pray': 4.0, 'fut.vow': 0.9, 'fut.scry': 0.4, 'fut.faith': 0.6, 'fut.guard': 2.0, 'fut.dolld': 0.9,
    'fut.misc': 1.0,
    # новая Кукла вуду мага
    'doll.hp': 3, 'doll.cost': 2,
})
PAY = ' +вера'
FB_MODE = {'С': 2, 'П': 1, 'Ч': 3}   # вариант Ф5 в фазе А
FB_MODE_A = {'С': 3, 'П': 3, 'Ч': 4}   # итог фазы А (16:50): Суд и Покровитель — трата, Чудотворец — Чудо


class PCard(Card):
    def __init__(self, cid, name, kind, text, opts, value=5, tags=(), build='', pr=None, fb=None):
        super().__init__(cid, name, 'P', kind, text, opts, value=value, tags=tags, branch=build)
        self.build = build; self.pr = pr; self.fb = fb


def fmode(card):
    m = p('fmode', 1)
    if m == 6:
        return FB_MODE_A.get(getattr(card, 'fb', None) or 'П', 3) if card is not None else 3
    if m == 5:
        return FB_MODE.get(getattr(card, 'fb', None) or 'П', 1) if card is not None else 1
    return m


def F(g, lo, hi, thr=None):
    """Вера-строка: значение между lo (без веры) и hi (с верой) по режиму."""
    P = g.H['P']; f = P.faith; m = fmode(g._cur)
    if m == 1:
        return hi if f >= (thr or p('f.thr', 4)) else lo
    if m == 2:
        k = thr or p('f.lin', 4)
        return lo + int((hi - lo) * f / k + 1e-9)
    if m == 3:
        if g._paid:
            return hi
        c = p('f.cost', 2)
        if g._pay and f >= c:
            P.faith -= c; g._paid = True; g.bst('f_spent', c)
            return hi
        return lo
    # m == 4: сожги всю веру, прибавка за каждую
    if g._paidX is None:
        if not g._pay or f <= 0:
            return lo
        g._paidX = f; P.faith = 0; g.bst('f_spent', f)
    return lo + int((hi - lo) * g._paidX / p('f.mir', 3) + 1e-9)


def FB(g, thr=None):
    """Логическая вера-строка («Вера 4+: ещё эффект»)."""
    P = g.H['P']; f = P.faith; m = fmode(g._cur)
    if m in (1, 2):
        return f >= (thr or p('f.thr', 4))
    if g._paid or g._paidX:
        return True
    c = p('f.cost', 2)
    if g._pay and f >= c:
        P.faith -= c; g._paid = True; g.bst('f_spent', c)
        return True
    return False


def one(fn):
    return [('', fn)]


def paid(g, n):
    """Доплата карты: сожги n веры. True — оплачено."""
    P = g.H['P']
    if P.faith >= n:
        P.faith -= n; g.bst('f_spent', n); g.bst('kick')
        return True
    return False


# ---------------------------------------------------------------- карты
BANK = {}      # cid -> фабрика
INFO = {}      # cid -> (номер в файле 03, билды)
START_CAND = []
UPGRADES = []


def card(num, cid, name, kind, text, opts, value=5, tags=(), build='', pr=None, fb=None):
    def mk():
        c = PCard(cid, name, kind, text() if callable(text) else text, opts, value=value, tags=tags, build=build, pr=pr, fb=fb)
        if fb and fmode(c) in (3, 4):
            o2 = []
            for lab, fn in c.opts:
                o2.append((lab, fn)); o2.append(((lab or 'эффект') + PAY, fn))
            c.opts = o2
        return c
    BANK[cid] = mk; INFO[cid] = (num, build)
    (START_CAND if num.startswith('С') else UPGRADES).append(cid)


A = 'P'
M = 'M'
# ---- стартовые кандидаты (25)
card('С01', 'z_kara', 'Кара', 'атака', '2 урона. Вера 4+: 3.', one(lambda g, h, o: g.hit(A, F(g, p('kara.lo', 2), p('kara.hi', 3)))), 5, fb='С')
card('С02', 'z_hammer', 'Светлый молот', 'атака', '1 урон и 2 щита себе. Вера 4+: 2 урона и 3 щита.',
     one(lambda g, h, o: (g.hit(A, F(g, 1, 2)), g.shield(A, F(g, 2, 3)))), 5, fb='С')
card('С03', 'z_verdict', 'Приговор', 'атака', 'Урон, равный вере (не меньше 2); вера не тратится.',
     one(lambda g, h, o: g.hit(A, max(p('verd.min', 2), g.H[A].faith))), 5)
card('С04', 'z_staff', 'Посох паломника', 'атака', '2 урона ИЛИ 2 щита себе. +1 вера.',
     [('урон', lambda g, h, o: (g.hit(A, 2), g.pf(1))), ('щит', lambda g, h, o: (g.shield(A, 2), g.pf(1)))], 4, tags=('faith',))
card('С05', 'z_fshield', 'Щит веры', 'защита', '3 щита себе или союзнику. Вера 4+: 5.',
     [('себе', lambda g, h, o: g.shield(A, F(g, 3, 5))), ('союзнику', lambda g, h, o: g.shield(M, F(g, 3, 5)))], 5, fb='П')
card('С06', 'z_lguard', 'Страж света', 'защита', 'Авангард. 3 щита себе. Вера 4+: ещё 2.',
     one(lambda g, h, o: (g.vanguard(A), g.shield(A, F(g, 3, 5)))), 5, tags=('vanguard',), fb='П')
card('С07', 'z_mlight', 'Чудо света', 'атака', 'Чудо: 2 урона за каждую веру (одним ударом).',
     one(lambda g, h, o: g.hit(A, p('mlight.k', 2) * g.burn_faith())), 5, tags=('miracle',))
card('С08', 'z_mint', 'Чудо заступничества', 'защита', 'Чудо: 2 щита за каждую веру, раздели между героями.',
     [('союзнику', lambda g, h, o: g.shield(M, 2 * g.burn_faith())), ('себе', lambda g, h, o: g.shield(A, 2 * g.burn_faith())),
      ('пополам', lambda g, h, o: (lambda f: (g.shield(A, f), g.shield(M, f)))(g.burn_faith()))], 5, tags=('miracle',))
card('С09', 'z_witness', 'Свидетель', 'вера', 'Ты и союзник берёте по 1 карте. Вера 4+: по 2.',
     one(lambda g, h, o: (lambda n: (g.draw(A, n), g.draw(M, n)))(F(g, 1, 2))), 4, tags=('draw',), fb='Ч')
card('С10', 'z_bless', 'Благословение', 'связка', 'Благословение союзнику. Если оно уже на нём — 2 щита ему и +1 вера.',
     one(lambda g, h, o: g.bless_or(lambda: (g.shield(M, 2), g.pf(1)))), 5, tags=('faith',))
card('С11', 'z_quiet', 'Тихая молитва', 'молитва', '+1 вера. Молитва.', one(lambda g, h, o: (g.pf(p('quiet.f', 1)), g.pray())), 5,
     tags=('draw', 'faith', 'prayer'))
card('С12', 'z_candle', 'Свеча', 'вера', '+2 веры. 1 щит себе.', one(lambda g, h, o: (g.pf(p('candle.f', 2)), g.shield(A, 1))), 3,
     tags=('faith',), pr=3.3)
card('С13', 'z_beads', 'Чётки', 'атака', '2 урона. Доплата: сожги 2 веры — вместо этого 5 урона.',
     [('', lambda g, h, o: g.hit(A, 2)), ('доплата', lambda g, h, o: g.hit(A, p('beads.big', 5) if paid(g, 2) else 2))], 5)
card('С14', 'z_conf', 'Исповедь', 'вера', 'Сбрось 1 карту из руки: +1 вера и возьми 1 карту.',
     one(lambda g, h, o: (g.pf(1), g.draw(A, 1)) if g.pdisc(1) else None), 3, tags=('draw', 'faith'))
card('С15', 'z_swsh', 'Меч и щит', 'атака', '2 урона и 2 щита союзнику.', one(lambda g, h, o: (g.hit(A, 2), g.shield(M, 2))), 5)
card('С16', 'z_mbell', 'Утренний звон', 'вера', '+1 вера. Если союзник в этом раунде уже сыграл 2+ карты — ещё +1 вера и возьми 1.',
     one(lambda g, h, o: (g.pf(1), (g.pf(1), g.draw(A, 1)) if g.m_plays_rnd >= 2 else None)), 4, tags=('faith',), pr=4.8)
card('С17', 'z_cheer', 'Слово ободрения', 'вера', 'Союзник берёт 1 карту. +1 вера.', one(lambda g, h, o: (g.draw(M, 1), g.pf(1))), 4,
     tags=('draw', 'faith'), pr=0.6)
card('С18', 'z_hair', 'Власяница', 'защита', '3 щита себе. Если в прошлом раунде тебя ранили — +2 веры.',
     one(lambda g, h, o: (g.shield(A, 3), g.pf(2) if g.p_taken_last > 0 else None)), 4, tags=('faith',))
card('С19', 'z_hands', 'Возложение рук', 'защита', '3 щита союзнику. Если на нём Благословение — +1 вера и ещё 2 щита.',
     one(lambda g, h, o: (g.shield(M, 3), (g.pf(1), g.shield(M, p('zhands.b', 2))) if g.H[M].blessed else None)), 4, tags=('faith',), pr=4.2)
card('С20', 'z_sermon', 'Проповедь', 'атака', '2 урона. Посмотри 2 верхние карты, положи обратно в любом порядке.',
     one(lambda g, h, o: (g.hit(A, 2), g.scry(2))), 5, pr=3.4)
card('С21', 'z_rod', 'Жезл осуждения', 'атака', '3 урона. Если веры 0 — только 1.', one(lambda g, h, o: g.hit(A, 3 if g.H[A].faith > 0 else 1)), 5)
card('С22', 'z_matins', 'Утреня', 'вера', 'Если это твоя первая карта в ходу — +2 веры. Иначе 3 щита себе.',
     one(lambda g, h, o: g.pf(2) if g.p_hand_plays == 1 else g.shield(A, 3)), 4, tags=('faith',), pr=3.2)
card('С23', 'z_pshield', 'Щит паломника', 'защита', '4 щита себе.', one(lambda g, h, o: g.shield(A, 4)), 4)
card('С24', 'z_censer', 'Кадило', 'атака', '1 урон и по 1 щиту каждому герою. Вера 3+: ещё по 1 щиту.',
     one(lambda g, h, o: (g.hit(A, 1), (lambda n: (g.shield(A, n), g.shield(M, n)))(F(g, 1, 2, thr=3)))), 4, fb='П')
card('С25', 'z_symbol', 'Символ веры', 'вера', 'Открой верхнюю карту. Если это карта веры — +2 веры и сбрось её; иначе возьми её в руку.',
     one(lambda g, h, o: g.symbol()), 4, tags=('draw', 'faith'))

# ---- Суд (20)
S = 'С'
card('Я01', 'y_last', 'Последний приговор', 'атака', 'Урон, равный вере ×2; вся вера сгорает. Если враг погиб — 2 веры остаются.',
     one(lambda g, h, o: g.last_verdict()), 6, tags=('miracle',), build=S)
card('Я02', 'y_right', 'Праведный удар', 'атака', '3 урона. Доплата: сожги 1 веру — ещё Благословение союзнику.',
     [('', lambda g, h, o: g.hit(A, p('right.d', 3))), ('доплата', lambda g, h, o: (g.hit(A, p('right.d', 3)), g.bless(M) if paid(g, 1) else None))],
     6, build=S)
card('Я03', 'y_hhammer', 'Молот небес', 'атака', '3 урона. Доплата: сожги 3 веры — вместо этого 9 урона.',
     [('', lambda g, h, o: g.hit(A, p('hh.d', 3))), ('доплата', lambda g, h, o: g.hit(A, p('hh.big', 9) if paid(g, 3) else p('hh.d', 3)))], 6, build=S)
card('Я04', 'y_nimb', 'Нимб', 'связка', 'Следующее попадание союзника в этом раунде ×2, если вера 4+; иначе +2.',
     one(lambda g, h, o: g.set_nimb()), 5, build='С', pr=0.5, fb='С')
card('Я05', 'y_blind', 'Ослепляющий свет', 'атака', '2 урона. Вера 3+: враг в этом раунде бьёт на 2 слабее.',
     one(lambda g, h, o: (g.hit(A, 2), g.weaken(p('blind.w', 2)) if FB(g, 3) else None)), 6, build=S, fb='С')
card('Я06', 'y_just', 'Суд праведных', 'атака', '1 урон за каждую веру и ещё 2 за каждого раненого героя.',
     one(lambda g, h, o: g.hit(A, g.H[A].faith + p('just.k', 2) * sum(1 for k in 'MP' if g.H[k].alive and g.H[k].hp < g.H[k].maxhp))),
     6, build=S)
card('Я07', 'y_hkara', 'Кара небесная', 'молитва', 'Молитва. Если так сыграна карта урона — ещё 3 урона.',
     one(lambda g, h, o: g.pray_then(lambda c: g.hit(A, p('hkara.d', 3)) if c.kind == 'атака' else None, est=p('hkara.d', 3) * 0.5)),
     6, tags=('draw', 'prayer'), build=S)
card('Я08', 'y_pillar', 'Огненный столп', 'атака', '4 урона. Сожги верхнюю карту колоды; если это карта урона — ещё 2.',
     one(lambda g, h, o: g.pillar()), 6, build=S)
card('Я09', 'y_brand', 'Клеймо еретика', 'атака', '2 урона. До конца раунда каждое попадание союзника — +1 вера (макс 2).',
     one(lambda g, h, o: (g.hit(A, p('brand.d', 2)), g.set_brand(p('brand.n', 2)))), 5, build=S, pr=0.7)
card('Я10', 'y_reflect', 'Возмездие света', 'атака', 'Урон, равный щитам на тебе; щиты остаются.',
     one(lambda g, h, o: g.hit(A, max(0, g.H[A].shield - p('refl.m', 0)))), 5, build='С–П', pr=4.6)
card('Я11', 'y_archsw', 'Меч архангела', 'атака', '3 урона. Вера 5+: ещё 3 и +1 вера.',
     one(lambda g, h, o: g.archsword()), 6, build=S, fb='С')
card('Я12', 'y_strict', 'Строгий суд', 'атака', '3 урона. Если 2 из 3 (у врага меньше половины здоровья; ты сбросил карту в этом раунде; на союзнике Благословение) — ещё 4 урона и +1 вера.',
     one(lambda g, h, o: g.strict()), 6, build=S, pr=4.7)
card('Я13', 'y_vowkara', 'Молитва о каре', 'атака', 'Выбери: 3 урона сейчас ИЛИ Обет: в начале следующего раунда урон = вера + 2.',
     [('сейчас', lambda g, h, o: g.hit(A, p('vk.now', 3))), ('Обет', lambda g, h, o: g.vow(lambda g2: g2.hit(A, g2.H[A].faith + p('vk.b', 2)), 'dmg', p('vk.est', 5)))],
     6, build=S)
card('Я14', 'y_anath', 'Анафема', 'атака', '2 урона за каждую веру выше 3; вера не тратится.',
     one(lambda g, h, o: g.hit(A, p('anath.k', 2) * max(0, g.H[A].faith - p('anath.t', 3)))), 5, build=S)
card('Я15', 'y_trump', 'Трубный глас', 'молитва', 'Открой 3 верхние карты. Сыграй бесплатно все карты урона среди них, остальные сбрось.',
     one(lambda g, h, o: g.trumpet()), 6, tags=('draw', 'prayer'), build=S)
card('Я16', 'y_ray', 'Карающий луч', 'атака', '2 попадания по 2. Вера 4+: 3 попадания.',
     one(lambda g, h, o: [g.hit(A, p('ray.d', 2)) for _ in range(F(g, p('ray.lo', 2), p('ray.hi', 3)))]), 6, build=S, fb='С')
card('Я17', 'y_pierce', 'Свет сквозь броню', 'атака', '3 урона, пробивает Броню. Вера 4+: +1 вера.',
     one(lambda g, h, o: (g.hit_ap(p('pierce.d', 3)), g.pf(1) if FB(g) else None)), 6, build=S, fb='С')
card('Я18', 'y_penance', 'Епитимья', 'атака', 'Сбрось до 2 карт из руки: 3 урона за каждую.',
     [('сбросить 1', lambda g, h, o: g.hit(A, p('pen.k', 3) * g.pdisc(1))), ('сбросить 2', lambda g, h, o: g.hit(A, max(0, p('pen.k', 3) * g.pdisc(2) - p('pen.m', 0))))],
     5, build=S)
card('Я19', 'y_angel', 'Ангельский клинок', 'атака', '3 урона. Если это твоя третья карта в ходу — ещё 3.',
     one(lambda g, h, o: g.hit(A, p('angel.d', 3) + (p('angel.b', 3) if g.p_hand_plays >= 3 else 0))), 6, build=S, pr=4.9)
card('Я20', 'y_name', 'Приговор именем бога', 'атака', 'Урон = вера × число разных видов карт, сыгранных тобой в этом раунде (урон / щит / вера / Молитва).',
     one(lambda g, h, o: g.hit(A, g.H[A].faith * max(0, len(g.kinds_rnd & {'атака', 'защита', 'вера', 'молитва'}) - p('name.m', 0)))), 6, build=S, pr=4.9)

# ---- Покровитель (20)
PB = 'П'
card('П01', 'b_double', 'Двойной покров', 'связка', 'Благословение союзнику. Если оно уже на нём — 5 щитов ему.',
     one(lambda g, h, o: g.bless_or(lambda: g.shield(M, p('dbl.sh', 5)))), 6, build=PB)
card('П02', 'b_lift', 'Снятое благословение', 'связка', 'Убери Благословение с союзника: его следующее попадание в этом раунде +5.',
     one(lambda g, h, o: g.lift_bless()), 5, build='П–С', pr=0.5)
card('П03', 'b_sbless', 'Благословение щита', 'связка', 'Благословение союзнику. Когда оно сработает — союзник берёт 1 карту, ты +1 вера.',
     one(lambda g, h, o: g.bless_rider(lambda g2: (g2.draw(M, 1), g2.pf(1)))), 6, build=PB)
card('П04', 'b_hshield', 'Щит небес', 'защита', '5 щитов союзнику. Вера 4+: ещё Благословение.',
     one(lambda g, h, o: (g.shield(M, p('hsh.sh', 5)), g.bless(M) if FB(g) else None)), 6, build=PB, fb='П')
card('П05', 'b_oath2', 'Клятва на двоих', 'защита', 'Выбери: 3 щита союзнику сейчас ИЛИ Обет: в конце следующей фазы героев урон врагу = щитам союзника.',
     [('сейчас', lambda g, h, o: g.shield(M, 3)), ('Обет', lambda g, h, o: g.vow(lambda g2: g2.hit(A, g2.H[M].shield), 'dmg', p('oath2.est', 4), when='endhp'))],
     5, build=PB)
card('П06', 'b_screen', 'Заслон', 'защита', 'Авангард. Щитов себе: 2 + вера.', one(lambda g, h, o: (g.vanguard(A), g.shield(A, p('screen.b', 2) + g.H[A].faith))), 6,
     tags=('vanguard',), build=PB)
card('П07', 'b_two', 'Покров над двумя', 'защита', '3 щита каждому герою. Если на союзнике Благословение — ещё 2 тебе.',
     one(lambda g, h, o: (g.shield(A, 3 + (2 if g.H[M].blessed else 0)), g.shield(M, 3))), 6, build=PB, pr=4.3)
card('П08', 'b_martyr', 'Мученик', 'защита', 'Авангард. Каждый удар по тебе в этом раунде — +1 вера (макс 3).',
     one(lambda g, h, o: (g.vanguard(A), g.shield(A, p('martyr.sh', 0)), g.set_martyr(3))), 5, tags=('vanguard', 'faith'), build='П–Ч')
card('П09', 'b_armor', 'Небесный доспех', 'связка', 'Благословение союзнику. В этом раунде оно снимает 5 урона, а не 3.',
     one(lambda g, h, o: (g.bless(M), g.set_bigbless())), 6, build=PB)
card('П10', 'b_grace', 'Благодать', 'связка', 'Если Благословение сработало в прошлом раунде — +2 веры и 3 щита союзнику; иначе Благословение союзнику.',
     one(lambda g, h, o: (g.pf(p('grace.f', 2)), g.shield(M, p('grace.sh', 3))) if g.bless_trig_last else g.bless(M)), 6, tags=('faith',), build='П–Ч')
card('П11', 'b_vowprot', 'Обет защиты', 'защита', 'Выбери: 4 щита себе сейчас ИЛИ Обет: в начале следующего раунда Благословение и 4 щита союзнику.',
     [('сейчас', lambda g, h, o: g.shield(A, p('vp.now', 4))), ('Обет', lambda g, h, o: g.vow(lambda g2: (g2.bless(M), g2.shield(M, p('vp.sh', 4))), 'def', p('vp.est', 6)))],
     5, build=PB)
card('П12', 'b_cover', 'Светлый покров', 'защита', '3 щита союзнику. Если 2 из 3 (союзник в этом раунде получил щит; ты сыграл 3 карты; вера 3+) — Благословение и +1 вера.',
     one(lambda g, h, o: g.light_cover()), 6, build=PB, pr=4.8)
card('П13', 'b_wall', 'Стена молитв', 'молитва', 'Молитва. Если открыта карта щита — сыграй обе открытые.',
     one(lambda g, h, o: g.wall()), 6, tags=('draw', 'prayer'), build='П–Ч')
card('П14', 'b_answer', 'Ответ света', 'связка', 'Сожги 2 веры: следующий удар по союзнику в этом раунде — 0.',
     one(lambda g, h, o: g.set_void() if paid(g, p('ans.cost', 2)) else None), 5, build=PB)
card('П15', 'b_holy', 'Святой щит', 'защита', '4 щита союзнику. Доплата: сожги 2 веры — ещё 4 щита тебе и Благословение.',
     [('', lambda g, h, o: g.shield(M, p('holy.m', 4))),
      ('доплата', lambda g, h, o: (g.shield(M, p('holy.m', 4)), (g.shield(A, p('holy.sh', 4)), g.bless(M)) if paid(g, 2) else None))], 6, build=PB)
card('П16', 'b_reflb', 'Отражение', 'связка', 'Благословение союзнику. Когда оно сработает — 3 урона врагу.',
     one(lambda g, h, o: g.bless_rider(lambda g2: g2.hit(A, p('reflb.d', 3)))), 6, build='П–С')
card('П17', 'b_help', 'Рука помощи', 'связка', 'Союзник может сбросить 1 карту и взять 2.',
     one(lambda g, h, o: (g.mdisc(1), g.draw(M, p('help.n', 2)))), 5, build=PB, pr=0.6)
card('П18', 'b_banner', 'Хоругвь', 'защита', 'Твои щиты в конце этого раунда не сгорают.', one(lambda g, h, o: (g.shield(A, p('banner.sh', 0)), g.set_banner())), 4, build=PB, pr=4.9)
card('П19', 'b_guard', 'Небесный заступник', 'связка', 'Держи на столе. Если союзник получит смертельный урон в этом бою — у него остаётся 1 здоровья, вера обнуляется, эта карта сгорает.',
     one(lambda g, h, o: g.set_guard()), 4, build=PB)
card('П20', 'b_litany', 'Литания', 'защита', '3 щита союзнику. Если в этом раунде ты играл Молитву — ещё 3 и +1 вера.',
     one(lambda g, h, o: (g.shield(M, p('lit.sh', 3)), (g.shield(M, p('lit.sh', 3)), g.pf(1)) if g.pray_rnd else None)), 5, build='П–Ч', pr=4.8)

# ---- Чудотворец (20)
W = 'Ч'
card('Ч01', 'w_tomor', 'Молитва на завтра', 'вера', 'Выбери: +1 вера сейчас ИЛИ Обет: +3 веры в начале следующего раунда.',
     [('сейчас', lambda g, h, o: g.pf(1)), ('Обет', lambda g, h, o: g.vow(lambda g2: g2.pf(p('tom.f', 3)), 'faith', p('tom.f', 3) * 0.6))],
     5, tags=('faith',), build=W)
card('Ч02', 'w_bell', 'Звон колокола', 'вера', '+1 вера за каждую карту, сыгранную союзником в этом раунде до неё.',
     one(lambda g, h, o: g.pf(min(p('bell.max', 6), g.m_plays_rnd))), 5, tags=('faith',), build=W, pr=4.8)
card('Ч03', 'w_inspire', 'Вдохновение', 'вера', 'Союзник берёт 1 карту. Если сыграет её в этом раунде — +2 веры.',
     one(lambda g, h, o: g.inspire()), 5, tags=('faith',), build=W, pr=0.6)
card('Ч04', 'w_testim', 'Свидетельство', 'молитва', 'Открой 4 верхние карты. Сыграй 2 из них (занимают места в лимите), остальные сбрось.',
     one(lambda g, h, o: g.pray(n_open=p('test.open', 4), n_play=2, uselimit=True)), 5, tags=('draw', 'prayer'), build=W)
card('Ч05', 'w_triple', 'Тройная молитва', 'атака', '2 урона. Если 2 из 3 (союзник в этом раунде нанёс урон; на враге есть статус; союзник сжёг или сбросил карту) — +2 веры и 4 щита союзнику.',
     one(lambda g, h, o: g.triple_prayer()), 6, tags=('faith',), build='Ч–П', pr=4.8)
card('Ч06', 'w_vigil', 'Бдение', 'вера', '+1 вера. Если в конце раунда вера 4+ — в начале следующего возьми 1 карту.',
     one(lambda g, h, o: (g.pf(p('vigil.f', 1)), g.set_vigil())), 4, tags=('faith',), build=W)
card('Ч07', 'w_mwrath', 'Чудо гнева', 'атака', 'Чудо: 3 урона за каждую веру, если вера 6; иначе 1 за каждую.',
     one(lambda g, h, o: (lambda f: g.hit(A, (p('mw.k', 3) if f >= 6 else 1) * f))(g.burn_faith())), 5, tags=('miracle',), build=W)
card('Ч08', 'w_mshare', 'Чудо разделения', 'атака', 'Чудо: за каждую веру 1 урон и 1 щит союзнику.',
     one(lambda g, h, o: (lambda f: (g.hit(A, f + p('msh.b', 0)), g.shield(M, f + p('msh.b', 0) + p('msh.s', 0))))(g.burn_faith())), 5, tags=('miracle',), build=W)
card('Ч09', 'w_mrevel', 'Чудо откровения', 'молитва', 'Чудо: Молитва за каждые 2 веры.',
     one(lambda g, h, o: (lambda f: [g.pray() for _ in range(min(p('mrev.max', 9), f // p('mrev.per', 2)))])(g.burn_faith())), 5, tags=('miracle', 'draw', 'prayer'), build=W)
card('Ч10', 'w_mercy', 'Милость', 'вера', '+1 вера. Если в этом раунде ты уже сыграл Чудо — ещё +3.',
     one(lambda g, h, o: g.pf(1 + (p('mercy.b', 3) if g.mir_rnd else 0))), 5, tags=('faith',), build=W, pr=5.2)
card('Ч11', 'w_prophecy', 'Пророчество', 'вера', 'Посмотри 3 верхние карты, положи в любом порядке. Следующая Молитва в этом ходу открывает 3.',
     one(lambda g, h, o: (g.scry(3), g.set_praybonus(1))), 4, build=W, pr=3.3)
card('Ч12', 'w_night', 'Всенощная', 'молитва', 'Молитва дважды. Сбрось 1 карту из руки.',
     one(lambda g, h, o: (g.pdisc(1), g.pray(), g.pray())), 6, tags=('draw', 'prayer'), build=W)
card('Ч13', 'w_ecstasy', 'Экстаз', 'вера', 'Удвой веру (до 6). В конце раунда вера −2.',
     one(lambda g, h, o: g.ecstasy()), 5, tags=('faith',), build=W)
card('Ч14', 'w_relics', 'Святые мощи', 'вера', 'Сожги верхнюю карту колоды: +2 веры; если это карта урона — ещё 2 урона.',
     one(lambda g, h, o: g.relics()), 5, tags=('faith',), build='Ч–С')
card('Ч15', 'w_commun', 'Причастие', 'вера', 'Ты и союзник можете сбросить по 1 карте: +1 вера за каждую, каждый сбросивший берёт 1.',
     [('оба', lambda g, h, o: g.communion(True)), ('только я', lambda g, h, o: g.communion(False))], 5, tags=('faith', 'draw'), build=W, pr=0.6)
card('Ч16', 'w_ladder', 'Лествица', 'вера', '+1 вера. Если после этого вера 6 — Молитва.',
     one(lambda g, h, o: (g.pf(p('ladder.f', 1)), g.pray() if g.H[A].faith >= 6 else None)), 5, tags=('faith', 'draw'), build=W)
card('Ч17', 'w_frenzy', 'Исступление', 'вера', 'Следующее Чудо в этом раунде считает веру ×1,5.', one(lambda g, h, o: g.set_frenzy()), 4, build=W, pr=3.3)
card('Ч18', 'w_news', 'Благая весть', 'вера', 'Союзник берёт 2 карты. Если он сыграет в этом раунде 3+ карты — +2 веры.',
     one(lambda g, h, o: (g.draw(M, 2), g.set_news())), 5, tags=('faith',), build='Ч–П', pr=0.6)
card('Ч19', 'w_tempt', 'Искушение', 'вера', '+3 веры. Враг в этом раунде бьёт на 2 сильнее.', one(lambda g, h, o: (g.pf(p('tempt.f', 3)), g.weaken(-2))), 4,
     tags=('faith',), build=W, pr=3.3)
card('Ч20', 'w_revel', 'Откровение', 'молитва', 'Молитва. Доплата: сожги 2 веры — открой 4 и сыграй 2.',
     [('', lambda g, h, o: g.pray(n_open=p('rev.open', 2))), ('доплата', lambda g, h, o: g.pray(n_open=4, n_play=2) if paid(g, 2) else g.pray(n_open=p('rev.open', 2)))], 5,
     tags=('draw', 'prayer'), build=W)

# ---- мосты (15)
card('М01', 'm_swsh', 'Меч и щит+', 'атака', '3 урона и 3 щита союзнику. Вера 4+: по 5.',
     one(lambda g, h, o: (lambda n: (g.hit(A, n), g.shield(M, n)))(F(g, p('swsh2.lo', 3), p('swsh2.hi', 5)))), 6, build='С–П', fb='С')
card('М02', 'm_spear', 'Святое копьё', 'атака', '3 урона за каждую карту, сыгранную тобой в этом раунде Молитвой.',
     one(lambda g, h, o: g.hit(A, p('spear.k', 3) * g.pray_rnd)), 5, build='С–Ч', pr=4.9)
card('М03', 'm_pcover', 'Карающий покров', 'связка', 'Благословение союзнику. Пока оно на нём, каждое его попадание +1.',
     one(lambda g, h, o: (g.bless(M), g.set_cover())), 6, build='С–П', pr=0.5)
card('М04', 'm_omen', 'Знамение', 'молитва', 'Молитва. Сыгранная так карта даёт ещё +1 веру.',
     one(lambda g, h, o: g.pray_then(lambda c: g.pf(p('omen.f', 1)), est=0.6 * p('omen.f', 1))), 5, tags=('draw', 'prayer', 'faith'), build='П–Ч')
card('М05', 'm_tithe', 'Десятина', 'связка', 'Сожги 2 веры: союзник берёт 2 карты и получает 2 щита.',
     one(lambda g, h, o: (g.draw(M, 2), g.shield(M, 2)) if paid(g, 2) else None), 5, build='Ч–П', pr=0.6)
card('М06', 'm_alarm', 'Набат', 'атака', '2 урона. Следующая карта урона союзника в этом раунде +2. +1 вера.',
     one(lambda g, h, o: (g.hit(A, p('alarm.d', 2)), g.mbonus_add(p('alarm.b', 2)), g.pf(1))), 5, tags=('faith',), build='С–Ч', pr=0.5)
card('М07', 'm_second', 'Вторая заповедь', 'вера', '+1 вера. Если 2 из 3 (союзник в этом раунде взял карту; союзник получил щит; ты сбросил карту) — Молитва и Благословение.',
     one(lambda g, h, o: g.second_commandment()), 5, tags=('faith', 'draw'), build='П–Ч', pr=4.8)
card('М08', 'm_purify', 'Очищение', 'вера', 'Убери 1 статус с героя или врага. +2 веры.',
     [('снять Благословение', lambda g, h, o: g.purify('bless')), ('снять Порчу', lambda g, h, o: g.purify('porcha'))], 4, tags=('faith',),
     build='все', pr=4.8)
card('М09', 'm_ways', 'Два пути', 'атака', 'Выбери: 2 урона и 2 щита союзнику сейчас ИЛИ Обет: в начале следующего раунда урон и щиты союзнику = вера.',
     [('сейчас', lambda g, h, o: (g.hit(A, 2), g.shield(M, 2))),
      ('Обет', lambda g, h, o: g.vow(lambda g2: (g2.hit(A, g2.H[A].faith), g2.shield(M, g2.H[A].faith)), 'dmg', p('ways.est', 6)))], 5, build='С–П')
card('М10', 'm_novice', 'Послушник', 'атака', '1 урон. Следующее твоё Чудо в этом раунде считает +2 веры.',
     one(lambda g, h, o: (g.hit(A, p('novice.d', 1)), g.add_mirplus(2))), 4, build='С–Ч', pr=3.3)
card('М11', 'm_right', 'Праведник', 'связка', 'Благословение союзнику. +1 вера за каждое сработавшее в этом бою Благословение (макс 3).',
     one(lambda g, h, o: (g.bless(M), g.pf(min(3, g.bless_trig_fight)))), 5, tags=('faith',), build='П–Ч')
card('М12', 'm_ascend', 'Вознесение', 'атака', 'Если вера 6 — 10 урона, вера становится 3. Иначе +2 веры.',
     one(lambda g, h, o: g.ascend()), 5, tags=('faith',), build='С–Ч', pr=4.9)
card('М13', 'm_proc', 'Крестный ход', 'молитва', '2 щита каждому герою. Молитва.', one(lambda g, h, o: (g.shield(A, p('proc.sh', 2)), g.shield(M, p('proc.sh', 2)), g.pray())), 6,
     tags=('draw', 'prayer'), build='П–Ч')
card('М14', 'm_humble', 'Смирение', 'вера', 'Сбрось всю руку: +1 вера за каждую, возьми 2.',
     one(lambda g, h, o: (lambda n: (g.pf(n), g.draw(A, 2)))(g.pdisc(99))), 4, tags=('faith', 'draw'), build='Ч–С', pr=4.9)
card('М15', 'm_vesp', 'Вечерня', 'вера', 'Выбери: возьми 2 карты сейчас ИЛИ Обет: в начале следующего раунда возьми 3 и +1 вера.',
     [('сейчас', lambda g, h, o: g.draw(A, 2)), ('Обет', lambda g, h, o: g.vow(lambda g2: (g2.draw_cards(A, 3), g2.pf(p('vesp.f', 1))), 'draw', p('vesp.est', 3.6)))],
     5, tags=('draw',), build='П–Ч')

assert len(START_CAND) == 25 and len(UPGRADES) == 75, (len(START_CAND), len(UPGRADES))

# калибровка яруса I (15:05): состав А, стартовые атаки −1 (как у мага, cut), Чудо света 1 за веру
DEFAULT_START = ['z_kara', 'z_kara', 'z_hammer', 'z_verdict', 'z_fshield', 'z_fshield', 'z_lguard', 'z_mlight', 'z_bless', 'z_bless',
                 'z_quiet', 'z_candle', 'z_conf', 'z_hands', 'z_mint']
DEFAULTS.update({'p.cut': 1, 'mlight.k': 1})
DEFAULTS.update({'doll.hp': 5, 'doll.cost': 2})   # новая Кукла: подбор 15:20 (−0,19 раунда, −4,6% потерь)


def make(cid):
    return BANK[cid]()


def P_start(start=None):
    d = [make(c) for c in (start or DEFAULT_START)]
    assert len(d) == 15
    return d


def P_deck(ups, start=None):
    """Апгрейд заменяет самую слабую оставшуюся стартовую карту своего вида, иначе самую слабую стартовую."""
    d = P_start(start); st = list(d)
    for cid in ups:
        c = make(cid)
        left = [x for x in d if any(x is s for s in st)]
        if not left:
            d.append(c); continue
        same = [x for x in left if x.kind == c.kind]
        tgt = min(same or left, key=lambda x: (x.value, x.cid))
        d = [x for x in d if x is not tgt]; d.append(c)
    return d


# ---------------------------------------------------------------- игра
class PGame(B11Game):
    def __init__(self, seed, mdeck, pdeck, cfg=None):
        super().__init__(seed, mdeck, pdeck, cfg=cfg)
        self.H['P'] = E.Hero('P', pdeck)     # без no_heal_priest: у нового Жреца лечения нет
        E.BLESS = p('bless.n', 3)
        import burn6
        zs = {c for c in START_CAND}
        if p('p.cut', 0):
            burn6.START_P |= zs
        else:
            burn6.START_P -= zs
        self._cur = None; self._pay = False; self._paid = False; self._paidX = None; self._free = 0
        self.est = 0.0; self.est_f = 0.0
        self.vows = []; self.bless_riders = []
        self.doll = 0; self.doll_dmg = 0
        self._reset_fight(); self._reset_round()
        self.bless_trig_last = 0
        for k in ('f_own', 'f_ally', 'f_spent', 'f_sum', 'f_n', 'f_at6', 'f_start', 'miracles', 'mir_faith', 'pray', 'pray_play',
                  'vows', 'bless_trig', 'kick', 'scry', 'dmgM', 'dmgP', 'guard', 'doll_hit', 'topburn', 'discards_p'):
            self.bstats.setdefault(k, 0)

    def _reset_fight(self):
        self.guard = False; self.bless_trig_fight = 0; self.banner_keep = 0; self.banner = False
        self.ecst_decay = False; self.vigil = False; self.vows = []; self.bless_riders = []; self.cover = False
        self.doll = 0; self.doll_dmg = 0

    def _reset_round(self):
        self.m_hit_rnd = 0; self.m_drew_rnd = 0; self.m_sh_rnd = 0; self.p_hand_plays = 0; self.kinds_rnd = set()
        self.pray_rnd = 0; self.pr_disc_rnd = 0; self.mir_rnd = 0; self.weak = 0; self.brand = 0; self.nimb = None
        self.void_next = False; self.martyr = 0; self.bless_big = False; self.pray_bonus = 0; self.frenzy = False
        self.mir_plus = 0; self.inspired = []; self.news = False; self.bless_trig_rnd = 0

    def clone_sim(self):
        g = super().clone_sim()
        g.__class__ = PGame
        g.vows = list(self.vows); g.bless_riders = list(self.bless_riders); g.kinds_rnd = set(self.kinds_rnd)
        g.inspired = list(self.inspired)
        return g

    # ---------- вера
    def gain_faith(self, n, why):
        P = self.H['P']; old = P.faith
        super().gain_faith(n, why)
        d = P.faith - old
        if d > 0 and not self.sim:
            self.bst('f_own' if why.startswith('карта') else 'f_ally', d)

    def pf(self, n):
        """Вера от своей карты (вариант В1 — src.own = 0)."""
        self.gain_faith(int(n * p('src.own', 1)), 'карта Жреца')

    def burn_faith(self):
        f = super().burn_faith()
        if self.frenzy:
            f = int(f * 1.5); self.frenzy = False
        f += self.mir_plus; self.mir_plus = 0
        self.mir_rnd += 1
        self.bst('miracles'); self.bst('mir_faith', f)
        return f

    # ---------- колоды и раунды
    def start_fight_decks(self):
        super().start_fight_decks()
        self._reset_fight()
        s = int(p('src.start', 0))
        if s:
            self.H['P'].faith = min(6, s); self.bst('f_start', s)

    def hero_phase(self):
        if not self.sim:
            self.bless_trig_last = self.bless_trig_rnd
            self._reset_round()
            P = self.H['P']
            if self.ecst_decay:
                P.faith = max(0, P.faith - 2); self.ecst_decay = False
            if self.vigil:
                if P.faith >= 4:
                    self.draw_cards('P', 1)
                self.vigil = False
            if self.banner_keep:
                P.shield += self.banner_keep; self.banner_keep = 0
            self.banner = False
            if self.doll_dmg > 0 and self.E and self.E.hp > 0:
                d = self.doll_dmg; self.doll_dmg = 0; self.doll = 0
                self.hit('M', d); self.bst('doll_hit', d)
            vs = [v for v in self.vows if v[0] == 'start']
            self.vows = [v for v in self.vows if v[0] != 'start']
            for _, fn, r in vs:
                if self.E and self.E.hp > 0:
                    fn(self)
        super().hero_phase()

    def end_hero_phase(self):
        if not self.sim and self.E and self.E.hp > 0:
            vs = [v for v in self.vows if v[0] == 'endhp' and v[2] < self.rnd]
            self.vows = [v for v in self.vows if not (v[0] == 'endhp' and v[2] < self.rnd)]
            for _, fn, r in vs:
                if self.E.hp > 0:
                    fn(self)
            if self.news and self.m_plays_rnd >= 3:
                self.pf(2)
            self.news = False
        super().end_hero_phase()
        if not self.sim:
            f = self.H['P'].faith
            self.bst('f_sum', f); self.bst('f_n'); self.bst('f_at6', int(f >= 6))

    # ---------- розыгрыш
    def play(self, hk, card, opt, want_off):
        if hk != 'P':
            ok = super().play(hk, card, opt, want_off)
            if ok and any(card is c for c in self.inspired):
                self.inspired = [c for c in self.inspired if c is not card]; self.pf(p('insp.f', 2))
            return ok
        h = self.H['P']
        if not h.alive or not any(c is card for c in h.hand) or h.plays >= h.maxplays:
            return False
        ctx = (self._cur, self._pay, self._paid, self._paidX)
        self._cur = card; self._pay = card.opts[opt][0].endswith(PAY); self._paid = False; self._paidX = None
        if not self._free:
            self.p_hand_plays += 1
        self.kinds_rnd = self.kinds_rnd | {card.kind}
        try:
            ok = super().play(hk, card, opt, want_off)
        finally:
            self._cur, self._pay, self._paid, self._paidX = ctx
        return ok

    @staticmethod
    def prio(a):
        if a[0] == 'play' and a[1] == 'P' and getattr(a[2], 'pr', None) is not None:
            return a[2].pr
        return B11Game.prio(a)

    # ---------- удары и защита
    def hit(self, h, n, pierce=False):
        e = self.E
        if e is None or e.hp <= 0:
            return
        if h == 'M' and n > 0:
            self.m_hit_rnd += 1
            if self.nimb == 'x2':
                n *= 2
            elif self.nimb:
                n += self.nimb
            self.nimb = None
            if self.cover and self.H['M'].blessed:
                n += p('cover.b', 1)
            if self.brand > 0:
                self.brand -= 1; self.gain_faith(1, 'союзник попал (Клеймо)')
        if getattr(self, '_apierce', False) and n > 0:
            n += e.traits.get('armor', 0)
        e0 = e.hp
        super().hit(h, n, pierce)
        if not self.sim:
            self.bst('dmgM' if h == 'M' else 'dmgP', max(0, e0 - self.E.hp))

    def hit_ap(self, n):
        self._apierce = True
        try:
            self.hit('P', n)
        finally:
            self._apierce = False

    def shield(self, h, n):
        if h == 'M' and n > 0 and self.H['M'].alive:
            self.m_sh_rnd += 1
        return super().shield(h, n)

    def draw(self, h, n):
        if h == 'M' and n > 0:
            self.m_drew_rnd += 1
        return super().draw(h, n)

    def deal(self, k, n, src='удар'):
        h = self.H[k]
        if not h.alive:
            return
        if self.doll > 0 and n > 0:        # новая Кукла вуду: запоминает принятый урон
            a = min(self.doll, n); self.doll -= a; n -= a; self.doll_dmg += a
        if k == 'M' and self.void_next and n > 0:
            n = 0; self.void_next = False
        if k == 'P' and n > 0 and self.martyr > 0:
            self.martyr -= 1; self.pf(1)
        trig = h.blessed and n > 0
        if trig and k == 'M' and self.bless_big:
            E.BLESS = p('bless.big', 5)
        try:
            B9Game.deal(self, k, n, src)
        finally:
            E.BLESS = p('bless.n', 3)
        if trig and k == 'M':
            self.bless_trig_rnd += 1; self.bless_trig_fight += 1; self.cover = False; self.bst('bless_trig')
            rs = self.bless_riders; self.bless_riders = []
            for r in rs:
                if self.E and self.E.hp > 0:
                    r(self)
        if k == 'M' and not h.alive and self.guard:
            h.alive = True; h.hp = 1; self.H['P'].faith = 0; self.guard = False; self.bst('guard')
            self.L('      Небесный заступник: союзник остаётся с 1 здоровья')

    def enemy_act(self, intent):
        d = self.weak
        if d:
            self.E.buff -= d
        try:
            super().enemy_act(intent)
        finally:
            if d:
                self.E.buff += d
        if self.banner and not self.sim:
            self.banner_keep = self.H['P'].shield

    # ---------- оценка плана: подсказки будущего
    def evaluate(self, base, seq):
        s = super().evaluate(base, seq)
        g = B10Game._last_eval
        if g is None:
            return s
        s += g.est - base.est
        if g.E.hp > 0:
            k = 1.0 + 2.2 * self.E.threat / max(1, self.E.maxhp)
            s += g.est_f - base.est_f
            s += (p('fut.faith', 0.6) - 0.6) * (g.H['P'].faith - base.H['P'].faith)
            s += p('fut.dolld', 0.9) * k * (g.doll_dmg - base.doll_dmg)
            if g.banner:
                s += 0.8 * g.H['P'].shield
            if g.guard and not base.guard:
                s += p('fut.guard', 2.0)
        return s

    # ---------- механики карт
    def pdisc(self, n):
        P = self.H['P']; done = 0
        for _ in range(n):
            cands = [c for c in P.hand if not any(c is r for r in self.reserved)]
            if not cands:
                break
            c = min(cands, key=lambda x: x.value); P.hand.remove(c); P.disc.append(c); done += 1
        if done:
            P.discarded = True; self.pr_disc_rnd += done
            self.bst('discards_p', done)
        return done

    def mdisc(self, n):
        m = self.H['M']; done = 0
        for _ in range(n):
            cands = [c for c in m.hand if not any(c is r for r in self.reserved)]
            if not cands:
                break
            c = min(cands, key=lambda x: x.value); m.hand.remove(c); m.disc.append(c); done += 1
        if done:
            m.discarded = True
        return done

    def _top(self):
        P = self.H['P']
        if not P.draw:
            if not P.disc:
                return None
            P.draw = P.disc; P.disc = []
            if not self.sim:
                self.rng.shuffle(P.draw)
        return P.draw[-1]

    def scry(self, n):
        if self.sim:
            self.est_f += p('fut.scry', 0.4) * n
            return
        P = self.H['P']
        if self._top() is None:
            return
        top = P.draw[-n:]; del P.draw[-n:]
        P.draw += sorted(top, key=lambda c: c.value)
        self.bst('scry')

    def _eval_free(self, c, oi, uselimit):
        g2 = self.clone_sim()
        P2 = g2.H['P']
        P2.hand.append(c)
        if uselimit:
            if P2.plays >= P2.maxplays:
                return None
        else:
            P2.maxplays += 1
        return g2.evaluate(self, [('play', 'P', c, oi, 0)])

    def pray(self, n_open=None, n_play=1, uselimit=False, filt=None, then=None, est=0.0):
        """Молитва: открой n_open верхних, сыграй n_play из них бесплатно (uselimit — занимают места в лимите)."""
        n_open = (n_open or p('pray.open', 2)) + self.pray_bonus; self.pray_bonus = 0
        if self.sim:
            k = n_play if filt is None else 0.45 * n_open
            w = p('fut.pray', 4.0) + est
            if uselimit:
                P = self.H['P']; k = min(k, max(0, P.maxplays - P.plays)); w = p('fut.prayl', 1.5)
            self.est += w * k
            self.pray_rnd += 1
            return []
        P = self.H['P']; opened = []
        for _ in range(n_open):
            if self._top() is None:
                break
            opened.append(P.draw.pop())
        self.bst('pray'); played = []
        rounds = n_play if filt is None else len(opened)
        for _ in range(rounds):
            cands = [c for c in opened if filt is None or filt(c)]
            if not cands or self.E.hp <= 0 or not P.alive:
                break
            best = None
            for c in cands:
                for oi in range(len(c.opts)):
                    s = self._eval_free(c, oi, uselimit)
                    if s is not None and (best is None or s > best[0]):
                        best = (s, c, oi)
            if best is None:
                break
            _, c, oi = best
            opened = [x for x in opened if x is not c]
            P.hand.append(c)
            if not uselimit:
                P.maxplays += 1
            self._free += 1
            try:
                ok = self.play('P', c, oi, 0)
            finally:
                self._free -= 1
            if not ok:
                P.hand = [x for x in P.hand if x is not c]; P.disc.append(c)
                if not uselimit:
                    P.maxplays -= 1
                continue
            played.append(c); self.pray_rnd += 1; self.bst('pray_play')
            if then:
                then(c)
        P.disc += opened
        return played

    def pray_then(self, fn, est=0.0):
        self.pray(then=fn, est=est)

    def trumpet(self):
        self.pray(n_open=p('trump.open', 3), filt=lambda c: c.kind == 'атака')

    def wall(self):
        if self.sim:
            self.est += p('fut.pray', 4.0) * 1.4; self.pray_rnd += 1
            return
        P = self.H['P']
        top2 = []
        if self._top() is not None:
            n = p('pray.open', 2) + self.pray_bonus
            top2 = P.draw[-n:]
        both = any(c.kind == 'защита' for c in top2)
        self.pray(n_play=2 if both else 1)
        self.shield('P', p('wall.sh', 0)); self.shield('M', p('wall.sh', 0))

    def symbol(self):
        c = self._top()
        if c is None:
            return
        P = self.H['P']
        if 'faith' in c.tags:
            P.draw.pop(); P.disc.append(c); self.pf(p('symbol.f', 2))
        else:
            P.draw.pop()
            if self.sim:
                P.pend += 1
            else:
                P.hand.append(c)

    def pillar(self):
        self.hit('P', p('pillar.d', 4))
        c = self._top()
        if c is None:
            return
        P = self.H['P']; P.draw.pop(); P.exiled.append(c); self.bst('topburn')
        if c.kind == 'атака':
            self.hit('P', p('pillar.b', 2))

    def relics(self):
        c = self._top()
        if c is None:
            return
        P = self.H['P']; P.draw.pop(); P.exiled.append(c); self.bst('topburn')
        self.pf(p('relics.f', 2))
        if c.kind == 'атака':
            self.hit('P', p('relics.d', 2))

    def vow(self, fn, kind, est, when='start'):
        if self.sim:
            k = 1.0 + 2.2 * self.E.threat / max(1, self.E.maxhp)
            self.est_f += p('fut.vow', 0.9) * est * (k if kind == 'dmg' else 1.0)
            return
        self.vows.append((when, fn, self.rnd)); self.bst('vows')

    def bless_or(self, alt):
        if self.H['M'].blessed:
            alt()
        else:
            self.bless('M')

    def bless_rider(self, fn):
        self.bless('M'); self.bless_riders = self.bless_riders + [fn]

    def lift_bless(self):
        m = self.H['M']
        if m.blessed:
            m.blessed = False; self.bless_riders = []; self.cover = False
            self.mbonus = getattr(self, 'mbonus', 0) + p('lift.b', 5)

    def mbonus_add(self, n):
        self.mbonus = getattr(self, 'mbonus', 0) + n

    def set_nimb(self):
        self.nimb = 'x2' if FB(self) else p('nimb.add', 2)

    def weaken(self, n):
        self.weak += n

    def set_brand(self, n):
        self.brand = max(self.brand, n)

    def archsword(self):
        big = FB(self, 5)
        self.hit('P', p('arch.d', 3) + (p('arch.b', 3) if big else 0))
        if big:
            self.pf(1)

    def strict(self):
        e = self.E
        c = int(e.hp * 2 < e.maxhp) + int(self.pr_disc_rnd > 0) + int(self.H['M'].blessed)
        full = c >= 2
        self.hit('P', p('strict.d', 3) + (p('strict.b', 4) if full else 0))
        if full:
            self.pf(1)

    def last_verdict(self):
        f = self.burn_faith()
        self.hit('P', 2 * f)
        if self.E.hp <= 0:
            self.H['P'].faith = min(6, self.H['P'].faith + p('last.keep', 2))

    def set_martyr(self, n):
        self.martyr = max(self.martyr, n)

    def set_bigbless(self):
        self.bless_big = True

    def light_cover(self):
        c = int(self.m_sh_rnd > 0) + int(self.p_hand_plays >= 3) + int(self.H['P'].faith >= 3)
        self.shield('M', 3)
        if c >= 2:
            self.bless('M'); self.pf(1)

    def set_void(self):
        self.void_next = True

    def set_banner(self):
        self.banner = True

    def set_guard(self):
        self.guard = True

    def inspire(self):
        self.draw('M', 1)
        if self.sim:
            self.est += p('fut.misc', 1.0) * 0.6
        else:
            m = self.H['M']
            if m.hand:
                self.inspired = self.inspired + [m.hand[-1]]

    def triple_prayer(self):
        c = int(self.m_hit_rnd > 0) + int(self.E.porcha > 0) + int(self.burned_rnd > 0 or self.H['M'].discarded)
        self.hit('P', p('tp.d', 2))
        if c >= p('tp.need', 2):
            self.pf(2); self.shield('M', p('tp.sh', 4))

    def set_vigil(self):
        self.vigil = True
        if self.sim:
            self.est_f += 0.5 * int(self.H['P'].faith >= 4)

    def set_praybonus(self, n):
        self.pray_bonus += n

    def ecstasy(self):
        P = self.H['P']; self.gain_faith(int(P.faith * p('src.own', 1)), 'карта Жреца (Экстаз)')
        self.ecst_decay = True
        if self.sim:
            self.est_f -= 0.6 * 2

    def communion(self, both):
        n = self.pdisc(1)
        if n:
            self.draw('P', 1)
        if both:
            k = self.mdisc(1)
            if k:
                self.draw('M', 1); n += k
        self.pf(n)

    def set_frenzy(self):
        self.frenzy = True

    def set_news(self):
        self.news = True
        if self.sim:
            self.est_f += 0.6

    def add_mirplus(self, n):
        self.mir_plus += n

    def set_cover(self):
        self.cover = True

    def second_commandment(self):
        self.pf(1)
        c = int(self.m_drew_rnd > 0) + int(self.m_sh_rnd > 0) + int(self.pr_disc_rnd > 0)
        if c >= 2:
            self.bless('M'); self.pray()

    def purify(self, what):
        ok = False
        if what == 'bless' and self.H['M'].blessed:
            self.H['M'].blessed = False; self.bless_riders = []; ok = True
        elif what == 'porcha' and self.E.porcha > 0:
            self.E.porcha -= 1; ok = True
        self.pf(p('pur.f', 2) if ok else 1)

    def ascend(self):
        P = self.H['P']
        if P.faith >= p('asc.t', 6):
            self.hit('P', p('asc.d', 10)); P.faith -= 3; self.bst('f_spent', 3)
        else:
            self.pf(2)


# ---------------------------------------------------------------- новая Кукла вуду у мага
def M_bank(extra=None):
    U = burn11.M_bank(extra)
    for c in U:
        if c.cid == 'x_doll':
            c.cost = p('doll.cost', 2)
            c.text = (f"{p('doll.cost', 2)} маны. Кукла с {p('doll.hp', 3)} здоровья принимает удары по любому герою и запоминает урон. "
                      "В начале следующего хода наносит его врагу и умирает.")
    return U


def names():
    return {cid: BANK[cid]().name for cid in BANK}

# Фаза В, итерация 1 → 2 (30.09): режем Суд, поднимаем слабую поддержку
DEFAULTS.update({
    'pen.k': 2, 'ray.lo': 1, 'pillar.d': 3, 'angel.d': 2, 'hh.d': 2, 'hh.big': 8, 'name.m': 1,
    'arch.d': 2, 'swsh2.lo': 2, 'swsh2.hi': 4, 'refl.m': 2, 'just.k': 1, 'strict.d': 2,
    'alarm.d': 1, 'right.d': 2, 'tp.sh': 3,
    'vp.now': 5, 'vp.sh': 6, 'mrev.per': 1, 'mrev.max': 3, 'rev.open': 3, 'wall.sh': 2,
    'asc.t': 5, 'asc.d': 9, 'novice.d': 2, 'anath.t': 2, 'anath.k': 3, 'vigil.f': 2,
    'trump.open': 4, 'tom.f': 4, 'vesp.f': 2, 'screen.b': 3, 'martyr.sh': 3, 'banner.sh': 3, 'insp.f': 3,
})

# Фаза В, итерация 2 → 3 (30.09 ~23:00): режем лидеров по ценности, второй/третий шанс слабым
DEFAULTS.update({
    'tp.sh': 2, 'ray.hi': 2, 'pen.m': 1, 'angel.b': 2, 'brand.n': 1, 'proc.sh': 1, 'pillar.b': 1,
    'asc.t': 4, 'asc.d': 8, 'trump.open': 2, 'martyr.sh': 5, 'screen.b': 5, 'banner.sh': 5,
    'ladder.f': 2, 'help.n': 3, 'lit.sh': 4, 'msh.b': 2, 'holy.m': 5, 'nimb.add': 3, 'omen.f': 2,
    'grace.sh': 5, 'spear.k': 4, 'hsh.sh': 6,
})

# Фаза В, итерация 3 → 4 (30.09 ~23:40): ценность считаю относительно медианы прогона (сиды итерации 3 дали всем +0,25)
DEFAULTS.update({
    'msh.b': 1, 'tp.sh': 1, 'angel.b': 1, 'swsh2.hi': 3, 'alarm.b': 1, 'screen.b': 4, 'pillar.b': 0,
    'strict.b': 3, 'refl.m': 3, 'reflb.d': 2, 'pierce.d': 2,
    'grace.f': 3, 'vigil.f': 3, 'lit.sh': 5,
})

# Фаза В, итог (01.10 ~00:50): Тройная молитва 1 урон (оставалась выше всех после 4 итераций)
DEFAULTS.update({'tp.d': 1})

# Дотест Г-2 (01.10 03:15): чистый Суд был слишком быстрым (босс 4,6) — вариант V2 (босс 5,1);
# Чудотворцу защита для пары с Проклинателем (90% → 94% побед) и ещё +1 к обоим щитам
DEFAULTS.update({'hh.big': 7, 'arch.b': 2, 'vk.b': 1, 'name.m': 2, 'pillar.d': 2, 'brand.d': 1, 'vk.now': 2,
                 'tp.sh': 4, 'msh.s': 3})

# Возложение рук: свой параметр (раньше брался hands.b мага = 7); пока оставляю 7 как во всех прогонах Б–Г, решение после проверки
DEFAULTS.update({'zhands.b': 2})   # проверка 03:50: 7 / 4 / 2 почти не отличаются (бонус срабатывает редко) — оставляю задуманные 2

# Подрезка чистого Суда (01.10 04:10): Меч архангела бонус 1, Молитва о каре по обету урон = вера, Молот небес доплата 6.
# Суд праведных не трогаю: без «+за раненого» он стал бы копией стартового Приговора.
DEFAULTS.update({'arch.b': 1, 'vk.b': 0, 'hh.big': 6})
