# -*- coding: utf-8 -*-
"""Словарь эффектов карт. Эффект — список шагов; каждый шаг — словарь с одним ключом (имя операции).

Общие операции (есть у всех героев):
  uron: X                         одно попадание по врагу на X (попадание 0 тоже попадание: Порча прибавляется)
  uron: {n: X, bez_broni: true}   попадание, которое пробивает Броню
  udary: {n: X, raz: Y}           Y попаданий по X
  shchit: {komu: ja|soyuznik|oba, n: X}
  porcha: X                       Порча на врага
  dobor: X / dobor_soyuznika: X   взять карты
  sozhgi: {otkuda: ruka|sbros|verh|verh_soyuznika, n: X, v: имя}   сжечь карты (маг получает заряд за каждую)
  soyuznik_szhigaet: {n: X, v: имя}       союзник может сжечь до X карт из руки (маг получает заряд)
  sbros: {n: X, v: имя} / soyuznik_sbrasyvaet: {n: X, v: имя}
  verni: {n: X, tolko_ranee: true}        вернуть в руку владельца сожжённые карты (свои или союзника)
  avangard: ja|soyuznik, blagoslovenie: soyuznik
  bonus_sebe: X / bonus_soyuzniku: X      следующее попадание этого героя в раунде сильнее на X
  esli: <условие>, to: [...], inache: [...]
  pust: {имя: выражение}                  запомнить число для следующих шагов
Механики Мага: mana, zaryad, a также особые операции из engine/special.py.
Механики Жреца: vera, chudo, molitva, obet, doplata (в вариантах карты) и особые операции.
Числа везде — выражения (см. engine/expr.py)."""
from .expr import compile_expr, ExprError


class EffectError(ValueError):
    pass


class Ctx:
    """Контекст розыгрыша одной карты."""
    __slots__ = ('me', 'card', 'o', 'paid', 'loc', 'opt')

    def __init__(self, me, card, o=0, paid=False, opt=0):
        self.me = me; self.card = card; self.o = o; self.paid = paid; self.loc = {}; self.opt = opt


def lookup(f, ctx):
    nums = ctx.card.d.numbers if ctx.card is not None else {}

    def look(name):
        if name in ctx.loc:
            return ctx.loc[name]
        if name in nums:
            return nums[name]
        if name == 'podnoshenie':
            return ctx.o
        if name == 'oplacheno':
            return int(bool(ctx.paid))
        return f.var(name, ctx.me)
    return look


def X(src, w):
    fn, _ = compile_expr(src, w)
    return lambda f, ctx: fn(lookup(f, ctx))


OPS = {}


def op(name, dmg=False, shield=False):
    def deco(fn):
        OPS[name] = (fn, dmg, shield)
        return fn
    return deco


def compile_block(steps, w):
    if steps is None:
        steps = []
    if not isinstance(steps, list):
        raise EffectError(f'{w}: эффект должен быть списком шагов')
    fns = []; info = {'dmg': False, 'shield': False}
    for i, s in enumerate(steps):
        sw = f'{w}, шаг {i + 1}'
        if not isinstance(s, dict) or not s:
            raise EffectError(f'{sw}: шаг должен быть словарём вида {{операция: значение}}')
        if 'esli' in s:
            extra = set(s) - {'esli', 'to', 'inache'}
            if extra:
                raise EffectError(f'{sw}: в шаге «esli» лишние ключи {sorted(extra)}')
            cond = X(s['esli'], sw)
            a, ia = compile_block(s.get('to') or [], sw + ' (to)')
            b, ib = compile_block(s.get('inache') or [], sw + ' (inache)')
            info['dmg'] |= ia['dmg'] or ib['dmg']; info['shield'] |= ia['shield'] or ib['shield']
            fns.append(lambda f, ctx, cond=cond, a=a, b=b: a(f, ctx) if cond(f, ctx) else b(f, ctx))
            continue
        if len(s) != 1:
            raise EffectError(f'{sw}: в шаге должна быть одна операция, а их {sorted(s)}')
        (name, arg), = s.items()
        if name not in OPS:
            raise EffectError(f'{sw}: неизвестная операция «{name}». Есть: {", ".join(sorted(OPS))}')
        comp, dmg, sh = OPS[name]
        try:
            fn = comp(arg, sw)
        except (ExprError, KeyError, TypeError) as e:
            raise EffectError(f'{sw}: «{name}»: {e}')
        if isinstance(fn, tuple):          # операция с вложенным эффектом сообщает, есть ли в нём урон и щит
            fn, sub = fn
            dmg = dmg or sub['dmg']; sh = sh or sub['shield']
        info['dmg'] |= dmg; info['shield'] |= sh
        fns.append(fn)

    def run(f, ctx):
        for fn in fns:
            fn(f, ctx)
    return run, info


