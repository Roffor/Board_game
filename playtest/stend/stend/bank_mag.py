# -*- coding: utf-8 -*-
"""Генератор YAML банка идей мага (heroes/mag/idei-kart.md, 153 идеи, 2026-10-24) в heroes/mag/karty/bank/.
Правила мага для банка — engine/mag2.py (жетон Подношения, Порча-индикатор, долг). Числа черновые: тест может
их менять, добавлять урон и щит и немного менять концепт (решение Никиты 2026-10-25, ai/pravila/03 §2).

    python -m stend.bank_mag [--zamenit]"""
import os, sys
import yaml

ROOT = os.path.normpath(os.path.join(os.path.dirname(__file__), '..', '..', '..'))
OUT = os.path.join(ROOT, 'heroes', 'mag', 'karty', 'bank')

U = lambda n: {'uron': n}
SH = lambda komu, n: {'shchit': {'komu': komu, 'n': n}}
IF = lambda c, to, inache=None: ({'esli': c, 'to': to, 'inache': inache} if inache else {'esli': c, 'to': to})
PUST = lambda **kw: {'pust': kw}
D = lambda n: {'dobor': n}
P = lambda n=1: {'porcha': n}
BURN = lambda n=1, otkuda='ruka', v=None: {'sozhgi': dict({'otkuda': otkuda, 'n': n}, **({'v': v} if v else {}))}
RF = lambda **kw: {'do_konca_raunda': kw}
OBET = lambda eff, ocenka, vid='dmg': {'obet': {'kogda': 'nachalo', 'vid_ocenki': vid, 'ocenka_bota': ocenka, 'effekt': eff}}
OFF = 'podnoshenie'

BILD = {'Б': '', 'П': 'П', 'Р': 'Р', 'Д': 'Д', 'ПР': 'П–Р', 'РД': 'Р–Д', 'ПД': 'П–Д'}
CARDS = []


def C(n, slug, imya, bild, vid, cena, chisla, tekst, effekt=None, varianty=None, metki=None, bot=None,
      uproshcheno=None, extra=None):
    CARDS.append(dict(n=n, slug=slug, imya=imya, bild=bild, vid=vid, cena=cena, chisla=chisla, tekst=tekst,
                      effekt=effekt, varianty=varianty, metki=metki, bot=bot, uproshcheno=uproshcheno, extra=extra or {}))


def V(name, eff):
    return {'nazvanie': name, 'effekt': eff}


# ================================================================ База
C(1, 'udar', 'Удар', 'Б', 'атака', 1, {'uron': 4}, '{uron:урон}.', [U('uron')])
C(2, 'obereg', 'Оберег', 'Б', 'защита', 1, {'shchit': 5}, '{shchit:щит} себе или союзнику.',
  varianty=[V('себе', [SH('ja', 'shchit')]), V('союзнику', [SH('soyuznik', 'shchit')])])
C(3, 'dvulikij-zhest', 'Двуликий жест', 'Б', 'связка', 1, {'uron': 4, 'shchit': 3},
  'Соларис: {uron:урон}. Лунарис: {shchit:щит} себе и союзнику.', [IF('solaris', [U('uron')], [SH('oba', 'shchit')])], metki=['blag'])
C(4, 'strazh-poroga', 'Страж порога', 'Б', 'защита', 1, {'shchit': 5}, 'Авангард. {shchit:щит} себе.', [{'avangard': 'ja'}, SH('ja', 'shchit')])
C(5, 'povorot-neba', 'Поворот неба', 'Б', 'связка', 0, {'dobor': 1}, 'Смени благословения, возьми {dobor:карту}.',
  [{'smena_blagoslovenij': 1}, D('dobor')], metki=['blag'], bot={'pereplan': True})
C(6, 'otgolosok-peremeny', 'Отголосок перемены', 'Б', 'атака', 1, {'uron': 3, 'dop': 3},
  '{uron:урон}. Если в этом раунде благословения менялись, ещё {dop:урон}.', [U('uron + (dop if blag_menyalis else 0)')], metki=['blag'])
C(7, 'otlozhennyj-obereg', 'Отложенный оберег', 'Б', 'защита', 1, {'shchit': 4, 'shchit_big': 7, 'ocenka': 5},
  'Сейчас: {shchit:щит} себе. Или после хода врага: {shchit_big:щит} себе.',
  varianty=[V('сейчас', [SH('ja', 'shchit')]), V('после', [OBET([SH('ja', 'shchit_big')], 'ocenka', 'shield')])])
C(8, 'otlozhennyj-udar', 'Отложенный удар', 'Б', 'атака', 1, {'uron': 3, 'uron_big': 6, 'ocenka': 5},
  'Сейчас: {uron:урон}. Или после хода врага: {uron_big:урон}.',
  varianty=[V('сейчас', [U('uron')]), V('после', [OBET([U('uron_big')], 'ocenka')])])
C(9, 'trojnaya-primeta', 'Тройная примета', 'Б', 'атака', 1, {'uron_mal': 1, 'uron': 7, 'nuzhno': 2},
  '{uron_mal:урон}. Если 2 из 3 (на враге Порча; у союзника есть щит; благословения менялись в этом раунде): ещё {uron:урон}.',
  [PUST(c='(porcha > 0) + (shchit_soyuznika > 0) + blag_menyalis'), U('uron_mal + (uron if c >= nuzhno else 0)')], metki=['blag'])
C(10, 'gadanie-na-uglyah', 'Гадание на углях', 'Б', 'связка', 0, {'n': 3}, 'Посмотри {n} верхние карты, разложи в любом порядке, одну возьми.',
  [{'smotri_verh': {'n': 'n', 'vzyat': 1, 'ostalnye': 'verh'}}], bot={'pereplan': True})
C(11, 'shepot-predkov', 'Шёпот предков', 'Б', 'связка', 0, {'dobor': 2}, 'Возьми {dobor:карту}, сбрось одну.',
  [D('dobor'), {'sbros': {'n': 1}}], bot={'pereplan': True})
C(12, 'dym-nad-ochagom', 'Дым над очагом', 'Б', 'связка', 0, {'dobor': 1}, 'Сбрось карту: союзник берёт {dobor:карту}.',
  [{'sbros': {'n': 1, 'v': 's'}}, IF('s', [{'dobor_soyuznika': 'dobor'}])])
C(13, 'svecha-predkov', 'Свеча предков', 'Б', 'атака', 1, {'uron': 3, 'shchit': 3}, '{uron:урон}. Если эту карту сжигают, союзник получает {shchit:щит}.',
  [U('uron')], extra={'pri_szhiganii': [SH('soyuznik', 'shchit')]})
