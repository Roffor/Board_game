# -*- coding: utf-8 -*-
"""Один бой по описанию задания. Выполняется в процессах пула."""
import signal, time, traceback

import engine
from .bot import run_fight
from .decks import build_deck, upgrade_pool
from . import situacii as S

_ROOT = None
_GAMES = {}
_TIMEOUT = 120


def init(root, timeout):
    global _ROOT, _TIMEOUT
    _ROOT = root; _TIMEOUT = timeout


def game_for(pravki):
    key = tuple(sorted((pravki or {}).items()))
    g = _GAMES.get(key)
    if g is None:
        if len(_GAMES) > 64:
            _GAMES.clear()
        g = _GAMES[key] = engine.load_game(_ROOT, dict(key))
    return g


def decks_for(g, v, sit, seed):
    """Колоды варианта: обязательные карты + случайные апгрейды (одни и те же для всех вариантов на этом сиде)."""
    n = S.APGREJDOV[sit]; out = {}; salts = {'mag': S.SOL_MAG, 'zhrec': S.SOL_ZHREC}
    for hid in sorted(g.heroes):
        spec = v['geroi'][hid]
        own = list(spec.get('obyazatelno') or [])
        if spec['apgrejdy'] == 'sluchajno':
            pul = spec['pul']
            pool = upgrade_pool(g, hid, tuple(pul.split('+'))) if isinstance(pul, str) else list(pul)
            ups = S.random_upgrades(pool, n, seed, salts.get(hid, (13, 7)), exclude=own)
        else:
            ups = list(spec['apgrejdy'])[:n]
        out[hid] = build_deck(g, hid, own + ups, spec.get('start'))
    return out


def _timeout(*a):
    raise TimeoutError('бой дольше тайм-аута')


def one(job):
    """job: dict(faza, volna, v (вариант: metka, geroi, pravki), sit, i, seed0). Возвращает строку результата."""
    v = job['v']; sit = job['sit']
    seed = S.seed_of(job['seed0'], sit, job['i'])
    row = dict(faza=job['faza'], volna=job['volna'], v=v['metka'], kt=v.get('kt'), sit=sit, i=job['i'], seed=seed)
    signal.signal(signal.SIGALRM, _timeout); signal.alarm(_TIMEOUT)
    t = time.time()
    try:
        g = game_for(v.get('pravki'))
        enemy, loc = S.pick(g, sit, seed)
        decks = decks_for(g, v, sit, seed)
        r, bot, f = run_fight(g, decks, enemy, loc, seed)
        hp = sum(h.maxhp for h in f.H.values())
        var = bot.var_rounds
        st = r['stats']
        dm, dp = st.get('uron_mag', 0), st.get('uron_zhrec', 0)
        row.update(won=r['won'], rounds=r['rounds'], stuck=r['stuck'], enemy=r['enemy'], loc=loc.lid,
                   taken=sum(r['taken'].values()), taken_h=r['taken'], hp_pair=hp,
                   maxhp={k: h.maxhp for k, h in f.H.items()}, min_frac=r['min_frac'],
                   choice=(sum(1 for a in var if a[1] > 0) / len(var)) if var else 0.0,
                   plays=st.get('sygrano_mag', 0) + st.get('sygrano_zhrec', 0),
                   dmg_share_mag=(dm / (dm + dp)) if dm + dp else None,
                   karty=st.get('karty', {}), v_ruke=st.get('v_ruke', {}), shchit_pary=st.get('shchit_mag', 0) + st.get('shchit_zhrec', 0),
                   shchit_h={'mag': st.get('shchit_mag', 0), 'zhrec': st.get('shchit_zhrec', 0)}, vrag_bil=st.get('vrag_bil', 0), errors_bot=bot.errors,
                   deck={k: [c.cid for c in d] for k, d in decks.items()})
    except TimeoutError as ex:
        row.update(error='timeout', detail=str(ex))
    except Exception as ex:
        row.update(error=repr(ex), detail=traceback.format_exc()[-1500:])
    finally:
        signal.alarm(0)
    row['sec'] = round(time.time() - t, 3)
    return row
