# -*- coding: utf-8 -*-
"""Генератор YAML банка идей Паладина (heroes/paladin/idei-kart.md, 153 идеи, 2026-10-25) в
heroes/paladin/karty/bank/. Числа черновые: тест может их менять, добавлять урон и щит и немного менять
концепт (решение Никиты 2026-10-25, ai/pravila/03-balans-i-testy.md). Запускать один раз; дальше YAML
правятся сами по себе, а этот файл остаётся записью исходного перевода идей в механику стенда.

    python -m stend.bank_paladin [--zamenit]"""
import os, sys
import yaml

ROOT = os.path.normpath(os.path.join(os.path.dirname(__file__), '..', '..', '..'))
OUT = os.path.join(ROOT, 'heroes', 'paladin', 'karty', 'bank')

U = lambda n: {'uron': n}
V = lambda n: {'vera': n}
SH = lambda komu, n: {'shchit': {'komu': komu, 'n': n}}
ZS = lambda komu='soyuznik', **kw: {'zaslon': dict(komu=komu, **kw)}
MOL = lambda **kw: {'molitva': kw or None}
IF = lambda c, to, inache=None: ({'esli': c, 'to': to, 'inache': inache} if inache else {'esli': c, 'to': to})
PUST = lambda **kw: {'pust': kw}
D = lambda n: {'dobor': n}
OBET = lambda eff, ocenka, vid='dmg': {'obet': {'kogda': 'nachalo', 'vid_ocenki': vid, 'ocenka_bota': ocenka, 'effekt': eff}}

BILD = {'Б': '', 'В': 'В', 'З': 'З', 'М': 'М', 'ВЗ': 'В–З', 'ЗМ': 'З–М', 'МВ': 'М–В', 'Л': ''}
CARDS = []


def C(n, slug, imya, bild, vid, chisla, tekst, effekt=None, varianty=None, metki=None, bot=None, uproshcheno=None):
    CARDS.append(dict(n=n, slug=slug, imya=imya, bild=bild, vid=vid, chisla=chisla, tekst=tekst, effekt=effekt,
                      varianty=varianty, metki=metki, bot=bot, uproshcheno=uproshcheno))


def doplata(base, paid, k='doplata'):
    return [{'nazvanie': '', 'effekt': base}, {'nazvanie': 'доплата', 'doplata': {'vera': 2}, 'effekt': paid}]


# ================================================================ База
C(1, 'udar-mecha', 'Удар меча', 'Б', 'атака', {'uron': 3}, '{uron:урон}.', [U('uron')])
C(2, 'shchit-very', 'Щит веры', 'Б', 'защита', {'shchit': 4}, '{shchit:щит} себе или союзнику.',
  varianty=[{'nazvanie': 'себе', 'effekt': [SH('ja', 'shchit')]}, {'nazvanie': 'союзнику', 'effekt': [SH('soyuznik', 'shchit')]}])
C(3, 'dvuruchnyj-zamah', 'Двуручный замах', 'Б', 'атака', {'uron': 6}, '{uron:урон}. Считается в лимите за две карты.',
  [U('uron')], metki=['dve_karty'])
C(4, 'shag-vpered', 'Шаг вперёд', 'Б', 'защита', {'shchit': 4}, 'Авангард. {shchit:щит} себе.', [{'avangard': 'ja'}, SH('ja', 'shchit')])
C(5, 'smena-znamen', 'Смена знамён', 'Б', 'вера', {'vera': 1}, 'Смени благословения. +{vera:вера}.',
  [{'smena_blagoslovenij': 1}, V('vera')], metki=['blag'])
C(6, 'rassvet-i-sumerki', 'Рассвет и сумерки', 'Б', 'связка', {'uron': 3, 'shchit': 4},
  'Соларис: {uron:урон}. Лунарис: {shchit:щит} союзнику.', [IF('solaris', [U('uron')], [SH('soyuznik', 'shchit')])], metki=['blag'])
C(7, 'obet-utra', 'Обет утра', 'Б', 'защита', {'shchit': 3, 'shchit_big': 5, 'vera': 1, 'ocenka': 4},
  'Выбери: {shchit:щит} союзнику сейчас или после хода врага {shchit_big:щит} ему и +{vera:вера}.',
  varianty=[{'nazvanie': 'сейчас', 'effekt': [SH('soyuznik', 'shchit')]},
            {'nazvanie': 'после', 'effekt': [OBET([SH('soyuznik', 'shchit_big'), V('vera')], 'ocenka', 'shield')]}])
C(8, 'trojnoe-znamenie', 'Тройное знамение', 'Б', 'атака', {'uron_mal': 1, 'uron': 6, 'nuzhno': 2},
  '{uron_mal:урон}. Если 2 из 3 (у союзника есть щит; вера 4+; благословения менялись в этом раунде): ещё {uron:урон}.',
  [PUST(c='(shchit_soyuznika > 0) + (vera >= 4) + blag_menyalis'), U('uron_mal + (uron if c >= nuzhno else 0)')],
  metki=['blag'])
C(9, 'ispytanie', 'Испытание', 'Б', 'молитва', {'n': 2}, 'Посмотри {n} верхние карты колоды: одну возьми, другую положи на верх.',
  [{'smotri_verh': {'n': 'n', 'vzyat': 1, 'ostalnye': 'verh'}}], bot={'pereplan': True})
C(10, 'prival', 'Привал', 'Б', 'вера', {'dobor': 1, 'vera': 1}, 'Возьми {dobor:карту}. Если это карта щита, +{vera:вера}.',
  [PUST(z='verh_zashchita'), D('dobor'), IF('z', [V('vera')])], bot={'pereplan': True})
C(11, 'nastavlenie', 'Наставление', 'Б', 'связка', {'dobor': 1}, 'Союзник берёт {dobor:карту}. Если на нём Заслон, ты тоже берёшь.',
  [{'dobor_soyuznika': 'dobor'}, IF('soyuznik_zaslon', [D('dobor')])], bot={'pereplan': True})
C(12, 'koster-dlya-eresi', 'Костёр для ереси', 'Б', 'вера', {'vera': 2}, 'Сожги карту из руки: +{vera:вера}.',
  [{'sozhgi': {'otkuda': 'ruka', 'n': 1, 'v': 's'}}, IF('s', [V('vera')])])
C(13, 'pokayanie', 'Покаяние', 'Б', 'вера', {'vera': 1, 'dobor': 1}, 'Сбрось карту: +{vera:вера}, возьми {dobor:карту}.',
  [{'sbros': {'n': 1, 'v': 's'}}, IF('s', [V('vera'), D('dobor')])], bot={'pereplan': True})
C(14, 'stroj', 'Строй', 'Б', 'защита', {'shchit': 3}, '{shchit:щит} себе и союзнику.', [SH('oba', 'shchit')])
C(15, 'tyazhelyj-dospeh', 'Тяжёлый доспех', 'Б', 'защита', {'shchit': 3, 'dop': 3},
  '{shchit:щит} себе. Если у тебя Авангард, ещё {dop:щит}.', [SH('ja', 'shchit + (dop if ja_avangard else 0)')])