C(14, 'zhertvennaya-chasha', 'Жертвенная чаша', 'Б', 'атака', 1, {'uron': 3, 'uron_big': 6},
  '{uron:урон}. После розыгрыша можешь сжечь эту карту, тогда {uron_big:урон}.',
  varianty=[V('', [U('uron')]), V('сжечь', [U('uron_big'), {'osobyj': 'sozhgi_etu'}])])
C(15, 'sorvat-pokrov', 'Сорвать покров', 'Б', 'связка', 0, {}, 'Сними со врага весь щит.', [{'snyat_shchit_vraga': 1}])
C(16, 'skvoz-zaslon', 'Сквозь заслон', 'Б', 'атака', 1, {'uron': 3}, '{uron:урон}, щит врага не учитывается.',
  [{'uron': {'n': 'uron', 'mimo_shchita': True}}])
C(17, 'golos-predka', 'Голос предка', 'Б', 'связка', 0, {}, 'Посмотри зону сожжённых, лучшую карту положи на верх колоды.', [{'verh_iz_szhzhennyh': 1}])
C(18, 'pripryatat', 'Припрятать', 'Б', 'связка', 0, {}, 'Оставь лучшую карту из руки на следующий ход.', [{'uderzhat': 1}])
C(19, 'ritualnyj-krug', 'Ритуальный круг', 'Б', 'защита', 1, {'shchit': 3, 'uron': 3}, '{shchit:щит} себе и союзнику. Если на враге Порча, ещё {uron:урон}.',
  [SH('oba', 'shchit'), IF('porcha > 0', [U('uron')])])
C(20, 'vspomnit', 'Вспомнить', 'Б', 'связка', 0, {}, 'Верни лучшую карту из сброса на верх колоды.', [{'iz_sbrosa_na_verh': 1}])
C(21, 'plechom-k-plechu', 'Плечом к плечу', 'Б', 'защита', 0, {'shchit': 2},
  'До конца раунда: когда союзник получает щит, ты получаешь {shchit:щит}.', [RF(plechom='shchit')])
C(22, 'dym-blagovonij', 'Дым благовоний', 'Б', 'атака', 1, {'uron': 4}, 'Смени благословения. Если на враге Порча, {uron:урон}.',
  [{'smena_blagoslovenij': 1}, IF('porcha > 0', [U('uron')])], metki=['blag'])
C(23, 'gri-gri', 'Гри-гри', 'Б', 'защита', 1, {'shchit': 4}, '{shchit:щит} себе. Подношение: такой же щит союзнику.',
  [SH('ja', 'shchit'), IF(OFF, [SH('soyuznik', 'shchit')])], extra={'podnoshenie': 1})
C(24, 'polnye-ruki', 'Полные руки', 'Б', 'атака', 1, {'za': 1}, '{za:урон} за каждую карту в руке.', [U('za * ruka')])
C(25, 'poslednij-dovod', 'Последний довод', 'Б', 'атака', 1, {'uron': 8, 'uron_mal': 1},
  'Если это единственная карта в руке, {uron:урон}. Иначе {uron_mal:урон}.', [U('uron if ruka == 0 else uron_mal')])
C(26, 'perekrestok', 'Перекрёсток', 'Б', 'связка', 1, {'uron': 4, 'shchit': 5, 'dobor': 2}, 'Выбери одно: {uron:урон}, {shchit:щит} или возьми {dobor:карту}.',
  varianty=[V('урон', [U('uron')]), V('щит', [SH('ja', 'shchit')]), V('карты', [D('dobor')])], bot={'pereplan': True})
C(27, 'ochag-greet-oboih', 'Очаг греет обоих', 'Б', 'связка', 0, {'dobor': 1, 'shchit': 3},
  'Соларис: союзник берёт {dobor:карту}. Лунарис: союзник получает {shchit:щит}.',
  [IF('solaris', [{'dobor_soyuznika': 'dobor'}], [SH('soyuznik', 'shchit')])], metki=['blag'])

# ================================================================ Подношение
C(28, 'iskra-v-peple', 'Искра в пепле', 'П', 'связка', 0, {'shchit': 3, 'uron': 4},
  'Сожги карту из руки: {shchit:щит}. Подношение: вместо щита {uron:урон}.',
  [BURN(v='s'), IF('s', [IF(OFF, [U('uron')], [SH('ja', 'shchit')])])], extra={'podnoshenie': 1})
C(29, 'dvojnaya-zhertva', 'Двойная жертва', 'П', 'связка', 0, {}, 'Сожги две карты из руки, можешь сменить благословения.',
  varianty=[V('', [BURN(2)]), V('сменить', [BURN(2), {'smena_blagoslovenij': 1}])], metki=['blag'])
C(30, 'golodnyj-duh', 'Голодный дух', 'П', 'атака', 0, {'uron': 5, 'shchit': 4}, 'Подношение: {uron:урон} и {shchit:щит}. Без Подношения ничего не делает.',
  [IF(OFF, [U('uron'), SH('ja', 'shchit')])], extra={'podnoshenie': 1})
C(31, 'ten-iz-pepla', 'Тень из пепла', 'П', 'связка', 1, {}, 'Сыграй лучшую сожжённую карту бесплатно.', [{'sygraj_szhzhennuyu': 1}],
  bot={'pereplan': True})
C(32, 'vozvrashchennyj', 'Возвращённый', 'П', 'связка', 0, {}, 'Выбери сожжённую карту: в начале следующего хода она возвращается в руку.',
  [{'vernut_potom': 1}])
C(33, 'vse-v-ogon', 'Всё в огонь', 'П', 'связка', 1, {'za': 1}, 'Сожги всю колоду. Получи {za:мана} за каждую сожжённую карту.',
  [{'szhech_kolodu': {'v': 'k'}}, {'mana': 'za * k'}], bot={'mana_v_plane': 3, 'pereplan': True})
C(34, 'pepel-pomnit', 'Пепел помнит', 'П', 'связка', 0, {}, 'До конца раунда: когда сжигается любая карта, возьми карту.',
  [RF(pepel_dobor=1)], uproshcheno='вариант «или смени благословения» на стенде не выбирается')
C(35, 'chistyj-list', 'Чистый лист', 'П', 'связка', 0, {}, 'Сожги руку, возьми столько же карт.',
  [{'pust': {'r': 'ruka'}}, BURN('r', v='k'), D('k')], bot={'pereplan': True})
