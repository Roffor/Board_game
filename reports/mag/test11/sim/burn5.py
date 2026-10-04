# -*- coding: utf-8 -*-
"""Тест билда №5: бюджет апгрейда поднят с +1,5 до +3 очков силы (Никита 2026-09-29).
Карты слабее +0,5 в тестах №3–4 получили примерно +1,5 очка; тексты — cards/mag/07. Поверх burn4.py."""
import burn2
from burn2 import p
from burn4 import B4Game, M_start, M_bank as M_bank4, DEFAULTS as D4
from burn import one
from cards import ally

DEFAULTS = dict(D4)
DEFAULTS.update({'common.sh': 1, 'gift.per': 3, 'ashsh.per': 2, 'alien.n': 5, 'alien.draw': 3,
                 'phx.dmg': 0, 'emb.cost': 0, 'emb.per': 2})
REMOVED = {'n_deal'}   # ждёт новой карты на «убери статус»
BOOSTED = []


def M_bank():
    U = [c for c in M_bank4() if c.cid not in REMOVED]
    by = {c.cid: c for c in U}
    def r(cid, text, opts=None, **kw):
        c = by[cid]; c.text = text; BOOSTED.append(cid)
        if opts is not None:
            c.opts = opts
        for k, v in kw.items():
            setattr(c, k, v)
    F = '0 маны. Топливо. '
    r('a_ember', F + '1 щит себе. Сожжена: 4 попадания по 1.', on_burn=lambda g: [g.hit('M', 1) for _ in range(p('ember.n', 4))])
    r('a_spirits', '0 маны. 1 щит себе, возьми 1 карту. До конца раунда каждое сжигание — попадание по 1.',
      one(lambda g, h, o: (g.shield(h, 1), g.draw(h, p('spirits.draw', 1)), g.set_pyre())), tags=('draw',))
    r('a_rite', '2 маны. 5 урона и 3 щита себе. Подношение 2: ещё 3 урона, весь урон сквозь щит.',
      one(lambda g, h, o: (g.hit(h, p('rite.d', 5) + (3 if o else 0) + (3 if o >= 2 else 0), pierce=bool(o)), g.shield(h, 3))))
    r('a_common', '1 мана. Ты и союзник сжигаете до 2 карт из руки, берёте столько же и получаете по 1 щиту.')
    r('a_ash2', '1 мана. Сожги 1 карту из руки, возьми 3 карты.', one(lambda g, h, o: (g.burn(h, 1), g.draw(h, p('ash2.d', 3)))), cost=p('ash2.cost', 1))
    r('n_chain', '0 маны. Сожги 1 карту из руки. Если это было топливо, союзник может сжечь 1 карту из руки и взять 1.', cost=p('chain.cost', 0))
    r('a_palm', F + '1 щит себе. Сожжена: следующее попадание союзника в этом раунде +5.', on_burn=lambda g: g.ally_bonus(5))
    r('a_sacshield', '1 мана. Союзник получает Авангард и 6 щитов. Подношение: +3 щита ему.',
      one(lambda g, h, o: (g.vanguard(ally(h)), g.shield(ally(h), p('sac.sh', 6) + 3 * o))))
    r('a_greedy', '1 мана. Сожги всю остальную руку. Возьми столько, сколько сжёг, минус 1.', cost=p('greedy.cost', 1))
    r('a_debt', '0 маны. +2 заряда; +3, если союзник в этом раунде получал урон или сжигал карту.',
      one(lambda g, h, o: g.add_charge(p('debt.b', 2) + (1 if (g.ally_burned_rnd or g.lost_rnd) else 0))))
    r('a_blood', '0 маны. 1 Порча. Подношение (сколько угодно раз): +1 Порча.',
      one(lambda g, h, o: g.porcha(1 + o)), tags=('porcha',), cost=p('blood5.cost', 0))
    r('a_gift', '1 мана. Союзник может сжечь любое число карт из руки и получает 3 щита за каждую. Подношение: ты тоже.')
    r('n_ashshield', '1 мана. 2 щита себе за каждую карту, сожжённую в этом раунде.')
    r('n_shield2', '0 маны. 2 щита союзнику. Подношение (сколько угодно раз): ещё 2 щита союзнику.',
      one(lambda g, h, o: g.shield('P', p('sh2.b', 2) + 2 * o)))
    r('n_alien', '1 мана. Союзник может сжечь 1 карту из руки. Если на ней есть урон — 5 урона врагу. '
                 'Если есть щит — 5 щитов союзнику. Если нет ни того, ни другого — возьми 3 карты.')
    r('a_spirit', '1 мана. 5 щитов себе ИЛИ союзнику, 2 щита другому. Подношение: +3 щита другому.',
      [('себе', lambda g, h, o: (g.shield(h, p('spirit.m', 5)), g.shield(ally(h), 2 + 3 * o))),
       ('союзнику', lambda g, h, o: (g.shield(ally(h), p('spirit.m', 5)), g.shield(h, 2 + 3 * o)))])
    r('a_whirl', '1 мана. Сожги 3 верхние карты своей колоды ИЛИ колоды союзника.',
      [('своей', lambda g, h, o: g.burn(h, p('whirl.n', 3), 'top')), ('союзника', lambda g, h, o: g.burn(h, p('whirl.n', 3), 'ally_top'))], cost=p('whirl.cost', 1))
    r('n_answer', '1 мана. 3 урона, +2 за каждую карту, сожжённую союзником в этом раунде.',
      one(lambda g, h, o: g.hit(h, 3 + 2 * g.ally_burned_rnd)))
    r('n_embers', '0 маны. Возьми 1 карту. Сбрось любое число карт из руки. В начале следующего раунда получи 2 заряда за каждую.',
      [(f'сбросить {k}', (lambda k: lambda g, h, o: (g.draw(h, p('emb.draw', 1)), g.embers(k)))(k)) for k in range(0, 5)])
    r('a_pyre', '2 маны. Сожги сколько угодно карт из руки. 2 щита себе за каждую.',
      [(f'сжечь {k}', (lambda k: lambda g, h, o: g.shield(h, p('pyre.per', 2) * g.burn(h, k)))(k)) for k in range(1, 6)], cost=p('pyre.cost', 2))
    r('a_brush', F + '1 щит себе. Сожжена: ещё 2 заряда и 1 щит себе.', on_burn=lambda g: (g.add_charge(p('brush.ch', 2)), g.shield('M', p('brush.sh', 1))))
    r('a_hero', F + '1 щит себе. Сожжена: союзник берёт 2 карты и получает 4 щита.', on_burn=lambda g: (g.draw('P', 2), g.shield('P', p('hero.sh', 4))))
    r('n_hands', '1 мана. Союзник может сжечь 1 карту из руки; если сжёг, его следующее попадание +5.',
      one(lambda g, h, o: g.ally_bonus(p('hands.b', 5)) if g.ally_burn(1) else None))
    r('n_rag', F + 'Сыграна: ничего. Сожжена: 2 урона и ещё 1 урон за каждый заряд подношения, который у тебя сейчас есть.',
      on_burn=lambda g: g.hit('M', p('rag.b', 2) + g.charges))
    r('a_bone', F + '1 щит себе. Сожжена: возьми 3 карты и 2 щита себе.', on_burn=lambda g: (g.draw('M', p('bone.d', 3)), g.shield('M', p('bone.sh', 2))))
    r('a_blade', '1 мана. Следующее попадание союзника +5. Подношение (сколько угодно раз): +3 к нему.',
      one(lambda g, h, o: g.ally_bonus(p('blade.b', 5) + 3 * o)))
    r('n_phoenix', '0 маны. Сожги эту карту. Когда эта карта сгорает, в начале следующего раунда она возвращается тебе в руку.')
    return U


class B5Game(B4Game):
    def clone_sim(self):
        g = super().clone_sim()
        g.__class__ = B5Game
        return g
