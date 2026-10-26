# -*- coding: utf-8 -*-
"""Новые карты банка вместо 82 неиграбельных (решение Никиты 2026-10-26: «Поменяй неиграбельные карты на другие,
придумай сам»). Те же билды, что ушли в запас. Принцип: польза сейчас, без долгой подготовки
(урок подгонки: карты-подготовки не окупаются в бою из 3–5 раундов), малые комбо с механикой героя.
Только общий словарь эффектов, без новых механик движка.

  python -m stend.bank_novye_2026_10_26 [--zamenit]   (из playtest/stend)"""
import os, sys
import yaml
from .yamlpis import dump

ROOT = os.path.normpath(os.path.join(os.path.dirname(__file__), '..', '..', '..'))
IST = '2026-10-26 Claude: новая карта вместо неиграбельных (решение Никиты «придумай сам»), числа черновые'

U = lambda n='uron': {'uron': n}
SH = lambda komu='ja', n='shchit': {'shchit': {'komu': komu, 'n': n}}
SOZ = lambda n=1: {'sozhgi': {'otkuda': 'ruka', 'n': n, 'v': 's'}}


def esli(c, to, inache=None):
    d = {'esli': c, 'to': to}
    if inache:
        d['inache'] = inache
    return d


# (id, имя, билд, вид, цена, chisla, текст, effekt | varianty, доп. поля)
MAG = [
    ('m201-tleyushchij-udar', 'Тлеющий удар', '', 'атака', 1, {'uron': 3, 'dop': 1},
     '{cena:мана}. {uron:урон}. Если в этом раунде сожжена карта, ещё {dop:урон}.', [U('uron + (dop if szhzheno_v_raunde > 0 else 0)')], {}),
    ('m202-pepelnaya-zavesa', 'Пепельная завеса', '', 'защита', 1, {'shchit': 3},
     '{cena:мана}. {shchit:щит} себе или союзнику.', None,
     {'varianty': [{'nazvanie': 'себе', 'effekt': [SH()]}, {'nazvanie': 'союзнику', 'effekt': [SH('soyuznik')]}]}),
    ('m203-dvojnoj-vypad', 'Двойной выпад', '', 'атака', 1, {'uron': 1, 'raz': 2},
     '{cena:мана}. {raz} попадания по {uron:урон}.', [{'udary': {'n': 'uron', 'raz': 'raz'}}], {}),
    ('m204-iskra-nadezhdy', 'Искра надежды', '', 'связка', 0, {'uron': 1, 'dobor': 1},
     '{cena:мана}. {uron:урон}. Возьми {dobor:карту}.', [U(), {'dobor': 'dobor'}], {}),
    # П — сжигание
    ('m205-zhertvennyj-ogon', 'Жертвенный огонь', 'П', 'атака', 0, {'uron': 3},
     '{cena:мана}. Сожги карту из руки: {uron:урон}.', [SOZ(), esli('s', [U()])], {}),
    ('m206-pepelnyj-shchit', 'Пепельный щит', 'П', 'защита', 0, {'shchit': 3},
     '{cena:мана}. Сожги карту из руки: {shchit:щит} себе.', [SOZ(), esli('s', [SH()])], {}),
    ('m207-plamya-iz-praha', 'Пламя из праха', 'П', 'атака', 1, {'uron': 1, 'za': 1},
     '{cena:мана}. {uron:урон} и ещё {za:урон} за каждую карту, сожжённую в этом раунде.', [U('uron + za * szhzheno_v_raunde')], {}),
    ('m208-podnoshenie-predkam', 'Подношение предкам', 'П', 'связка', 1, {'mana': 2},
     '{cena:мана}. Сожги две карты из руки: +{mana:мана}.', [SOZ(2), esli('s >= 2', [{'mana': 'mana'}])], {}),
    ('m209-ognennyj-dar', 'Огненный дар', 'П', 'атака', 1, {'uron': 3, 'shchit': 2},
     '{cena:мана}. {uron:урон}. Подношение: и {shchit:щит} союзнику.', [U(), esli('podnoshenie', [SH('soyuznik')])], {'podnoshenie': 1}),
    ('m210-toplivo-ochaga', 'Топливо очага', 'П', 'связка', 0, {'mana': 1, 'dobor': 1},
     '{cena:мана}. Сожги карту из руки: +{mana:мана}, возьми {dobor:карту}.', [SOZ(), esli('s', [{'mana': 'mana'}, {'dobor': 'dobor'}])], {}),
    ('m211-koster-v-ladonyah', 'Костёр в ладонях', 'П', 'атака', 2, {'uron': 4, 'dop': 3},
     '{cena:мана}. {uron:урон}. Подношение: ещё {dop:урон}.', [U(), esli('podnoshenie', [U('dop')])], {'podnoshenie': 1}),
    # Р — Порча
    ('m212-chernaya-metka', 'Чёрная метка', 'Р', 'атака', 1, {'uron': 2},
     '{cena:мана}. Наложи Порчу, затем {uron:урон}.', [{'porcha': 1}, U()], {}),
    ('m213-ukol-proklyatiya', 'Укол проклятия', 'Р', 'атака', 0, {'uron': 1, 'dobor': 1},
     '{cena:мана}. {uron:урон}. Если на враге Порча, возьми {dobor:карту}.', [U(), esli('porcha > 0', [{'dobor': 'dobor'}])], {}),
    ('m214-sglaz-shchit', 'Сглаз-щит', 'Р', 'защита', 1, {'shchit': 2},
     '{cena:мана}. Наложи Порчу. {shchit:щит} себе.', [{'porcha': 1}, SH()], {}),
    ('m215-ship-porchi', 'Шип порчи', 'Р', 'атака', 1, {'uron': 1, 'raz': 3},
     '{cena:мана}. {raz} попадания по {uron:урон}.', [{'udary': {'n': 'uron', 'raz': 'raz'}}], {}),
    ('m216-gniloj-ukus', 'Гнилой укус', 'Р', 'атака', 1, {'uron': 2, 'dop': 2},
     '{cena:мана}. {uron:урон}. Если на враге Порча, ещё {dop:урон}.', [U('uron + (dop if porcha > 0 else 0)')], {}),
    ('m217-porcha-na-dvoih', 'Порча на двоих', 'Р', 'защита', 1, {'shchit': 2},
     '{cena:мана}. Наложи Порчу. {shchit:щит} союзнику.', [{'porcha': 1}, SH('soyuznik')], {}),
    ('m218-zloj-glaz', 'Злой глаз', 'Р', 'атака', 1, {'uron': 4},
     '{cena:мана}. Если на враге Порча, {uron:урон}. Иначе наложи Порчу.', [esli('porcha > 0', [U()], [{'porcha': 1}])], {}),
    ('m220-proklyatyj-shchit', 'Проклятый щит', 'Р', 'защита', 1, {'shchit': 3, 'dop': 2},
     '{cena:мана}. {shchit:щит} себе. Если на враге Порча, ещё {dop:щит} союзнику.', [SH(), esli('porcha > 0', [SH('soyuznik', 'dop')])], {}),
    ('m221-nit-porchi', 'Нить порчи', 'Р', 'связка', 1, {'dobor': 1},
     '{cena:мана}. Наложи Порчу, возьми {dobor:карту}.', [{'porcha': 1}, {'dobor': 'dobor'}], {}),
    ('m222-vorozhba', 'Ворожба', 'Р', 'связка', 1, {'uron': 2, 'shchit': 4},
     '{cena:мана}. Выбери: Порча и {uron:урон} или {shchit:щит} союзнику.', None,
     {'varianty': [{'nazvanie': 'порча', 'effekt': [{'porcha': 1}, U()]}, {'nazvanie': 'щит', 'effekt': [SH('soyuznik')]}]}),
    ('m223-grad-proklyatij', 'Град проклятий', 'Р', 'атака', 2, {'uron': 1, 'raz': 4},
     '{cena:мана}. {raz} попадания по {uron:урон}.', [{'udary': {'n': 'uron', 'raz': 'raz'}}], {}),
    ('m224-metka-dlya-soyuznika', 'Метка для союзника', 'Р', 'связка', 0, {'bonus': 1},
     '{cena:мана}. Наложи Порчу. Следующее попадание союзника в этом раунде сильнее на {bonus}.', [{'porcha': 1}, {'bonus_soyuzniku': 'bonus'}], {}),
    ('m225-tyazhelaya-porcha', 'Тяжёлая порча', 'Р', 'атака', 2, {'uron': 4},
     '{cena:мана}. Наложи Порчу, затем {uron:урон}.', [{'porcha': 1}, U()], {}),
    ('m226-oslablyayushchij-sglaz', 'Ослабляющий сглаз', 'Р', 'защита', 1, {'oslab': 1},
     '{cena:мана}. Наложи Порчу. В этом раунде враг бьёт на {oslab} слабее.', [{'porcha': 1}, {'oslab_vraga': 'oslab'}], {}),
    ('m227-kost-v-gorle', 'Кость в горле', 'Р', 'атака', 1, {'uron': 2, 'oslab': 2},
     '{cena:мана}. {uron:урон}. Если на враге Порча, в этом раунде он бьёт на {oslab} слабее.', [U(), esli('porcha > 0', [{'oslab_vraga': 'oslab'}])], {}),
    # Д — долг духам
    ('m231-bystryj-zajm', 'Быстрый займ', 'Д', 'связка', 0, {'mana': 1, 'dobor': 1},
     '{cena:мана}. +{mana:мана} в долг, возьми {dobor:карту}.', [{'mana_v_dolg': 'mana'}, {'dobor': 'dobor'}], {}),
    ('m232-udar-v-dolg', 'Удар в долг', 'Д', 'атака', 0, {'uron': 4, 'dolg_n': 2},
     '{cena:мана}. {uron:урон}. {dolg_n:мана} в долг.', [U(), {'dolg': 'dolg_n'}], {}),
    ('m233-shchit-v-dolg', 'Щит в долг', 'Д', 'защита', 0, {'shchit': 5, 'dolg_n': 2},
     '{cena:мана}. {shchit:щит} себе или союзнику. {dolg_n:мана} в долг.', None,
     {'varianty': [{'nazvanie': 'себе', 'effekt': [SH(), {'dolg': 'dolg_n'}]}, {'nazvanie': 'союзнику', 'effekt': [SH('soyuznik'), {'dolg': 'dolg_n'}]}]}),
    ('m234-chistyj-raschet', 'Чистый расчёт', 'Д', 'атака', 1, {'uron': 3, 'shchit': 2},
     '{cena:мана}. {uron:урон}. Если у тебя нет долга, ещё {shchit:щит} себе.', [U(), esli('dolg == 0', [SH()])], {}),
    ('m235-otsrochka', 'Отсрочка', 'Д', 'защита', 1, {'shchit': 4, 'dobor': 1},
     '{cena:мана}. {shchit:щит} союзнику. Если у тебя есть долг, возьми {dobor:карту}.', [SH('soyuznik'), esli('dolg > 0', [{'dobor': 'dobor'}])], {}),
    ('m236-zalog-sily', 'Залог силы', 'Д', 'связка', 0, {'mana': 2, 'dobor': 1},
     '{cena:мана}. +{mana:мана} в долг. Возьми {dobor:карту}.', [{'mana_v_dolg': 'mana'}, {'dobor': 'dobor'}], {}),
    ('m237-dolzhnik-v-yarosti', 'Должник в ярости', 'Д', 'атака', 1, {'uron': 2, 'dop': 2},
     '{cena:мана}. {uron:урон}. Если у тебя есть долг, ещё {dop:урон}.', [U('uron + (dop if dolg > 0 else 0)')], {}),
    ('m239-kredit-duhov', 'Кредит духов', 'Д', 'связка', 0, {'mana': 2, 'dobor': 2, 'dolg_n': 1},
     '{cena:мана}. Выбери: +{mana:мана} в долг или возьми {dobor:карту} и {dolg_n:мана} в долг.', None,
     {'varianty': [{'nazvanie': 'мана', 'effekt': [{'mana_v_dolg': 'mana'}]}, {'nazvanie': 'карты', 'effekt': [{'dobor': 'dobor'}, {'dolg': 'dolg_n'}]}],
      'bot': {'poryadok': 2, 'cennost': 5, 'pereplan': True}}),
    ('m240-dolzhnik-b-yot', 'Должник бьёт', 'Д', 'атака', 1, {'uron': 2, 'za': 2},
     '{cena:мана}. {za:урон} за каждый жетон долга, но не меньше {uron:урон}.', [U('max(uron, za * dolg)')], {}),
    ('m241-duhi-zhdut', 'Духи ждут', 'Д', 'защита', 1, {'shchit': 3, 'dop': 3},
     '{cena:мана}. {shchit:щит} себе. Если у тебя есть долг, ещё {dop:щит}.', [SH('ja', 'shchit + (dop if dolg > 0 else 0)')], {}),
    ('m242-vklad-predkam', 'Вклад предкам', 'Д', 'атака', 1, {'uron': 3, 'shchit': 2},
     '{cena:мана}. {uron:урон} и {shchit:щит} союзнику.', [U(), SH('soyuznik')], {}),
    ('m243-zajm-na-shchit', 'Займ на щит', 'Д', 'защита', 0, {'shchit': 3, 'dobor': 1, 'dolg_n': 1},
     '{cena:мана}. Союзник получает {shchit:щит} и берёт {dobor:карту}. {dolg_n:мана} в долг.',
     [SH('soyuznik'), {'dobor_soyuznika': 'dobor'}, {'dolg': 'dolg_n'}], {}),
    # П–Д
    ('m244-ogon-v-uplatu', 'Огонь в уплату', 'П–Д', 'связка', 0, {'mana': 2, 'dolg_n': 1},
     '{cena:мана}. Сожги карту из руки: +{mana:мана}, {dolg_n:мана} в долг.', [SOZ(), esli('s', [{'mana': 'mana'}, {'dolg': 'dolg_n'}])], {}),
    ('m245-pepelnyj-zajm', 'Пепельный займ', 'П–Д', 'атака', 0, {'uron': 3, 'dolg_n': 1},
     '{cena:мана}. {dolg_n:мана} в долг: сожги карту из руки и {uron:урон}.', [{'dolg': 'dolg_n'}, SOZ(), U()], {}),
    ('m246-goryashchaya-raspiska', 'Горящая расписка', 'П–Д', 'атака', 1, {'uron': 3, 'dop': 2},
     '{cena:мана}. {uron:урон}. Если у тебя есть долг, сожги карту из руки: ещё {dop:урон}.', [U(), esli('dolg > 0', [SOZ(), esli('s', [U('dop')])])], {}),
    ('m247-plamya-kreditora', 'Пламя кредитора', 'П–Д', 'атака', 0, {'uron': 1, 'za': 2, 'dolg_n': 1},
     '{cena:мана}. {uron:урон} и ещё {za:урон} за каждую карту, сожжённую в этом раунде. {dolg_n:мана} в долг.',
     [U('uron + za * szhzheno_v_raunde'), {'dolg': 'dolg_n'}], {}),
    ('m248-zola-i-dolg', 'Зола и долг', 'П–Д', 'защита', 1, {'shchit': 4, 'dop': 2},
     '{cena:мана}. Сожги карту из руки: {shchit:щит} себе. Если у тебя есть долг, ещё {dop:щит} союзнику.',
     [SOZ(), esli('s', [SH(), esli('dolg > 0', [SH('soyuznik', 'dop')])])], {}),
    ('m249-podnoshenie-v-rassrochku', 'Подношение в рассрочку', 'П–Д', 'связка', 0, {'mana': 2, 'dobor': 1, 'dolg_n': 1},
     '{cena:мана}. Подношение: +{mana:мана}. Иначе {dolg_n:мана} в долг и возьми {dobor:карту}.',
     [esli('podnoshenie', [{'mana': 'mana'}], [{'dolg': 'dolg_n'}, {'dobor': 'dobor'}])], {'podnoshenie': 1}),
    # П–Р
    ('m219-porcha-i-pepel', 'Порча и пепел', 'П–Р', 'атака', 0, {'uron': 1},
     '{cena:мана}. Сожги карту из руки: наложи Порчу и {uron:урон}.', [SOZ(), esli('s', [{'porcha': 1}, U()])], {}),
    ('m250-goryashchij-sglaz', 'Горящий сглаз', 'П–Р', 'атака', 1, {'uron': 3},
     '{cena:мана}. Сожги карту из руки: наложи Порчу и {uron:урон}.', [SOZ(), esli('s', [{'porcha': 1}, U()])], {}),
    ('m251-proklyatyj-pepel', 'Проклятый пепел', 'П–Р', 'атака', 0, {'uron': 3},
     '{cena:мана}. Если на враге Порча, сожги карту из руки: {uron:урон}.', [esli('porcha > 0', [SOZ(), esli('s', [U()])])], {}),
    ('m252-podnoshenie-porchi', 'Подношение порчи', 'П–Р', 'атака', 1, {'uron': 2, 'dop': 2},
     '{cena:мана}. {uron:урон}. Подношение: наложи Порчу и ещё {dop:урон}.', [U(), esli('podnoshenie', [{'porcha': 1}, U('dop')])], {'podnoshenie': 1}),
    # Р–Д
    ('m238-dolgovaya-metka', 'Долговая метка', 'Р–Д', 'атака', 0, {'uron': 2, 'dolg_n': 1},
     '{cena:мана}. {dolg_n:мана} в долг: наложи Порчу и {uron:урон}.', [{'dolg': 'dolg_n'}, {'porcha': 1}, U()], {}),
    ('m253-sglaz-v-rassrochku', 'Сглаз в рассрочку', 'Р–Д', 'связка', 0, {'dobor': 1, 'dolg_n': 1},
     '{cena:мана}. Наложи Порчу, возьми {dobor:карту}. {dolg_n:мана} в долг.', [{'porcha': 1}, {'dobor': 'dobor'}, {'dolg': 'dolg_n'}], {}),
    ('m254-dolg-proklyatogo', 'Долг проклятого', 'Р–Д', 'атака', 1, {'uron': 3},
     '{cena:мана}. {uron:урон}. Если у тебя есть долг, наложи Порчу.', [U(), esli('dolg > 0', [{'porcha': 1}])], {}),
]