C(36, 'gadanie-peplom', 'Гадание пеплом', 'П', 'связка', 0, {'n': 3}, 'Посмотри {n} верхние карты, одну возьми, остальные сожги.',
  [{'smotri_verh': {'n': 'n', 'vzyat': 1, 'ostalnye': 'szhech'}}], bot={'pereplan': True})
C(37, 'poslednij-vzdoh', 'Последний вздох', 'П', 'связка', 0, {}, 'До конца хода: когда сжигаешь карту из руки, сначала бесплатно срабатывает её эффект.',
  [RF(poslednij_vzdoh=1)])
C(38, 'feniks', 'Феникс', 'П', 'атака', 1, {'uron': 4}, '{uron:урон}. Эту карту можно сыграть из зоны сожжённых.', [U('uron')], metki=['iz_pepla'])
C(39, 'zhadnye-duhi', 'Жадные духи', 'П', 'связка', 0, {}, 'Союзник сжигает до двух карт из своей руки, каждый из вас берёт по карте за каждую.',
  [{'soyuznik_szhigaet': {'n': 2, 'v': 'k'}}, D('k'), {'dobor_soyuznika': 'k'}], bot={'pereplan': True})
C(40, 'slepoe-podnoshenie', 'Слепое подношение', 'П', 'атака', 1, {'uron': 4}, 'Сожги две верхние карты своей колоды не глядя. {uron:урон}.',
  [BURN(2, 'verh'), U('uron')])
C(41, 'prah-k-prahu', 'Прах к праху', 'П', 'защита', 1, {'shchit': 5}, 'Сожги две карты из своего сброса. {shchit:щит} себе.',
  [BURN(2, 'sbros'), SH('ja', 'shchit')])
C(42, 'pozhiranie', 'Пожирание', 'П', 'атака', 2, {'uron': 7}, '{uron:урон}. Цену можно оплатить, сжигая карты из сброса: одна карта за одну ману.',
  [U('uron')], metki=['pozhiranie'])
C(43, 'golod-ognya', 'Голод огня', 'П', 'атака', 3, {'uron': 8}, '{uron:урон}. Стоит на одну ману меньше за каждую карту, сожжённую в этом раунде.',
  [U('uron')], extra={'cena_vyrazhenie': 'max(0, 3 - szhzheno_v_raunde)'})
C(44, 'mimoletnyj-duh', 'Мимолётный дух', 'П', 'атака', 1, {'uron': 7}, '{uron:урон}. Если в конце хода эта карта в руке, она сгорает.',
  [U('uron')], metki=['sgoraet_v_ruke'])
C(45, 'shchedraya-zhertva', 'Щедрая жертва', 'П', 'атака', 0, {'za': 4}, 'Потрать сколько угодно жетонов Подношения: {za:урон} за каждый.',
  varianty=[V('все', [{'potrat_zheton': {'n': 'zhetony', 'v': 'k'}}, U('za * k')]), V('один', [{'potrat_zheton': {'n': 1, 'v': 'k'}}, U('za * k')])])
C(46, 'sytye-duhi', 'Сытые духи', 'П', 'атака', 1, {'uron': 4}, '{uron:урон}. Если у тебя есть жетон Подношения, эта карта стоит 0 (жетон не тратится).',
  [U('uron')], extra={'cena_vyrazhenie': '0 if zhetony > 0 else 1'})
C(47, 'vykup', 'Выкуп', 'П', 'связка', 0, {}, 'Потрать жетон Подношения: возьми лучшую сожжённую карту в руку.',
  [{'potrat_zheton': {'n': 1, 'v': 'k'}}, IF('k', [{'verni': {'n': 1}}])], bot={'pereplan': True})
C(48, 'zaslon-iz-pepla', 'Заслон из пепла', 'П', 'защита', 1, {'za': 1}, '{za:щит} за каждую карту в зоне сожжённых.', [SH('ja', 'za * szhzheno_vsego')])
C(49, 'pepelnaya-burya', 'Пепельная буря', 'П', 'атака', 1, {'za': 3}, 'Сожги из руки сколько хочешь карт, {za:урон} за каждую.',
  varianty=[V(f'сжечь {k}', [BURN(k, v='s'), U('za * s')]) for k in (1, 2, 3)])
C(50, 'podmenysh', 'Подменыш', 'П', 'связка', 0, {}, 'Поменяй местами карту из руки и лучшую карту из зоны сожжённых.',
  [{'snimok_szhzhennyh': 1}, BURN(1, v='s'), IF('s', [{'verni': {'n': 1, 'tolko_ranee': True}}])], bot={'pereplan': True})
C(51, 'eho-obryada', 'Эхо обряда', 'П', 'атака', 1, {'uron': 4}, '{uron:урон}. Подношение: ещё раз {uron:урон}.',
  [U('uron'), IF(OFF, [U('uron')])], extra={'podnoshenie': 1})
C(52, 'dar-soyuzniku', 'Дар союзнику', 'П', 'связка', 0, {'dobor': 2}, 'Потрать жетон Подношения: союзник берёт {dobor:карту}.',
  [{'potrat_zheton': {'n': 1, 'v': 'k'}}, IF('k', [{'dobor_soyuznika': 'dobor'}])])
C(53, 'teplyj-pepel', 'Тёплый пепел', 'П', 'защита', 0, {'shchit': 3}, 'До конца раунда: каждая карта, которую сжигает союзник, даёт тебе {shchit:щит}.',
  [RF(teplyj_pepel='shchit')])
C(54, 'pepel-na-vetru', 'Пепел на ветру', 'П', 'связка', 0, {'uron': 4, 'shchit': 4}, 'Сожги карту из руки. Соларис: {uron:урон}. Лунарис: {shchit:щит} союзнику.',
  [BURN(v='s'), IF('s', [IF('solaris', [U('uron')], [SH('soyuznik', 'shchit')])])], metki=['blag'])
C(55, 'dym-predkov', 'Дым предков', 'П', 'связка', 1, {'nuzhno': 2},
  '2 из 3 (есть жетон Подношения; в руке не больше двух карт; благословения менялись): сыграй лучшую сожжённую карту бесплатно.',
  [PUST(c='(zhetony > 0) + (ruka <= 2) + blag_menyalis'), IF('c >= nuzhno', [{'sygraj_szhzhennuyu': 1}])], metki=['blag'])
C(56, 'poslednyaya-iskra', 'Последняя искра', 'П', 'защита', 0, {'shchit': 3}, '{shchit:щит} себе. Сожги эту карту и ещё одну из руки (две сожжённые — жетон Подношения).',
  [SH('ja', 'shchit'), BURN(1), {'osobyj': 'sozhgi_etu'}])
