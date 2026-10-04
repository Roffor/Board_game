---
name: lokalnaya-rabota
description: Как устроена локальная работа с 2026-10-02: один git-репозиторий, общие правила для Cursor и Claude Code, команды-скиллы, сервер открывает папку stend/
metadata:
  type: project
---

2026-10-02 проект перенесён из облачного проекта Claude на локальную машину Никиты.
- Один git-репозиторий: дизайн (`design/`, `cards/`, `playtest/`…) и стенд (`stend/`). Сервер Никиты открывает в Cursor только `stend/` (правила исполнителя — `stend/AGENTS.md`, скилл `progon-plana`).
- Общий источник правил: `AGENTS.md` (Cursor читает сам, Claude Code через `CLAUDE.md` с `@AGENTS.md`), подробности в `pravila/`, состояние в `STATUS.md`, память в `pamyat/`.
- Команды — скиллы в `.claude/skills/` (их видят и Cursor, и Claude Code), субагенты `kritik`, `nastolshchik`, `balansirovshchik` в `.claude/agents/`, правила Cursor с привязкой к папкам в `.cursor/rules/`.
- `stend/runs/*/boi.jsonl` убран из git (≈1,3 КБ на бой, на сервере сотни МБ за ночь, лимит GitHub 100 МБ на файл).
- Стенд умеет работать кусками: `python run.py plans/<план>.yaml --minut 9` (код 3 — пауза, та же команда продолжит, код 0 — готово). Так присмотр раз в 10 минут работает и в Cursor, и в Claude Code, и на сервере.
- Сырые результаты старых прогонов — отдельным архивом в `syrye-dannye/`, вне git.

**Why:** Никита хочет тратить сильную модель на дизайн и анализ, а прогоны отдать серверу; облачный проект как среда больше не основной.
**How to apply:** новые решения и правила записывать в `pamyat/` и `pravila/`, состояние — в `STATUS.md` через `/itog`. См. [[shema-raboty-stend]], [[stil-obshcheniya]].