def who(f, ctx, arg):
    if arg in ('ja', None):
        return [ctx.me]
    if arg == 'soyuznik':
        return [f.ally(ctx.me)]
    if arg == 'oba':
        return [ctx.me, f.ally(ctx.me)]
    raise EffectError(f'кому: ja, soyuznik или oba, а не {arg!r}')


def store(ctx, name, v):
    if name:
        ctx.loc[name] = v


# ---------------------------------------------------------------- урон
@op('uron', dmg=True)
def _uron(arg, w):
    if isinstance(arg, dict):
        n = X(arg['n'], w); ap = bool(arg.get('bez_broni'))
        return lambda f, ctx: f.hit(ctx.me, n(f, ctx), armor_pierce=ap)
    n = X(arg, w)
    return lambda f, ctx: f.hit(ctx.me, n(f, ctx))


@op('udary', dmg=True)
def _udary(arg, w):
    n = X(arg['n'], w); k = X(arg['raz'], w)
    def run(f, ctx):
        for _ in range(int(k(f, ctx))):
            f.hit(ctx.me, n(f, ctx))
    return run


# ---------------------------------------------------------------- защита
@op('shchit', shield=True)
def _shchit(arg, w):
    n = X(arg['n'], w); komu = arg.get('komu', 'ja')
    def run(f, ctx):
        v = n(f, ctx)
        for h in who(f, ctx, komu):
            f.shield(h, v)
    return run


@op('shchit_sebe', shield=True)
def _sh1(arg, w):
    n = X(arg, w)
    return lambda f, ctx: f.shield(ctx.me, n(f, ctx))


@op('shchit_soyuzniku', shield=True)
def _sh2(arg, w):
    n = X(arg, w)
    return lambda f, ctx: f.shield(f.ally(ctx.me), n(f, ctx))


@op('avangard')
def _avangard(arg, w):
    return lambda f, ctx: [f.vanguard(h) for h in who(f, ctx, arg)]


@op('blagoslovenie')
def _bless(arg, w):
    return lambda f, ctx: [f.bless(h) for h in who(f, ctx, arg)]


# ---------------------------------------------------------------- статусы и ресурсы
@op('porcha')
def _porcha(arg, w):
    n = X(arg, w)
    return lambda f, ctx: f.add_porcha(n(f, ctx))


@op('dobor')
def _dobor(arg, w):
    n = X(arg, w)
    return lambda f, ctx: f.draw(ctx.me, n(f, ctx))


@op('dobor_soyuznika')
def _dobor2(arg, w):
    n = X(arg, w)
    return lambda f, ctx: f.draw(f.ally(ctx.me), n(f, ctx))


@op('mana')
def _mana(arg, w):
    n = X(arg, w)
    return lambda f, ctx: f.gain_mana(ctx.me, n(f, ctx))


@op('zaryad')
def _zaryad(arg, w):
    n = X(arg, w)
    return lambda f, ctx: f.add_charge(n(f, ctx))


@op('vera')
def _vera(arg, w):
    n = X(arg, w)
    return lambda f, ctx: f.own_faith(n(f, ctx))


@op('bonus_sebe')
def _bonus_me(arg, w):
    n = X(arg, w)
    return lambda f, ctx: f.add_next_bonus(ctx.me, n(f, ctx))


@op('bonus_soyuzniku')
def _bonus_ally(arg, w):
    n = X(arg, w)
    return lambda f, ctx: f.add_next_bonus(f.ally(ctx.me), n(f, ctx))


@op('oslab_vraga')
def _weak(arg, w):
    n = X(arg, w)
    return lambda f, ctx: f.weaken(n(f, ctx))


# ---------------------------------------------------------------- карты
@op('sozhgi')
def _sozhgi(arg, w):
    n = X(arg.get('n', 1), w); src = arg.get('otkuda', 'ruka'); v = arg.get('v')
    if src not in ('ruka', 'sbros', 'verh', 'verh_soyuznika', 'ruka_soyuznika'):
        raise EffectError(f'{w}: otkuda — ruka, sbros, verh, verh_soyuznika или ruka_soyuznika')
    def run(f, ctx):
        store(ctx, v, f.burn(ctx.me, int(n(f, ctx)), src))
    return run


