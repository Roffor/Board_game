# -*- coding: utf-8 -*-
"""Подгонка кругами (план 2026-10-25-podgonka-16ch.md, этап 2): круг = бои → правка карт и врагов по правилам → новый круг.

  python run.py podgonka plans/<конфиг>.yaml [--yader N] [--minut M] [--git]

Колоды: старт героя (карты с nabor: start) + случайные апгрейды из банка (кроме карт старта).
Папка прогона reports/progony/<имя конфига>/: sostoyanie.json, boi.jsonl (все бои, с номером круга),
zhurnal.md, progress.md, krug-NN.md (отчёт круга), pravki.md (все правки по порядку).

Правила (числа — в конфиге, по умолчанию как в плане):
- вклад карты: разница раундов и потерь пары (ХП) между боями с картой и без неё внутри ситуации II/EL/BOSS,
  среднее с весом числа боёв с картой; только бои с текущими числами карты;
- выбросы: Δр от медианы ≥ porog_r → урон ∓1 (или цена ±1); Δп от медианы ≥ porog_p → щит ±1;
- общий сдвиг: ситуация вне середины коридора [С 8.6] → ещё sdvig_kart карт каждого героя; при споре — ослабление;
- старт: по ярусу I раз в start_kazhdye кругов; враги: раз в vragi_kazhdye кругов, удар ≤ udar_maks, здоровье ≤ [С 4.1].
Карты, которые бот играет реже redko раз за бой, не правятся."""
import json, os, random, subprocess, time
from collections import defaultdict
from multiprocessing import Pool

import yaml
import engine
from . import worker, metrics as M
from .situacii import SITUACII
from .yamlpis import set_scalar, rewrite

URON_KEYS = ('uron', 'uron_big', 'uron_mal')
SHCHIT = ('shchit', 'shchit_big', 'shchit_mal', 'shchit_soyuzniku', 'shchit_s')
SHAPKA = {'uron': 6, 'uron_mal': 6, 'uron_big': 8, 'shchit': 5, 'shchit_mal': 5, 'shchit_big': 6,
          'shchit_soyuzniku': 5, 'shchit_s': 5, 'cena': 2}          # [С 5.2–5.4]
NIZ = {'cena': 0}

DEFAULT = dict(boev={'I': 800, 'II': 2400, 'EL': 2400, 'BOSS': 2400}, porog_r=0.3, porog_p=1.5, sdvig_kart=15,
               min_boev_karty=60, redko=0.5, redko_dolya=0.35, start_kazhdye=1, start_kart=2, vragi_kazhdye=4, udar_maks=6, tajmaut=30, pobedy_zapas=0.97, odna_ataka=True, dolya_v_koridore=0.8,
               bez_pravok=False, seed0=None, srok_chasov=6.0, poslednij_krug=None)


class Pauza(Exception):
    pass


def now():
    return time.strftime('%Y-%m-%d %H:%M:%S')


