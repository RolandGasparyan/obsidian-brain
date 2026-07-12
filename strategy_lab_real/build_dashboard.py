#!/usr/bin/env python3
"""
Build a self-contained dashboard for the REAL strategy lab.
Reads result files (shadow, forward-test, eligibility, authorized, leaderboard,
shadow track) and writes dashboard/data.json + dashboard/index.html.
Serves the live paper results — NO secrets, NO keys, read-only render.
"""
import os, json, csv, html, time

OUT = os.environ.get("LAB_OUT", os.path.join(os.path.dirname(__file__), "results"))
DASH = os.environ.get("DASH_DIR", os.path.join(os.path.dirname(__file__), "dashboard"))
os.makedirs(DASH, exist_ok=True)

def jload(name, default=None):
    p = os.path.join(OUT, name)
    try:
        return json.load(open(p))
    except Exception:
        return default if default is not None else {}

def track_rows():
    p = os.path.join(OUT, "shadow_track.csv")
    rows = []
    if os.path.exists(p):
        try:
            for r in csv.DictReader(open(p)):
                rows.append(r)
        except Exception:
            pass
    return rows

data = {
    "generated": time.strftime("%Y-%m-%d %H:%M:%SZ", time.gmtime()),
    "shadow": jload("shadow_report.json", {}),
    "forward": jload("forward_test.json", {}),
    "eligibility": jload("live_eligibility.json", {}),
    "authorized": jload("authorized.json", {}),
    "leaderboard": jload("leaderboard.json", {}),
    "track": track_rows(),
}
json.dump(data, open(os.path.join(DASH, "data.json"), "w"), indent=2)

