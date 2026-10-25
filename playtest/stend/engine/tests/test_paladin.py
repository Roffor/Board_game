# -*- coding: utf-8 -*-
"""Механики банка Паладина ведут себя как задумано (Заслон, шипы, благословения, верх колоды, лимит, легендарки).
Запуск: python -m engine.tests.test_paladin  (из папки playtest/stend)"""
import os, sys
from engine import load_game, Fight, Choices, CardInst

ROOT = os.path.join(os.path.dirname(__file__), '..', '..', '..', '..')


def fight(g, extra=(), seed=3):
    decks = {h: g.start_deck(h) for h in g.heroes}
    decks['zhrec'] = decks['zhrec'] + [g.cards[c] for c in extra]
    e = g.enemies_of('II')[0]
    f = Fight(g, decks, e, None, seed, Choices())
    f.start_round()
    f.E.hp = f.E.maxhp = 99; f.E.shield = 0; f.E.porcha = 0
    return f


def play(f, cid, vi=0):
    P = f.H[f.P]; c = CardInst(f.game.cards[cid], f.P); P.hand.append(c)
    return f.play(f.P, c, vi, 0)


def run():
    g = load_game(ROOT)
    bad = []; n = [0]

    def check(name, cond):
        n[0] += 1
        if not cond:
            bad.append(name)

    # Заслон ослабляет удар и снимается; Крепкий — сильнее
    f = fight(g); play(f, 'b061-zaslon'); M = f.H[f.M]; hp = M.hp
    f.deal(f.M, 5); check('Заслон −3', M.hp == hp - 2 and not M.blessed)
    f = fight(g); play(f, 'b063-krepkij-zaslon'); M = f.H[f.M]; hp = M.hp
    f.deal(f.M, 6); check('Крепкий заслон −5', M.hp == hp - 1)
    # Стойкий: каждый удар раунда, снимается в конце раунда
    f = fight(g); play(f, 'b066-stojkij-zaslon'); M = f.H[f.M]; hp = M.hp
    f.deal(f.M, 4); f.deal(f.M, 4); check('Стойкий: два удара', M.hp == hp - 2 and M.blessed)
    f.finish_round(); check('Стойкий снят в конце раунда', not M.blessed)
    # Переходящий
    f = fight(g); play(f, 'b067-perehodyashchij-zaslon'); f.deal(f.M, 4)
    check('Переходящий на Паладина', f.H[f.P].blessed and not f.H[f.M].blessed)
    # Полный заслон и запрет урона
    f = fight(g); play(f, 'b085-polnyj-zaslon'); M = f.H[f.M]; hp = M.hp
    f.deal(f.M, 9); check('Полный заслон', M.hp == hp)
    check('Запрет карт урона', not play(f, 'b001-udar-mecha'))
    # Ответный: урон врагу при срабатывании
    f = fight(g); play(f, 'b069-otvetnyj-zaslon'); e0 = f.E.hp; f.deal(f.M, 4)
    check('Ответный заслон', f.E.hp < e0)
    # Перехват
    f = fight(g); play(f, 'b061-zaslon'); play(f, 'b074-perehvat'); M, P = f.H[f.M], f.H[f.P]
    mh, ph = M.hp, P.hp; P.shield = 0; f.deal(f.M, 8)
    check('Перехват: бьёт Паладина', M.hp == mh and P.hp == ph - 3)
    # Шипы: урон = снятый ударом щит
    f = fight(g, ['b153-shipy-zaslona']); play(f, 'b061-zaslon'); M = f.H[f.M]; M.shield = 4; e0 = f.E.hp
    f.bl[f.P] = 'lun'; f.deal(f.M, 6)
    check('Шипы по снятому щиту', e0 - f.E.hp == 3 and M.blessed)
    # Благословения
    f = fight(g); check('Старт: маг Соларис', f.bl[f.M] == 'sol' and f.bl[f.P] == 'lun')
    e0 = f.E.hp; play(f, 'b006-rassvet-i-sumerki'); check('Лунарис: щит союзнику', f.E.hp == e0)
    play(f, 'b005-smena-znamen'); check('Смена', f.bl[f.P] == 'sol' and f.bl_swapped)
    # Лимит: двуручный за две
    f = fight(g); play(f, 'b001-udar-mecha'); play(f, 'b001-udar-mecha')
    check('Двуручный не влезает', not play(f, 'b003-dvuruchnyj-zamah'))
    f = fight(g); check('Быстрый заслон вне лимита', all(play(f, 'b083-bystryj-zaslon') for _ in range(4)))
    # Вера: переворот
    f = fight(g); f.H[f.P].faith = 2; play(f, 'b036-perevorot'); check('Переворот 2→5', f.H[f.P].faith == 5)
    # Молитва: Возвращение на верх; Открытая молитва возвращается на верх
    f = fight(g); play(f, 'b102-vozvrashchenie'); check('Возвращение на верх', f.H[f.P].draw[-1].cid == 'b102-vozvrashchenie')
    f = fight(g); top = f.H[f.P].draw[-1]; play(f, 'b120-otkrytaya-molitva')
    check('Открытая: в руке', any(c is top for c in f.H[f.P].hand))
    f.finish_round(); check('Открытая: назад на верх', f.H[f.P].draw[-1] is top)
    # Легендарки
    f = fight(g, ['b151-neugasimaya-vera']); check('Неугасимая: вера на старте', f.H[f.P].faith >= 2)
    f = fight(g, ['b152-dvojnaya-molitva']); n0 = f.stats.get('molitvoj_sygrano', 0)
    play(f, 'b094-tihaya-molitva'); check('Двойная молитва: две карты', f.stats.get('molitvoj_sygrano', 0) - n0 == 2)
    check('Легендарка не в колоде', not any(c.d.set == 'legendarka' for c in f.H[f.P].draw + f.H[f.P].hand))
    print(f'механики банка Паладина: проверок {n[0]}, ошибок {len(bad)}' + (': ' + ', '.join(bad) if bad else ''))
    return not bad


if __name__ == '__main__':
    sys.exit(0 if run() else 1)