C(57, 'koster-na-dvoih', 'Костёр на двоих', 'П', 'защита', 0, {'shchit': 3}, 'Ты и союзник сжигаете по карте из руки, оба получаете {shchit:щит}.',
  [BURN(1), {'soyuznik_szhigaet': {'n': 1}}, SH('oba', 'shchit')])
C(58, 'pustoj-altar', 'Пустой алтарь', 'П', 'связка', 0, {}, 'Если в руке нет других карт, получи жетон Подношения.', [IF('ruka == 0', [{'zheton': 1}])])
C(59, 'golod-plameni', 'Голод пламени', 'П', 'связка', 0, {}, 'Сожги карту из руки. Если у неё есть строка Подношения, она срабатывает без жетона.',
  [{'effekt_kart_ruki': 1}])
C(60, 'pererozhdenie', 'Перерождение', 'П', 'защита', 1, {'shchit': 4}, 'Замешай зону сожжённых обратно в колоду. {shchit:щит} себе.',
  [{'zameshaj_szhzhennye': 1}, SH('ja', 'shchit')])

# ================================================================ Порча
C(61, 'sglaz', 'Сглаз', 'Р', 'связка', 0, {}, 'Наложи Порчу.', [P()])
C(62, 'snyat-sglaz', 'Снять сглаз', 'Р', 'связка', 0, {'shchit': 5, 'mana': 2}, 'Сними Порчу с врага: {shchit:щит} или +{mana:мана}.',
  varianty=[V('щит', [{'snyat_porchu': {'v': 's'}}, IF('s', [SH('ja', 'shchit')])]),
            V('мана', [{'snyat_porchu': {'v': 's'}}, IF('s', [{'mana': 'mana'}])])], bot={'mana_v_plane': 1})
C(63, 'gnil', 'Гниль', 'Р', 'атака', 1, {'uron': 4},
  'Порча в этом раунде не снимается. Если на враге Порча, в конце хода героев {uron:урон}.',
  [{'porcha_derzhitsya': 1}, IF('porcha > 0', [{'osobyj': {'imya': 'pozdnij_uron', 'n': 'uron'}}])],
  uproshcheno='урон приходит в конце фазы героев (готовая операция «поздний урон»), а не в конце раунда')
C(64, 'osinyj-roj', 'Осиный рой', 'Р', 'атака', 1, {'uron': 2}, 'До конца хода каждая следующая сыгранная тобой карта наносит {uron:урон}.',
  [RF(osy='uron')])
C(65, 'grad', 'Град', 'Р', 'атака', 1, {'uron': 1, 'raz': 3}, '{raz:попадание} по {uron}.', [{'udary': {'n': 'uron', 'raz': 'raz'}}])
C(66, 'dvojnoj-sglaz', 'Двойной сглаз', 'Р', 'атака', 0, {'uron': 4}, 'Наложи Порчу. Если Порча уже была, вместо этого {uron:урон}.',
  [IF('porcha > 0', [U('uron')], [P()])])
C(67, 'tyanushchaya-porcha', 'Тянущая порча', 'Р', 'атака', 1, {'uron': 3}, '{uron:урон}. Если на враге Порча, ещё раз.',
  [U('uron'), IF('porcha > 0', [U('uron')])])
C(68, 'slabost', 'Слабость', 'Р', 'защита', 1, {'oslab': 2}, 'Наложи Порчу. В этом раунде враг бьёт на {oslab} слабее.', [P(), {'oslab_vraga': 'oslab'}])
C(69, 'uyazvimost', 'Уязвимость', 'Р', 'связка', 0, {}, 'Если на враге Порча, следующее попадание союзника вдвое сильнее.',
  [IF('porcha > 0', [RF(udvoit_soyuznika=1)])])
C(70, 'dva-proklyatiya', 'Два проклятия', 'Р', 'атака', 1, {'uron': 4}, 'Если на враге есть статус союзника, наложи Порчу и нанеси {uron:урон}.',
  [IF('status_soyuznika_na_vrage', [P(), U('uron')])],
  uproshcheno='у Паладина статус лежит на героях, поэтому в паре с ним карта не срабатывает')
C(71, 'pyl-mertveca', 'Пыль мертвеца', 'Р', 'связка', 0, {}, 'Наложи Порчу. Подношение: Порча в конце раунда не снимается.',
  [P(), IF(OFF, [{'porcha_derzhitsya': 1}])], extra={'podnoshenie': 1})
C(72, 'sglaz-i-obereg', 'Сглаз и оберег', 'Р', 'защита', 1, {'shchit': 4}, 'Наложи Порчу, союзник получает {shchit:щит}.', [P(), SH('soyuznik', 'shchit')])
C(73, 'otlozhennyj-sglaz', 'Отложенный сглаз', 'Р', 'связка', 0, {'ocenka': 3}, 'Сейчас: Порча. Или после хода врага: Порча до конца следующего раунда.',
  varianty=[V('сейчас', [P()]), V('после', [OBET([P(), {'porcha_derzhitsya': 1}], 'ocenka')])])
C(74, 'otvetnyj-sglaz', 'Ответный сглаз', 'Р', 'связка', 0, {'ocenka': 2}, 'После хода врага: если враг нанёс урон, наложи на него Порчу.',
  [OBET([IF('para_poteryala_proshlyj > 0', [P()])], 'ocenka')])
C(75, 'chuzhoj-obereg', 'Чужой оберег', 'Р', 'защита', 0, {}, 'Если на враге Порча, щит, который враг получает в этом раунде, достаётся тебе (в начале следующего раунда).',
  [RF(chuzhoj_shchit=1)], uproshcheno='враг получает щит в свой ход, после него щит мага сгорает; поэтому щит приходит магу в начале следующего раунда')
C(76, 'nebo-derzhit', 'Небо держит', 'Р', 'связка', 0, {}, 'Если в этом раунде благословения менялись, Порча в конце раунда не снимается.',
  [IF('blag_menyalis', [{'porcha_derzhitsya': 1}])], metki=['blag'])
C(77, 'klyuch-k-sglazu', 'Ключ к сглазу', 'Р', 'атака', 1, {'uron': 4}, '{uron:урон}. Если на враге Порча, эта карта стоит 0.',
  [U('uron')], extra={'cena_vyrazhenie': '0 if porcha > 0 else 1'})
C(78, 'tolko-pod-sglazom', 'Только под сглазом', 'Р', 'атака', 1, {'uron': 8}, 'Можно сыграть, только если на враге Порча. {uron:урон}.',
  [U('uron')], extra={'uslovie': 'porcha > 0'})