PAL = [
    ('b201-mech-sveta', 'Меч света', '', 'атака', {'uron': 3}, '{uron:урон}.', [U()], {}),
    ('b202-shchit-stroya', 'Щит строя', '', 'защита', {'shchit': 3}, '{shchit:щит} союзнику.', [SH('soyuznik')], {}),
    ('b203-udar-i-stojka', 'Удар и стойка', '', 'атака', {'uron': 2, 'shchit': 1}, '{uron:урон} и {shchit:щит} себе.', [U(), SH()], {}),
    ('b204-boevoj-klich', 'Боевой клич', '', 'атака', {'uron': 2, 'dobor': 1}, '{uron:урон}. Союзник берёт {dobor:карту}.',
     [U(), {'dobor_soyuznika': 'dobor'}], {}),
    # В — вера
    ('b205-ogon-very', 'Огонь веры', 'В', 'атака', {'uron': 2, 'vera': 1}, '{uron:урон}. +{vera:вера}.', [U(), {'vera': 'vera'}], {}),
    ('b206-shchit-molitvennika', 'Щит молитвенника', 'В', 'защита', {'shchit': 3, 'vera': 1}, '{shchit:щит} себе. +{vera:вера}.', [SH(), {'vera': 'vera'}], {}),
    ('b207-karayushchaya-vera', 'Карающая вера', 'В', 'атака', {'uron': 2, 'uron_big': 5, 'doplata': 2},
     '{uron:урон}. Доплата {doplata:веру}: {uron_big:урон}.', None,
     {'varianty': [{'nazvanie': '', 'effekt': [U()]}, {'nazvanie': 'доплата', 'doplata': {'vera': 2}, 'effekt': [U('uron_big if oplacheno else uron')]}]}),
    ('b208-svyatoj-obereg', 'Святой оберег', 'В', 'защита', {'shchit': 2, 'shchit_big': 5, 'doplata': 2},
     '{shchit:щит} союзнику. Доплата {doplata:веру}: {shchit_big:щит}.', None,
     {'varianty': [{'nazvanie': '', 'effekt': [SH('soyuznik')]},
                   {'nazvanie': 'доплата', 'doplata': {'vera': 2}, 'effekt': [SH('soyuznik', 'shchit_big if oplacheno else shchit')]}]}),
    ('b209-pyl', 'Пыл', 'В', 'вера', {'vera': 2, 'uron': 1}, '+{vera:вера}. {uron:урон}.', [{'vera': 'vera'}, U()], {}),
    ('b210-vspyshka-very', 'Вспышка веры', 'В', 'атака', {'uron': 1, 'uron_big': 4, 'doplata': 1},
     '{uron:урон}. Доплата {doplata:веру}: {uron_big:урон}.', None,
     {'varianty': [{'nazvanie': '', 'effekt': [U()]}, {'nazvanie': 'доплата', 'doplata': {'vera': 1}, 'effekt': [U('uron_big if oplacheno else uron')]}]}),
    ('b211-tverdaya-vera', 'Твёрдая вера', 'В', 'защита', {'shchit': 2, 'shchit_big': 4, 'vera': 1, 'porog': 3},
     'Вера {porog}+: {shchit_big:щит} себе. Иначе {shchit:щит} себе и +{vera:вера}.',
     [esli('vera >= porog', [SH('ja', 'shchit_big')], [SH(), {'vera': 'vera'}])], {}),
    ('b212-propoved-mecha', 'Проповедь меча', 'В', 'атака', {'uron': 2, 'za': 2},
     '1 урон за каждые {za} веры, но не меньше {uron:урон}. Вера не тратится.', [U('max(uron, vera // za)')], {}),
    ('b213-blagodat', 'Благодать', 'В', 'вера', {'vera': 1, 'shchit': 2}, '+{vera:вера}. {shchit:щит} союзнику.', [{'vera': 'vera'}, SH('soyuznik')], {}),
    ('b214-obet-sily', 'Обет силы', 'В', 'атака', {'uron': 1, 'uron_big': 3, 'shchit': 1, 'vera': 1, 'doplata': 1},
     '{uron:урон} и +{vera:вера}. Доплата {doplata:веру}: вместо этого {uron_big:урон} и {shchit:щит} себе.', None,
     {'varianty': [{'nazvanie': '', 'effekt': [U(), {'vera': 'vera'}]},
                   {'nazvanie': 'доплата', 'doplata': {'vera': 1}, 'effekt': [U('uron_big if oplacheno else uron'), SH()]}]}),
    ('b215-krepost-duha', 'Крепость духа', 'В', 'защита', {'shchit': 2, 'uron': 2, 'porog': 4},
     '{shchit:щит} себе и союзнику. Вера {porog}+: ещё {uron:урон}.', [SH('oba'), esli('vera >= porog', [U()])], {}),
    ('b216-neistovaya-vera', 'Неистовая вера', 'В', 'атака', {'uron': 3, 'vera': 2}, '{uron:урон}. Если вера 0, +{vera:вера}.',
     [U(), esli('vera == 0', [{'vera': 'vera'}])], {}),
    ('b217-svet-v-ladonyah', 'Свет в ладонях', 'В', 'защита', {'shchit': 2, 'shchit_big': 6, 'doplata': 2},
     '{shchit:щит} союзнику. Доплата {doplata:веру}: {shchit_big:щит}.', None,
     {'varianty': [{'nazvanie': '', 'effekt': [SH('soyuznik')]},
                   {'nazvanie': 'доплата', 'doplata': {'vera': 2}, 'effekt': [SH('soyuznik', 'shchit_big if oplacheno else shchit')]}]}),
    # В–З
    ('b218-zaslon-very', 'Заслон веры', 'В–З', 'защита', {'doplata': 2}, 'Заслон союзнику. Доплата {doplata:веру}: и Заслон тебе.', None,
     {'varianty': [{'nazvanie': '', 'effekt': [{'zaslon': {'komu': 'soyuznik'}}]},
                   {'nazvanie': 'доплата', 'doplata': {'vera': 2}, 'effekt': [{'zaslon': {'komu': 'soyuznik'}}, esli('oplacheno', [{'zaslon': {'komu': 'ja'}}])]}]}),
    # З — Заслон
    ('b219-zaslon-i-shchit', 'Заслон и щит', 'З', 'защита', {'shchit': 2}, 'Заслон союзнику. {shchit:щит} себе.', [{'zaslon': {'komu': 'soyuznik'}}, SH()], {}),
    ('b220-karayushchij-zaslon', 'Карающий заслон', 'З', 'атака', {'uron': 2, 'shchit': 2}, '{uron:урон}. Если на союзнике Заслон, {shchit:щит} ему.',
     [U(), esli('soyuznik_zaslon', [SH('soyuznik')])], {}),
    ('b221-pod-zashchitoj', 'Под защитой', 'З', 'защита', {'uron': 2}, 'Заслон союзнику. Если на тебе Авангард, {uron:урон}.',
     [{'zaslon': {'komu': 'soyuznik'}}, esli('ja_avangard', [U()])], {}),
    ('b222-stena', 'Стена', 'З', 'защита', {'shchit': 3, 'dop': 2}, 'Авангард. {shchit:щит} себе. Если на союзнике Заслон, ещё {dop:щит}.',
     [{'avangard': 'ja'}, SH('ja', 'shchit + (dop if soyuznik_zaslon else 0)')], {}),
    # М — Молитва
    ('b223-molitva-mecha', 'Молитва меча', 'М', 'молитва', {'uron': 2}, '{uron:урон}. Молитва.', [U(), {'molitva': None}], {'bot': {'poryadok': 4, 'cennost': 5, 'pereplan': True}}),
    ('b224-molitva-shchita', 'Молитва щита', 'М', 'молитва', {'shchit': 2}, '{shchit:щит} союзнику. Молитва.', [SH('soyuznik'), {'molitva': None}], {'bot': {'poryadok': 4, 'cennost': 5, 'pereplan': True}}),
    ('b225-pesn', 'Песнь', 'М', 'молитва', {'uron': 1}, 'Молитва. {uron:урон}.', [{'molitva': None}, U()], {'bot': {'poryadok': 4, 'cennost': 5, 'pereplan': True}}),
    ('b226-udar-molyashchegosya', 'Удар молящегося', 'М', 'атака', {'uron': 3, 'dop': 2}, '{uron:урон}. Если эта карта сыграна Молитвой, ещё {dop:урон}.',
     [U('uron + (dop if sygrana_molitvoj else 0)')], {}),
    ('b227-shchit-molyashchegosya', 'Щит молящегося', 'М', 'защита', {'shchit': 3}, '{shchit:щит} себе. Если эта карта сыграна Молитвой, и союзнику {shchit:щит}.',
     [SH(), esli('sygrana_molitvoj', [SH('soyuznik')])], {}),
    ('b228-blagaya-molitva', 'Благая молитва', 'М', 'молитва', {'dobor': 1}, 'Возьми {dobor:карту}. Молитва.', [{'dobor': 'dobor'}, {'molitva': None}], {'bot': {'poryadok': 4, 'cennost': 5, 'pereplan': True}}),
    ('b229-stih', 'Стих', 'М', 'атака', {'uron': 2, 'shchit': 1, 'vera': 1}, '{uron:урон} и {shchit:щит} себе. Если эта карта сыграна Молитвой, +{vera:вера}.',
     [U(), SH(), esli('sygrana_molitvoj', [{'vera': 'vera'}])], {}),
    # М–В
    ('b230-molitva-o-sile', 'Молитва о силе', 'М–В', 'молитва', {'vera': 1, 'uron': 2, 'porog': 4}, '+{vera:вера}. Молитва. Вера {porog}+: ещё {uron:урон}.',
     [{'vera': 'vera'}, {'molitva': None}, esli('vera >= porog', [U()])], {'bot': {'poryadok': 4, 'cennost': 5, 'pereplan': True}}),
    ('b231-chudo-molitvy', 'Чудо молитвы', 'М–В', 'молитва', {'uron': 1, 'doplata': 2}, '{uron:урон}. Доплата {doplata:веру}: вместо этого Молитва дважды.', None,
     {'varianty': [{'nazvanie': '', 'effekt': [U()]},
                   {'nazvanie': 'доплата', 'doplata': {'vera': 2}, 'effekt': [esli('oplacheno', [{'molitva': None}, {'molitva': None}], [U()])]}],
      'bot': {'poryadok': 4, 'cennost': 5, 'pereplan': True}}),
]


