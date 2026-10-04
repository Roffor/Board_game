# Серия №11: шлифовка мага (2026-09-30)

Отчёт — [../22-shlifovka-itogovyj-otchet.md](../22-shlifovka-itogovyj-otchet.md), журнал — [../21-shlifovka-maga-hod.md](../21-shlifovka-maga-hod.md).

Запуск (из sim/, нужен Python 3.11, все ядра):
- `python3 bt12.py out.json v_s5.json --no-extra` — прогон вариантов (база + карты);
- `python3 gen_draft12.py v_draft.json 120 3 p_armor.json` — драфт-колоды и чистые билды;
- `python3 rep12.py out.json [out2.json ...]` — сводка: раунды и потери против коридоров.

Итоговые числа — burn11.py (DEFAULTS после STEP3) и final_defaults.json. Броня рядовых II (`r2.armor` = 1) в итоговых DEFAULTS включена; в шагах 4–5 задавалась в вариантах.
Данные шагов: s1.json … s5.json, сводки sim/s*.rep.txt.
