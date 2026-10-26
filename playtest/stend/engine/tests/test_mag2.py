# -*- coding: utf-8 -*-
"""Новые правила мага и механики его банка ведут себя как задумано (Подношение, Порча-индикатор, долг, легендарки).
Запуск: python -m engine.tests.test_mag2  (из папки playtest/stend)"""
import os, sys
from engine import load_game, Fight, Choices, CardInst
from engine import mag2

ROOT = os.path.join(os.path.dirname(__file__), '..', '..', '..', '..')


def fight(g, extra=(), seed=3):
    decks = {h: g.start_deck(h, zapasnoj=True) for h in g.heroes}
    decks['mag'] = decks['mag'] + [g.cards[c] for c in ('m001-udar',) + tuple(extra)]
    e = g.enemies_of('II')[0]
    f = Fight(g, decks, e, None, seed, Choices())
    f.start_round()
    f.E.hp = f.E.maxhp = 99; f.E.shield = 0; f.E.porcha = 0; f.E.traits.pop('armor', None)
    f.H[f.M].mana = 9
    return f


def play(f, cid, vi=0, hid=None, o=0):
    hid = f.M if hid is None else hid
    c = CardInst(f.game.cards[cid], hid); f.H[hid].hand.append(c)
    return f.play(hid, c, vi, o)


def run():
    g = load_game(ROOT)
    bad = []; n = [0]

    def check(name, cond):
        n[0] += 1
        if not cond:
            bad.append(name)

    f = fight(g); check('Правила включены колодой банка', f.nm)
    # Порча — индикатор: +2 к каждому попаданию, повторное наложение не копится, снимается в конце раунда
    play(f, 'm061-sglaz'); play(f, 'm061-sglaz'); PS = g.rules['porcha_sila']   # сила Порчи из правил (2026-10-26: +1)
    check('Порча не копится', f.E.porcha == PS)
    e0 = f.E.hp; f.hit(f.M, 3); f.hit(f.P, 3); check('Порча +сила к каждому попаданию', e0 - f.E.hp == 6 + 2 * PS)
    mag2.end_round_porcha(f); check('Порча снята в конце раунда', f.E.porcha == 0)
    # Порча держится раунд
    f = fight(g); play(f, 'm061-sglaz'); play(f, 'm063-gnil'); mag2.end_round_porcha(f)
    check('Гниль: Порча держится', f.E.porcha == PS)
    # Займ: мана сейчас, плата в начале следующего хода; не хватило маны — долг остаётся
    f = fight(g); m0 = f.H[f.M].mana; play(f, 'm094-zajm')
    check('Займ: мана сейчас', f.H[f.M].mana >= m0 + 2 - 1 and f.m2.debt == 2)
    f.H[f.M].mana = 0; f.finish_round(); f.start_round()
    check('Займ: плата из маны', f.m2.paid == 2 and f.m2.debt == 0)
    f = fight(g); play(f, 'm094-zajm'); f.m2.debt = 9; f.finish_round(); f.start_round()
    check('Долг больше маны переходит дальше', f.m2.debt > 0)
    # Вклад: отдал сейчас — получил больше в следующий ход
    f = fight(g); play(f, 'm114-vklad'); check('Вклад записан', f.m2.credit == 3)
    # Залог: карта под планшетом, долг отдан — карта в руке
    f = fight(g); play(f, 'm115-zalog'); z = list(f.m2.zalog)
    check('Залог: карта под планшетом', len(z) == 1 and f.m2.debt > 0)
    f.finish_round(); f.H[f.M].mana = 0; f.start_round()
    check('Залог: карта вернулась', not f.m2.zalog and any(c is z[0] for c in f.H[f.M].hand))
    # Отложить: карта в следующий ход в руке и бесплатно
    f = fight(g); play(f, 'm101-otlozhit'); k = list(f.m2.free_next)
    f.finish_round(); f.start_round()
    check('Отложенная карта бесплатна', k and mag2.cost_of(f, f.H[f.M], k[0]) == 0)
    # Подношение: жетон, когда за один розыгрыш сожжено 2+ карты; Подношение-строка тратит жетон
    f = fight(g); f.m2.ptok = 0; play(f, 'm029-dvojnaya-zhertva')
    check('Жетон за 2 сожжённые', f.m2.ptok == 1)
    f = fight(g); f.m2.ptok = 1; play(f, 'm128-mechenyj-udar', o=1)
    check('Подношение тратит жетон и кладёт Порчу', f.m2.ptok == 0 and f.E.porcha == PS)
    # Легендарки
    f = fight(g, ['m156-glubokij-sglaz']); f.bl[f.M] = 'sol'; play(f, 'm061-sglaz'); play(f, 'm061-sglaz')
    MX = g.rules['porcha_maks_zhetonov']; ZH = min(4, MX)   # предел жетонов из правил (26.10: 3)
    check('Глубокий сглаз: жетоны копятся', f.m2.ptoks == ZH and f.E.porcha == ZH * g.rules.get('porcha_zheton', 1))
    f.bl[f.M] = 'lun'; mag2.end_round_porcha(f); check('Глубокий сглаз Лунарис: −1 жетон', f.m2.ptoks == ZH - 1)
    f = fight(g, ['m158-plata-duham']); f.bl[f.M] = 'lun'; f.m2.debt = 3; f.H[f.M].shield = 0; f.shield(f.M, 4)
    check('Плата духам Лунарис: щит гасит долг', f.m2.debt == 0 and f.H[f.M].shield == 1)
    f = fight(g, ['m152-pepelnyj-tron']); c = CardInst(g.cards['m001-udar'], f.M); f.H[f.M].exiled.append(c)
    mag2.ash_open(f); check('Пепельный трон: сожжённая в руке', any(x is c for x in f.H[f.M].hand))
    dp = g.cards['m152-pepelnyj-tron'].numbers['doplata']
    check('Пепельный трон: доплата', mag2.cost_of(f, f.H[f.M], c) == c.d.cost + dp)
    mag2.finish_round(f); check('Пепельный трон: назад в сожжённые', any(x is c for x in f.H[f.M].exiled))
    check('Легендарка не в колоде', not any(x.d.set == 'legendarka' for x in f.H[f.M].draw + f.H[f.M].hand))
    print(f'механики банка мага: проверок {n[0]}, ошибок {len(bad)}' + (': ' + ', '.join(bad) if bad else ''))
    return not bad


if __name__ == '__main__':
    sys.exit(0 if run() else 1)
