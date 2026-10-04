# -*- coding: utf-8 -*-
"""Запуск плана: делит срок по фазам, гоняет бои волнами на всех ядрах, пишет чекпоинты и отчёты.

Папка прогона runs/<дата>-<название>/:
  meta.json      план, сид, версии движка, коммит, время старта
  boi.jsonl      по строке на бой (это и есть чекпоинт: перезапуск досчитывает недостающее)
  sostoyanie.json  где остановились: фаза, волна, потраченное время, найденные числа подбора
  progress.md    что идёт сейчас (обновляется раз в минуту)
  zhurnal.md     события: старт, фазы, правки файлов, ошибки
  otchet-<фаза>.md и itog.md
"""
import json, os, random, subprocess, sys, time
from multiprocessing import Pool

import yaml
import engine
from . import plan as planmod, worker, metrics as M, report
from .yamlpis import set_scalar, rewrite


class Pauza(Exception):
    """Остановка по ключу --minut: состояние сохранено, та же команда продолжит."""


def now():
    return time.strftime('%Y-%m-%d %H:%M:%S')


def git_commit(root):
    try:
        return subprocess.check_output(['git', 'rev-parse', '--short', 'HEAD'], cwd=root, stderr=subprocess.DEVNULL).decode().strip()
    except Exception:
        return 'нет git'


