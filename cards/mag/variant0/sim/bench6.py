import json, sys
from collections import defaultdict
r = json.load(open(sys.argv[1])); V = {v['label']: v for v in json.load(open(sys.argv[2]))}
d = defaultdict(list)
for x in r:
    if 'error' in x: print('ERR', x); continue
    d[(x['v'], x['sit'])].append(x)
for k in sorted(d):
    L = d[k]; hp = V[k[0]].get('CFG', {}).get('hp', {'M': 16, 'P': 18}); H = hp['M'] + hp['P']
    t = sum(x['taken'] for x in L) / len(L)
    print(k, 'раундов', round(sum(x['rounds'] for x in L) / len(L), 2), 'потери %', round(100 * t / H), 'победы', round(sum(x['won'] for x in L) / len(L), 2), 'зависло', sum(x.get('stuck', 0) for x in L))
