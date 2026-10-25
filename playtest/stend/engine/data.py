import copy
# -*- coding: utf-8 -*-
"""Загрузка данных игры: правила, герои, карты, враги, локации.

Где лежат файлы (с 2026-10-04, относительно корня репозитория): общие числа правил и пороги
соглашения — рядом с дизайн-документами в design/; герой — heroes/<герой>/geroj.yaml, его карты —
karty/osnovnye/ (колода) и karty/zapas/ (в коробку не идут); враги и комнаты — dungeons/<подземелье>/;
эталоны силы нужны только тестам и лежат в playtest/stend/etalon/<id героя>/.
Копия данных для золотых тестов движка (engine/tests/igra) осталась в старой раскладке одной папки game/,
поэтому раскладка определяется по наличию pravila.yaml в корне.

Карта — один YAML-файл. Поля карты:
  id, imya, geroj, nabor (start / apgrejd / zapas / zheton / bank — банк идей / legendarka — пассивка), bild, vid, kopij (для стартовых),
  cena (мана мага), podnoshenie (1 / 2 / r), chisla, tekst, effekt или varianty, pri_szhiganii,
  metki, zamenyaet (какую стартовую карту заменяет апгрейд), bot (подсказки бота), granicy, status, istoriya.
Текст карты собирается из чисел: «{uron:урон}» даёт «3 урона», «{cena}» — цену."""
import os, glob
import yaml
from .expr import compile_expr, ExprError
from . import effects

VIDY = {'атака', 'защита', 'связка', 'топливо', 'двигатель', 'визитка', 'вера', 'молитва'}
NABORY = {'start', 'apgrejd', 'zapas', 'zheton', 'etalon', 'otkaz', 'bank', 'legendarka'}


class DataError(ValueError):
    pass


# ---------------------------------------------------------------- русские числа для текста карты
FORMS = {
    'урон': ('урон', 'урона', 'урона'),
    'щит': ('щит', 'щита', 'щитов'),
    'Порча': ('Порча', 'Порчи', 'Порчи'),
    'Порчу': ('Порчу', 'Порчи', 'Порчи'),
    'вера': ('вера', 'веры', 'веры'),
    'веру': ('веру', 'веры', 'веры'),
    'мана': ('мана', 'маны', 'маны'),
    'карта': ('карта', 'карты', 'карт'),
    'карту': ('карту', 'карты', 'карт'),
    'попадание': ('попадание', 'попадания', 'попаданий'),
    'заряд': ('заряд', 'заряда', 'зарядов'),
    'здоровье': ('здоровье', 'здоровья', 'здоровья'),
    'раз': ('раз', 'раза', 'раз'),
    'Осколок': ('Осколок', 'Осколка', 'Осколков'),
}


def plural(n, word):
    f = FORMS.get(word)
    if f is None:
        return f'{n} {word}'
    n = int(n)
    a = abs(n) % 100
    if 11 <= a <= 14:
        w = f[2]
    elif a % 10 == 1:
        w = f[0]
    elif a % 10 in (2, 3, 4):
        w = f[1]
    else:
        w = f[2]
    if n == 0 and word in ('мана',):
        w = 'маны'
    return f'{n} {w}'


def render(template, values):
    """«{x}» → число, «{x:урон}» → «3 урона»."""
    out = []; i = 0
    while i < len(template):
        j = template.find('{', i)
        if j < 0:
            out.append(template[i:]); break
        out.append(template[i:j])
        k = template.find('}', j)
        if k < 0:
            raise DataError(f'незакрытая скобка в тексте «{template}»')
        key = template[j + 1:k]
        name, _, word = key.partition(':')
        if name not in values:
            raise DataError(f'в тексте «{template}» нет числа «{name}» (есть: {sorted(values)})')
        v = values[name]
        out.append(plural(v, word) if word else str(v))
        i = k + 1
    return ''.join(out)


# ---------------------------------------------------------------- карта
class Variant:
    __slots__ = ('name', 'effect', 'pay_faith', 'pay_mana', 'has_dmg', 'has_shield')

    def __init__(self, name, effect, pay_faith=0, pay_mana=0, has_dmg=False, has_shield=False):
        self.name = name; self.effect = effect; self.pay_faith = pay_faith; self.pay_mana = pay_mana
        self.has_dmg = has_dmg; self.has_shield = has_shield