C(79, 'sglaz-iz-ruk-soyuznika', 'Сглаз из рук союзника', 'Р', 'связка', 0, {}, 'Следующее попадание союзника в этом раунде накладывает Порчу.',
  [RF(soyuznik_nakladyvaet=1)])
C(80, 'zapertyj-shchit', 'Запертый щит', 'Р', 'связка', 0, {}, 'Пока на враге Порча, в этом раунде он не получает щит.', [RF(zapertyj_shchit=1)])
C(81, 'dvojnaya-dolya', 'Двойная доля', 'Р', 'атака', 0, {}, 'Если на враге Порча, бонус Порчи на твоём следующем попадании считается дважды.',
  [IF('porcha > 0', [RF(dvojnaya_porcha=1)])])
C(82, 'porcha-zaslon', 'Порча-заслон', 'Р', 'защита', 0, {'dop': 2}, 'Пока на враге Порча, в этом раунде ты и союзник получаете на {dop} щита больше.',
  [RF(porcha_shchit='dop')])
C(83, 'broshennyj-zhrebij', 'Брошенный жребий', 'Р', 'связка', 0, {}, 'Сбрось карту: наложи Порчу.', [{'sbros': {'n': 1, 'v': 's'}}, IF('s', [P()])])
C(84, 'znaki-soshlis', 'Знаки сошлись', 'Р', 'атака', 1, {'uron_mal': 1, 'uron': 8, 'nuzhno': 2},
  '{uron_mal:урон}. Если 2 из 3 (на враге Порча; у врага нет щита; у тебя Соларис): ещё {uron:урон}.',
  [PUST(c='(porcha > 0) + (vrag_shchit == 0) + solaris'), U('uron_mal + (uron if c >= nuzhno else 0)')], metki=['blag'])
C(85, 'rasplata', 'Расплата', 'Р', 'связка', 0, {'dobor': 2}, 'Сними Порчу: союзник берёт {dobor:карту}.',
  [{'snyat_porchu': {'v': 's'}}, IF('s', [{'dobor_soyuznika': 'dobor'}])])
C(86, 'pepel-v-glaza', 'Пепел в глаза', 'Р', 'связка', 0, {}, 'Сожги карту из руки: наложи Порчу.', [BURN(v='s'), IF('s', [P()])])
C(87, 'zloradstvo', 'Злорадство', 'Р', 'защита', 0, {'shchit': 1}, 'До конца раунда: когда Порча срабатывает, получи {shchit:щит}.', [RF(zloradstvo='shchit')])
C(88, 'dobivanie', 'Добивание', 'Р', 'атака', 1, {'uron': 5}, 'Если у врага меньше половины здоровья, наложи Порчу и нанеси {uron:урон}.',
  [IF('vrag_zdorove * 2 < vrag_maks_zdorove', [P(), U('uron')])])
C(89, 'sglaz-primanka', 'Сглаз-приманка', 'Р', 'защита', 1, {'shchit': 2}, 'Наложи Порчу. Авангард: в этом раунде враг бьёт тебя, а не союзника. {shchit:щит} себе.',
  [P(), {'avangard': 'ja'}, SH('ja', 'shchit')])
C(90, 'porcha-golod', 'Порча-голод', 'Р', 'связка', 0, {'dobor': 2}, 'Если на враге Порча, сожги карту из руки и возьми {dobor:карту}.',
  [IF('porcha > 0', [BURN(1), D('dobor')])], bot={'pereplan': True})
C(91, 'hudoj-znak', 'Худой знак', 'Р', 'атака', 0, {'uron': 4}, 'Наложи Порчу. Если в руке нет других карт, ещё {uron:урон}.', [P(), IF('ruka == 0', [U('uron')])])
C(92, 'sglaz-ot-boli', 'Сглаз от боли', 'Р', 'связка', 0, {}, 'До конца раунда: когда союзник получает урон, на врага ложится Порча (в начале следующего раунда).',
  [RF(bol_v_porchu=1)], uproshcheno='союзник получает урон в ход врага, после него Порча снимается; поэтому она ложится в начале следующего раунда')
C(93, 'krivoe-zerkalo', 'Кривое зеркало', 'Р', 'защита', 1, {}, 'Если на враге Порча, его атака в этом раунде бьёт и его самого.', [RF(zerkalo=1)])

# ================================================================ Долг духам
C(94, 'zajm', 'Займ', 'Д', 'связка', 0, {'mana': 2}, '+{mana:мана}. В следующий ход у тебя на столько же меньше.', [{'mana_v_dolg': 'mana'}],
  bot={'mana_v_plane': 2})
C(95, 'udvoit-stavku', 'Удвоить ставку', 'Д', 'связка', 0, {}, 'Удвой свой долг и получи столько же маны сейчас.', [{'mana_v_dolg': 'dolg'}],
  bot={'mana_v_plane': 2})
C(96, 'duh-hranitel', 'Дух-хранитель', 'Д', 'атака', 1, {'uron': 3}, 'Карта остаётся перед тобой, пока платишь: в начале каждого хода плата растёт на 1, и пока она лежит, каждый ход {uron:урон}.',
  [{'soderzhanie': {'vid': 'uron', 'n': 'uron'}}])
C(97, 'vechnyj-obereg', 'Вечный оберег', 'Д', 'защита', 1, {'shchit': 2}, 'Карта остаётся перед тобой, пока платишь: в начале каждого хода плата растёт на 1, и пока она лежит, ты и союзник получаете {shchit:щит}.',
  [{'soderzhanie': {'vid': 'shchit', 'n': 'shchit'}}])
C(98, 'doplata-v-dolg', 'Доплата в долг', 'Д', 'атака', 1, {'uron': 3, 'doplata': 1}, '{uron:урон}. Доплата {doplata:мана}: эффект дважды; доплату можно взять в долг.',
  varianty=[V('', [U('uron')]), V('в долг', [U('uron'), U('uron'), {'dolg': 'doplata'}])])
C(99, 'dosrochno', 'Досрочно', 'Д', 'защита', 0, {'za': 3}, 'Отдай долг сейчас, не дожидаясь хода: {za:щит} за каждый отданный жетон.',
  [{'otdaj_dolg': {'v': 'k'}}, SH('ja', 'za * k')])
C(100, 'skidka-duhov', 'Скидка духов', 'Д', 'связка', 1, {'n': 1}, 'До конца хода карты стоят на {n:мана} меньше.', [{'skidka': 'n'}], bot={'mana_v_plane': 2})
C(101, 'otlozhit', 'Отложить', 'Д', 'связка', 0, {}, 'Отложи карту из руки на следующий ход: тогда сыграешь её бесплатно.', [{'otlozhit_kartu': 1}])
C(102, 'ryvok', 'Рывок', 'Д', 'связка', 0, {'mana': 1, 'dobor': 2}, '+{mana:мана}, возьми {dobor:карту}. Эта карта сгорает.',
  [{'mana': 'mana'}, D('dobor'), {'osobyj': 'sozhgi_etu'}], bot={'mana_v_plane': 1, 'pereplan': True})