HTML = """<!doctype html><html lang="en"><head>
<meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Trading Guru — Strategy Lab (live paper)</title>
<script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.1/dist/chart.umd.min.js"></script>
<style>
:root{--bg:#0a0e17;--panel:#111827;--line:#1f2937;--ink:#e5e7eb;--dim:#94a3b8;
--green:#22c55e;--red:#ef4444;--amber:#f59e0b;--cyan:#22d3ee;--mag:#d946ef}
*{box-sizing:border-box}body{margin:0;background:var(--bg);color:var(--ink);
font-family:ui-monospace,SFMono-Regular,Menlo,monospace;padding:18px}
h1{font-size:18px;letter-spacing:2px;margin:0 0 2px}
.sub{color:var(--dim);font-size:12px;margin-bottom:16px}
.grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(260px,1fr));gap:14px}
.card{background:var(--panel);border:1px solid var(--line);border-radius:12px;padding:14px}
.card h2{font-size:12px;letter-spacing:1px;color:var(--dim);margin:0 0 10px;text-transform:uppercase}
.big{font-size:30px;font-weight:700}
.pos{display:inline-block;padding:3px 10px;border-radius:999px;font-size:12px;font-weight:700}
.in-btc{background:rgba(34,197,94,.15);color:var(--green);border:1px solid var(--green)}
.in-cash{background:rgba(148,163,184,.12);color:var(--dim);border:1px solid var(--dim)}
.row{display:flex;justify-content:space-between;padding:4px 0;font-size:13px;border-bottom:1px dashed var(--line)}
.row:last-child{border-bottom:none}
.g{color:var(--green)}.r{color:var(--red)}.a{color:var(--amber)}.c{color:var(--cyan)}
table{width:100%;border-collapse:collapse;font-size:12px}
th,td{text-align:left;padding:6px 8px;border-bottom:1px solid var(--line)}
th{color:var(--dim);text-transform:uppercase;font-size:10px;letter-spacing:1px}
.pill{font-size:10px;padding:1px 7px;border-radius:999px;border:1px solid var(--line)}
.ok{color:var(--green);border-color:var(--green)}.no{color:var(--red);border-color:var(--red)}
.full{grid-column:1/-1}.foot{color:var(--dim);font-size:11px;margin-top:14px;text-align:center}
canvas{max-height:240px}
</style></head><body>
<h1>⚡ TRADING GURU — STRATEGY LAB</h1>
<div class="sub">live paper results · the validated edge, zero real money · auto-refresh 60s · <span id="gen"></span></div>
<div class="grid">
  <div class="card"><h2>Shadow — MA50W10 / BTC</h2>
     <div><span id="pos" class="pos in-cash">—</span></div>
     <div class="big" id="ret">—</div>
     <div class="row"><span>vs buy &amp; hold</span><span id="bh">—</span></div>
     <div class="row"><span>max drawdown</span><span id="dd">—</span></div>
     <div class="row"><span>Sharpe (ann.)</span><span id="sh">—</span></div>
     <div class="row"><span>days live</span><span id="days">—</span></div>
     <div class="row"><span>inception</span><span id="incep">—</span></div>
     <div class="row"><span>trades / win</span><span id="tr">—</span></div>
  </div>
  <div class="card"><h2>Forward-test (full window)</h2>
     <div class="row"><span>state</span><span id="f_state">—</span></div>
     <div class="row"><span>return</span><span id="f_ret">—</span></div>
     <div class="row"><span>vs B&amp;H</span><span id="f_bh">—</span></div>
     <div class="row"><span>last ~30d</span><span id="f_30">—</span></div>
     <div class="row"><span>max DD</span><span id="f_dd">—</span></div>
     <div class="row"><span>Sharpe</span><span id="f_sh">—</span></div>
     <div class="row"><span>last close</span><span id="f_px">—</span></div>
  </div>
  <div class="card"><h2>Live eligibility / guard</h2>
     <div id="elig"></div>
  </div>
  <div class="card full"><h2>Shadow forward equity (paper vs buy&amp;hold)</h2>
     <canvas id="chart"></canvas>
  </div>
  <div class="card full"><h2>Strategy leaderboard (real backtests)</h2>
     <div id="lb"></div>
  </div>
</div>
<div class="foot">Trading Guru Empire · served from VPS · paper only — fund real money only after the forward track proves itself.</div>
<script>
const pct=x=>(x>0?'+':'')+(x==null?'—':Number(x).toFixed(2))+'%';
const cls=x=>x>0?'g':(x<0?'r':'');
async function load(){
  let d; try{ d=await (await fetch('data.json?_='+Date.now())).json(); }catch(e){ return; }
  document.getElementById('gen').textContent='updated '+(d.generated||'');
  const s=d.shadow||{};
  const inb=(s.current_state==='IN_BTC');
  const pe=document.getElementById('pos');
  pe.textContent=inb?'🟢 IN BTC':'⚪️ IN CASH'; pe.className='pos '+(inb?'in-btc':'in-cash');
  const re=document.getElementById('ret'); re.textContent=pct(s.paper_return_pct); re.className='big '+cls(s.paper_return_pct);
  const bh=document.getElementById('bh'); bh.textContent=pct(s.buy_hold_pct); bh.className=cls(s.buy_hold_pct);
  document.getElementById('dd').textContent=(s.max_dd_pct!=null?s.max_dd_pct+'%':'—');
  document.getElementById('sh').textContent=(s.sharpe!=null?s.sharpe:'—');
  document.getElementById('days').textContent=(s.days_live!=null?s.days_live+' d':'—');
  document.getElementById('incep').textContent=s.inception||'—';
  document.getElementById('tr').textContent=(s.closed_trades!=null?s.closed_trades+' / '+(s.win_rate_pct||0)+'%':'—');
  const f=d.forward||{};
  document.getElementById('f_state').textContent=f.current_state||'—';
  const fr=document.getElementById('f_ret'); fr.textContent=pct(f.paper_return_pct); fr.className=cls(f.paper_return_pct);
  document.getElementById('f_bh').textContent=pct(f.buy_hold_pct);
  document.getElementById('f_30').textContent=pct(f.last30d_pct);
  document.getElementById('f_dd').textContent=(f.max_dd_pct!=null?f.max_dd_pct+'%':'—');
  document.getElementById('f_sh').textContent=(f.sharpe!=null?f.sharpe:'—');
  document.getElementById('f_px').textContent=(f.last_close!=null?Number(f.last_close).toLocaleString():'—');
  let eh=''; const el=d.eligibility, au=d.authorized||{};
  const pairs=(au.eligible||au.allowed||au.pairs||el.eligible||[]);
  if(Array.isArray(pairs)&&pairs.length){ eh+='<div style="margin-bottom:8px">'+pairs.map(p=>'<span class="pill ok">'+p+'</span>').join(' ')+'</div>'; }
  if(au.max_leverage!=null) eh+='<div class="row"><span>max leverage</span><span class="a">'+au.max_leverage+'x</span></div>';
  const forb=au.forbidden_pairs||au.forbidden||[];
  if(Array.isArray(forb)&&forb.length) eh+='<div class="row"><span>forbidden</span><span class="r">'+forb.slice(0,8).join(', ')+'</span></div>';
  if(!eh) eh='<div class="row"><span>status</span><span class="c">guard active — BTC-only eligible</span></div>';
  document.getElementById('elig').innerHTML=eh;
  const t=d.track||[];
  if(t.length){
    const labels=t.map(r=>r.date);
    const pa=t.map(r=>parseFloat(r.paper_return_pct));
    const bhh=t.map(r=>parseFloat(r.buy_hold_pct));
    if(window._ch){window._ch.data.labels=labels;window._ch.data.datasets[0].data=pa;window._ch.data.datasets[1].data=bhh;window._ch.update();}
    else{window._ch=new Chart(document.getElementById('chart'),{type:'line',
      data:{labels,datasets:[
        {label:'MA50W10 paper %',data:pa,borderColor:'#22c55e',backgroundColor:'rgba(34,197,94,.1)',tension:.2,fill:true},
        {label:'buy & hold %',data:bhh,borderColor:'#94a3b8',borderDash:[5,4],tension:.2,fill:false}]},
      options:{plugins:{legend:{labels:{color:'#94a3b8'}}},scales:{x:{ticks:{color:'#64748b'},grid:{color:'#1f2937'}},y:{ticks:{color:'#64748b'},grid:{color:'#1f2937'}}}}});}
  }
  let lb=d.leaderboard; if(lb&&!Array.isArray(lb)) lb=lb.rows||lb.leaderboard||Object.values(lb);
  if(Array.isArray(lb)&&lb.length){
    const keys=['strategy','pair','total_return','cagr','sharpe','max_dd','trades'];
    let h='<table><tr>'+keys.map(k=>'<th>'+k+'</th>').join('')+'</tr>';
    lb.slice(0,30).forEach(r=>{h+='<tr>'+keys.map(k=>{let v=r[k];if(typeof v==='number')v=v.toFixed(2);return '<td>'+(v==null?'—':v)+'</td>';}).join('')+'</tr>';});
    document.getElementById('lb').innerHTML=h+'</table>';
  } else { document.getElementById('lb').innerHTML='<div class="row"><span>leaderboard</span><span>—</span></div>'; }
}
load(); setInterval(load,60000);
</script></body></html>"""

open(os.path.join(DASH, "index.html"), "w").write(HTML)
print(f"dashboard: wrote {DASH}/index.html + data.json "
      f"(shadow={bool(data['shadow'])} forward={bool(data['forward'])} track={len(data['track'])})")