C(16, 'udar-shchitom', 'Удар щитом', 'Б', 'атака', {'uron': 2, 'shchit': 2, 'shchit_big': 4, 'doplata': 2},
  '{uron:урон} и {shchit:щит} себе. Доплата {doplata:веру}: {shchit_big:щит}.',
  varianty=doplata([U('uron'), SH('ja', 'shchit')], [U('uron'), SH('ja', 'shchit_big if oplacheno else shchit')]))
C(17, 'poslednij-rubezh', 'Последний рубеж', 'Б', 'защита', {'shchit': 5, 'shchit_mal': 1},
  'Если у союзника здоровья меньше, чем у тебя: Авангард и {shchit:щит}. Иначе {shchit_mal:щит}.',
  [IF('zdorove_soyuznika < zdorove', [{'avangard': 'ja'}, SH('ja', 'shchit')], [SH('ja', 'shchit_mal')])])
C(18, 'pravednyj-gnev', 'Праведный гнев', 'Б', 'атака', {'za': 2}, '{za:урон} за каждого героя, у которого здоровье не полное.',
  [U('za * ranenyh')])
C(19, 'karayushchij-vypad', 'Карающий выпад', 'Б', 'атака', {'uron': 2, 'uron_big': 4, 'doplata': 2},
  '{uron:урон}. Доплата {doplata:веру}: {uron_big:урон}.', varianty=doplata([U('uron')], [U('uron_big if oplacheno else uron')]))
C(20, 'blagaya-vest', 'Благая весть', 'Б', 'связка', {'dobor': 1}, 'Соларис: союзник берёт {dobor:карту}. Лунарис: Заслон союзнику.',
  [IF('solaris', [{'dobor_soyuznika': 'dobor'}], [ZS()])], metki=['blag'])
C(21, 'vyzov', 'Вызов', 'Б', 'атака', {'uron': 4}, 'Авангард. Если на тебе нет щита, {uron:урон}.',
  [IF('shchit == 0', [U('uron')]), {'avangard': 'ja'}])
C(22, 'zavershayushchij-udar', 'Завершающий удар', 'Б', 'атака', {'uron': 7, 'uron_mal': 1},
  'Если это твоя третья карта в раунде, {uron:урон}. Иначе {uron_mal:урон}.', [U('uron if sygrano_mnoj_do == 2 else uron_mal')])
C(23, 'pervyj-natisk', 'Первый натиск', 'Б', 'атака', {'uron': 2},
  'Если это твоя первая карта в раунде, она не считается в лимит. {uron:урон}.',
  [IF('sygrano_mnoj_do == 0', [{'ne_v_limit': 1}]), U('uron')], metki=['mozhet_vne_limita'])
C(24, 'mech-i-shchit', 'Меч и щит', 'Б', 'атака', {'uron': 2, 'shchit': 2, 'big': 3, 'doplata': 2},
  '{uron:урон} и {shchit:щит} союзнику. Доплата {doplata:веру}: по {big}.',
  varianty=doplata([U('uron'), SH('soyuznik', 'shchit')], [U('big if oplacheno else uron'), SH('soyuznik', 'big if oplacheno else shchit')]))
C(25, 'otmshchenie', 'Отмщение', 'Б', 'атака', {'uron': 2, 'dop': 2, 'vera': 1},
  '{uron:урон}. Если здоровье союзника не полное, ещё {dop:урон} и +{vera:вера}.',
  [IF('soyuznik_ranen', [U('uron + dop'), V('vera')], [U('uron')])])
C(26, 'chasha-na-dvoih', 'Чаша на двоих', 'Б', 'связка', {'uron': 2, 'shchit': 2, 'vera': 1},
  'Соларис: {uron:урон} и {shchit:щит} союзнику. Лунарис: {shchit:щит} обоим и +{vera:вера}.',
  [IF('solaris', [U('uron'), SH('soyuznik', 'shchit')], [SH('oba', 'shchit'), V('vera')])], metki=['blag'])
C(27, 'perekrestok', 'Перекрёсток', 'Б', 'связка', {'uron': 3, 'shchit': 4, 'vera': 2},
  'Выбери одно: {uron:урон}, {shchit:щит} или +{vera:вера}.',
  varianty=[{'nazvanie': 'урон', 'effekt': [U('uron')]}, {'nazvanie': 'щит', 'effekt': [SH('ja', 'shchit')]},
            {'nazvanie': 'вера', 'effekt': [V('vera')]}])

# ================================================================ Вера
C(28, 'svecha', 'Свеча', 'В', 'вера', {'vera': 2, 'shchit': 1}, '+{vera:вера}. {shchit:щит} себе.', [V('vera'), SH('ja', 'shchit')])
C(29, 'chudo-sveta', 'Чудо света', 'В', 'атака', {'za': 1, 'plus': 0}, 'Чудо: {za:урон} за каждую сожжённую веру.',
  [{'chudo': 'f'}, U('za * f + (plus if f > 0 else 0)')], metki=['chudo'])
C(30, 'chudo-zastupnichestva', 'Чудо заступничества', 'В', 'защита', {'za': 2}, 'Чудо: {za:щит} за каждую веру, раздели между героями.',
  varianty=[{'nazvanie': 'союзнику', 'effekt': [{'chudo': 'f'}, SH('soyuznik', 'za * f')]},
            {'nazvanie': 'себе', 'effekt': [{'chudo': 'f'}, SH('ja', 'za * f')]},
            {'nazvanie': 'пополам', 'effekt': [{'chudo': 'f'}, SH('oba', 'za * f // 2')]}], metki=['chudo'])
C(31, 'chudo-prozreniya', 'Чудо прозрения', 'В', 'вера', {'za': 2}, 'Чудо: возьми карту за каждые {za} веры.',
  [{'chudo': 'f'}, D('f // za')], metki=['chudo'], bot={'pereplan': True})
C(32, 'maloe-chudo', 'Малое чудо', 'В', 'атака', {'za': 2},
  'Сожги половину веры (с округлением вверх): {za:урон} за каждую сожжённую, остальная вера остаётся.',
  [{'szhech_veru': {'n': '(vera + 1) // 2', 'v': 'k'}}, U('za * k')], metki=['chudo'],
  uproshcheno='в идее «эффект любого своего Чуда из руки»; на стенде — урон за сожжённую веру')
C(33, 'smirenie', 'Смирение', 'В', 'атака', {'uron': 6, 'uron_mal': 1}, 'Если вера 0: {uron:урон}. Иначе {uron_mal:урон}.',
  [U('uron if vera == 0 else uron_mal')])
