import sys, json, subprocess, os
from multiprocessing import Pool
def one(s):
    p=f'/tmp/claude-0/-home-claude/1a207df5-131f-5651-a26b-fc53e8298add/scratchpad/mass_{os.path.basename(os.getcwd())}_{s}.json'
    json.dump({'seed':s,'auto':True,'decisions':[]},open(p,'w'))
    subprocess.run(['python3','run.py',p],capture_output=True)
    d=json.load(open(p+'.result.json'))
    F=d['fights']; o=[f for f in F if f['tier'] in (1,2)]
    return dict(won=d['won'],t=d['total_min'],minf=min(d['min_frac'].values()),leg=d['n_leg'],
      ordr=sum(f['rounds'] for f in o)/max(1,len(o)), ordt=sum(f['sec'] for f in o)/60/max(1,len(o)),
      el=[f['rounds'] for f in F if f['tier']=='elite'], boss=[f['rounds'] for f in F if f['tier']=='boss'],
      dark=d['stats']['dark_rounds']/d['stats']['rounds'], nel=sum(1 for f in F if f['tier']=='elite'),
      died=None if d['won'] else F[-1]['tier'],
      tk={t: [f['taken']['M']+f['taken']['P'] for f in F if f['tier']==t] for t in (1,2,'elite','boss')},
      where=d.get('min_where'), rest=[st['text'] for st in d['stages'] if st['room']=='Отд'])
if __name__=='__main__':
    with Pool(4) as p: R=p.map(one, range(1000,1000+int(sys.argv[1])))
    n=len(R); w=[r for r in R if r['won']]
    avg=lambda xs: sum(xs)/max(1,len(xs))
    print(f"побед {len(w)}/{n}; время побед {avg([r['t'] for r in w]):.0f} мин; мин.здоровье {100*avg([r['minf'] for r in R]):.0f}%;"
      f" рядовой {avg([r['ordr'] for r in R]):.2f} р / {avg([r['ordt'] for r in R]):.1f} мин; элит за забег {avg([r['nel'] for r in R]):.1f},"
      f" элита {avg([x for r in R for x in r['el']]):.2f} р; босс {avg([x for r in R for x in r['boss']]):.2f} р; темнота {100*avg([r['dark'] for r in R]):.0f}%;"
      f" потери за бой I/II/элита/босс {avg([x for r in R for x in r['tk'][1]]):.1f}/{avg([x for r in R for x in r['tk'][2]]):.1f}/{avg([x for r in R for x in r['tk']['elite']]):.1f}/{avg([x for r in R for x in r['tk']['boss']]):.1f};"
      f" боёв I/II за забег {avg([len(r['tk'][1]) for r in R]):.1f}/{avg([len(r['tk'][2]) for r in R]):.1f};"
      f" самая низкая точка в бою: { {t: sum(1 for r in R if r['where']==t) for t in (1,2,'elite','boss')} };"
      f" где погибли {[r['died'] for r in R if not r['won']]}")
