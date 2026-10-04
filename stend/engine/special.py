# -*- coding: utf-8 -*-
"""Особые операции: механики, которые не собрать из общего словаря эффектов.
Пишутся в карте так:  - osobyj: {imya: rok, porcha: porcha, mnozhitel: mnozhitel}
Параметры — выражения (обычно имена из chisla карты). Новую особую операцию добавляет человек или Claude,
агенту их менять нельзя."""
from .effects import X, compile_block, Ctx, EffectError

SPECIAL = {}


def special(name, dmg=False, shield=False):
    def deco(fn):
        SPECIAL[name] = (fn, dmg, shield)
        return fn
    return deco


def P(params, key, w, default=None):
    if key not in params:
        if default is None:
            raise EffectError(f'{w}: у особой операции нет параметра «{key}»')
        return X(default, w)
    return X(params[key], w)


# ================================================================ Маг
@special('sozhgi_etu')
def _burn_self(params, w):
    """После розыгрыша эта карта сгорает (даёт заряд)."""
    return lambda f, ctx: f._after.append(('burn_self', None))


@special('feniks')
def _phoenix(params, w):
    """Когда эта карта сгорает, в начале следующего раунда она возвращается в руку."""
    return lambda f, ctx: f.phx_mark(ctx.card)


@special('vozvrat_odin_raz')
def _ash_once(params, w):
    """Когда эта карта сгорает в первый раз за бой, в начале следующего раунда она возвращается в руку."""
    def run(f, ctx):
        if id(ctx.card) not in f.ash_used:
            f.ash_used = f.ash_used | {id(ctx.card)}
            f.phx_mark(ctx.card); f.st('vozvrat_odin_raz')
    return run


@special('steklo')
def _glass(params, w):
    """Следующее попадание мага в раунде ×множитель; после розыгрыша с шансом карта сгорает."""
    shans = P(params, 'shans', w); zar = P(params, 'zaryad', w, 0)
    def run(f, ctx):
        f.mmult = True
        f._after.append(('glass', (shans(f, ctx), zar(f, ctx))))
    return run


@special('rok', dmg=True)
def _doom(params, w):
    porcha = P(params, 'porcha', w); k = P(params, 'mnozhitel', w)
    def run(f, ctx):
        e = f.E
        f.add_porcha(porcha(f, ctx))
        if e.hp > 0 and e.porcha * k(f, ctx) >= e.hp:
            f.st('rok_ubil'); f.kill_enemy(ctx.me)
    return run


@special('razryv', dmg=True)
def _rip(params, w):
    k = P(params, 'za_porchu', w)
    def run(f, ctx):
        n = f.E.porcha
        if n <= 0:
            return
        f.E.porcha = 0; f.st('razryv')
        f.hit(ctx.me, k(f, ctx) * n)
    return run


@special('gnil')
def _rot(params, w):
    """В конце этого раунда Порча на враге не снимается."""
    def run(f, ctx):
        f.rot = True; f.st('gnil')
    return run


@special('kukla', shield=True)
def _doll(params, w):
    hp = P(params, 'zdorove', w)
    def run(f, ctx):
        f.doll += hp(f, ctx); f.st('kukla')
    return run


@special('pozdnij_uron', dmg=True)
def _late(params, w):
    n = P(params, 'n', w)
    return lambda f, ctx: setattr(f, 'late_dmg', f.late_dmg + n(f, ctx))


@special('razrastanie', shield=True)
def _prolif(params, w):
    porcha = P(params, 'porcha', w, 1); zar = P(params, 'zaryad', w, 1); sh = P(params, 'shchit', w, 1)
    def run(f, ctx):
        f.add_porcha(porcha(f, ctx)); f.add_charge(zar(f, ctx))
        for k in f.order:
            if f.H[k].shield > 0:
                f.shield(k, sh(f, ctx))
    return run


@special('oskolki', dmg=True)
def _shards(params, w):
    """Взять в руку N жетонов-Осколков (карта-жетон из папки героя)."""
    n = P(params, 'n', w); token = params.get('karta', 'oskolok')
    def run(f, ctx):
        td = f.game.cards[token]
        k = int(n(f, ctx))
        if f.planning:      # оценка бота: осколки будут сыграны после переплана
            for _ in range(k):
                f.hit(ctx.me, td.numbers.get('uron', 2)); f.charges += 1; f.burned_rnd += 1
            return
        from .data import CardInst
        for _ in range(k):
            f.H[ctx.me].hand.append(CardInst(td, ctx.me))
        f.st('oskolkov', k)
    return run