class CardDef:
    """Неизменяемое описание карты. Экземпляры в колоде — CardInst."""

    def __init__(self, d, path=''):
        self.raw = d; self.path = path
        try:
            self.cid = d['id']; self.name = d['imya']; self.hero = d['geroj']
        except KeyError as e:
            raise DataError(f'{path}: нет обязательного поля {e}')
        w = f'{path} ({self.cid})'
        self.set = d.get('nabor', 'apgrejd')
        if self.set not in NABORY:
            raise DataError(f'{w}: nabor должен быть одним из {sorted(NABORY)}')
        self.build = d.get('bild', '')
        self.kind = d.get('vid', 'связка')
        if self.kind not in VIDY:
            raise DataError(f'{w}: vid «{self.kind}» не из {sorted(VIDY)}')
        self.copies = int(d.get('kopij', 1))
        self.numbers = dict(d.get('chisla') or {})
        for k, v in self.numbers.items():
            if not isinstance(v, (int, float)):
                raise DataError(f'{w}: число «{k}» должно быть числом, а не {v!r}')
        self.cost = int(self._num(d.get('cena', 0), w, 'cena'))
        # новые правила мага (2026-10-24): цена выражением и разрешение играть в долг
        self.cost_expr = effects.X(d['cena_vyrazhenie'], w) if 'cena_vyrazhenie' in d else None
        self.cond_expr = effects.X(d['uslovie'], w) if 'uslovie' in d else None   # когда карту вообще можно сыграть
        dv = d.get('v_dolg')
        self.debt_expr = None if dv in (None, False, 0) else effects.X(1 if dv is True else dv, w)
        off = d.get('podnoshenie')
        self.offering = None if off in (None, 0, '0') else str(off)
        if self.offering not in (None, '1', '2', 'r'):
            raise DataError(f'{w}: podnoshenie — 1, 2 или r')
        self.tags = set(d.get('metki') or [])
        self.replaces = d.get('zamenyaet')
        bot = d.get('bot') or {}
        self.order = float(bot.get('poryadok', 3))
        self.value = float(bot.get('cennost', 5))
        self.replan = bool(bot.get('pereplan', False))
        self.bot = bot
        self.bounds = d.get('granicy') or {}
        self.status = d.get('status', '')
        self.fuel = d.get('pri_szhiganii') is not None
        # эффекты
        if 'varianty' in d and 'effekt' in d:
            raise DataError(f'{w}: нужно что-то одно — effekt или varianty')
        self.passive = None
        if self.set == 'legendarka':       # легендарка: пассивка рядом с планшетом, правило в fight.py по имени
            self.passive = (d.get('passiv') or {}).get('imya')
            if not self.passive:
                raise DataError(f'{w}: у легендарки нужен passiv: {{imya: ...}}')
        if 'varianty' in d:
            vs = d['varianty']
        elif self.set == 'legendarka':
            vs = []
        else:
            vs = [{'nazvanie': '', 'effekt': d.get('effekt') or []}]
        self.variants = []
        for i, v in enumerate(vs):
            vw = f'{w}, вариант {i + 1}'
            eff, info = effects.compile_block(v.get('effekt') or [], vw)
            pay = v.get('doplata') or {}
            self.variants.append(Variant(v.get('nazvanie', ''), eff, int(pay.get('vera', 0)), int(pay.get('mana', 0)),
                                         info['dmg'], info['shield']))
        self.on_burn = None
        if d.get('pri_szhiganii') is not None:
            self.on_burn, info = effects.compile_block(d['pri_szhiganii'], f'{w}, pri_szhiganii')
        self.has_dmg = any(v.has_dmg for v in self.variants)
        self.has_shield = any(v.has_shield for v in self.variants)
        tpl = d.get('tekst', '')
        self.text = render(tpl, dict(self.numbers, cena=self.cost)) if tpl else ''
        self.check_bounds(w)

    def _num(self, v, w, field):
        if isinstance(v, (int, float)):
            return v
        if isinstance(v, str) and v in self.numbers:
            return self.numbers[v]
        raise DataError(f'{w}: поле {field} должно быть числом или именем из chisla')

    def check_bounds(self, w):
        for k, b in self.bounds.items():
            if k not in self.numbers and k != 'cena':
                raise DataError(f'{w}: граница для «{k}», но такого числа нет в chisla')
            v = self.cost if k == 'cena' else self.numbers[k]
            if not (isinstance(b, list) and len(b) == 2 and b[0] <= v <= b[1]):
                raise DataError(f'{w}: число «{k}» = {v} вне своих границ {b}')

    def __repr__(self):
        return self.name


class CardInst:
    """Конкретная карта в колоде (у двух копий — два разных объекта)."""
    __slots__ = ('d', 'owner')

    def __init__(self, d, owner):
        self.d = d; self.owner = owner

    @property
    def cid(self): return self.d.cid
    @property
    def name(self): return self.d.name
    @property
    def kind(self): return self.d.kind
    @property
    def cost(self): return self.d.cost
    @property
    def value(self): return self.d.value
    @property
    def tags(self): return self.d.tags

    def __repr__(self):
        return self.d.name


# ---------------------------------------------------------------- враги и локации
TARGETS = {'odin': 'single', 'vse': 'all', 'ranenyj': 'weakest', 'bez_shchita': 'unshielded', 'motylek': 'moth'}


