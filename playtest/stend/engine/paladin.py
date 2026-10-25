# -*- coding: utf-8 -*-
"""Операции банка идей Паладина (2026-10-25): Заслон со свойствами, благословения Лунарис/Соларис,
верх колоды, вера на кубике, лимит карт. Регистрируются в общем словаре effects.OPS.

  zaslon: {komu: soyuznik|ja|oba, sila: X, stojkij: 1, perehod: 1, polnyj: 1, opora: 1, effekt: [...]}
          Заслон на героя; effekt — «когда сработает» (в нём доступно число snyato — сколько урона снял Заслон)
  snyat_zaslon: {s: soyuznik|ja|oba, v: имя}     снять Заслон, в v — сколько снято
  perenesti_zaslon: 1                             Заслон с союзника на себя или с себя на союзника
  perehvat: X                                     в этом раунде удар по герою под Заслоном принимает Паладин, ещё −X
  zapret_urona: 1 / tolko_molitvy: 1              до конца раунда: нельзя карты урона / нельзя карты из руки
  shchit_potom: {komu: ..., n: X}                 щит в начале следующего раунда
  smena_blagoslovenij: 1                          перевернуть жетоны Лунарис/Соларис
  perevernut_veru: 1                              кубик веры на противоположную грань (0 остаётся 0)
  szhech_veru: {n: X, v: имя}                     сжечь до X веры, в v — сколько сожжено
  relikvarij: 1                                   вся вера уходит на карту и возвращается в начале следующего раунда
  chudo_ne_szhigaet: 1                            следующее Чудо не сжигает веру
  usilit_vraga: X                                 враг в этом раунде бьёт сильнее на X
  ne_v_limit: 1 / konec_hoda: 1                   карта не считается в лимит / больше карт в этом раунде нет
  eta_na_verh: 1                                  после розыгрыша эта карта кладётся на верх колоды
  smotri_verh: {n: X, vzyat: Y, ostalnye: verh|niz}   посмотреть X верхних, Y лучших взять, остальные разложить
  uporyadochit: X                                 посмотреть X верхних и положить лучшие сверху
  na_verh_iz_ruki: {n: X, v: имя, tolko_metka: m} положить X карт из руки на верх колоды (лучшие; только с меткой m)
  iz_sbrosa_na_verh: X                            лучшие X карт из сброса на верх колоды
  sbros_verha: {n: X, v: имя}                     сбросить X верхних, в v — сколько среди них карт урона
  otkryt_verh: 1                                  верхняя карта в руку до конца раунда; не сыграна — назад на верх
  zameshaj_sbros: 1                               замешать свой сброс в колоду
  otdat_shchit: X                                 отдать союзнику до X своего щита
  ocenka: X                                       подсказка боту: ценность невидимого эффекта при планировании"""
from .effects import op, X, compile_block, who, store, EffectError


@op('zaslon')
def _zaslon(arg, w):
    arg = dict(arg or {})
    komu = arg.pop('komu', 'soyuznik')
    has_rider = 'effekt' in arg
    eff, sub = compile_block(arg.pop('effekt', None) or [], w + ' (effekt)')
    flags = {k: X(arg[k], w) for k in ('sila', 'stojkij', 'perehod', 'polnyj', 'opora') if k in arg}
    extra = set(arg) - set(flags)
    if extra:
        raise EffectError(f'{w}: у zaslon лишние ключи {sorted(extra)}')

    def run(f, ctx):
        mods = {k: fn(f, ctx) for k, fn in flags.items()}
        mods = {k: v for k, v in mods.items() if v}
        for h in who(f, ctx, komu):
            f.zaslon(h, mods, (eff, ctx.me, ctx.card) if has_rider else None)
    return run, sub


@op('snyat_zaslon')
def _snyat(arg, w):
    s = (arg or {}).get('s', 'soyuznik'); v = (arg or {}).get('v')
    def run(f, ctx):
        n = sum(f.unzaslon(h) for h in who(f, ctx, s))
        store(ctx, v, n)
    return run


@op('perenesti_zaslon')
def _move(arg, w):
    def run(f, ctx):
        me, al = f.H[ctx.me], f.H[f.ally(ctx.me)]
        src, dst = (al, me) if al.blessed and not me.blessed else (me, al)
        if src.blessed and not dst.blessed and dst.alive:
            dst.blessed = True; dst.zmod = src.zmod; dst.zriders = src.zriders
            src.blessed = False; src.zmod = {}; src.zriders = []
    return run


@op('perehvat')
def _perehvat(arg, w):
    n = X(arg, w)
    def run(f, ctx):
        f.intercept = max(f.intercept, 1 + n(f, ctx))     # 1 + насколько ещё слабее удар
    return run


@op('zapret_urona')
def _nodmg(arg, w):
    return lambda f, ctx: setattr(f, 'no_dmg_cards', True)


@op('tolko_molitvy')
def _nohand(arg, w):
    return lambda f, ctx: setattr(f, 'no_hand', True)


@op('shchit_potom')
def _later_shield(arg, w):
    n = X(arg['n'], w); komu = arg.get('komu', 'ja')
    def run(f, ctx):
        v = n(f, ctx)
        if f.planning:
            f.est_f += 0.7 * v * len(who(f, ctx, komu))
            return
        for h in who(f, ctx, komu):
            f.next_shields[h] = f.next_shields.get(h, 0) + v
    return run


@op('smena_blagoslovenij')
def _swap(arg, w):
    return lambda f, ctx: f.swap_blessings()