C(103, 'perezanyat', 'Перезанять', 'Д', 'связка', 0, {'rost': 1}, 'Перенеси весь долг на ход позже, но он растёт на {rost}.', [{'otlozhit_dolg': {'rost': 'rost'}}])
C(104, 'poruchitel', 'Поручитель', 'Д', 'связка', 0, {}, 'Союзник может сжечь карту из руки, чтобы погасить один жетон твоего долга. Это сжигание не даёт жетон Подношения.',
  [IF('dolg > 0', [{'soyuznik_szhigaet': {'n': 1, 'v': 's'}}, {'spisat_dolg': {'n': 's'}}])],
  uproshcheno='жетон Подношения не даётся и так: сжигается одна карта')
C(105, 'dolgovaya-yama', 'Долговая яма', 'Д', 'атака', 1, {'za': 3}, '{za:урон} за каждый жетон долга у тебя.', [U('za * dolg')])
C(106, 'raspiska', 'Расписка', 'Д', 'связка', 0, {}, 'Сыграй карту из руки бесплатно, её цена становится долгом.', [{'sygraj_v_dolg': {'otkuda': 'ruka'}}])
C(107, 'kredit-doveriya', 'Кредит доверия', 'Д', 'связка', 0, {'mana': 1, 'dobor': 1}, 'Если долга нет: +{mana:мана} в долг и возьми {dobor:карту}. Если есть: возьми две карты.',
  [IF('dolg == 0', [{'mana_v_dolg': 'mana'}, D('dobor')], [D(2)])], bot={'mana_v_plane': 1, 'pereplan': True})
C(108, 'chistye-ruki', 'Чистые руки', 'Д', 'атака', 1, {'uron': 7, 'uron_mal': 2}, 'Если у тебя нет долга, {uron:урон}. Иначе {uron_mal:урон}.',
  [U('uron if dolg == 0 else uron_mal')])
C(109, 'svecha-v-dolg', 'Свеча в долг', 'Д', 'атака', 2, {'uron': 7}, '{uron:урон}. Эту карту можно сыграть в долг вместо маны.', [U('uron')],
  extra={'v_dolg': True})
C(110, 'zajm-dlya-druga', 'Займ для друга', 'Д', 'защита', 0, {'shchit': 5, 'dolg_n': 1}, 'Союзник получает {shchit:щит} сейчас, {dolg_n:мана} в долг твоя.',
  [SH('soyuznik', 'shchit'), {'dolg': 'dolg_n'}])
C(111, 'dobrosovestnyj', 'Добросовестный', 'Д', 'защита', 0, {'shchit': 4, 'dobor': 1}, 'Если в начале этого хода ты отдал долг, получи {shchit:щит} и возьми {dobor:карту}.',
  [IF('dolg_otdan > 0', [SH('ja', 'shchit'), D('dobor')])])
C(112, 'lunnyj-kredit', 'Лунный кредит', 'Д', 'связка', 0, {'za': 3}, 'Лунарис: долг отодвигается на ход. Соларис: отдай долг сейчас и нанеси {za:урон} за каждый жетон.',
  [IF('lunaris', [{'otlozhit_dolg': {'rost': 0}}], [{'otdaj_dolg': {'v': 'k'}}, U('za * k')])], metki=['blag'])
C(113, 'smena-neba', 'Смена неба', 'Д', 'связка', 0, {}, 'Смени благословения; до конца раунда каждая смена благословений списывает жетон долга.',
  [RF(smena_spisyvaet=1), {'smena_blagoslovenij': 1}], metki=['blag'],
  uproshcheno='карта сама меняет благословения: иначе смена после розыгрыша в раунде почти не случается')
C(114, 'vklad', 'Вклад', 'Д', 'связка', 0, {'n': 1, 'plus': 2}, 'Отдай {n:мана} сейчас, в следующий ход получишь на {plus} больше.', [{'vklad': {'n': 'n', 'plus': 'plus'}}])
C(115, 'zalog', 'Залог', 'Д', 'связка', 0, {'mana': 2}, 'Положи худшую карту из руки под планшет и получи {mana:мана} в долг. Отдашь долг — карта вернётся в руку.',
  [{'zalog': {'mana': 'mana'}}], bot={'mana_v_plane': 2})
C(116, 'poslednij-zajm', 'Последний займ', 'Д', 'атака', 1, {'uron': 8}, 'Можно сыграть, только если у тебя есть долг. {uron:урон}.', [U('uron')],
  extra={'uslovie': 'dolg > 0'})
C(117, 'zajm-s-procentami', 'Займ с процентами', 'Д', 'связка', 0, {'mana': 2, 'dobor': 1, 'procent': 1},
  '+{mana:мана} и возьми {dobor:карту}. Долг на {procent} больше взятой маны.',
  [{'mana_v_dolg': 'mana'}, {'dolg': 'procent'}, D('dobor')], bot={'mana_v_plane': 2, 'pereplan': True})
C(118, 'zaklad-neba', 'Заклад неба', 'Д', 'связка', 0, {'mana': 1}, 'Смени благословения и получи {mana:мана} в долг.',
  [{'smena_blagoslovenij': 1}, {'mana_v_dolg': 'mana'}], metki=['blag'], bot={'mana_v_plane': 1})
C(119, 'zajm-na-dvoih', 'Займ на двоих', 'Д', 'связка', 0, {}, 'Ты и союзник берёте по карте. В следующий ход вы оба сбрасываете по карте.',
  [D(1), {'dobor_soyuznika': 1}, {'sbros_potom': {'komu': 'oba', 'n': 1}}], bot={'pereplan': True})
C(120, 'mana-v-peple', 'Мана в пепле', 'Д', 'атака', 1, {'uron': 2, 'mana': 2}, '{uron:урон}. Если эту карту сжечь, +{mana:мана}.', [U('uron')],
  extra={'pri_szhiganii': [{'mana': 'mana'}]}, bot={'mana_v_plane': 1})
C(121, 'zhadnost', 'Жадность', 'Д', 'связка', 0, {}, 'Бери карты по одной, до трёх. Каждая взятая — жетон долга.',
  varianty=[V(f'{k}', [D(k), {'dolg': k}]) for k in (1, 2, 3)], bot={'pereplan': True})