@op('soyuznik_szhigaet')
def _ally_burn(arg, w):
    n = X(arg.get('n', 1), w); v = arg.get('v')
    return lambda f, ctx: store(ctx, v, f.ally_burn(ctx.me, int(n(f, ctx))))


@op('sbros')
def _sbros(arg, w):
    n = X(arg.get('n', 1), w); v = arg.get('v')
    return lambda f, ctx: store(ctx, v, f.discard(ctx.me, int(n(f, ctx))))


@op('soyuznik_sbrasyvaet')
def _ally_disc(arg, w):
    n = X(arg.get('n', 1), w); v = arg.get('v')
    return lambda f, ctx: store(ctx, v, f.discard(f.ally(ctx.me), int(n(f, ctx))))


@op('snimok_szhzhennyh')
def _snap(arg, w):
    """Запомнить, какие карты сожжены к этому моменту (для «верни сожжённую раньше»)."""
    return lambda f, ctx: ctx.loc.__setitem__('_snap', f.burned_snapshot())


@op('verni')
def _verni(arg, w):
    n = X((arg or {}).get('n', 1), w); only_before = bool((arg or {}).get('tolko_ranee'))
    skip_self = bool((arg or {}).get('krome_etoj'))
    def run(f, ctx):
        before = ctx.loc.get('_snap') if only_before else None
        for _ in range(int(n(f, ctx))):
            f.restore(before=before, skip_card=ctx.card if skip_self else None)
    return run


# ---------------------------------------------------------------- логика
@op('pust')
def _pust(arg, w):
    fs = [(k, X(v, w)) for k, v in arg.items()]
    def run(f, ctx):
        for k, fn in fs:
            ctx.loc[k] = fn(f, ctx)
    return run


@op('nichego')
def _nothing(arg, w):
    return lambda f, ctx: None


# ---------------------------------------------------------------- Жрец: вера, Чудо, Молитва, Обет
@op('chudo')
def _chudo(arg, w):
    """Чудо: сжечь всю веру; число сожжённой веры кладётся в переменную (по умолчанию «chudo»)."""
    v = (arg or {}).get('v', 'chudo') if isinstance(arg, dict) else (arg or 'chudo')
    return lambda f, ctx: store(ctx, v, f.miracle())


@op('molitva')
def _molitva(arg, w):
    arg = arg or {}
    n_open = X(arg['otkryt'], w) if 'otkryt' in arg else None
    n_play = X(arg.get('sygrat', 1), w)
    uselimit = bool(arg.get('v_limit'))
    filt = arg.get('tolko_vid')
    then, sub = compile_block(arg.get('posle') or [], w + ' (posle)')
    est = X(arg.get('ocenka_bota', 0), w)
    def run(f, ctx):
        f.pray(ctx, n_open=None if n_open is None else int(n_open(f, ctx)), n_play=int(n_play(f, ctx)),
               uselimit=uselimit, kind_filter=filt, then=then if arg.get('posle') else None, est=est(f, ctx))
    return run, sub


@op('obet')
def _obet(arg, w):
    eff, sub = compile_block(arg['effekt'], w + ' (effekt)')
    when = {'nachalo': 'start', 'konec_fazy': 'endhp'}[arg.get('kogda', 'nachalo')]
    kind = arg.get('vid_ocenki', 'dmg')
    est = X(arg.get('ocenka_bota', 0), w)
    def run(f, ctx):
        f.vow(ctx, eff, kind, est(f, ctx), when)
    return run, sub


@op('blagoslovenie_s_effektom')
def _bless_rider(arg, w):
    eff, sub = compile_block(arg['effekt'], w + ' (effekt)')
    return (lambda f, ctx: f.bless_rider(ctx, eff)), sub


@op('osobyj')
def _special(arg, w):
    from . import special
    if isinstance(arg, str):
        name, params = arg, {}
    else:
        params = dict(arg); name = params.pop('imya')
    if name not in special.SPECIAL:
        raise EffectError(f'{w}: нет особой операции «{name}». Есть: {", ".join(sorted(special.SPECIAL))}')
    comp, dmg, sh = special.SPECIAL[name]
    fn = comp(params, w)
    return fn, {'dmg': dmg, 'shield': sh}