C(34, 'pepel-posle-chuda', 'Пепел после чуда', 'В', 'вера', {'vera': 3, 'dobor': 1, 'vera_mal': 1},
  'Если вера 0: +{vera:вера}, возьми {dobor:карту}. Иначе +{vera_mal:вера}.',
  [IF('vera == 0', [V('vera'), D('dobor')], [V('vera_mal')])], bot={'pereplan': True})
C(35, 'rovno-tri', 'Ровно три', 'В', 'связка', {'uron': 3, 'shchit': 3, 'uron_mal': 1},
  'Если вера ровно 3: {uron:урон} и {shchit:щит} союзнику. Иначе {uron_mal:урон}.',
  [IF('vera == 3', [U('uron'), SH('soyuznik', 'shchit')], [U('uron_mal')])])
C(36, 'perevorot', 'Переворот', 'В', 'вера', {}, 'Переверни кубик веры на противоположную грань.', [{'perevernut_veru': 1}])
C(37, 'chet-i-nechet', 'Чёт и нечет', 'В', 'связка', {'uron': 3, 'shchit': 4, 'vera': 1},
  'Вера чётная: {uron:урон}. Нечётная: {shchit:щит} союзнику. В любом случае +{vera:вера}.',
  [IF('vera % 2 == 0', [U('uron')], [SH('soyuznik', 'shchit')]), V('vera')])
C(38, 'klinok-veruyushchego', 'Клинок верующего', 'В', 'атака', {'uron': 2, 'uron_big': 5}, '{uron:урон}. Вера 4+: {uron_big:урон}.',
  [U('uron_big if vera >= 4 else uron')])
C(39, 'strazh-obeta', 'Страж обета', 'В', 'защита', {'shchit': 4}, '{shchit:щит} себе. Вера 4+: ещё Заслон союзнику.',
  [SH('ja', 'shchit'), IF('vera >= 4', [ZS()])])
C(40, 'propoved', 'Проповедь', 'В', 'атака', {'plus': 0}, 'Урон = вера. Вера не тратится.', [U('vera + plus')])
C(41, 'svidetelstvo', 'Свидетельство', 'В', 'вера', {'vera': 1, 'vera_big': 3},
  '+{vera:вера}. Если у союзника здоровья меньше, чем у тебя, +{vera_big:вера}.',
  [V('vera_big if zdorove_soyuznika < zdorove else vera')])
C(42, 'obet-bednosti', 'Обет бедности', 'В', 'вера', {'za': 1}, 'Сбрось руку: +{za:вера} за каждую сброшенную карту.',
  [{'sbros': {'n': 'ruka', 'v': 's'}}, V('za * s')])
C(43, 'anafema', 'Анафема', 'В', 'атака', {'za': 3, 'porog': 3}, '{za:урон} за каждую веру выше {porog}. Вера не тратится.',
  [U('za * max(0, vera - porog)')])
C(44, 'voznesenie', 'Вознесение', 'В', 'атака', {'uron': 7, 'cena': 3, 'vera': 2},
  'Вера 4+: {uron:урон} и −{cena:вера}. Иначе +{vera:вера}.',
  [IF('vera >= 4', [U('uron'), {'szhech_veru': {'n': 'cena'}}], [V('vera')])])
C(45, 'iskushenie', 'Искушение', 'В', 'вера', {'vera': 3, 'sila': 2}, '+{vera:вера}. Враг в этом раунде бьёт на {sila} сильнее.',
  [V('vera'), {'usilit_vraga': 'sila'}])
C(46, 'chudo-suda', 'Чудо суда', 'В', 'атака', {'za': 1}, 'Чудо: {za:урон} за каждую веру. Если вера была 6, вдвое.',
  [{'chudo': 'f'}, U('za * f * (2 if f >= 6 else 1)')], metki=['chudo'])
C(47, 'polnota', 'Полнота', 'В', 'атака', {'uron': 3}, 'Если вера 6: эта карта не считается в лимит. {uron:урон}.',
  [IF('vera >= 6', [{'ne_v_limit': 1}]), U('uron')], metki=['mozhet_vne_limita'])
C(48, 'bdenie', 'Бдение', 'В', 'вера', {'vera': 3}, '+{vera:вера}. После неё ты больше не играешь карт в этом раунде.',
  [V('vera'), {'konec_hoda': 1}])
C(49, 'vera-v-brata', 'Вера в брата', 'В', 'вера', {'za': 2}, '+1 вера за каждые {za:щит} союзника.', [V('shchit_soyuznika // za')])
C(50, 'chudo-razdeleniya', 'Чудо разделения', 'В', 'связка', {'za': 1}, 'Чудо: за каждую веру {za:урон} и {za:щит} союзнику.',
  [{'chudo': 'f'}, U('za * f'), SH('soyuznik', 'za * f')], metki=['chudo'])
C(51, 'ogon-very', 'Огонь веры', 'В', 'атака', {'za': 2}, 'Доплата любой верой: {za:урон} за каждую сожжённую.',
  varianty=[{'nazvanie': 'вся вера', 'effekt': [{'szhech_veru': {'n': 'vera', 'v': 'k'}}, U('za * k')]},
            {'nazvanie': 'половина', 'effekt': [{'szhech_veru': {'n': 'vera // 2', 'v': 'k'}}, U('za * k')]}])
C(52, 'svet-nadezhdy', 'Свет надежды', 'В', 'вера', {'vera': 3, 'shchit': 2}, 'Если вера меньше 2: +{vera:вера}. Иначе {shchit:щит} обоим.',
  [IF('vera < 2', [V('vera')], [SH('oba', 'shchit')])])
C(53, 'chudo-otrazheniya', 'Чудо отражения', 'В', 'защита', {'za': 1}, 'Чудо: в этом раунде каждый удар врага слабее на {za} за каждую сожжённую веру.',
  [{'chudo': 'f'}, {'oslab_vraga': 'za * f'}], metki=['chudo'])
C(54, 'zapal', 'Запал', 'В', 'вера', {'vera': 1, 'dobor': 1}, '+{vera:вера}. Вера 4+: возьми {dobor:карту}.',
  [V('vera'), IF('vera >= 4', [D('dobor')])], bot={'pereplan': True})
C(55, 'stojkost', 'Стойкость', 'В', 'защита', {'plus': 1}, 'Щит себе = вера + {plus}.', [SH('ja', 'vera + plus')])
C(56, 'znamenie', 'Знамение', 'В', 'вера', {'vera': 2, 'vera_mal': 1, 'shchit': 2},
  'Соларис: +{vera:вера}. Лунарис: +{vera_mal:вера} и {shchit:щит} союзнику.',
  [IF('solaris', [V('vera')], [V('vera_mal'), SH('soyuznik', 'shchit')])], metki=['blag'])
C(57, 'posvyashchenie', 'Посвящение', 'В', 'вера', {'porog': 4, 'shchit': 3}, 'Подними веру до {porog}, если она ниже. Иначе {shchit:щит} себе.',
  [IF('vera < porog', [V('porog - vera')], [SH('ja', 'shchit')])])