C(122, 'karty-vzajmy', 'Карты взаймы', 'Д', 'связка', 0, {'dobor': 3, 'sbros': 2}, 'Возьми {dobor:карту}. В следующий ход сбрось {sbros:карту}.',
  [D('dobor'), {'sbros_potom': {'komu': 'ja', 'n': 'sbros'}}], bot={'pereplan': True})
C(123, 'chuzhoj-udar-v-uplatu', 'Чужой удар в уплату', 'Д', 'связка', 0, {}, 'До конца раунда каждое попадание союзника по врагу гасит один жетон долга.',
  [RF(udar_soyuznika_platit=1)])
C(124, 'va-bank', 'Ва-банк', 'Д', 'связка', 0, {}, 'Сыграй верхнюю карту колоды бесплатно, её цена становится долгом.', [{'sygraj_v_dolg': {'otkuda': 'verh'}}])
C(125, 'dolzhnik-pod-zashchitoj', 'Должник под защитой', 'Д', 'защита', 1, {'za': 3}, '{za:щит} за каждый жетон долга у тебя.', [SH('ja', 'za * dolg')])
C(126, 'rost-procentov', 'Рост процентов', 'Д', 'связка', 0, {'dobor': 2}, 'Твой долг растёт на жетон, возьми {dobor:карту}.', [{'dolg': 1}, D('dobor')],
  bot={'pereplan': True})

# ================================================================ Связки
C(127, 'shvyrnut-v-ogon', 'Швырнуть в огонь', 'ПР', 'атака', 1, {'za': 2}, 'Сожги карту из руки: наложи Порчу и нанеси урон = {za} × цена этой карты.',
  [BURN(v='s'), IF('s', [P(), U('za * cena_szhzhennoj')])])
C(128, 'mechenyj-udar', 'Меченый удар', 'ПР', 'атака', 1, {'uron': 3}, '{uron:урон}. Подношение: наложи Порчу (до удара).',
  [IF(OFF, [P()]), U('uron')], extra={'podnoshenie': 1})
C(129, 'sglaz-v-zhertvu', 'Сглаз в жертву', 'ПР', 'связка', 0, {}, 'Сними Порчу: получи жетон Подношения.', [{'snyat_porchu': {'v': 's'}}, IF('s', [{'zheton': 1}])])
C(130, 'neugasimyj-sglaz', 'Неугасимый сглаз', 'ПР', 'связка', 0, {}, 'Сожги две карты из руки: Порча в этом раунде не снимается.',
  [BURN(2, v='s'), IF('s >= 2', [{'porcha_derzhitsya': 1}])])
C(131, 'goryashchaya-metka', 'Горящая метка', 'ПР', 'атака', 0, {'uron': 2}, 'До конца раунда: пока на враге Порча, каждая сожжённая карта наносит ему {uron:урон}.',
  [RF(goryashchaya_metka='uron')])
C(132, 'zhertva-za-dvoih', 'Жертва за двоих', 'ПР', 'связка', 0, {}, 'Сожги карту. Если на враге Порча, считается, что ты сжёг две: жетон Подношения.',
  [BURN(v='s'), IF('s and porcha > 0', [{'uslovnyj_zheton': 1}])])
C(133, 'dolgij-sglaz', 'Долгий сглаз', 'ПР', 'связка', 0, {}, 'Потрать жетон Подношения: Порча держится до конца следующего раунда.',
  [{'potrat_zheton': {'n': 1, 'v': 'k'}}, IF('k', [{'porcha_derzhitsya': 2}])])
C(134, 'polnyj-obryad', 'Полный обряд', 'ПР', 'атака', 1, {'uron_mal': 1, 'uron': 7, 'nuzhno': 2},
  '{uron_mal:урон}. Если 2 из 3 (на враге Порча; есть жетон Подношения; в руке не больше двух карт): ещё {uron:урон}, возьми сожжённую карту.',
  [PUST(c='(porcha > 0) + (zhetony > 0) + (ruka <= 2)'), U('uron_mal'), IF('c >= nuzhno', [U('uron'), {'verni': {'n': 1}}])])
C(135, 'peregruzka-sglazom', 'Перегрузка сглазом', 'РД', 'атака', 1, {'uron': 3, 'shchit': 3, 'dolg_n': 1},
  'Порча, {uron:урон} и {shchit:щит} себе. В следующий ход у тебя на {dolg_n:мана} меньше.', [P(), U('uron'), SH('ja', 'shchit'), {'dolg': 'dolg_n'}])
C(136, 'prostit-dolg', 'Простить долг', 'РД', 'связка', 0, {}, 'Сними Порчу: долг списан.', [{'snyat_porchu': {'v': 's'}}, IF('s', [{'spisat_dolg': {}}])])
C(137, 'dolzhnik-proklinaet', 'Должник проклинает', 'РД', 'атака', 1, {'za': 2}, 'Наложи Порчу. Если у тебя есть долг, ещё {za:урон} за каждый жетон.',
  [P(), U('za * dolg')])
C(138, 'perelozhit-dolg', 'Переложить долг', 'РД', 'атака', 1, {'za': 2}, 'Спиши с себя долг: наложи Порчу и нанеси {za:урон} за каждый снятый жетон.',
  [{'spisat_dolg': {'v': 'k'}}, IF('k', [P(), U('za * k')])])
C(139, 'sglaz-skidka', 'Сглаз-скидка', 'РД', 'связка', 0, {'n': 1}, 'Если на враге Порча, в этом ходу твои карты стоят на {n:мана} меньше.',
  [IF('porcha > 0', [{'skidka': 'n'}])], bot={'mana_v_plane': 1})
C(140, 'procenty', 'Проценты', 'РД', 'связка', 0, {}, 'Если в начале следующего хода ты не отдашь долг полностью, на врага ложится Порча, а долг растёт.',
  [{'procenty': 1}], uproshcheno='срабатывает один раз, в начале следующего хода')
C(141, 'pod-sglazom-v-dolg', 'Под сглазом в долг', 'РД', 'атака', 2, {'uron': 6}, '{uron:урон}. Если на враге Порча, эту карту можно сыграть в долг.',
  [U('uron')], extra={'v_dolg': 'porcha > 0'})
C(142, 'zalogovyj-sglaz', 'Залоговый сглаз', 'РД', 'атака', 0, {'dolg_n': 1, 'uron': 5}, 'Возьми {dolg_n:мана} в долг. Когда отдашь весь долг, наложи Порчу и нанеси {uron:урон}.',
  [{'dolg': 'dolg_n'}, {'pri_oplate': [P(), U('uron')]}])