TG_TEXT = {'single': '', 'all': ' по всем', 'weakest': ' по самому раненому', 'unshielded': ' по незащищённому',
           'moth': ' (мотылёк)'}


def intent_text(acts):
    out = []
    for a in acts:
        if a[0] == 'atk':
            out.append(f'удар {a[1]}' + (f'×{a[3]}' if a[3] > 1 else '') + TG_TEXT[a[2]])
        elif a[0] == 'shield':
            out.append(f'щит {a[1]}')
        elif a[0] == 'buff':
            out.append(f'усиление +{a[1]}')
        elif a[0] == 'heal':
            out.append(f'лечится {a[1]}')
        elif a[0] == 'oil':
            out.append(f'кража: −{a[1]} масла')
    s = ', '.join(out)
    return s[:1].upper() + s[1:]


class EnemyDef:
    def __init__(self, d, path=''):
        w = f'{path} ({d.get("id")})'
        try:
            self.eid = d['id']; self.name = d['imya']; self.tier = d['yarus']; self.hp = int(d['zdorove'])
        except KeyError as e:
            raise DataError(f'{w}: нет обязательного поля {e}')
        self.shield0 = int(d.get('shchit_na_starte', 0))
        self.traits = {}
        for k, v in (d.get('svojstva') or {}).items():
            key = {'tma': 'dark', 'motylek': 'moth', 'golem': 'golem', 'skrytyj': 'hidden', 'bronya': 'armor',
                   'pancir': 'regen'}.get(k)
            if key is None:
                raise DataError(f'{w}: неизвестное свойство «{k}»')
            self.traits[key] = v
        self.mode = d.get('rezhim', 'cikl')
        if self.mode not in ('cikl', 'koloda'):
            raise DataError(f'{w}: rezhim — cikl или koloda')
        self.intents = []
        for it in d['namereniya']:
            acts = []
            for a in it['dejstviya']:
                if 'ataka' in a:
                    tg = TARGETS.get(a.get('cel', 'odin'))
                    if tg is None:
                        raise DataError(f'{w}: цель атаки «{a.get("cel")}» не из {sorted(TARGETS)}')
                    acts.append(('atk', int(a['ataka']), tg, int(a.get('raz', 1))))
                elif 'shchit' in a:
                    acts.append(('shield', int(a['shchit'])))
                elif 'usilenie' in a:
                    acts.append(('buff', int(a['usilenie'])))
                elif 'lechenie' in a:
                    acts.append(('heal', int(a['lechenie'])))
                elif 'kradet_maslo' in a:
                    acts.append(('oil', int(a['kradet_maslo'])))
                else:
                    raise DataError(f'{w}: неизвестное действие врага {a}')
            self.intents.append({'type': it['tip'], 'acts': acts, 'text': it.get('tekst') or intent_text(acts)})
        seq = self.intents
        self.threat = sum(sum(a[1] * a[3] * (2 if a[2] == 'all' else 1) for a in i['acts'] if a[0] == 'atk')
                          for i in seq) / len(seq)


class LocationDef:
    KINDS = {'sbros': 'discard', 'dvojnaya': 'double', 'passiv': 'passive', 'opasnost_nachalo': 'hazard_start',
             'opasnost_konec': 'hazard_end', 'uslovie': 'cond'}
    FEATS = {'altar', 'bones', 'pillar', 'sealheal', 'draftshield', 'narrow', 'drip', 'pit', 'seals', 'draft'}

    def __init__(self, d, path=''):
        self.lid = d['id']; self.name = d['imya']; self.feats = []
        for f in d.get('osobennosti') or []:
            k = self.KINDS.get(f['tip'])
            if k is None or f['kod'] not in self.FEATS:
                raise DataError(f'{path}: неизвестная особенность {f}')
            self.feats.append((k, f['kod'], f.get('tekst', '')))


# ---------------------------------------------------------------- вся игра
def layout(root):
    """Пути ко всем файлам игры от корня root (см. описание модуля)."""
    j = lambda *p: os.path.join(root, *p)
    g = lambda *p: sorted(glob.glob(j(*p)))
    if os.path.exists(j('pravila.yaml')):
        return dict(pravila=j('pravila.yaml'), soglashenie=j('soglashenie.yaml'), geroi=g('geroi', '*', 'geroj.yaml'),
                    karty=lambda hdir, hid: sorted(sum((glob.glob(os.path.join(hdir, d, '*.yaml')) for d in ('karty', 'bank', 'etalon')), [])),
                    vragi=g('vragi', '*.yaml'), lokacii=g('lokacii', '*.yaml'))
    return dict(pravila=j('design', '03-bazovye-pravila.yaml'), soglashenie=j('design', '05-soglashenie-po-balansu.yaml'),
                geroi=g('heroes', '*', 'geroj.yaml'),
                karty=lambda hdir, hid: sorted(glob.glob(os.path.join(hdir, 'karty', 'osnovnye', '*.yaml'))
                                               + glob.glob(os.path.join(hdir, 'karty', 'zapas', '*.yaml'))
                                               + glob.glob(os.path.join(hdir, 'karty', 'bank', '*.yaml'))
                                               + glob.glob(j('playtest', 'stend', 'etalon', hid, '*.yaml'))),
                vragi=g('dungeons', '*', 'vragi', '*.yaml'), lokacii=g('dungeons', '*', 'lokacii', '*.yaml'))


