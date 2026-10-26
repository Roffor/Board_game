# -*- coding: utf-8 -*-
"""Учитель бота (этап 1 подгонки 2026-10-25): подбор весов оценки плана (раздел bot в design/03) так,
чтобы бот играл лучше — бои короче, потери меньше, побед больше. Игру не меняет: только то, как бот выбирает план.

  python run.py uchitel plans/<конфиг>.yaml [--yader N]

Один запуск = один проход: для каждого веса пробуем ×(1 − shag) и ×(1 + shag) (для нулевого — ±shag_nol),
на одних и тех же сидах, что и текущие веса. Лучший кандидат по каждому весу принимается, если он лучше
текущих больше чем на порог шума. Найденные веса записываются в design/03 (раздел bot) и в zhurnal.md.
Цель J (меньше — лучше): по ситуациям среднее (раунды + потери пары в ХП / 8 + 10 за поражение),
делённое на то же у текущих весов, затем среднее по ситуациям."""
import json, os, time
from multiprocessing import Pool

import yaml
import engine
from . import worker, metrics as M
from .yamlpis import set_scalar

DEFAULT = dict(vesa=['ves_ubijstva', 'ves_zaslona', 'ves_very', 'ves_ruki', 'ves_sozhzhennoj', 'ves_podnosheniya', 'ves_dolga',
                     'ocenka_molitvy', 'ocenka_obeta'],
               boev={'I': 400, 'II': 1200, 'EL': 1200, 'BOSS': 1200}, shag=0.5, shag_nol=1.0, porog=0.01, seed0=777001,
               tajmaut=30)


def now():
    return time.strftime('%Y-%m-%d %H:%M:%S')


class Uchitel:
    def __init__(self, cfg_path, game_dir, runs_dir, procs=None):
        c = yaml.safe_load(open(cfg_path, encoding='utf-8')) or {}
        self.cfg = dict(DEFAULT); self.cfg.update(c)
        self.game_dir = game_dir
        self.name = os.path.splitext(os.path.basename(cfg_path))[0]
        self.dir = os.path.join(runs_dir, self.name); os.makedirs(self.dir, exist_ok=True)
        self.procs = procs or os.cpu_count()
        self.f_state = os.path.join(self.dir, 'sostoyanie.json')
        self.st = json.load(open(self.f_state, encoding='utf-8')) if os.path.exists(self.f_state) else dict(prohod=0, istoriya=[])

    def log(self, s):
        with open(os.path.join(self.dir, 'zhurnal.md'), 'a', encoding='utf-8') as f:
            f.write(f'- {now()} {s}\n')
        print(f'- {now()} {s}', flush=True)

    def variant(self, g, metka, pravki):
        geroi = {}
        for h in g.heroes:
            start = [c.cid for c in g.start_deck(h)]
            pul = [c.cid for c in g.hero_cards(h, {'bank'}) if c.status != 'ubrana' and c.cid not in start]
            geroi[h] = dict(apgrejdy='sluchajno', pul=pul, obyazatelno=[], start=start)
        return dict(metka=metka, geroi=geroi, pravki=pravki)

    def J(self, rows_by_v, base):
        def per_sit(rows):
            out = {}
            for s, rr in M.by(M.ok_rows(rows), 'sit').items():
                out[s] = M.mean(r['rounds'] + r['taken'] / 8.0 + (0 if r['won'] else 10) for r in rr)
            return out
        b = per_sit(rows_by_v[base])
        res = {}
        for v, rows in rows_by_v.items():
            p = per_sit(rows)
            res[v] = M.mean(p[s] / b[s] for s in b if s in p)
        return res

    def run(self):
        g = engine.load_game(self.game_dir)
        W = g.rules['bot']; cur = {k: W.get(k, 0.0) for k in self.cfg['vesa']}
        cands = {'tekushchie': {}}
        for k in self.cfg['vesa']:
            v = cur[k]
            vals = [round(v * (1 - self.cfg['shag']), 3), round(v * (1 + self.cfg['shag']), 3)] if v else [self.cfg['shag_nol'], -self.cfg['shag_nol']]
            for x in vals:
                cands[f'{k}={x}'] = {f'pravila.bot.{k}': x}
        p = self.st['prohod'] + 1
        jobs = []
        for name, pr in cands.items():
            v = self.variant(g, name, pr)
            for s, n in self.cfg['boev'].items():
                for i in range(n):
                    jobs.append(dict(faza=f'prohod-{p}', volna=p, v=v, sit=s, i=p * 100000 + i, seed0=self.cfg['seed0']))
        self.log(f'проход {p}: кандидатов {len(cands)}, боёв {len(jobs)}, веса {cur}')
        t0 = time.time(); rows = {n: [] for n in cands}
        with Pool(self.procs, initializer=worker.init, initargs=(self.game_dir, self.cfg['tajmaut'])) as pool:
            for r in pool.imap_unordered(worker.one, jobs, chunksize=8):
                rows[r['v']].append(r)
        J = self.J(rows, 'tekushchie')
        nerr = sum('error' in r for rr in rows.values() for r in rr)
        lines = sorted(J.items(), key=lambda kv: kv[1])
        self.log(f'проход {p} за {(time.time() - t0) / 60:.1f} мин, ошибок {nerr}. J (меньше — лучше, текущие = 1): '
                 + ', '.join(f'{n} {j:.3f}' for n, j in lines))
        new = dict(cur); ch = []
        for k in self.cfg['vesa']:
            best = min(((J[n], n) for n in cands if n.startswith(k + '=')), default=None)
            if best and best[0] < 1 - self.cfg['porog']:
                val = float(best[1].split('=')[1]); new[k] = val; ch.append(f'{k}: {cur[k]} → {val} (J {best[0]:.3f})')
        path = g.rules_path
        for k, val in new.items():
            if val != cur[k]:
                set_scalar(path, ['bot', k], val)
        # итог: сравнение всех принятых вместе с текущими на новых сидах
        summ = {n: M.summary(rows[n], {'raundy': {}, 'poteri_pary_proc': {}}) for n in ('tekushchie',)}
        d = summ['tekushchie']
        self.log(f'проход {p}: принято {len(ch)}: ' + ('; '.join(ch) if ch else 'ничего') + '. Текущие веса на этих боях: '
                 + ' | '.join(f'{s} {x["rounds"]:.2f} р / {x["loss"]:.1f}% / {100 * x["won"]:.0f}%' for s, x in d.items()))
        self.st['prohod'] = p; self.st['istoriya'].append(dict(prohod=p, vesa=new, prinyato=ch))
        json.dump(self.st, open(self.f_state, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
        return ch