C(143, 'pereplavka', 'Переплавка', 'ПД', 'связка', 0, {}, 'Сожги карту из руки: получи ману по её цене или погаси столько же долга.',
  varianty=[V('мана', [BURN(v='s'), {'mana': 'cena_szhzhennoj if s else 0'}]), V('долг', [BURN(v='s'), {'spisat_dolg': {'n': 'cena_szhzhennoj if s else 0'}}])],
  bot={'mana_v_plane': 1})
C(144, 'topka', 'Топка', 'ПД', 'связка', 0, {}, 'До конца хода каждая сожжённая тобой карта даёт ману.', [RF(topka=1)], bot={'mana_v_plane': 1})
C(145, 'vyplata-ognem', 'Выплата огнём', 'ПД', 'связка', 0, {}, 'Отдай долг, сжигая карты из руки: одна карта за одну ману долга.',
  [BURN('dolg', v='k'), {'spisat_dolg': {'n': 'k'}}])
C(146, 'zheton-pod-raspisku', 'Жетон под расписку', 'ПД', 'связка', 0, {'dolg_n': 1}, 'Возьми {dolg_n:мана} в долг: получи жетон Подношения.', [{'dolg': 'dolg_n'}, {'zheton': 1}])
C(147, 'otkup', 'Откуп', 'ПД', 'связка', 0, {}, 'Потрать жетон Подношения: спиши весь долг.',
  [IF('dolg > 0', [{'potrat_zheton': {'n': 1, 'v': 'k'}}, IF('k', [{'spisat_dolg': {}}])])])
C(148, 'avans', 'Аванс', 'ПД', 'связка', 0, {}, 'Возьми лучшую сожжённую карту в руку, её цена становится долгом.',
  [{'verni': {'n': 1}}, {'dolg': 1}], bot={'pereplan': True}, uproshcheno='долг — 1 мана, а не цена именно этой карты')
C(149, 'sgorevshaya-raspiska', 'Сгоревшая расписка', 'ПД', 'связка', 0, {'mana': 1},
  '+{mana:мана} в долг. Отдавая долг в начале следующего хода, вместо маны сожги две верхние карты колоды.',
  [{'mana_v_dolg': 'mana'}, {'zhech_po_rozygryshu': 1}], bot={'mana_v_plane': 1},
  uproshcheno='добавлен займ, чтобы было что отдавать')
C(150, 'zajm-pod-pepel', 'Займ под пепел', 'ПД', 'связка', 0, {}, 'Получи ману за каждую карту в зоне сожжённых, вся она в долг.',
  [{'mana_v_dolg': 'szhzheno_vsego'}], bot={'mana_v_plane': 2})

LEG = [
    (152, 'pepelnyj-tron', 'Пепельный трон', 'pepelnyj_tron', {'sol_skidka': 1, 'lun_shchit': 2},
     'Сожжённые карты можно играть из зоны сожжённых как из руки (на стенде бот видит 4 лучшие). Соларис: на {sol_skidka:мана} дешевле. '
     'Лунарис: каждая такая карта даёт {lun_shchit:щит}.'),
    (156, 'glubokij-sglaz', 'Глубокий сглаз', 'glubokij_sglaz', {},
     'Порча копится жетонами (предел в правилах), каждый усиливает попадания. Соларис: наложенная Порча — сразу два жетона. '
     'Лунарис: в конце раунда снимается только один жетон.'),
    (158, 'plata-duham', 'Плата духам', 'plata_duham', {},
     'Урон или щит с карты можно направить на долг: вместо урона врагу (Соларис) или вместо щита (Лунарис) гаси столько же долга. '
     'Такая оплата ещё и даёт ману.'),
]


def granicy(ch, cena):
    out = {}
    for k, v in ch.items():
        if k.startswith('ocenka'):
            out[k] = [0, max(10, v * 2)]
        elif k == 'nuzhno':
            out[k] = [1, 3]
        else:
            out[k] = [min(0, v), max(v * 2, v + 3)]
    out['cena'] = [0, max(3, cena + 1)]
    return out


def yamls():
    out = []
    for c in CARDS:
        d = {'id': f"m{c['n']:03d}-{c['slug']}", 'imya': c['imya'], 'geroj': 'mag', 'nabor': 'bank',
             'bild': BILD[c['bild']], 'vid': c['vid'], 'nomer_idei': c['n'], 'cena': c['cena']}
        ex = dict(c['extra'])
        if 'podnoshenie' in ex:
            d['podnoshenie'] = ex.pop('podnoshenie')
        if c['chisla']:
            d['chisla'] = dict(c['chisla'])
        d['tekst'] = '{cena:мана}. ' + c['tekst']
        if c['varianty'] is not None:
            d['varianty'] = c['varianty']
        else:
            d['effekt'] = c['effekt']
        d.update(ex)
        if c['metki']:
            d['metki'] = c['metki']
        d['bot'] = dict({'poryadok': 3, 'cennost': 5}, **(c['bot'] or {}))
        d['granicy'] = granicy(c['chisla'], c['cena'])
        d['status'] = 'ideya'
        ist = ['2026-10-25 Claude: перевод идеи из heroes/mag/idei-kart.md, числа черновые']
        if c['uproshcheno']:
            ist.append('упрощено для стенда: ' + c['uproshcheno'])
        d['istoriya'] = ist
        out.append(d)
    for n, slug, imya, passiv, ch, tekst in LEG:
        d = {'id': f'm{n:03d}-{slug}', 'imya': imya, 'geroj': 'mag', 'nabor': 'legendarka', 'bild': '',
             'vid': 'связка', 'nomer_idei': n}
        if ch:
            d['chisla'] = ch
            d['granicy'] = {k: [0, max(v * 2, v + 3)] for k, v in ch.items()}
        d.update({'tekst': tekst, 'passiv': {'imya': passiv}, 'status': 'ideya',
                  'istoriya': ['2026-10-25 Claude: легендарка, выбранная Никитой 2026-10-24; числа черновые']})
        out.append(d)
    return out


def main():
    os.makedirs(OUT, exist_ok=True)
    zam = '--zamenit' in sys.argv
    n = 0
    for d in yamls():
        p = os.path.join(OUT, d['id'] + '.yaml')
        if os.path.exists(p) and not zam:
            continue
        with open(p, 'w', encoding='utf-8') as f:
            yaml.safe_dump(d, f, allow_unicode=True, sort_keys=False, width=140)
        n += 1
    print(f'записано карт: {n} в {os.path.relpath(OUT, ROOT)}')


if __name__ == '__main__':
    main()