class Run:
    def __init__(self, repo, plan_path, game_dir='game', runs_dir='runs', procs=None, use_git=False, smoke=True, minut=None):
        self.repo = repo
        self.stop_at = time.time() + minut * 60 if minut else None
        self.game_dir = os.path.join(repo, game_dir)
        self.plan_path = plan_path
        self.game = engine.load_game(self.game_dir)
        self.plan = planmod.load(plan_path, self.game)
        with open(os.path.join(self.game_dir, 'soglashenie.yaml'), encoding='utf-8') as f:
            self.sog = yaml.safe_load(f)
        name = os.path.splitext(os.path.basename(plan_path))[0]
        self.dir = os.path.join(repo, runs_dir, name)
        os.makedirs(self.dir, exist_ok=True)
        self.procs = procs or os.cpu_count()
        self.use_git = use_git; self.smoke = smoke
        self.rows = []
        self.f_rows = os.path.join(self.dir, 'boi.jsonl')
        self.f_state = os.path.join(self.dir, 'sostoyanie.json')
        self.state = self._load_state()

    # ------------------------------------------------ состояние и журнал
    def _load_state(self):
        if os.path.exists(self.f_rows):
            bad = 0
            with open(self.f_rows, encoding='utf-8') as f:
                for l in f:
                    if not l.strip():
                        continue
                    try:
                        self.rows.append(json.loads(l))
                    except json.JSONDecodeError:
                        bad += 1
            if bad:
                # процесс убили посреди записи: переписываем файл без оборванной строки, иначе следующая допишется к ней
                with open(self.f_rows + '.tmp', 'w', encoding='utf-8') as f:
                    for r in self.rows:
                        f.write(json.dumps(r, ensure_ascii=False) + '\n')
                os.replace(self.f_rows + '.tmp', self.f_rows)
                self.log(f'перезапуск: в boi.jsonl пропущено оборванных строк: {bad}')
        if os.path.exists(self.f_state):
            with open(self.f_state, encoding='utf-8') as f:
                return json.load(f)
        s0 = self.plan['seed0']
        seed0 = random.SystemRandom().randrange(10 ** 6, 10 ** 8) if s0 == 'sluchajno' else int(s0)
        return dict(seed0=seed0, faza=0, potracheno={}, volna={}, sled_i={}, podbor={}, zadanie=None,
                    start=now(), srok_sek=self.plan['srok_chasov'] * 3600, gotovo=False)

    def save_state(self):
        tmp = self.f_state + '.tmp'
        with open(tmp, 'w', encoding='utf-8') as f:
            json.dump(self.state, f, ensure_ascii=False, indent=1)
        os.replace(tmp, self.f_state)

    def log(self, s):
        line = f'- {now()} {s}\n'
        with open(os.path.join(self.dir, 'zhurnal.md'), 'a', encoding='utf-8') as f:
            f.write(line)
        print(line, end='', flush=True)

    def progress(self, text):
        with open(os.path.join(self.dir, 'progress.md'), 'w', encoding='utf-8') as f:
            f.write(f'# Прогресс: {self.plan["nazvanie"]}\n\nОбновлено {now()}\n\n{text}\n')

    def commit(self, msg):
        if not self.use_git:
            return
        try:
            subprocess.run(['git', 'add', '-A', os.path.relpath(self.dir, self.repo), os.path.relpath(self.game_dir, self.repo)],
                           cwd=self.repo, check=True, capture_output=True)
            subprocess.run(['git', 'commit', '-m', msg], cwd=self.repo, capture_output=True)
        except Exception as ex:
            self.log(f'git: не удалось закоммитить: {ex}')

    # ------------------------------------------------ варианты
    def variant(self, metka, geroi=None, pravki=None):
        g = {h: dict(self.plan['geroi'][h]) for h in self.game.heroes}
        for h, spec in (geroi or {}).items():
            g[h].update(spec)
        for h in g:
            g[h] = planmod._deck(g[h], f'вариант {metka}')
        pr = dict(self.plan['pravki']); pr.update(pravki or {})
        return dict(metka=metka, geroi=g, pravki=pr)

    def card_variant(self, cid, pravki=None, metka=None):
        hid = self.game.cards[cid].hero
        own = list(self.plan['geroi'][hid].get('obyazatelno') or []) + [cid]
        v = self.variant(metka or cid, {hid: {'obyazatelno': own}}, pravki)
        v['kt'] = cid
        return v

    def phase_variants(self, ph):
        """Все варианты фазы на текущей волне (для подбора зависят от уже найденного)."""
        t = ph['tip']
        if t == 'progon':
            return [self.variant(v['metka'], v.get('geroi'), v.get('pravki')) for v in ph['varianty']]
        et = self.sog['etalony']
        if t == 'test_bilda':
            vs = [self.variant('baza')] + [self.card_variant(e) for e in et]
            cards = ph['karty']
            done = ph['id'] in self.state['volna'] and self.state['volna'][ph['id']] > 0
            if done:      # следующие волны — только картам с неясным итогом; если таких нет, всем (точнее)
                tab, _, _ = M.card_table(self.phase_rows(ph), 'baza', cards, et, ph['situacii'], self.sog)
                unclear = [r['karta'] for r in tab if r['karta'] in cards and r['verdict'].startswith('не ясно')]
                cards = unclear or cards
            return vs + [self.card_variant(c) for c in cards]
        if t == 'podbor':
            return self.podbor_variants(ph)
        raise ValueError(t)

    # ------------------------------------------------ подбор чисел
    def podbor_cur(self, ph):
        st = self.state['podbor'].setdefault(ph['id'], {})
        for x in ph['parametry']:
            if x['chislo'] not in st:
                st[x['chislo']] = self.current_value(x['chislo'])
        return st

    def current_value(self, key):
        parts = key.split('.')
        if parts[0] == 'karta':
            c = self.game.cards[parts[1]]
            return c.cost if parts[2] == 'cena' else c.numbers[parts[2]]
        if parts[0] == 'pravila':
            node = self.game.rules
            for p in parts[1:]:
                node = node[p]
            return node
        if parts[0] == 'vrag':
            raw = yaml.safe_load(open(self.file_of(key), encoding='utf-8'))
            node = raw
            for p in parts[2:]:
                node = node[int(p)] if isinstance(node, list) else node[p]
            return node
        raise ValueError(key)

    def candidates(self, x, cur):
        lo, hi = x['granicy']; sh = x['shag']
        return sorted({v for v in (cur - sh, cur, cur + sh) if lo <= v <= hi})

    @staticmethod
    def sig(pr):
        return ';'.join(f'{k}={v}' for k, v in sorted(pr.items())) or 'tekushchee'

    def cand_pravki(self, ph, x, val):
        """Правки кандидата: текущие найденные числа (для sila — только этой карты) и одно изменённое."""
        cur = self.podbor_cur(ph)
        if ph['cel'] == 'sila':
            pr = {y['chislo']: cur[y['chislo']] for y in ph['parametry'] if y['karta'] == x['karta']}
        else:
            pr = dict(cur)
        pr[x['chislo']] = val
        return pr

    def podbor_variants(self, ph):
        cur = self.podbor_cur(ph)
        vs = []
        if ph['cel'] == 'sila':
            vs = [self.variant('baza')] + [self.card_variant(e) for e in self.sog['etalony']]
            seen = set()
            for x in ph['parametry']:
                for val in self.candidates(x, cur[x['chislo']]):
                    pr = self.cand_pravki(ph, x, val); name = self.sig(pr)
                    if name not in seen:
                        seen.add(name); vs.append(self.card_variant(x['karta'], pr, name))
        else:
            seen = {self.sig(cur)}
            vs = [self.variant(self.sig(cur), pravki=dict(cur))]
            for x in ph['parametry']:
                for val in self.candidates(x, cur[x['chislo']]):
                    pr = self.cand_pravki(ph, x, val); name = self.sig(pr)
                    if name not in seen:
                        seen.add(name); vs.append(self.variant(name, pravki=pr))
        return vs

    def podbor_update(self, ph):
        """После волны: для каждого параметра берём значение, лучшее по цели. Окно сдвигается к лучшему."""
        cur = self.podbor_cur(ph); rows = self.phase_rows(ph)
        ch = []; new = dict(cur)
        for x in ph['parametry']:
            k = x['chislo']; best = None
            for val in self.candidates(x, cur[k]):
                name = self.sig(self.cand_pravki(ph, x, val))
                if ph['cel'] == 'sila':
                    tab, _, _ = M.card_table(rows, 'baza', [name], self.sog['etalony'], ph['situacii'], self.sog)
                    r = next(t for t in tab if t['karta'] == name)
                    c = (sum(self.sog['apgrejd_norma_proc']) / 2)
                    score = abs(r['pct'] - c) if r['pct'] == r['pct'] else 1e9
                else:
                    summ = M.summary([r for r in rows if r['v'] == name], self.sog)
                    score = M.corridor_score(summ)
                if best is None or score < best[0] - 1e-9 or (abs(score - best[0]) < 1e-9 and val == cur[k]):
                    best = (score, val)
            if best and best[1] != cur[k]:
                ch.append(f'{k}: {cur[k]} → {best[1]}')
                new[k] = best[1]
        cur.update(new)
        if ch:
            self.log(f'подбор «{ph["id"]}»: ' + '; '.join(ch))
        return ch

    def file_of(self, key):
        parts = key.split('.')
        if parts[0] == 'karta':
            return os.path.join(self.game_dir, self.game.cards[parts[1]].path)
        if parts[0] == 'pravila':
            return os.path.join(self.game_dir, 'pravila.yaml')
        if parts[0] == 'vrag':
            import glob
            for p in glob.glob(os.path.join(self.game_dir, 'vragi', '*.yaml')):
                if yaml.safe_load(open(p, encoding='utf-8')).get('id') == parts[1]:
                    return p
        raise ValueError(f'не нашёл файл для {key}')

    def write_found(self, ph):
        """Записать найденные числа в файлы игры (с историей в карте)."""
        cur = self.podbor_cur(ph); done = []
        for x in ph['parametry']:
            k = x['chislo']; val = cur[k]; old = self.current_value(k)
            if val == old:
                continue
            path = self.file_of(k); parts = k.split('.')
            if parts[0] == 'karta':
                keys = [parts[2]] if parts[2] == 'cena' else ['chisla', parts[2]]
            elif parts[0] == 'pravila':
                keys = parts[1:]
            else:
                keys = [int(p) if p.isdigit() else p for p in parts[2:]]
            set_scalar(path, keys, val)
            if parts[0] == 'karta':
                note = f'{time.strftime("%Y-%m-%d")} стенд, план {self.plan["nazvanie"]}, фаза {ph["id"]}: {parts[2]} {old} → {val}'
                rewrite(path, lambda d: d.setdefault('istoriya', []).append(note))
            done.append(f'{k}: {old} → {val}')
        if done:
            self.log('записал в файлы игры: ' + '; '.join(done))
            self.game = engine.load_game(self.game_dir)
        return done

    # ------------------------------------------------ строки
    def phase_rows(self, ph):
        return [r for r in self.rows if r['faza'] == ph['id']]

    def add_rows(self, new):
        with open(self.f_rows, 'a', encoding='utf-8') as f:
            for r in new:
                f.write(json.dumps(r, ensure_ascii=False) + '\n')
        self.rows += new

    # ------------------------------------------------ главный цикл
    def time_left_total(self):
        spent = sum(self.state['potracheno'].values())
        return self.state['srok_sek'] - spent

    def phase_budget(self, idx):
        """Бюджет фазы: её доля срока плюс всё, что недобрали предыдущие фазы."""
        fazy = self.plan['fazy']; total = self.state['srok_sek']
        planned = sum(f['dolya'] for f in fazy[:idx + 1]) * total
        spent_before = sum(self.state['potracheno'].get(f['id'], 0) for f in fazy[:idx])
        return planned - spent_before

    def check_pauza(self):
        if self.stop_at and time.time() > self.stop_at:
            self.progress(f'Пауза по --minut, срока осталось {self.time_left_total() / 60:.0f} мин. Продолжить: та же команда.')
            self.log(f'пауза по --minut: сыграно {len(self.rows)} боёв, продолжить той же командой')
            raise Pauza()

    def run(self):
        meta = dict(plan=self.plan, seed0=self.state['seed0'], api=engine.API_VERSION, pravila=engine.RULES_VERSION,
                    kommit=git_commit(self.repo), yader=self.procs, start=self.state['start'])
        with open(os.path.join(self.dir, 'meta.json'), 'w', encoding='utf-8') as f:
            json.dump(meta, f, ensure_ascii=False, indent=1)
        if not self.rows:
            self.log(f'старт плана «{self.plan["nazvanie"]}», срок {self.plan["srok_chasov"]} ч, сид {self.state["seed0"]}, '
                     f'ядер {self.procs}, движок {engine.API_VERSION}/{engine.RULES_VERSION}, коммит {meta["kommit"]}')
        else:
            self.log(f'продолжаю с чекпоинта: {len(self.rows)} боёв уже сыграно')
        with Pool(self.procs, initializer=worker.init, initargs=(self.game_dir, self.plan['tajmaut_boya_sek'])) as pool:
            self.pool = pool
            if self.smoke and not self.rows:
                self.smoke_test()
            fazy = self.plan['fazy']
            while self.state['faza'] < len(fazy):
                idx = self.state['faza']; ph = fazy[idx]
                self.run_phase(idx, ph)
                report.phase_report(self, ph)
                self.log(f'фаза «{ph["id"]}» закончена, отчёт otchet-{ph["id"]}.md')
                self.state['faza'] += 1; self.save_state()
                self.commit(f'стенд: {self.plan["nazvanie"]}, фаза {ph["id"]}')
        report.final_report(self)
        self.state['gotovo'] = True; self.save_state()
        self.log('план выполнен, итог в itog.md')
        self.commit(f'стенд: {self.plan["nazvanie"]}, итог')

    def smoke_test(self):
        """Дымовой прогон: по одному бою каждого варианта первой волны каждой фазы в каждой ситуации."""
        t = time.time(); jobs = []
        for ph in self.plan['fazy']:
            for v in self.phase_variants(ph):
                for s in ph['situacii']:
                    jobs.append(dict(faza='_dym', volna=0, v=v, sit=s, i=999999, seed0=self.state['seed0']))
        res = list(self.pool.imap_unordered(worker.one, jobs))
        bad = [r for r in res if 'error' in r]
        self.speed = len(res) / max(1e-6, time.time() - t)
        self.log(f'дымовой прогон: {len(res)} боёв за {time.time() - t:.0f} с, ошибок {len(bad)}')
        if bad:
            for r in bad[:3]:
                self.log(f'ошибка в варианте {r["v"]} ({r["sit"]}): {r["error"]}\n```\n{r.get("detail", "")}\n```')
            raise SystemExit('дымовой прогон с ошибками — план не запущен, см. zhurnal.md')

    def run_phase(self, idx, ph):
        pid = ph['id']
        self.log(f'фаза «{pid}» ({ph["tip"]}): бюджет {self.phase_budget(idx) / 60:.0f} мин')
        speed = getattr(self, 'speed', None)
        while True:
            self.check_pauza()
            budget = self.phase_budget(idx) - self.state['potracheno'].get(pid, 0)
            wave_no = self.state['volna'].get(pid, 0)
            # незаконченная волна после перезапуска
            if self.state.get('zadanie') and self.state['zadanie']['faza'] == pid:
                z = self.state['zadanie']
                vs, i0, n = z['v'], z['i0'], z['n']
            else:
                vs = self.phase_variants(ph)
                n = ph['pervaya_volna'] if wave_no == 0 else ph['volna']
                i0 = self.state['sled_i'].get(pid, 0)
                est = len(vs) * len(ph['situacii']) * n / speed if speed else 0
                if wave_no > 0 and est > budget:
                    # не влезает целая волна — уменьшаем, но не меньше 10 боёв
                    n = int(n * budget / est) if est else n
                    if n < 10:
                        break
                if wave_no == 0 and budget <= 0:
                    self.log(f'фаза «{pid}»: на неё не осталось времени — прогон только первой волны')
                self.state['zadanie'] = dict(faza=pid, v=vs, i0=i0, n=n, volna=wave_no + 1)
                self.save_state()
            done = {(r['v'], r['sit'], r['i']) for r in self.rows if r['faza'] == pid}
            jobs = [dict(faza=pid, volna=wave_no + 1, v=v, sit=s, i=i, seed0=self.state['seed0'])
                    for v in vs for s in ph['situacii'] for i in range(i0, i0 + n) if (v['metka'], s, i) not in done]
            t0 = time.time(); last = t0; buf = []; nerr = 0
            for r in self.pool.imap_unordered(worker.one, jobs, chunksize=2):
                buf.append(r); nerr += 'error' in r
                if self.stop_at and time.time() > self.stop_at:
                    self.add_rows(buf)
                    self.state['potracheno'][pid] = self.state['potracheno'].get(pid, 0) + (time.time() - last)
                    self.save_state()
                    self.check_pauza()
                if time.time() - last > 60 or len(buf) >= 500:
                    self.add_rows(buf); buf = []
                    el = time.time() - t0
                    self.state['potracheno'][pid] = self.state['potracheno'].get(pid, 0) + (time.time() - last)
                    last = time.time(); self.save_state()
                    left = len(jobs) - sum(1 for x in self.rows if x['faza'] == pid and x['volna'] == wave_no + 1)
                    self.progress(f'Фаза **{pid}** ({ph["tip"]}), волна {wave_no + 1}: в волне осталось {left} боёв из {len(jobs)}, '
                                  f'ошибок {nerr}. Осталось срока: {self.time_left_total() / 60:.0f} мин.')
            self.add_rows(buf)
            dt = time.time() - last
            self.state['potracheno'][pid] = self.state['potracheno'].get(pid, 0) + dt
            el = time.time() - t0
            if jobs and el > 0:
                speed = len(jobs) / el
            self.speed = speed
            self.state['volna'][pid] = wave_no + 1
            self.state['sled_i'][pid] = i0 + n
            self.state['zadanie'] = None
            if nerr:
                self.log(f'фаза «{pid}», волна {wave_no + 1}: ошибок {nerr} из {len(jobs)} (см. boi.jsonl, поле error)')
            if ph['tip'] == 'podbor':
                self.podbor_update(ph)
            self.save_state()
            self.progress(f'Фаза **{pid}**: волна {wave_no + 1} готова, {len(self.phase_rows(ph))} боёв, '
                          f'скорость {speed:.1f} боя/с. Осталось срока: {self.time_left_total() / 60:.0f} мин.')
            if self.phase_budget(idx) - self.state['potracheno'].get(pid, 0) <= 0:
                break
        if ph['tip'] == 'podbor' and ph.get('zapisyvat'):
            self.write_found(ph)
