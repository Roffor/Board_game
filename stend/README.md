# Стенд тестов «Двое во тьме»

Игра как данные (`game/`), движок правил (`engine/`), стенд с ботом и запуском планов (`stend/`). Агенту — [AGENTS.md](AGENTS.md).

```
pip install -r requirements.txt
python run.py proverka                    # данные и тесты движка
python run.py plans/primer-dym.yaml       # пример плана на 10 минут
python run.py boj II 5                    # один бой с журналом
```

Три части правятся независимо:
- `game/` — YAML: по файлу на карту, врага, комнату; `pravila.yaml` — общие числа; `soglashenie.yaml` — пороги соглашения по балансу.
- `engine/` — правила боя. Ничего не знает о тестах. Версии `API_VERSION` и `RULES_VERSION` в `engine/__init__.py`. Свои проверки: `engine/tests/test_karty.py` (каждая карта во всех вариантах) и `engine/tests/test_zolotye.py` (эталонные бои на замороженной копии данных `engine/tests/igra/`; ломаются только от правок кода правил).
- `stend/` — бот (перенос бота старого симулятора), колоды и ситуации [С 8.7], метрики и сила карт [С 8.8–8.9], запуск по плану волнами с чекпоинтами, подбор чисел, отчёты.

Результаты прогона — `runs/<план>/`: `boi.jsonl` (по строке на бой, это же чекпоинт), `zhurnal.md`, `progress.md`, `otchet-<фаза>.md`, `itog.md`.

## Карта

```yaml
id: rok
imya: Рок
geroj: mag
nabor: apgrejd          # start / apgrejd / zapas (банк) / zheton / etalon / otkaz
bild: П
vid: связка
cena: 1
chisla: {porcha: 2, mnozhitel: 4}
tekst: '{cena:мана}. {porcha:Порча}. Затем, если Порча ×{mnozhitel} не меньше здоровья врага, враг погибает.'
effekt:
- {osobyj: {imya: rok, porcha: porcha, mnozhitel: mnozhitel}}
zamenyaet: porcha-karta # какую стартовую карту заменяет апгрейд
bot: {poryadok: 4.7, cennost: 6}
granicy: {porcha: [0, 4], mnozhitel: [2, 6], cena: [0, 2]}
status: v_teste
istoriya: [...]
```

Текст собирается из чисел, поэтому не расходится с поведением. Эффекты — из общего словаря (`engine/effects.py`), уникальные механики — именованные обработчики `osobyj` (`engine/special.py`).