C(58, 'relikvarij', 'Реликварий', 'В', 'вера', {}, 'Вся вера уходит на эту карту и в начале следующего раунда возвращается на кубик.',
  [{'ocenka': '0.3 * vera'}, {'relikvarij': 1}],
  uproshcheno='в идее веру возвращают, сбросив карту; на стенде — сама в начале следующего раунда')
C(59, 'chudo-shchedrosti', 'Чудо щедрости', 'В', 'связка', {'za': 2}, 'Чудо: союзник берёт карту за каждые {za} веры.',
  [{'chudo': 'f'}, {'dobor_soyuznika': 'f // za'}], metki=['chudo'], bot={'pereplan': True})
C(60, 'zhertvennik', 'Жертвенник', 'В', 'защита', {'za': 2}, 'Доплата любой верой: Авангард и {za:щит} себе за каждую сожжённую.',
  varianty=[{'nazvanie': 'вся вера', 'effekt': [{'szhech_veru': {'n': 'vera', 'v': 'k'}}, {'avangard': 'ja'}, SH('ja', 'za * k')]},
            {'nazvanie': 'половина', 'effekt': [{'szhech_veru': {'n': 'vera // 2', 'v': 'k'}}, {'avangard': 'ja'}, SH('ja', 'za * k')]}])

# ================================================================ Заслон
C(61, 'zaslon', 'Заслон', 'З', 'защита', {}, 'Заслон союзнику.', [ZS()])
C(62, 'dvojnoj-zaslon', 'Двойной заслон', 'З', 'защита', {'shchit': 3, 'vera': 1},
  'Заслон союзнику. Если он уже есть, {shchit:щит} союзнику и +{vera:вера}.',
  [IF('soyuznik_zaslon', [SH('soyuznik', 'shchit'), V('vera')], [ZS()])])
C(63, 'krepkij-zaslon', 'Крепкий заслон', 'З', 'защита', {'sila': 2}, 'Заслон союзнику. Этот Заслон ослабляет удар ещё на {sila}.',
  [ZS(sila='sila')])
C(64, 'zaslon-na-sebya', 'Заслон на себя', 'З', 'защита', {}, 'Заслон себе. Авангард.', [ZS('ja'), {'avangard': 'ja'}])
C(65, 'zaslon-dlya-dvoih', 'Заслон для двоих', 'З', 'защита', {}, 'Заслон обоим героям.', [ZS('oba')])
C(66, 'stojkij-zaslon', 'Стойкий заслон', 'З', 'защита', {}, 'Заслон союзнику. В этом раунде он ослабляет каждый удар, а снимается в конце раунда.',
  [ZS(stojkij=1)])
C(67, 'perehodyashchij-zaslon', 'Переходящий заслон', 'З', 'защита', {}, 'Заслон союзнику. Сработав, он не снимается, а переходит на тебя.',
  [ZS(perehod=1)])
C(68, 'primanka', 'Приманка', 'З', 'защита', {}, 'Заслон и Авангард союзнику: враг бьёт того, кого ты защитил.',
  [ZS(), {'avangard': 'soyuznik'}])
C(69, 'otvetnyj-zaslon', 'Ответный заслон', 'З', 'связка', {'uron': 3}, 'Заслон союзнику. Когда он сработает, {uron:урон} врагу.',
  [ZS(effekt=[U('uron')])])
C(70, 'zaslon-vest', 'Заслон-весть', 'З', 'связка', {'dobor': 1, 'ocenka': 2},
  'Заслон союзнику. Когда он сработает, союзник берёт {dobor:карту} в начале следующего раунда.',
  [ZS(effekt=[OBET([{'dobor_soyuznika': 'dobor'}], 'ocenka', 'draw')])],
  uproshcheno='карта приходит в начале следующего раунда: Заслон срабатывает в ход врага, после него рука сбрасывается')
C(71, 'zaslon-bronya', 'Заслон-броня', 'З', 'защита', {}, 'Заслон союзнику. Когда он сработает, снятый урон становится щитом союзнику на следующий раунд.',
  [ZS(effekt=[{'shchit_potom': {'komu': 'soyuznik', 'n': 'snyato'}}])])
C(72, 'snyat-zaslon', 'Снять заслон', 'З', 'защита', {'shchit': 7}, 'Сними Заслон с союзника: {shchit:щит} ему.',
  [{'snyat_zaslon': {'s': 'soyuznik', 'v': 's'}}, IF('s', [SH('soyuznik', 'shchit')])])
C(73, 'sorvat-zaslon', 'Сорвать заслон в гнев', 'З', 'атака', {'uron': 6}, 'Сними Заслон с союзника: {uron:урон} врагу.',
  [{'snyat_zaslon': {'s': 'soyuznik', 'v': 's'}}, IF('s', [U('uron')])])
C(74, 'perehvat', 'Перехват', 'З', 'защита', {'sila': 2, 'shchit': 2},
  'В этом раунде удар по герою под Заслоном принимаешь ты, и он слабее ещё на {sila}. {shchit:щит} себе.',
  [{'perehvat': 'sila'}, SH('ja', 'shchit')])
C(75, 'shchit-pod-zaslonom', 'Щит под заслоном', 'З', 'защита', {'shchit': 3}, '{shchit:щит} союзнику. Если на нём Заслон, вдвое.',
  [SH('soyuznik', 'shchit * (2 if soyuznik_zaslon else 1)')])
C(76, 'udar-pod-zaslonom', 'Удар под заслоном', 'З', 'атака', {'uron': 2, 'dop': 3}, '{uron:урон}. Если на союзнике Заслон, ещё {dop:урон}.',
  [U('uron + (dop if soyuznik_zaslon else 0)')])
C(77, 'svyataya-bronya', 'Святая броня', 'З', 'защита', {'shchit': 4}, '{shchit:щит} себе. Если на тебе Заслон, ещё Авангард.',
  [SH('ja', 'shchit'), IF('ja_zaslon', [{'avangard': 'ja'}])])
C(78, 'zaslon-naperyod', 'Заслон наперёд', 'З', 'защита', {'shchit': 3, 'ocenka': 4},
  'Выбери: Заслон союзнику сейчас или после хода врага Заслон обоим и {shchit:щит} союзнику.',
  varianty=[{'nazvanie': 'сейчас', 'effekt': [ZS()]},
            {'nazvanie': 'после', 'effekt': [OBET([ZS('oba'), SH('soyuznik', 'shchit')], 'ocenka', 'shield')]}])
C(79, 'obryad-zaslona', 'Обряд заслона', 'З', 'связка', {'uron': 4, 'uron_mal': 1, 'nuzhno': 2},
  '{uron_mal:урон}. Если 2 из 3 (на союзнике Заслон; у союзника есть щит; благословения менялись в этом раунде): Заслон обоим и {uron:урон}.',
  [PUST(c='soyuznik_zaslon + (shchit_soyuznika > 0) + blag_menyalis'), U('uron_mal'),
   IF('c >= nuzhno', [ZS('oba'), U('uron')])], metki=['blag'])
