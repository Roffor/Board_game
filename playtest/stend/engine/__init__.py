# -*- coding: utf-8 -*-
"""Движок «Двое во тьме». Отделён от стенда: стенд пользуется только тем, что здесь перечислено.

API_VERSION меняется, когда меняется интерфейс движка (что стенд вызывает и что получает).
RULES_VERSION меняется, когда меняется поведение правил так, что результаты боёв сдвигаются;
эталонные бои (engine/tests/zolotye.json) при этом перезаписываются осознанно, с записью в журнал."""
from .data import Game, CardDef, CardInst, DataError, render, plural
from .fight import Fight
from .choices import Choices
from .effects import EffectError
from .expr import ExprError

API_VERSION = '1.0'
RULES_VERSION = '1.0'

__all__ = ['Game', 'Fight', 'Choices', 'CardDef', 'CardInst', 'DataError', 'EffectError', 'ExprError',
           'render', 'plural', 'API_VERSION', 'RULES_VERSION', 'load_game']


def load_game(root, pravki=None):
    """Загрузить игру из корня репозитория (правила, герои, карты, враги, локации; раскладка — data.layout) с проверкой.
    pravki — временные правки чисел без изменения файлов (см. Game)."""
    return Game(root, pravki)