def granicy(ch, cena=None):
    g = {}
    for k, v in ch.items():
        g[k] = [0, max(6, v + 3)] if not k.startswith(('porog', 'za', 'doplata', 'dolg')) else [1, max(6, v + 2)]
    if cena is not None:
        g['cena'] = [0, 3]
    return g


def card(hero, folder, row, mag):
    if mag:
        cid, imya, bild, vid, cena, ch, tekst, eff, extra = row
    else:
        cid, imya, bild, vid, ch, tekst, eff, extra = row; cena = None
    d = dict(id=cid, imya=imya, geroj=hero, nabor='bank', bild=bild, vid=vid, nomer_idei=int(cid[1:4]))
    if mag:
        d['cena'] = cena
    if extra.get('podnoshenie'):
        d['podnoshenie'] = 1
    d['chisla'] = dict(ch)
    d['tekst'] = tekst if not mag else tekst
    if eff is not None:
        d['effekt'] = eff
    if extra.get('varianty'):
        d['varianty'] = extra['varianty']
    d['bot'] = extra.get('bot') or {'poryadok': 3 if mag else 4, 'cennost': 5}
    d['granicy'] = granicy(ch, cena)
    d['status'] = 'ideya'
    d['istoriya'] = [IST]
    return os.path.join(ROOT, 'heroes', folder, 'karty', 'bank', f'{cid}.yaml'), d


def main():
    zam = '--zamenit' in sys.argv; n = 0
    for hero, folder, rows, mag in (('mag', 'mag', MAG, True), ('zhrec', 'paladin', PAL, False)):
        for row in rows:
            path, d = card(hero, folder, row, mag)
            if os.path.exists(path) and not zam:
                continue
            open(path, 'w', encoding='utf-8').write(dump(d, '# Новая карта банка 2026-10-26 (stend/bank_novye_2026_10_26.py)\n'))
            n += 1
    print(f'записано карт: {n} (маг {len(MAG)}, Паладин {len(PAL)} в списке)')


if __name__ == '__main__':
    main()