C(80, 'opornyj-zaslon', 'Опорный заслон', 'З', 'защита', {}, 'Заслон союзнику. Пока он на нём, щит союзника не сгорает в конце раунда.',
  [ZS(opora=1)])
C(81, 'znamya-nad-golovoj', 'Знамя над головой', 'З', 'связка', {'shchit': 2, 'uron': 3, 'shchit_s': 3},
  'Заслон союзнику и {shchit:щит} себе. Соларис: ещё {uron:урон}. Лунарис: ещё {shchit_s:щит} союзнику.',
  [ZS(), SH('ja', 'shchit'), IF('solaris', [U('uron')], [SH('soyuznik', 'shchit_s')])], metki=['blag'])
C(82, 'pamyat-zaslona', 'Память заслона', 'З', 'связка', {'uron': 2, 'shchit': 3},
  'Если на союзнике нет Заслона: Заслон и {uron:урон}. Если есть: {shchit:щит} обоим.',
  [IF('soyuznik_zaslon', [SH('oba', 'shchit')], [ZS(), U('uron')])])
C(83, 'bystryj-zaslon', 'Быстрый заслон', 'З', 'защита', {}, 'Заслон союзнику. Не считается в лимит.',
  [ZS(), {'ne_v_limit': 1}], metki=['mozhet_vne_limita'])
C(84, 'obmen', 'Обмен', 'З', 'защита', {'shchit': 2}, 'Перенеси Заслон с союзника на себя или с себя на союзника. {shchit:щит} обоим.',
  [{'perenesti_zaslon': 1}, SH('oba', 'shchit')])
C(85, 'polnyj-zaslon', 'Полный заслон', 'З', 'защита', {}, 'Заслон союзнику: следующий удар по нему отменяется целиком. Ты не можешь играть карт урона в этом раунде.',
  [ZS(polnyj=1), {'zapret_urona': 1}])
C(86, 'zaslon-i-mech', 'Заслон и меч', 'З', 'атака', {'uron': 2}, '{uron:урон} и Заслон союзнику.', [U('uron'), ZS()])
C(87, 'zaslon-na-rassvete', 'Заслон на рассвете', 'З', 'защита', {}, 'Заслон союзнику. Если в этом раунде менялись благословения, Заслон и тебе.',
  [ZS(), IF('blag_menyalis', [ZS('ja')])], metki=['blag'])
C(88, 'tyazhelyj-zaslon', 'Тяжёлый заслон', 'З', 'защита', {}, 'Заслон союзнику. Если у тебя Авангард, Заслон и тебе.',
  [ZS(), IF('ja_avangard', [ZS('ja')])])
C(89, 'zaslon-pod-blagosloveniem', 'Заслон под благословением', 'З', 'связка', {'uron': 2, 'shchit': 3},
  'Соларис: Заслон союзнику и {uron:урон}. Лунарис: Заслон союзнику и {shchit:щит} ему.',
  [ZS(), IF('solaris', [U('uron')], [SH('soyuznik', 'shchit')])], metki=['blag'])
C(90, 'poslednij-zaslon', 'Последний заслон', 'З', 'защита', {'sila': 6},
  'Заслон союзнику. Если у него здоровья меньше, чем у тебя, этот Заслон ослабляет удар ещё на {sila}.',
  [IF('zdorove_soyuznika < zdorove', [ZS(sila='sila')], [ZS()])])
C(91, 'zaslon-klyatva', 'Заслон-клятва', 'З', 'защита', {'shchit': 3}, 'Сбрось карту: Заслон союзнику и {shchit:щит} ему.',
  [{'sbros': {'n': 1, 'v': 's'}}, IF('s', [ZS(), SH('soyuznik', 'shchit')])])
C(92, 'raskolotyj-zaslon', 'Расколотый заслон', 'З', 'защита', {'slabee': 1},
  'Сними Заслон с союзника: Заслон на него и на тебя, каждый слабее обычного на {slabee}.',
  [{'snyat_zaslon': {'s': 'soyuznik', 'v': 's'}}, IF('s', [ZS('oba', sila='-slabee')])])
C(93, 'svet-na-shchite', 'Свет на щите', 'З', 'атака', {'uron_mal': 1}, 'Урон = щит союзника, если на нём Заслон. Иначе {uron_mal:урон}.',
  [U('shchit_soyuznika if soyuznik_zaslon else uron_mal')])

# ================================================================ Молитва
C(94, 'tihaya-molitva', 'Тихая молитва', 'М', 'молитва', {'vera': 1}, '+{vera:вера}. Молитва.', [V('vera'), MOL()], bot={'pereplan': True})
C(95, 'vsenoshchnaya', 'Всенощная', 'М', 'молитва', {}, 'Молитва дважды. Сбрось 1 карту из руки.',
  [MOL(raz=2), {'sbros': {'n': 1}}], bot={'pereplan': True})
C(96, 'znamenie-svyshe', 'Знамение свыше', 'М', 'молитва', {'vera': 2}, 'Молитва. Сыгранная так карта даёт ещё +{vera:вера}.',
  [MOL(posle=[V('vera')], ocenka_bota='0.6 * vera')], bot={'pereplan': True})
C(97, 'kara-nebesnaya', 'Кара небесная', 'М', 'молитва', {'uron': 3}, 'Молитва. Если так сыграна карта урона, ещё {uron:урон}.',
  [MOL(posle=[IF('sygrana_ataka', [U('uron')])], ocenka_bota='0.5 * uron')], bot={'pereplan': True})
C(98, 'prozrenie', 'Прозрение', 'М', 'молитва', {'n': 3, 'shchit': 2}, 'Посмотри {n} верхние карты колоды, разложи в любом порядке. {shchit:щит} себе.',
  [{'uporyadochit': 'n'}, SH('ja', 'shchit')])
C(99, 'chetki', 'Чётки', 'М', 'молитва', {}, 'Положи карту из руки на верх колоды. Молитва.',
  [{'na_verh_iz_ruki': {'n': 1}}, MOL()], bot={'pereplan': True})
C(100, 'psalom', 'Псалом', 'М', 'атака', {'uron': 2, 'mnozhitel': 3}, '{uron:урон}. Если эта карта сыграна Молитвой, урон ×{mnozhitel}.',
  [U('uron * (mnozhitel if sygrana_molitvoj else 1)')])
C(101, 'otlozhennyj-psalom', 'Отложенный псалом', 'М', 'защита', {'shchit': 3, 'shchit_big': 6},
  'Выбери: {shchit:щит} себе сейчас или положи эту карту на верх колоды: сыгранная Молитвой, она даёт {shchit_big:щит} обоим.',
  varianty=[{'nazvanie': 'сейчас', 'effekt': [IF('sygrana_molitvoj', [SH('oba', 'shchit_big')], [SH('ja', 'shchit')])]},
            {'nazvanie': 'на верх', 'effekt': [{'ocenka': 2}, {'eta_na_verh': 1}]}])