class Game:
    """Все данные игры (раскладка файлов — layout())."""

    def __init__(self, root, pravki=None):
        """pravki — временные правки чисел без изменения файлов, {путь: значение}:
        «karta.<id>.<число>» (число из chisla или cena), «vrag.<id>.<поле>[.<индекс>...]», «pravila.<ключ>».
        Правки проходят те же проверки, что и файлы (в том числе границы карт)."""
        self.root = root
        self.pravki = dict(pravki or {})
        self._unused = set(self.pravki)
        lay = layout(root)
        self.rules_path = lay['pravila']
        self.soglashenie_path = lay['soglashenie']
        self.rules = self._patch('pravila', None, self._load(self.rules_path))
        self.heroes = {}
        self.cards = {}
        for hp in lay['geroi']:
            h = self._load(hp)
            self.heroes[h['id']] = h
            for cp in lay['karty'](os.path.dirname(hp), h['id']):
                raw = self._load(cp)
                c = CardDef(self._patch('karta', raw.get('id'), raw), os.path.relpath(cp, root))
                if c.cid in self.cards:
                    raise DataError(f'{cp}: id «{c.cid}» уже есть в {self.cards[c.cid].path}')
                if c.hero != h['id']:
                    raise DataError(f'{cp}: geroj «{c.hero}», а лежит в папке героя {h["id"]}')
                self.cards[c.cid] = c
        self.enemies = {}
        for ep in lay['vragi']:
            raw = self._load(ep)
            e = EnemyDef(self._patch('vrag', raw.get('id'), raw), os.path.relpath(ep, root))
            self.enemies[e.eid] = e
        self.locations = {}
        for lp in lay['lokacii']:
            l = LocationDef(self._load(lp), os.path.relpath(lp, root))
            self.locations[l.lid] = l
        self._check()
        if self._unused:
            raise DataError(f'правки не нашли, что менять: {sorted(self._unused)}')

    def _patch(self, kind, oid, raw):
        """Применить правки к сырым данным одного файла."""
        for key, val in self.pravki.items():
            parts = key.split('.')
            if parts[0] != kind:
                continue
            if kind == 'pravila':
                path = parts[1:]
            else:
                if len(parts) < 3 or parts[1] != oid:
                    continue
                path = parts[2:]
                if kind == 'karta' and path[0] not in raw and path[0] in (raw.get('chisla') or {}):
                    path = ['chisla'] + path
            raw = copy.deepcopy(raw)
            node = raw
            try:
                for p in path[:-1]:
                    node = node[int(p)] if isinstance(node, list) else node[p]
                last = int(path[-1]) if isinstance(node, list) else path[-1]
                if isinstance(node, dict) and last not in node:
                    raise KeyError(last)
                node[last] = val
            except (KeyError, IndexError, ValueError, TypeError):
                raise DataError(f'правка «{key}»: такого поля нет')
            self._unused.discard(key)
        return raw

    def _yaml(self, rel):
        return self._load(os.path.join(self.root, rel))

    @staticmethod
    def _load(path):
        with open(path, encoding='utf-8') as f:
            try:
                return yaml.safe_load(f) or {}
            except yaml.YAMLError as e:
                raise DataError(f'{path}: ошибка YAML: {e}')

    def _check(self):
        for hid, h in self.heroes.items():
            start = [c for c in self.cards.values() if c.hero == hid and c.set == 'start']
            n = sum(c.copies for c in start)
            if n != h.get('start_kart', 15):
                raise DataError(f'герой {hid}: в стартовой колоде {n} карт, нужно {h.get("start_kart", 15)}')
            for c in self.cards.values():
                if c.hero == hid and c.replaces and c.replaces not in self.cards:
                    raise DataError(f'{c.path}: zamenyaet «{c.replaces}» — такой карты нет')

    def hero_cards(self, hid, sets):
        return sorted((c for c in self.cards.values() if c.hero == hid and c.set in sets), key=lambda c: c.cid)

    def start_deck(self, hid):
        d = []
        for c in self.hero_cards(hid, {'start'}):
            d += [c] * c.copies
        return d

    def enemies_of(self, tier):
        return [e for e in sorted(self.enemies.values(), key=lambda e: e.eid) if e.tier == tier]
