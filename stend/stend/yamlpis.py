# -*- coding: utf-8 -*-
"""Запись YAML-файлов игры в том же стиле, в каком они лежат (короткие словари в строку, chisla столбиком),
чтобы правки стенда давали маленький и читаемый diff."""
import yaml

BLOCK = {'chisla'}


class _D(yaml.SafeDumper):
    pass


def _scalar(v):
    return not isinstance(v, (dict, list)) or (isinstance(v, list) and all(not isinstance(x, (dict, list)) for x in v))


class _Flow(dict):
    pass


def _flowable(v):
    return _scalar(v) or isinstance(v, _Flow)


def _mark(x, depth=0, key=None, in_list=False):
    if isinstance(x, dict):
        y = {k: _mark(v, depth + 1, k) for k, v in x.items()}
        if depth >= 1 and key not in BLOCK and y and all(_scalar(v) for v in x.values()):
            return _Flow(y)
        if in_list and len(y) == 1 and all(_flowable(v) for v in y.values()):
            return _Flow(y)
        return y
    if isinstance(x, list):
        return [_mark(v, depth + 1, None, True) for v in x]
    return x


_D.add_representer(_Flow, lambda d, v: d.represent_mapping('tag:yaml.org,2002:map', v.items(), flow_style=True))


def dump(d, head=''):
    txt = yaml.dump(_mark(d), Dumper=_D, allow_unicode=True, sort_keys=False, width=140)
    return head + txt


def leading_comments(text):
    out = []
    for line in text.splitlines(True):
        if line.startswith('#'):
            out.append(line)
        else:
            break
    return ''.join(out)


def rewrite(path, fn):
    """Прочитать файл, изменить данные функцией fn(d) и записать обратно, сохранив комментарии в начале."""
    with open(path, encoding='utf-8') as f:
        text = f.read()
    d = yaml.safe_load(text)
    fn(d)
    with open(path, 'w', encoding='utf-8') as f:
        f.write(dump(d, leading_comments(text)))


def set_scalar(path, keys, value):
    """Поменять одно число в файле, не трогая остальной текст и комментарии.
    keys: путь до числа, например ['zdorove'] или ['chisla', 'uron']. Возвращает старое значение.
    Если путь глубже (например, удар в намерении), файл переписывается целиком через rewrite."""
    import re
    with open(path, encoding='utf-8') as f:
        lines = f.read().splitlines(True)
    d = yaml.safe_load(''.join(lines))
    node = d
    for k in keys[:-1]:
        node = node[k]
    old = node[keys[-1]]
    if len(keys) <= 2 and all(isinstance(k, str) for k in keys):
        indent = 0; start = 0
        if len(keys) == 2:
            start = next((i for i, l in enumerate(lines) if re.match(rf'^{re.escape(keys[0])}:\s*(#.*)?$', l)), None)
            if start is None:
                start = -1
            indent = 2; start += 1
        if start >= 0:
            pat = re.compile(rf'^(\s{{{indent}}}{re.escape(keys[-1])}:\s*)([^#\n]+?)(\s*(#.*)?)$')
            for i in range(start, len(lines)):
                m = pat.match(lines[i].rstrip('\n'))
                if m and yaml.safe_load(m.group(2)) == old:
                    lines[i] = m.group(1) + yaml.safe_dump(value).split('\n')[0] + m.group(3) + '\n'
                    with open(path, 'w', encoding='utf-8') as f:
                        f.write(''.join(lines))
                    return old
                if indent and lines[i].strip() and not lines[i].startswith(' ') and i > start:
                    break
    def fn(dd):
        n = dd
        for k in keys[:-1]:
            n = n[k]
        n[keys[-1]] = value
    rewrite(path, fn)
    return old