C(102, 'vozvrashchenie', 'Возвращение', 'М', 'атака', {'uron': 2}, '{uron:урон}. После розыгрыша положи эту карту на верх колоды.',
  [U('uron'), {'eta_na_verh': 1}])
C(103, 'kolokol', 'Колокол', 'М', 'молитва', {}, 'Молитва. Если так сыграна карта щита, такой же щит союзнику.',
  [MOL(posle=[IF('sygrana_zashchita', [SH('soyuznik', 'shchit_s_karty')])], ocenka_bota=1)], bot={'pereplan': True})
C(104, 'otkrovenie', 'Откровение', 'М', 'молитва', {}, 'Открой верхнюю карту: если это карта урона, сыграй её Молитвой; иначе возьми её в руку.',
  [IF('verh_ataka', [MOL(otkryt=1)], [D(1)])], bot={'pereplan': True})
C(105, 'perebor-chetok', 'Перебор чёток', 'М', 'молитва', {},
  'Открывай верхние карты, пока не откроешь карту урона, сыграй её Молитвой. Остальные под низ колоды.',
  [MOL(tolko_vid='атака', do_pervoj=True, ostalnye='niz')], bot={'pereplan': True})
C(106, 'litaniya', 'Литания', 'М', 'защита', {'shchit': 4, 'dop': 3, 'vera': 1},
  '{shchit:щит} союзнику. Если в этом раунде ты играл Молитву, ещё {dop:щит} и +{vera:вера}.',
  [SH('soyuznik', 'shchit'), IF('molitv_v_raunde > 0', [SH('soyuznik', 'dop'), V('vera')])])
C(107, 'molitva-iz-glubiny', 'Молитва из глубины', 'М', 'молитва', {}, 'Сыграй нижнюю карту своей колоды, как Молитвой.',
  [MOL(otkuda='niz', otkryt=1)], bot={'pereplan': True})
C(108, 'tyazhkaya-molitva', 'Тяжкая молитва', 'М', 'молитва', {}, 'Молитва: сыгранная карта срабатывает дважды, затем сожги её.',
  [MOL(otkryt=1, dvazhdy=True)], bot={'pereplan': True})
C(109, 'pustaya-molitva', 'Пустая молитва', 'М', 'молитва', {'vera': 2}, 'Посмотри верхнюю карту: сыграй её Молитвой или сбрось и получи +{vera:вера}.',
  varianty=[{'nazvanie': 'сыграть', 'effekt': [MOL(otkryt=1)]},
            {'nazvanie': 'сбросить', 'effekt': [{'sbros_verha': {'n': 1}}, V('vera')]}], bot={'pereplan': True})
C(110, 'podgotovka', 'Подготовка', 'М', 'вера', {'za': 1}, 'Положи одну или две карты из руки на верх колоды. +{za:вера} за каждую.',
  varianty=[{'nazvanie': 'одну', 'effekt': [{'na_verh_iz_ruki': {'n': 1, 'v': 'k'}}, V('za * k')]},
            {'nazvanie': 'две', 'effekt': [{'na_verh_iz_ruki': {'n': 2, 'v': 'k'}}, V('za * k')]}])
C(111, 'predvestie', 'Предвестие', 'М', 'молитва', {'ocenka': 6}, 'Выбери: Молитва сейчас или после хода врага Молитва дважды.',
  varianty=[{'nazvanie': 'сейчас', 'effekt': [MOL()]}, {'nazvanie': 'после', 'effekt': [OBET([MOL(raz=2)], 'ocenka', 'draw')]}],
  bot={'pereplan': True})
C(112, 'posoh-palomnika', 'Посох паломника', 'М', 'атака', {'uron': 4}, 'Сбрось верхнюю карту колоды. Если это карта урона, {uron:урон}.',
  [{'sbros_verha': {'n': 1, 'v': 'a'}}, IF('a', [U('uron')])])
C(113, 'kayushchijsya', 'Кающийся', 'М', 'молитва', {}, 'Сбрось карту из руки: Молитва.',
  [{'sbros': {'n': 1, 'v': 's'}}, IF('s', [MOL()])], bot={'pereplan': True})
C(114, 'svyatye-moshchi', 'Святые мощи', 'М', 'вера', {'vera': 2, 'uron': 3}, 'Сожги верхнюю карту колоды: +{vera:вера}. Если это карта урона, ещё {uron:урон}.',
  [{'osobyj': {'imya': 'sozhgi_verh_svoej', 'v': 'a'}}, V('vera'), IF('a', [U('uron')])])
C(115, 'bdenie-u-altarya', 'Бдение у алтаря', 'М', 'защита', {}, 'Посмотри верхнюю карту. Если это карта щита, сыграй её Молитвой и получи Авангард.',
  [IF('verh_zashchita', [MOL(otkryt=1), {'avangard': 'ja'}])], bot={'pereplan': True})
C(116, 'slovo-nastavnika', 'Слово наставника', 'М', 'молитва', {'dobor': 1},
  'Молитва. Сыгранная так карта после розыгрыша уходит под низ колоды, а не в сброс. Возьми {dobor:карту}.',
  [MOL(sygrannye='niz'), D('dobor')], bot={'pereplan': True})
C(117, 'nebesnyj-poryadok', 'Небесный порядок', 'М', 'молитва', {'n': 3}, 'Замешай сброс в колоду. Посмотри {n} верхние карты и разложи в любом порядке.',
  [{'zameshaj_sbros': 1}, {'uporyadochit': 'n'}])
C(118, 'horal', 'Хорал', 'М', 'молитва', {}, 'Молитва. Если так сыграна карта с Молитвой, ещё одна Молитва.',
  [MOL(posle=[IF('sygrana_molitva', [MOL()])], ocenka_bota=1)], bot={'pereplan': True},
  uproshcheno='в идее «она играет две верхние карты»; на стенде — ещё одна Молитва')
C(119, 'molitva-v-stroyu', 'Молитва в строю', 'М', 'молитва', {'shchit': 1}, '{shchit:щит} себе и союзнику. Молитва.',
  [SH('oba', 'shchit'), MOL()], bot={'pereplan': True})
C(120, 'otkrytaya-molitva', 'Открытая молитва', 'М', 'молитва', {}, 'Открой верхнюю карту колоды: в этом раунде её можно сыграть как из руки. Не сыграна — возвращается на верх.',
  [{'otkryt_verh': 1}], bot={'pereplan': True})
C(121, 'obet-molchaniya', 'Обет молчания', 'М', 'молитва', {'raz': 3}, 'Ты не играешь карт из руки до конца раунда. Молитва {raz:раз}.',
  [{'tolko_molitvy': 1}, MOL(raz='raz')], bot={'pereplan': True})
