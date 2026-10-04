# -*- coding: utf-8 -*-
"""Безопасные выражения в картах: числа, имена, + - * // %, сравнения, and/or/not,
условие «a if b else c» и функции min, max, abs, int.

Имена ищутся по очереди: локальные переменные эффекта (например, «szhzheno»), числа карты
(раздел «chisla»), затем переменные состояния боя (см. engine/fight.py, Fight.var)."""
import ast

FUNCS = {'min': min, 'max': max, 'abs': abs, 'int': int}
_ALLOWED = (ast.Expression, ast.BinOp, ast.UnaryOp, ast.BoolOp, ast.Compare, ast.IfExp, ast.Call,
            ast.Name, ast.Load, ast.Constant, ast.Add, ast.Sub, ast.Mult, ast.FloorDiv, ast.Mod, ast.Div,
            ast.USub, ast.UAdd, ast.Not, ast.And, ast.Or, ast.Eq, ast.NotEq, ast.Lt, ast.LtE, ast.Gt, ast.GtE)


class ExprError(ValueError):
    pass


def compile_expr(src, where=''):
    """Возвращает (fn(lookup) -> значение, множество имён). Число возвращается как есть."""
    if isinstance(src, bool):
        v = int(src)
        return (lambda look: v), set()
    if isinstance(src, (int, float)):
        return (lambda look: src), set()
    if not isinstance(src, str):
        raise ExprError(f'{where}: ожидалось число или выражение, получено {src!r}')
    try:
        tree = ast.parse(src.strip(), mode='eval')
    except SyntaxError as e:
        raise ExprError(f'{where}: ошибка в выражении «{src}»: {e.msg}')
    names = set()
    for node in ast.walk(tree):
        if not isinstance(node, _ALLOWED):
            raise ExprError(f'{where}: в выражении «{src}» нельзя использовать {type(node).__name__}')
        if isinstance(node, ast.Call):
            if not isinstance(node.func, ast.Name) or node.func.id not in FUNCS or node.keywords:
                raise ExprError(f'{where}: в выражении «{src}» разрешены только функции {sorted(FUNCS)}')
        elif isinstance(node, ast.Name) and node.id not in FUNCS:
            names.add(node.id)
    code = compile(tree, f'<{where}>', 'eval')

    def fn(look):
        env = dict(FUNCS)
        for n in names:
            env[n] = look(n)
        v = eval(code, {'__builtins__': {}}, env)
        if isinstance(v, bool):
            return int(v)
        if isinstance(v, float) and v.is_integer():
            return int(v)
        return v
    return fn, names