@op('perevernut_veru')
def _flip(arg, w):
    def run(f, ctx):
        P = f.H[f.P]
        if P.faith > 0:
            P.faith = 7 - P.faith
    return run


@op('szhech_veru')
def _burnfaith(arg, w):
    n = X(arg.get('n', 'vera'), w); v = arg.get('v')
    def run(f, ctx):
        P = f.H[f.P]; k = max(0, min(int(n(f, ctx)), P.faith))
        P.faith -= k; f.st('vera_potrachena', k); store(ctx, v, k)
    return run


@op('relikvarij')
def _reliq(arg, w):
    def run(f, ctx):
        P = f.H[f.P]; f.reliq += P.faith; P.faith = 0
    return run


@op('chudo_ne_szhigaet')
def _mirkeep(arg, w):
    return lambda f, ctx: setattr(f, 'mir_keep', True)


@op('usilit_vraga')
def _buff(arg, w):
    n = X(arg, w)
    return lambda f, ctx: f.weaken(-n(f, ctx))


@op('ne_v_limit')
def _free(arg, w):
    def run(f, ctx):
        f.H[ctx.me].maxplays += 1
    return run


@op('konec_hoda')
def _endturn(arg, w):
    def run(f, ctx):
        h = f.H[ctx.me]; h.maxplays = h.plays
    return run


@op('eta_na_verh')
def _ontop(arg, w):
    return lambda f, ctx: f._post.append('na_verh')


def _best_first(cards):
    return sorted(cards, key=lambda c: c.value)          # конец списка — верх колоды


@op('smotri_verh')
def _look(arg, w):
    n = X(arg.get('n', 2), w); k = X(arg.get('vzyat', 0), w); rest = arg.get('ostalnye', 'verh')
    def run(f, ctx):
        h = f.H[ctx.me]; nn = int(n(f, ctx)); kk = int(k(f, ctx))
        if f.planning:
            f.est += 0.4 * nn; h.pend += kk
            return
        top = []
        for _ in range(nn):
            c = f._top(ctx.me)
            if c is None:
                break
            h.draw.pop(); top.append(c)
        top = _best_first(top)
        take = top[len(top) - kk:] if kk else []
        top = top[:len(top) - kk] if kk else top
        h.hand += take
        if rest == 'szhech':
            for c in top:
                f._exile(ctx.me, c)
        elif rest == 'niz':
            h.draw[0:0] = top
        else:
            h.draw += top
    return run


@op('uporyadochit')
def _order(arg, w):
    n = X(arg, w)
    def run(f, ctx):
        h = f.H[ctx.me]; nn = int(n(f, ctx))
        if f.planning:
            f.est += 0.4 * nn
            return
        top = []
        for _ in range(nn):
            c = f._top(ctx.me)
            if c is None:
                break
            h.draw.pop(); top.append(c)
        h.draw += _best_first(top)
    return run


@op('na_verh_iz_ruki')
def _handtop(arg, w):
    n = X(arg.get('n', 1), w); v = arg.get('v'); tag = arg.get('tolko_metka')
    def run(f, ctx):
        h = f.H[ctx.me]; done = 0
        for _ in range(int(n(f, ctx))):
            cands = [c for c in f._free_cards(h.hand) if c is not ctx.card and (tag is None or tag in c.tags)]
            if not cands:
                break
            c = max(cands, key=lambda x: x.value)
            h.hand = [x for x in h.hand if x is not c]; h.draw.append(c); done += 1
        store(ctx, v, done)
    return run


@op('iz_sbrosa_na_verh')
def _disctop(arg, w):
    n = X(arg, w)
    def run(f, ctx):
        h = f.H[ctx.me]
        for _ in range(int(n(f, ctx))):
            if not h.disc:
                break
            c = max(h.disc, key=lambda x: x.value)
            h.disc = [x for x in h.disc if x is not c]; h.draw.append(c)
    return run


@op('sbros_verha')
def _mill(arg, w):
    n = X(arg.get('n', 1), w); v = arg.get('v')
    def run(f, ctx):
        h = f.H[ctx.me]; atk = 0
        for _ in range(int(n(f, ctx))):
            c = f._top(ctx.me)
            if c is None:
                break
            h.draw.pop(); h.disc.append(c); atk += int(c.kind == 'атака')
        store(ctx, v, atk)
        if atk:
            f.H[ctx.me].discarded = True
    return run


@op('otkryt_verh')
def _open(arg, w):
    def run(f, ctx):
        h = f.H[ctx.me]
        if f.planning:
            h.pend += 1
            return
        c = f._top(ctx.me)
        if c is None:
            return
        h.draw.pop(); h.hand.append(c); f.opened = f.opened + [c]
    return run


@op('ocenka')
def _est(arg, w):
    n = X(arg, w)
    def run(f, ctx):
        if f.planning:
            f.est += n(f, ctx)
    return run


@op('zameshaj_sbros')
def _shuffle_disc(arg, w):
    def run(f, ctx):
        h = f.H[ctx.me]
        if f.planning or not h.disc:
            return
        h.draw = h.disc + h.draw; h.disc = []
        f.rng.shuffle(h.draw)
    return run


@op('otdat_shchit', shield=True)
def _give_shield(arg, w):
    n = X(arg, w)
    def run(f, ctx):
        me = f.H[ctx.me]; k = min(me.shield, max(0, int(n(f, ctx))))
        me.shield -= k; f.shield(f.ally(ctx.me), k)
    return run
