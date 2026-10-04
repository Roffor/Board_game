#!/bin/bash
# добавить решение(я) и перезапустить
cd /mnt/project-files/playtest/run2/sim
python3 - "$@" <<'PY'
import json,sys
d=json.load(open('decisions.json'))
d['decisions']+=sys.argv[1:]
json.dump(d,open('decisions.json','w'),ensure_ascii=False)
PY
python3 run.py decisions.json; echo EXIT $?