@special('chuzhoe_plamya', dmg=True, shield=True)
def _alien(params, w):
    """Союзник может сжечь 1 карту выбранного вида: урон → урон врагу, щит → щит союзнику, иначе добор."""
    vybor = params.get('vybor', 'drugoe'); n = P(params, 'n', w); dob = P(params, 'dobor', w)
    def run(f, ctx):
        a = f.H[f.ally(ctx.me)]
        if not a.alive:
            return
        cands = f._free_cards(a.hand)
        if vybor == 'uron':
            cands = [c for c in cands if c.d.has_dmg]
        elif vybor == 'shchit':
            cands = [c for c in cands if c.d.has_shield]
        else:
            cands = [c for c in cands if not c.d.has_dmg and not c.d.has_shield]
        if not cands:
            return
        c = min(cands, key=lambda x: x.value)
        a.hand.remove(c); f._exile(a.id, c); a.burned_by_ally_rnd += 1
        f.st('soyuznik_szheg'); f.st('chuzhoe_plamya')
        v = n(f, ctx)
        if c.d.has_dmg:
            f.hit(ctx.me, v)
        if c.d.has_shield:
            f.shield(a.id, v)
        if not c.d.has_dmg and not c.d.has_shield:
            f.draw(ctx.me, dob(f, ctx))
    return run


@special('eho')
def _echo(params, w):
    """Повтори эффект самой ценной карты, сыгранной союзником в этом раунде (без доплаты)."""
    def run(f, ctx):
        a = f.H[f.ally(ctx.me)]
        if not a.played:
            return
        card, opt = f.choices.echo_pick(f, a.played)
        f.st('eho')
        card.d.variants[opt].effect(f, Ctx(a.id, card, 0, False, opt))
    return run


# ================================================================ Жрец
@special('sozhgi_verh_svoej')
def _burn_top(params, w):
    """Сожги верхнюю карту своей колоды (без заряда мага). В переменную v — 1, если это карта урона."""
    v = params.get('v', 'szhzhena_ataka')
    def run(f, ctx):
        c = f._top(ctx.me)
        ctx.loc[v] = 0
        if c is None:
            return
        h = f.H[ctx.me]; h.draw.pop(); h.exiled.append(c); f.st('szhzheno_sverhu')
        ctx.loc[v] = int(c.kind == 'атака')
    return run


@special('potrat_veru')
def _spend(params, w):
    n = P(params, 'n', w)
    return lambda f, ctx: f.spend_faith(n(f, ctx))


@special('potrat_manu')
def _spend_mana(params, w):
    n = P(params, 'n', w)
    def run(f, ctx):
        f.H[ctx.me].mana -= n(f, ctx)
    return run


@special('stena_molitv', shield=True)
def _wall(params, w):
    sh = P(params, 'shchit', w)
    def run(f, ctx):
        if f.planning:
            f.est += f.R['bot']['ocenka_molitvy'] * 1.4; f.pray_rnd += 1
            return
        P_ = f.H[f.P]
        top = []
        if f._top(f.P) is not None:
            n = f.R['molitva_otkryt'] + f.pray_bonus
            top = P_.draw[-n:]
        both = any(c.kind == 'защита' for c in top)
        f.pray(ctx, n_play=2 if both else 1)
        f.shield(f.P, sh(f, ctx)); f.shield(f.M, sh(f, ctx))
    return run


@special('klejmo')
def _brand(params, w):
    n = P(params, 'n', w)
    def run(f, ctx):
        f.brand = max(f.brand, n(f, ctx))
    return run


@special('muchenik')
def _martyr(params, w):
    n = P(params, 'n', w)
    def run(f, ctx):
        f.martyr = max(f.martyr, n(f, ctx))
    return run


@special('horugv')
def _banner(params, w):
    return lambda f, ctx: setattr(f, 'banner', True)


@special('bolshoe_blagoslovenie')
def _bigbless(params, w):
    return lambda f, ctx: setattr(f, 'bless_big', True)


@special('karayushchij_pokrov')
def _cover(params, w):
    return lambda f, ctx: setattr(f, 'cover', True)


@special('bdenie')
def _vigil(params, w):
    def run(f, ctx):
        f.vigil = True
        if f.planning:
            f.est_f += 0.5 * int(f.H[f.P].faith >= f.R['bdenie_porog'])
    return run


@special('blagaya_vest')
def _news(params, w):
    def run(f, ctx):
        f.news = True
        if f.planning:
            f.est_f += 0.6
    return run


@special('vdohnovenie')
def _inspire(params, w):
    def run(f, ctx):
        M = f.H[f.M]
        f.draw(f.M, 1)
        if f.planning:
            f.est += 0.6
        elif M.hand:
            f.inspired = f.inspired + [M.hand[-1]]
    return run


@special('poslushnik')
def _novice(params, w):
    n = P(params, 'n', w)
    def run(f, ctx):
        f.mir_plus += n(f, ctx)
    return run