C(122, 'molitva-otvet', 'Молитва-ответ', 'М', 'молитва', {}, 'Молитва; несыгранные открытые карты уходят под низ колоды.',
  [MOL(otkryt=2, ostalnye='niz')], bot={'pereplan': True},
  uproshcheno='базовая Молитва уже открывает 2 карты; отличие — несыгранная уходит под низ, а не в сброс')
C(123, 'trojnaya-molitva', 'Тройная молитва', 'М', 'молитва', {'vera': 1, 'nuzhno': 2},
  '+{vera:вера}. Если 2 из 3 (вера 4+; на союзнике Заслон; верхняя карта колоды — карта урона): Молитва дважды.',
  [PUST(c='(vera >= 4) + soyuznik_zaslon + verh_ataka'), V('vera'), IF('c >= nuzhno', [MOL(raz=2)])], bot={'pereplan': True})
C(124, 'horugv', 'Хоругвь', 'М', 'молитва', {'uron': 2},
  'Молитва. Соларис: сыгранная так карта урона бьёт ещё на {uron}. Лунарис: щит с сыгранной так карты получает и союзник.',
  [MOL(posle=[IF('solaris and sygrana_ataka', [U('uron')]), IF('lunaris and sygrana_zashchita', [SH('soyuznik', 'shchit_s_karty')])],
       ocenka_bota=1)], metki=['blag'], bot={'pereplan': True})
C(125, 'otpushchenie', 'Отпущение', 'М', 'вера', {'vera': 1}, 'Положи лучшую карту из сброса на верх колоды. +{vera:вера}.',
  [{'iz_sbrosa_na_verh': 1}, V('vera')])
C(126, 'molitva-pod-udarom', 'Молитва под ударом', 'М', 'молитва', {}, 'Если на тебе Авангард: Молитва дважды. Иначе Молитва.',
  [IF('ja_avangard', [MOL(raz=2)], [MOL()])], bot={'pereplan': True})

# ================================================================ Связки
C(127, 'chudo-stojkosti', 'Чудо стойкости', 'ВЗ', 'защита', {'za': 1}, 'Чудо: Заслон обоим, каждый ослабляет удар ещё на {za} за каждую сожжённую веру.',
  [{'chudo': 'f'}, ZS('oba', sila='za * f')], metki=['chudo'])
C(128, 'zaslon-very', 'Заслон веры', 'ВЗ', 'связка', {'vera': 2}, 'Заслон союзнику. Когда он сработает, +{vera:вера}.', [ZS(effekt=[V('vera')])])
C(129, 'plata-za-zaslon', 'Плата за заслон', 'ВЗ', 'защита', {'doplata': 1}, 'Заслон союзнику. Доплата {doplata:веру}: не считается в лимит.',
  varianty=[{'nazvanie': '', 'effekt': [ZS()]},
            {'nazvanie': 'доплата', 'doplata': {'vera': 1}, 'effekt': [ZS(), IF('oplacheno', [{'ne_v_limit': 1}])]}],
  metki=['mozhet_vne_limita'])
C(130, 'vera-na-shchite', 'Вера на щите', 'ВЗ', 'защита', {}, 'Заслон союзнику. Вера 4+: этот Заслон ослабляет каждый удар раунда и снимается в конце раунда.',
  [ZS(stojkij='vera >= 4')])
C(131, 'snyatie-v-veru', 'Снятие в веру', 'ВЗ', 'вера', {'vera': 3}, 'Сними Заслон с союзника: +{vera:вера}.',
  [{'snyat_zaslon': {'s': 'soyuznik', 'v': 's'}}, IF('s', [V('vera')])])
C(132, 'chudo-vozmezdiya', 'Чудо возмездия', 'ВЗ', 'атака', {'za': 1, 'dop': 3}, 'Чудо: {za:урон} за каждую веру. Если на союзнике Заслон, ещё {dop:урон}.',
  [{'chudo': 'f'}, U('za * f + (dop if soyuznik_zaslon else 0)')], metki=['chudo'])
C(133, 'obryad-dvoih', 'Обряд двоих', 'ВЗ', 'защита', {'shchit': 3, 'shchit_mal': 2, 'nuzhno': 2},
  'Если 2 из 3 (вера 6; на союзнике Заслон; у союзника есть щит): Заслон и {shchit:щит} обоим. Иначе {shchit_mal:щит} союзнику.',
  [PUST(c='(vera >= 6) + soyuznik_zaslon + (shchit_soyuznika > 0)'),
   IF('c >= nuzhno', [ZS('oba'), SH('oba', 'shchit')], [SH('soyuznik', 'shchit_mal')])])
C(134, 'zaslon-pod-chudo', 'Заслон под чудо', 'ВЗ', 'защита', {'vera': 2}, 'Если вера 0: Заслон обоим и +{vera:вера}. Иначе Заслон союзнику.',
  [IF('vera == 0', [ZS('oba'), V('vera')], [ZS()])])
C(135, 'pokrov-molitvy', 'Покров молитвы', 'ЗМ', 'молитва', {}, 'Заслон союзнику. Молитва.', [ZS(), MOL()], bot={'pereplan': True})
C(136, 'molitva-za-brata', 'Молитва за брата', 'ЗМ', 'молитва', {},
  'Молитва. Если так сыграна карта щита, щит с неё получает союзник, и на него ложится Заслон.',
  [MOL(posle=[IF('sygrana_zashchita', [{'otdat_shchit': 'shchit_s_karty'}, ZS()])], ocenka_bota=1)], bot={'pereplan': True})
C(137, 'zaslon-iz-kolody', 'Заслон из колоды', 'ЗМ', 'защита', {}, 'Посмотри верхнюю карту: если это карта щита, сыграй её Молитвой; иначе Заслон союзнику.',
  [IF('verh_zashchita', [MOL(otkryt=1)], [ZS()])], bot={'pereplan': True})
C(138, 'kolokol-trevogi', 'Колокол тревоги', 'ЗМ', 'молитва', {}, 'Сними Заслон с союзника: Молитва дважды.',
  [{'snyat_zaslon': {'s': 'soyuznik', 'v': 's'}}, IF('s', [MOL(raz=2)])], bot={'pereplan': True})
C(139, 'zastava', 'Застава', 'ЗМ', 'защита', {}, 'Положи карту из руки на верх колоды. Заслон союзнику.', [{'na_verh_iz_ruki': {'n': 1}}, ZS()])
C(140, 'litaniya-strazhi', 'Литания стражи', 'ЗМ', 'защита', {}, 'Заслон союзнику. Если в этом раунде ты играл Молитву, Заслон и тебе.',
  [ZS(), IF('molitv_v_raunde > 0', [ZS('ja')])])
C(141, 'znamya-na-kolode', 'Знамя на колоде', 'ЗМ', 'связка', {'uron': 4, 'uron_mal': 1},
  'Выбери: {uron_mal:урон} или положи эту карту на верх колоды. Сыгранная Молитвой, она даёт Заслон обоим и {uron:урон}.',
  varianty=[{'nazvanie': 'сыграть', 'effekt': [IF('sygrana_molitvoj', [ZS('oba'), U('uron')], [U('uron_mal')])]},
            {'nazvanie': 'на верх', 'effekt': [{'ocenka': 2}, {'eta_na_verh': 1}]}])