class Podgonka:
    def __init__(self, repo, cfg_path, game_dir, runs_dir, procs=None, minut=None, use_git=False):
        self.repo = repo; self.game_dir = game_dir; self.use_git = use_git
        with open(cfg_path, encoding='utf-8') as f:
            c = yaml.safe_load(f) or {}
        self.cfg = dict(DEFAULT); self.cfg.update(c)
        self.name = os.path.splitext(os.path.basename(cfg_path))[0]
        self.dir = os.path.join(runs_dir, self.name); os.makedirs(self.dir, exist_ok=True)
        self.procs = procs or os.cpu_count()
        self.stop_at = time.time() + minut * 60 if minut else None
        self.f_state = os.path.join(self.dir, 'sostoyanie.json'); self.f_rows = os.path.join(self.dir, 'boi.jsonl')
        self.game = engine.load_game(game_dir)
        with open(self.game.soglashenie_path, encoding='utf-8') as f:
            self.sog = yaml.safe_load(f)
        if os.path.exists(self.f_state):
            self.st = json.load(open(self.f_state, encoding='utf-8'))
        else:
            s0 = self.cfg['seed0'] or random.SystemRandom().randrange(10 ** 6, 10 ** 8)
            self.st = dict(seed0=s0, krug=1, start=now(), potracheno=0.0, rev={}, v_seredine=0, istoriya=[])
            self.save()
            self.log(f'старт подгонки «{self.name}», срок {self.cfg["srok_chasov"]} ч, сид {s0}, ядер {self.procs}')

    # ------------------------------------------------ служебное
    def save(self):
        tmp = self.f_state + '.tmp'
        json.dump(self.st, open(tmp, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
        os.replace(tmp, self.f_state)

    def log(self, s):
        with open(os.path.join(self.dir, 'zhurnal.md'), 'a', encoding='utf-8') as f:
            f.write(f'- {now()} {s}\n')
        print(f'- {now()} {s}', flush=True)

    def progress(self, s):
        with open(os.path.join(self.dir, 'progress.md'), 'w', encoding='utf-8') as f:
            f.write(f'# Прогресс: {self.name}\n\nОбновлено {now()}\n\n{s}\n')

    def commit(self, msg):
        if not self.use_git:
            return
        root = os.path.normpath(os.path.join(self.repo))
        paths = [os.path.relpath(p, root) for p in (self.dir, os.path.join(self.game_dir, 'heroes'), os.path.join(self.game_dir, 'dungeons'))]
        subprocess.run(['git', 'add', '-A'] + paths, cwd=root, capture_output=True)
        subprocess.run(['git', 'commit', '-m', msg], cwd=root, capture_output=True)

    def srok_ostalos(self):
        return self.cfg['srok_chasov'] * 3600 - self.st['potracheno']

    # ------------------------------------------------ колоды и бои
    def variant(self):
        g = self.game; geroi = {}
        for h in g.heroes:
            start = [c.cid for c in g.start_deck(h)]
            pul = [c.cid for c in g.hero_cards(h, {'bank'}) if c.status != 'ubrana' and c.cid not in start]
            geroi[h] = dict(apgrejdy='sluchajno', pul=pul, obyazatelno=[], start=start)
        return dict(metka=f'krug-{self.st["krug"]}', geroi=geroi, pravki={}, rev=self.rev_key())

    def rev_key(self):
        return f'{self.st["krug"]}'

    def f_krug(self, k):
        return os.path.join(self.dir, f'boi-krug-{k:02d}.jsonl')    # бои одного круга (в git не идут, как boi.jsonl)

    def krug_rows(self, k=None):
        k = k or self.st['krug']; out = []
        if os.path.exists(self.f_krug(k)):
            for l in open(self.f_krug(k), encoding='utf-8'):
                try:
                    r = json.loads(l)
                except json.JSONDecodeError:
                    continue
                if r.get('krug') == k:
                    out.append(r)
        return out

    def play_krug(self, pool):
        k = self.st['krug']; v = self.variant()
        done = {(r['sit'], r['i']) for r in self.krug_rows()}
        base = k * 100000
        jobs = [dict(faza=f'krug-{k}', volna=k, v=v, sit=s, i=base + i, seed0=self.st['seed0'])
                for s in SITUACII for i in range(self.cfg['boev'][s]) if (s, base + i) not in done]
        total = sum(self.cfg['boev'].values()); t0 = time.time(); last = t0; buf = []; nerr = 0
        with open(self.f_krug(k), 'a', encoding='utf-8') as fo:
            for r in pool.imap_unordered(worker.one, jobs, chunksize=4):
                r['krug'] = k; nerr += 'error' in r
                fo.write(json.dumps(r, ensure_ascii=False) + '\n')
                if time.time() - last > 30:
                    fo.flush()
                    self.st['potracheno'] += time.time() - last; last = time.time(); self.save()
                    self.progress(f'Круг **{k}**: сыграно {len(done) + len(buf)} из {total} боёв, ошибок {nerr}. '
                                  f'Срока осталось {self.srok_ostalos() / 60:.0f} мин.')
                    if self.stop_at and time.time() > self.stop_at:
                        raise Pauza()
                buf.append(1)
        self.st['potracheno'] += time.time() - last; self.save()

    # ------------------------------------------------ анализ
    def svodka(self, rows):
        """Средние по ситуациям + распределение (Никита 2026-10-26): доля боёв с потерями внутри коридора
        и с раундами внутри коридора ±1 — цель не меньше dolya_v_koridore (80%)."""
        summ = M.summary(rows, self.sog)
        for sit, d in summ.items():
            rr = [r for r in M.ok_rows(rows) if r['sit'] == sit]
            kl, kr = d['loss_k'], d['rounds_k']
            kw = self.sog.get('poteri_shirokij_proc', {}).get(sit, kl)
            d['loss_in'] = M.mean(kl[0] <= 100.0 * r['taken'] / r['hp_pair'] <= kl[1] for r in rr)     # узкий [С 3.2]
            d['loss_in_w'] = M.mean(kw[0] <= 100.0 * r['taken'] / r['hp_pair'] <= kw[1] for r in rr)   # широкий
            d['rounds_in'] = M.mean(kr[0] - 1 <= r['rounds'] <= kr[1] + 1 for r in rr)
        return summ

    def vklad(self, rows):
        """{карта: dict(dr, dp, n, plays)} по II/EL/BOSS; только бои с текущей ревизией карты (бои этого круга)."""
        out = {}
        by_sit = defaultdict(list)
        for r in M.ok_rows(rows):
            if r['sit'] != 'I':
                by_sit[r['sit']].append(r)
        cards = [c for c in self.game.cards.values() if c.set == 'bank']
        for c in cards:
            h = c.hero; acc_r = acc_p = n_all = 0; plays = 0; ruka = sum(r.get('v_ruke', {}).get(c.cid, 0) for rr in by_sit.values() for r in rr)
            igr = sum(r['karty'].get(c.cid, 0) for rr in by_sit.values() for r in rr)
            for s, rr in by_sit.items():
                w = [r for r in rr if c.cid in r['deck'][h]]
                wo = [r for r in rr if c.cid not in r['deck'][h]]
                if len(w) < 5 or len(wo) < 5:
                    continue
                dr = M.mean(r['rounds'] for r in w) - M.mean(r['rounds'] for r in wo)
                dp = M.mean(r['taken'] for r in w) - M.mean(r['taken'] for r in wo)
                acc_r += dr * len(w); acc_p += dp * len(w); n_all += len(w)
                plays += sum(r['karty'].get(c.cid, 0) for r in w)
            if n_all:
                out[c.cid] = dict(dr=acc_r / n_all, dp=acc_p / n_all, n=n_all, plays=plays / n_all,
                                  dolya=igr / ruka if ruka else 0.0)
        return out

    def napravlenie(self, summ, sits):
        """Куда двигать: rounds −1 (бои короткие → ослабить урон), +1 (длинные → усилить), 0; то же для потерь (щит)."""
        q = self.sog['serediina_koridora']
        sr = []; sp = []
        for s in sits:
            d = summ.get(s)
            if not d:
                continue
            for x, k, acc in ((d['rounds'], d['rounds_k'], sr), (d['loss'], d['loss_k'], sp)):
                c = (k[0] + k[1]) / 2; w = (k[1] - k[0]) * q
                acc.append(-1 if x < c - w else (1 if x > c + w else 0))
            if d['won'] < self.pob(s):      # победы в бою (рабочий порог стенда; [С 3.5] — про забеги): мало побед — как «потери велики», важнее остального
                sp[-1] = 2
            elif d['won'] < min(1.0, self.pob(s) + 0.02) and sp[-1] == -1:
                sp[-1] = 0                            # побед впритык: потери не поднимаем, даже если ниже центра
        # раунды: короткие бои (−1) → ослабить урон; потери: малые (−1) → ослабить щит. Спор → ослабление.
        f = lambda a: (-1 if -1 in a else (1 if 1 in a else 0))
        return f(sr), (1 if 2 in sp else f(sp))

    POBEDY_BOJ = {'I': 0.99, 'II': 0.99, 'EL': 0.97, 'BOSS': 0.85}   # 2026-10-26: [С 3.5] 70–90% забегов → пороги для одного боя

    def pob(self, s):
        return self.POBEDY_BOJ.get(s, 0.95)

    def neraskryta(self, x):
        return x['plays'] < self.cfg['redko'] and x['dolya'] < self.cfg['redko_dolya']

    # ------------------------------------------------ правки
    def rychag(self, c, kind):
        """Число карты, которое двигаем: kind 'r' — урон (или цена), 'p' — щит. Возвращает (ключ, знак силы)."""
        keys = URON_KEYS if kind == 'r' else SHCHIT
        have = [k for k in keys if k in c.numbers and isinstance(c.numbers[k], (int, float))]
        if have:                         # самое большое число (урок 26.10: «после хода врага 7 щитов» не резалось — рычаг брал первое)
            return max(have, key=lambda k: c.numbers[k]), 1
        # у мага цена — рычаг и у карт за 0 маны (иначе карта без чисел, как Сглаз, неподвижна, а режется всё остальное)
        if kind == 'r' and c.hero == 'mag' and not c.cost_expr:
            return 'cena', -1
        return None, 0

    def shag(self, c, kind, sila):
        """Сдвинуть карту на ±1 по силе (sila +1 — усилить). Возвращает строку правки или None."""
        k, zn = self.rychag(c, kind)
        if not k:
            return None
        cur = c.cost if k == 'cena' else c.numbers[k]
        new = cur + sila * zn
        lo = NIZ.get(k, 1); hi = SHAPKA.get(k, 6)
        if c.set == 'start' and k == 'uron':
            lo = 2                        # старт не режем в «пустые» карты по урону; щит старта можно до 1 (26.10: щит старта держал потери у 0)                        # старт не режем в «пустые» карты (круг 9: старт срезали до 1, Броня 1 съедала удары)
        if not (lo <= new <= hi):
            return None
        path = os.path.join(self.game_dir, c.path)
        b = c.bounds.get(k)
        if b and not (b[0] <= new <= b[1]):
            if (c.set != 'bank' and c.set != 'start') or k == 'cena':   # границу цены не раздвигаем (26.10: Сглаз дорожал до неиграбельности)
                return None
            nb = [min(b[0], new), max(b[1], new)]
            rewrite(path, lambda d: d.setdefault('granicy', {}).__setitem__(k, nb))
        set_scalar(path, ['cena'] if k == 'cena' else ['chisla', k], new)
        note = f'{time.strftime("%Y-%m-%d")} стенд, подгонка {self.name}, круг {self.st["krug"]}: {k} {cur} → {new}'
        rewrite(path, lambda d: d.setdefault('istoriya', []).append(note))
        return f'{c.cid}: {k} {cur} → {new}'

    def pravki_kart(self, vk, napr):
        g = self.game; cfg = self.cfg; done = []; tronuty = set()
        ok = {cid: x for cid, x in vk.items() if x['n'] >= cfg['min_boev_karty'] and not self.neraskryta(x)}
        if not ok:
            return done
        med_r = sorted(x['dr'] for x in ok.values())[len(ok) // 2]
        med_p = sorted(x['dp'] for x in ok.values())[len(ok) // 2]

        def try_(cid, kind, sila, why):
            if cid in tronuty:
                return
            s = self.shag(g.cards[cid], kind, sila)
            if s:
                tronuty.add(cid); done.append(f'{s} ({why})')

        for cid, x in sorted(ok.items()):
            if x['dr'] - med_r <= -cfg['porog_r']:
                try_(cid, 'r', -1, f'выброс: Δр {x["dr"]:+.2f} от медианы {med_r:+.2f}')
            elif x['dr'] - med_r >= cfg['porog_r']:
                try_(cid, 'r', +1, f'выброс: Δр {x["dr"]:+.2f} от медианы {med_r:+.2f}')
            elif x['dp'] - med_p >= cfg['porog_p']:
                try_(cid, 'p', +1, f'выброс: Δп {x["dp"]:+.2f} ХП от медианы {med_p:+.2f}')
            elif x['dp'] - med_p <= -cfg['porog_p']:
                try_(cid, 'p', -1, f'выброс: Δп {x["dp"]:+.2f} ХП от медианы {med_p:+.2f}')
        nr, np_ = napr
        for h in g.heroes:
            mine = {cid: x for cid, x in ok.items() if g.cards[cid].hero == h}
            if nr:
                # nr −1: бои короткие → ослабить самые сильные (самые отрицательные Δр); +1 → усилить самые слабые
                order = sorted(mine, key=lambda cid: mine[cid]['dr'], reverse=(nr > 0))
                n = 0
                for cid in order:
                    if n >= cfg['sdvig_kart']:
                        break
                    if cid not in tronuty and self.rychag(g.cards[cid], 'r')[0]:
                        before = len(done); try_(cid, 'r', nr, 'общий сдвиг: раунды'); n += len(done) > before
            if np_:
                # np −1: потери малые → ослабить щит у карт, сильнее всех снижающих потери; +1 → усилить у самых слабых
                order = sorted(mine, key=lambda cid: mine[cid]['dp'], reverse=(np_ > 0))
                n = 0
                for cid in order:
                    if n >= cfg['sdvig_kart']:
                        break
                    if cid not in tronuty and self.rychag(g.cards[cid], 'p')[0]:
                        before = len(done); try_(cid, 'p', np_, 'общий сдвиг: потери'); n += len(done) > before
        return done

    def pravki_starta(self, summ):
        """Ярус I: одна стартовая карта на героя ±1, если I вне середины коридора."""
        nr, np_ = self.napravlenie(summ, ['I'])
        done = []; last = set(self.st.get('start_last', [])); now_ = []
        for h in self.game.heroes:
            uniq = {c.cid: c for c in self.game.start_deck(h)}
            cnt = defaultdict(int)
            for c in self.game.start_deck(h):
                cnt[c.cid] += 1
            for kind, napr in (('r', nr), ('p', np_)):
                if not napr:
                    continue
                cand = [c for c in uniq.values() if self.rychag(c, kind)[0] and self.rychag(c, kind)[0] != 'cena']
                key = lambda c: c.numbers[self.rychag(c, kind)[0]] * cnt[c.cid]
                cand.sort(key=key, reverse=(napr < 0))      # ослабляем самую «тяжёлую», усиливаем самую лёгкую
                n = 0
                for c in cand:
                    if n >= self.cfg['start_kart']:
                        break
                    if c.cid in last:             # одну и ту же стартовую карту не двигаем два круга подряд
                        continue
                    s = self.shag(c, kind, napr)
                    if s:
                        done.append(f'{s} (старт, ярус I: {"раунды" if kind == "r" else "потери"})'); n += 1; now_.append(c.cid)
        self.st['start_last'] = now_
        return done

    def vrag_fajl(self, eid):
        import glob
        for p in glob.glob(os.path.join(self.game_dir, 'dungeons', '*', 'vragi', '*.yaml')):
            if (yaml.safe_load(open(p, encoding='utf-8')) or {}).get('id') == eid:
                return p
        raise ValueError(f'нет файла врага {eid}')

    DEJSTVIE_MAKS = {'I': 8, 'II': 8, 'EL': 13, 'BOSS': 16}   # [С 3.6] с 2026-10-26 (Никита): урон за действие
    V_CEL_MAKS = 10                                            # [С 3.6]: в одну цель не больше 10 за раз

    SHCHIT_VRAGA = {'I': 10, 'II': 10, 'EL': 10, 'BOSS': 12}   # 26.10 пачка 1: у рядовых рамка 6 держала ярус I на 3,3 раунда      # рамки щита в намерении (урок 26.10: щит рядового дорос до 58)
    ZDOROVE_VRAGA = {'I': (16, 20), 'II': (16, 20), 'EL': (34, 40), 'BOSS': (50, 70)}   # рамки здоровья

    def acap(self, a, tier):
        """Потолок числа атаки: по обоим — половина потолка действия, в одного — потолок действия, но не больше 10."""
        tot = self.DEJSTVIE_MAKS[tier]
        return min(self.V_CEL_MAKS, tot // 2) if a.get('cel') == 'vse' else min(self.V_CEL_MAKS, tot)

    # Атаки в намерении (Никита 2026-10-26: «добавим атак врагам в намерение»): урон за ход ≤ DEJSTVIE_MAKS,
    # один удар в одну цель ≤ 10, атака по обоим считается дважды, без серий raz.
    @staticmethod
    def ataki(it):
        return [a for a in it['dejstviya'] if 'ataka' in a]

    @staticmethod
    def za_hod(it):
        return sum(a['ataka'] * (2 if a.get('cel') == 'vse' else 1) for a in it['dejstviya'] if 'ataka' in a)

    def mozhno_plus(self, it, a, tier):
        return a['ataka'] + 1 <= self.V_CEL_MAKS and self.za_hod(it) + (2 if a.get('cel') == 'vse' else 1) <= self.DEJSTVIE_MAKS[tier]

    def shag_atak(self, d, tier, dz, L, kp):
        its = [it for it in d['namereniya'] if self.ataki(it)]
        if not its:
            return []
        if dz > 0:
            ok = [(self.za_hod(it), it) for it in its if any(self.mozhno_plus(it, a, tier) for a in self.ataki(it))]
            if not ok:
                return []
            it = min(ok, key=lambda x: x[0])[1]
            a = min((a for a in self.ataki(it) if self.mozhno_plus(it, a, tier)), key=lambda a: a['ataka'])
            a['ataka'] += 1
            return [f'удар +1 в самом слабом намерении (потери {L:.1f}% при коридоре {kp})']
        it = max(its, key=self.za_hod)
        a = max(self.ataki(it), key=lambda a: a['ataka'])
        a['ataka'] -= 1
        if a['ataka'] <= 0:
            it['dejstviya'].remove(a)
        return [f'удар −1 в самом сильном намерении (потери {L:.1f}% при коридоре {kp})']

    def vyrovnyat(self, d, tier, inside):
        its = [it for it in d['namereniya'] if self.ataki(it)]
        if len(its) < 2:
            return []
        hi_ = max(its, key=self.za_hod); lo_ = min(its, key=self.za_hod)
        if self.za_hod(hi_) - self.za_hod(lo_) < 3:
            return []
        b = min((a for a in self.ataki(lo_) if self.mozhno_plus(lo_, a, tier)), key=lambda a: a['ataka'], default=None)
        if b is None:
            return []
        a = max(self.ataki(hi_), key=lambda a: a['ataka']); a['ataka'] -= 1; b['ataka'] += 1
        if a['ataka'] <= 0:
            hi_['dejstviya'].remove(a)
        return [f'намерения ровнее: сильное −1, слабое +1 (в коридоре потерь {inside:.0%} боёв)']

    def k_porogu(self, d, tier):
        """Привести действия врага к [С 3.6]: удар ≤ udar_maks, удар × серия ≤ порога яруса. Возвращает список правок."""
        cap = self.DEJSTVIE_MAKS[tier]; ch = []
        hlo, hhi = self.ZDOROVE_VRAGA[tier]
        d['zdorove'] = max(hlo, min(hhi, d['zdorove']))
        for it in d['namereniya']:
            for a in it['dejstviya']:
                if 'shchit' in a:
                    a['shchit'] = min(a['shchit'], self.SHCHIT_VRAGA[tier])
        for it in d['namereniya']:
            for a in self.ataki(it):
                a.pop('raz', None)
                a['ataka'] = min(a['ataka'], self.V_CEL_MAKS)
            while self.za_hod(it) > cap:
                a = max(self.ataki(it), key=lambda a: a['ataka']); a['ataka'] -= 1
                if a['ataka'] <= 0:
                    it['dejstviya'].remove(a)
        return ch

    def pravki_vragov(self, rows, summ):
        q = self.sog['serediina_koridora']; done = []; cap = self.cfg['udar_maks']
        hp_cap = self.sog['vragi_zdorove_maks']
        for eid, e in sorted(self.game.enemies.items()):
            if e.tier == 'I' and self.st['krug'] % 2 == 1:
                continue                                  # в нечётных кругах ярус I правит старт
            rr = [r for r in M.ok_rows(rows) if r['enemy'] == eid or r.get('enemy') == e.name]
            if len(rr) < 100:
                continue
            s = e.tier; kr = self.sog['raundy'][s]; kp = self.sog['poteri_pary_proc'][s]
            R = M.mean(r['rounds'] for r in rr); L = M.mean(100.0 * r['taken'] / r['hp_pair'] for r in rr)
            path = self.vrag_fajl(eid); ch = []

            def edit(d):
                cL = (kp[0] + kp[1]) / 2; wL = (kp[1] - kp[0]) * q
                cR = (kr[0] + kr[1]) / 2; wR = (kr[1] - kr[0]) * q
                won = M.mean(r['won'] for r in rr)
                dz = 0
                if L > cL + wL or L < cL - wL or won < self.pob(s):
                    dz = -1 if (L > cL + wL or won < self.pob(s)) else 1
                    if dz > 0 and won < min(1.0, self.pob(s) + 0.02):
                        dz = 0                         # побед впритык — удары не поднимаем
                if dz:
                    # далеко от коридора (> 2 четвертей ширины) — шаг по всем намерениям, рядом — по одному (круг 14: босс шёл по −0,2 за раунд)
                    n_sh = len([it for it in d['namereniya'] if self.ataki(it)]) if abs(L - cL) > 2 * wL else 1
                    for _ in range(n_sh):
                        ch.extend(self.shag_atak(d, s, dz, L, kp))
                hlo, hhi = self.ZDOROVE_VRAGA[s]; shmax = self.SHCHIT_VRAGA[s]
                if R > cR + wR:
                    sh = [a for it in d['namereniya'] for a in it['dejstviya'] if a.get('shchit', 0) > 0]
                    if sh:
                        a = max(sh, key=lambda a: a['shchit']); a['shchit'] -= 1
                        ch.append(f'щит −1 (раунды {R:.2f} при коридоре {kr})')
                    elif d['zdorove'] > hlo:
                        d['zdorove'] -= 1; ch.append(f'здоровье −1 (раунды {R:.2f})')
                elif R < cR - wR:
                    sh = [a for it in d['namereniya'] for a in it['dejstviya'] if 'shchit' in a and a['shchit'] < shmax]
                    daleko = R < cR - 2 * wR
                    if d['zdorove'] < hhi:
                        d['zdorove'] += 1; ch.append(f'здоровье +1 (раунды {R:.2f} при коридоре {kr})')
                    elif sh:
                        for a in (sh if daleko else [min(sh, key=lambda a: a['shchit'])]):
                            a['shchit'] += 1
                        ch.append(f'щит +1{" во всех намерениях" if daleko else ""} (раунды {R:.2f} при коридоре {kr})')
                    if daleko:                    # далеко: ещё и щит 2 в одно атакующее намерение без щита (у рядовых щит был лишь в одном намерении)
                        bez = [it for it in d['namereniya'] if self.ataki(it) and not any('shchit' in a for a in it['dejstviya'])]
                        if bez:
                            bez[0]['dejstviya'].insert(0, {'shchit': 2}); ch.append(f'щит 2 в атакующее намерение (раунды {R:.2f})')
                # распределение: средние в норме, но меньше 80% боёв в коридоре потерь — выровнять удары врага
                inside = M.mean(kp[0] <= 100.0 * r['taken'] / r['hp_pair'] <= kp[1] for r in rr)
                kw = self.sog.get('poteri_shirokij_proc', {}).get(s, kp)
                inside_w = M.mean(kw[0] <= 100.0 * r['taken'] / r['hp_pair'] <= kw[1] for r in rr)
                if dz == 0 and (inside < self.sog.get('dolya_uzkij', 0.5) or inside_w < self.sog.get('dolya_shirokij', 0.8)):
                    ch.extend(self.vyrovnyat(d, s, inside))
            rewrite(path, lambda d: (edit(d), self.k_porogu(d, s)))
            if ch:
                done.append(f'враг {eid}: ' + '; '.join(ch))
        return done

    # ------------------------------------------------ тревоги (2026-10-26: проверки, которые находили первопричины в разборах)
    def trevogi(self, rows, summ):
        out = []; ok = M.ok_rows(rows)
        for s, d in summ.items():
            rr = [r for r in ok if r['sit'] == s]
            if not rr or 'shchit_pary' not in rr[0]:
                continue
            shp = M.mean(r['shchit_pary'] / r['rounds'] for r in rr); vb = M.mean(r['vrag_bil'] / r['rounds'] for r in rr)
            d['shchit_r'] = shp; d['vrag_r'] = vb
            if shp >= vb:
                out.append(f'{s}: щит пары за раунд {shp:.1f} ≥ удара врага {vb:.1f} — урон проходит только за счёт выбора цели')
            tm = sum(r['taken_h']['mag'] for r in rr); tz = sum(r['taken_h']['zhrec'] for r in rr)
            if tm + tz and max(tm, tz) / (tm + tz) > 0.75:
                out.append(f'{s}: {"маг" if tm > tz else "Паладин"} принимает {max(tm, tz) / (tm + tz):.0%} урона')
            prev = self.st.get('prev_in', {}).get(s)
            if prev is not None and d['loss_in'] < prev - 0.10:
                out.append(f'{s}: доля боёв в коридоре потерь упала {prev:.0%} → {d["loss_in"]:.0%}')
        self.st['prev_in'] = {s: d['loss_in'] for s, d in summ.items()}
        # числа у рамок
        for h in self.game.heroes:
            cs = [c for c in self.game.cards.values() if c.hero == h and c.set == 'bank']
            sh = [c for c in cs if self.rychag(c, 'p')[0]]
            low = [c for c in sh if c.numbers[self.rychag(c, 'p')[0]] <= 1]
            if sh and len(low) / len(sh) > 0.5:
                out.append(f'{h}: у {len(low)} из {len(sh)} карт щит на нижней границе 1 — рычаг щита исчерпан')
        for eid, e in self.game.enemies.items():
            d = yaml.safe_load(open(self.vrag_fajl(eid), encoding='utf-8'))
            its = [it for it in d['namereniya'] if self.ataki(it)]
            if its and all(self.za_hod(it) >= self.DEJSTVIE_MAKS[e.tier] or all(a['ataka'] >= self.V_CEL_MAKS for a in self.ataki(it)) for it in its):
                out.append(f'враг {eid}: все удары у потолка [С 3.6]')
            lo, hi = self.ZDOROVE_VRAGA[e.tier]
            if d['zdorove'] == lo:
                out.append(f'враг {eid}: здоровье на нижней рамке {d["zdorove"]}')
        return out

    # ------------------------------------------------ отчёт круга
    def otchet(self, k, rows, summ, vk, changes, sec):
        L = [f'# Круг {k}', '', f'Боёв {len(rows)}, ошибок {sum("error" in r for r in rows)}, время {sec / 60:.0f} мин.', '',
             '| Ситуация | Боёв | Раунды (коридор) | Потери пары, % (коридор) | Победы | Затяжные | Боёв в коридоре потерь | Боёв в раундах ±1 |',
             '|---|---|---|---|---|---|---|---|']
        for s, d in summ.items():
            L.append(f'| {s} | {d["n"]} | {d["rounds"]:.2f} ({d["rounds_k"][0]}–{d["rounds_k"][1]}) | {d["loss"]:.1f} '
                     f'({d["loss_k"][0]}–{d["loss_k"][1]}) | {100 * d["won"]:.0f}% | {100 * d.get("long", 0):.0f}% | '
                     f'{100 * d["loss_in"]:.0f}% (шир. {100 * d.get("loss_in_w", 0):.0f}%) | {100 * d["rounds_in"]:.0f}% |')
        tr = self.trevogi(rows, summ); self.posl_trevogi = tr
        L += ['', '| Ситуация | Щит пары за раунд | Удар врага за раунд |', '|---|---|---|']
        L += [f'| {s} | {d.get("shchit_r", float("nan")):.1f} | {d.get("vrag_r", float("nan")):.1f} |' for s, d in summ.items()]
        L += ['', f'**Тревоги ({len(tr)}):**', ''] + [f'- {t}' for t in tr]
        redko = sorted(cid for cid, x in vk.items() if self.neraskryta(x))
        L += ['', f'Правок: {len(changes)}.', ''] + [f'- {c}' for c in changes]
        L += ['', f'Бот не раскрывает (< {self.cfg["redko"]} розыгрыша за бой и < {self.cfg["redko_dolya"]:.0%} розыгрышей, '
              f'когда в руке): {len(redko)} карт: ' + ', '.join(redko)]
        L += ['', '## Вклад карт (II/EL/BOSS)', '', '| Карта | Боёв | Δр | Δп, ХП | Розыгрышей за бой | Сыграна, когда в руке |',
              '|---|---|---|---|---|---|']
        for cid, x in sorted(vk.items(), key=lambda kv: kv[1]['dr']):
            L.append(f'| {cid} | {x["n"]} | {x["dr"]:+.2f} | {x["dp"]:+.2f} | {x["plays"]:.2f} | {x["dolya"]:.0%} |')
        open(os.path.join(self.dir, f'krug-{k:02d}.md'), 'w', encoding='utf-8').write('\n'.join(L) + '\n')
        with open(os.path.join(self.dir, 'pravki.md'), 'a', encoding='utf-8') as f:
            f.write(f'\n## Круг {k}\n\n' + ''.join(f'- {c}\n' for c in changes))

    # ------------------------------------------------ главный цикл
    def run(self):
        while self.srok_ostalos() > 0 and (not self.cfg['poslednij_krug'] or self.st['krug'] <= self.cfg['poslednij_krug']):
            k = self.st['krug']; t0 = time.time()
            with Pool(self.procs, initializer=worker.init, initargs=(self.game_dir, self.cfg['tajmaut'])) as pool:
                self.play_krug(pool)
            rows = self.krug_rows(k)
            summ = self.svodka(rows); vk = self.vklad(rows)
            if self.st.get('obrabotan') == k:      # правки этого круга уже внесены (сбой после них) — не повторять
                self.st['krug'] = k + 1; self.save(); continue
            changes = []
            napr = self.napravlenie(summ, ['II', 'EL', 'BOSS'])
            vse_v_seredine = napr == (0, 0) and self.napravlenie(summ, ['I']) == (0, 0)
            self.st['v_seredine'] = self.st['v_seredine'] + 1 if vse_v_seredine else 0
            if self.st['v_seredine'] >= 3:
                napr = (0, 0)
            if self.cfg.get('bez_pravok'):
                napr = None
            if napr is not None:
                changes += self.pravki_kart(vk, napr)
            if napr is None:
                pass
            elif k % 2 == 1:      # ярус I: нечётные круги — старт, чётные — враги яруса I (круг 13: два рычага в одном круге качали потери)
                changes += self.pravki_starta(summ)
            if napr is not None and k % self.cfg['vragi_kazhdye'] == 0:   # 26.10 пачка 2: враг судится по своему ярусу, не по общему направлению
                changes += self.pravki_vragov(rows, summ)
            self.st['obrabotan'] = k; self.save()
            self.otchet(k, rows, summ, vk, changes, time.time() - t0)
            line = ' | '.join(f'{s} {d["rounds"]:.2f} р / {d["loss"]:.1f}% / {100 * d["won"]:.0f}% / узк. {100 * d["loss_in"]:.0f}% шир. {100 * d.get("loss_in_w", 0):.0f}% р±1 {100 * d["rounds_in"]:.0f}%'
                              for s, d in summ.items())
            self.log(f'круг {k} готов: {line}; правок {len(changes)}, тревог {len(getattr(self, "posl_trevogi", []))}, отчёт krug-{k:02d}.md')
            self.game = engine.load_game(self.game_dir)       # проверка: правки не сломали данные
            self.st['krug'] = k + 1; self.save()
            self.commit(f'стенд: подгонка {self.name}, круг {k}')
            if self.stop_at and time.time() > self.stop_at:
                raise Pauza()
        self.log('подгонка закончена по сроку')
        return True