C(142, 'shchit-iz-molitvy', 'Щит из молитвы', 'ЗМ', 'молитва', {}, 'Молитва. Если на союзнике Заслон, весь щит с сыгранной карты получает союзник.',
  [MOL(posle=[IF('soyuznik_zaslon', [{'otdat_shchit': 'shchit_s_karty'}])])], bot={'pereplan': True})
C(143, 'lestnica', 'Лестница', 'МВ', 'вера', {'vera': 2}, '+{vera:вера}. Если стало 6, Молитва.',
  [V('vera'), IF('vera >= 6', [MOL()])], bot={'pereplan': True})
C(144, 'dar-svyshe', 'Дар свыше', 'МВ', 'молитва', {'n': 2}, 'Молитва. Если так сыграно Чудо, оно считает +{n:вера}.',
  [{'osobyj': {'imya': 'poslushnik', 'n': 'n'}}, MOL()], bot={'pereplan': True},
  uproshcheno='прибавка держится до первого Чуда в этом раунде, не только сыгранного Молитвой')
C(145, 'vozglas', 'Возглас', 'МВ', 'атака', {'uron': 2}, '{uron:урон}. Вера 4+: Молитва.', [U('uron'), IF('vera >= 4', [MOL()])], bot={'pereplan': True})
C(146, 'chudo-v-kolode', 'Чудо в колоде', 'МВ', 'вера', {}, 'Положи карту Чуда из руки на верх колоды. Следующее Чудо не сжигает веру.',
  [{'na_verh_iz_ruki': {'n': 1, 'tolko_metka': 'chudo'}}, {'chudo_ne_szhigaet': 1}],
  uproshcheno='веру не сжигает следующее Чудо, а не только сыгранное Молитвой')
C(147, 'svyatoe-kope', 'Святое копьё', 'МВ', 'атака', {'za': 3}, '{za:урон} за каждую карту, сыгранную Молитвой в этом раунде.',
  [U('za * molitv_v_raunde')])
C(148, 'post-i-molitva', 'Пост и молитва', 'МВ', 'молитва', {'za': 2}, 'Сожги веру: Молитва за каждые {za} сожжённые.',
  varianty=[{'nazvanie': f'сжечь {k}', 'effekt': [{'szhech_veru': {'n': k, 'v': 'k'}}, MOL(raz='k // za')]} for k in (2, 4, 6)],
  bot={'pereplan': True})
C(149, 'perevernutaya-molitva', 'Перевёрнутая молитва', 'МВ', 'молитва', {}, 'Переверни кубик веры. Если вера стала больше, Молитва.',
  [PUST(a='vera'), {'perevernut_veru': 1}, IF('vera > a', [MOL()])], bot={'pereplan': True})
C(150, 'vera-v-kolodu', 'Вера в колоду', 'МВ', 'молитва', {'n': 3, 'doplata': 2},
  'Доплата {doplata:веру}: посмотри {n} верхние карты, одну сыграй Молитвой, остальные разложи в любом порядке. Без доплаты — только разложи.',
  varianty=[{'nazvanie': '', 'effekt': [{'uporyadochit': 'n'}]},
            {'nazvanie': 'доплата', 'doplata': {'vera': 2},
             'effekt': [IF('oplacheno', [MOL(otkryt='n', ostalnye='verh')], [{'uporyadochit': 'n'}])]}], bot={'pereplan': True})

# ================================================================ Легендарки (выбраны Никитой 2026-10-25)
LEG = [
    (151, 'neugasimaya-vera', 'Неугасимая вера', 'neugasimaya_vera', {'vera_na_starte': 2, 'sol_vera': 1, 'lun_ostatok': 1},
     'Вера не обнуляется между боями (на стенде: бой начинается с {vera_na_starte:веру}). Соларис: в начале боя ещё +{sol_vera:вера}. '
     'Лунарис: Чудо оставляет {lun_ostatok:веру}.'),
    (152, 'dvojnaya-molitva', 'Двойная молитва', 'dvojnaya_molitva', {'dop_kart': 1, 'sol_uron': 2, 'lun_otkryt': 1},
     'Каждая Молитва играет на {dop_kart:карту} с верха колоды больше. Соларис: лишняя карта урона бьёт ещё на {sol_uron}. '
     'Лунарис: Молитва открывает ещё {lun_otkryt:карту} на выбор.'),
    (153, 'shipy-zaslona', 'Шипы заслона', 'shipy_zaslona', {'sol_uron': 1},
     'Если враг ударил героя под Заслоном, враг получает урон, равный щиту, который этот удар снял. Соларис: ещё {sol_uron:урон}. '
     'Лунарис: Заслон после удара не снимается.'),
]


def granicy(ch):
    out = {}
    for k, v in ch.items():
        if k.startswith('ocenka'):
            out[k] = [0, max(10, v * 2)]
        elif k == 'nuzhno':
            out[k] = [1, 3]
        else:
            out[k] = [min(0, v), max(v * 2, v + 3)]
    return out


def yamls():
    out = []
    for c in CARDS:
        d = {'id': f"b{c['n']:03d}-{c['slug']}", 'imya': c['imya'], 'geroj': 'zhrec', 'nabor': 'bank',
             'bild': BILD[c['bild']], 'vid': c['vid'], 'nomer_idei': c['n']}
        if c['chisla']:
            d['chisla'] = dict(c['chisla'])
        d['tekst'] = c['tekst']
        if c['varianty'] is not None:
            d['varianty'] = c['varianty']
        else:
            d['effekt'] = c['effekt']
        if c['metki']:
            d['metki'] = c['metki']
        d['bot'] = dict({'poryadok': 4, 'cennost': 5}, **(c['bot'] or {}))
        if c['chisla']:
            d['granicy'] = granicy(c['chisla'])
        d['status'] = 'ideya'
        ist = ['2026-10-25 Claude: перевод идеи из heroes/paladin/idei-kart.md, числа черновые']
        if c['uproshcheno']:
            ist.append('упрощено для стенда: ' + c['uproshcheno'])
        d['istoriya'] = ist
        out.append(d)
    for n, slug, imya, passiv, ch, tekst in LEG:
        out.append({'id': f'b{n:03d}-{slug}', 'imya': imya, 'geroj': 'zhrec', 'nabor': 'legendarka', 'bild': '',
                    'vid': 'связка', 'nomer_idei': n, 'chisla': ch, 'tekst': tekst, 'passiv': {'imya': passiv},
                    'granicy': granicy(ch), 'status': 'ideya',
                    'istoriya': ['2026-10-25 Claude: легендарка Никиты, эффекты Соларис/Лунарис — Claude; числа черновые']})
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
