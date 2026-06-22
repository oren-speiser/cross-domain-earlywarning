"""
build.py - assemble the self-contained demo (index.html) from the processed data.

Reads data/processed/{engine,battery,bearing}.json, attaches per-domain metadata,
embeds everything inline, and writes index.html (no server / no fetch needed).
Run the three analysis/*.py scripts first to (re)generate the processed data.
"""
import os, json

ROOT = os.path.dirname(os.path.abspath(__file__))
P = ROOT

eng = json.load(open(os.path.join(P, "engine.json")))
for e in eng:
    e["label"] = "Engine " + str(e["id"])
eng = sorted(eng, key=lambda e: 0 if e["id"] == 34 else 1)      # lead-18 engine first
batt = [b for b in json.load(open(os.path.join(P, "battery.json"))) if b["fail"] is not None]
bear = json.load(open(os.path.join(P, "bearing.json")))

domains = [
    dict(key="engine", name="Turbofan engine", source="NASA C-MAPSS benchmark \u00b7 high-fidelity simulation",
         summary="99 of 100 engines warned \u00b7 median 16 cycles of advance warning \u00b7 alarm at 92% of life",
         xlabel="engine cycle", xtime=False, leadunit="cyc", leadscale=1, units=eng),
    dict(key="battery", name="Li-ion battery", source="NASA Li-ion aging \u00b7 real measured cells",
         summary="Real measured battery cells \u00b7 18 to 42 discharge cycles of advance warning",
         xlabel="discharge cycle", xtime=False, leadunit="cyc", leadscale=1, units=batt),
    dict(key="bearing", name="Bearing", source="FEMTO PRONOSTIA \u00b7 real measured run-to-failure",
         summary="Abrupt mechanical failure \u00b7 still flagged 2 to 5 minutes before the bearing lets go",
         xlabel="elapsed time (min)", xtime=True, leadunit="s", leadscale=10, units=bear),
]
data_txt = json.dumps(dict(domains=domains))

TEMPLATE = r'''<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>One Detector, Three Machines — Failure Called Early</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Space+Grotesk:wght@400;500;600;700&family=IBM+Plex+Mono:wght@400;500;600&display=swap" rel="stylesheet">
<style>
  :root{
    --bg:#0B0E14;--panel:#11161F;--panel2:#0E131B;--grid:#1A2130;
    --txt:#D6DBE3;--muted:#5C6675;--dim:#39424F;
    --teal:#35D0BE;--amber:#F2A93B;--red:#E5484D;
    --mono:'IBM Plex Mono',ui-monospace,monospace;--disp:'Space Grotesk',system-ui,sans-serif;}
  *{margin:0;padding:0;box-sizing:border-box}
  html,body{background:var(--bg);color:var(--txt);font-family:var(--disp)}
  body{min-height:100vh;display:flex;flex-direction:column;align-items:center;
       padding:clamp(20px,5vw,60px) clamp(16px,4vw,32px);line-height:1.5;-webkit-font-smoothing:antialiased}
  .wrap{width:100%;max-width:940px}
  .eyebrow{font-family:var(--mono);font-size:11.5px;letter-spacing:.2em;color:var(--muted);
           text-transform:uppercase;display:flex;gap:10px;align-items:center}
  .eyebrow .dot{width:6px;height:6px;border-radius:50%;background:var(--teal);
           box-shadow:0 0 10px var(--teal);animation:pulse 2.4s ease-in-out infinite}
  @keyframes pulse{0%,100%{opacity:.4}50%{opacity:1}}
  h1{font-weight:600;font-size:clamp(32px,5.6vw,58px);letter-spacing:-.025em;margin:16px 0 10px;line-height:1.0}
  .lede{color:var(--muted);max-width:62ch;font-size:clamp(14px,1.7vw,16px)}
  .lede b{color:var(--txt);font-weight:500}

  .console{margin-top:26px;background:linear-gradient(180deg,var(--panel),var(--panel2));
     border:1px solid #1B2230;border-radius:14px;overflow:hidden;
     box-shadow:0 24px 60px -28px #000,inset 0 1px 0 #ffffff08}

  .domainbar{display:flex;align-items:center;justify-content:space-between;gap:12px;flex-wrap:wrap;
     padding:12px 14px;border-bottom:1px solid #1A212F;background:#0E131B}
  .seg{display:inline-flex;background:#0A0E15;border:1px solid #212a39;border-radius:9px;padding:3px;gap:2px}
  .seg button{font-family:var(--disp);font-weight:500;font-size:13px;color:var(--muted);
     background:transparent;border:none;padding:7px 13px;border-radius:6px;cursor:pointer;transition:.16s;white-space:nowrap}
  .seg button:hover{color:var(--txt)}
  .seg button.on{background:#172230;color:var(--teal);box-shadow:inset 0 0 0 1px #2b6b63}
  .source{font-family:var(--mono);font-size:10.5px;letter-spacing:.04em;color:var(--dim);text-align:right}

  .statusbar{display:flex;align-items:center;justify-content:space-between;gap:16px;
     padding:14px 18px;border-bottom:1px solid #1A212F;font-family:var(--mono);transition:background .35s}
  .statusbar .badge{display:flex;align-items:center;gap:9px;font-weight:600;font-size:13px;letter-spacing:.14em;text-transform:uppercase}
  .statusbar .badge .led{width:9px;height:9px;border-radius:50%;background:currentColor;box-shadow:0 0 12px currentColor}
  .statusbar .detail{font-size:12.5px;color:var(--muted);text-align:right}
  .s-nominal{color:var(--teal)} .s-warn{color:var(--amber)} .s-fail{color:var(--red)}
  .statusbar.bg-warn{background:linear-gradient(180deg,#2a1e0833,transparent)}
  .statusbar.bg-fail{background:linear-gradient(180deg,#2a0c0d44,transparent)}

  .plot{position:relative;padding:6px 6px 0}
  canvas{display:block;width:100%;height:auto}

  .readouts{display:grid;grid-template-columns:repeat(4,1fr);gap:1px;background:#1A212F;border-top:1px solid #1A212F}
  .ro{background:var(--panel);padding:13px 16px}
  .ro .k{font-family:var(--mono);font-size:10px;letter-spacing:.14em;color:var(--muted);text-transform:uppercase}
  .ro .v{font-family:var(--mono);font-size:19px;font-weight:500;margin-top:5px;font-variant-numeric:tabular-nums}
  @media(max-width:560px){.readouts{grid-template-columns:repeat(2,1fr)}}

  .controls{display:flex;align-items:center;gap:14px;flex-wrap:wrap;padding:15px 18px;border-top:1px solid #1A212F;background:var(--panel2)}
  .playbtn{width:42px;height:42px;border-radius:50%;border:1px solid #2A3342;background:#161C27;color:var(--teal);
     cursor:pointer;display:grid;place-items:center;flex:0 0 auto;transition:.18s}
  .playbtn:hover{border-color:var(--teal);background:#192230}
  .playbtn svg{width:18px;height:18px}
  input[type=range]{-webkit-appearance:none;appearance:none;flex:1 1 160px;height:4px;border-radius:3px;background:#222B39;outline:none;cursor:pointer}
  input[type=range]::-webkit-slider-thumb{-webkit-appearance:none;width:15px;height:15px;border-radius:50%;background:var(--txt);border:2px solid var(--bg);cursor:pointer}
  input[type=range]::-moz-range-thumb{width:15px;height:15px;border-radius:50%;background:var(--txt);border:2px solid var(--bg);cursor:pointer}
  .unitsel{display:flex;gap:6px;flex-wrap:wrap;width:100%;margin-top:2px}
  .unitsel .lbl{font-family:var(--mono);font-size:10px;letter-spacing:.14em;color:var(--muted);text-transform:uppercase;align-self:center;margin-right:2px}
  .chip{font-family:var(--mono);font-size:11.5px;padding:5px 10px;border-radius:7px;border:1px solid #232C3A;background:#141A24;color:var(--muted);cursor:pointer;transition:.15s;font-variant-numeric:tabular-nums}
  .chip:hover{border-color:#374252;color:var(--txt)}
  .chip.on{border-color:var(--teal);color:var(--teal);background:#10201e}

  .summary{margin-top:20px;font-family:var(--mono);font-size:13px;color:var(--txt);
     background:var(--panel2);border:1px solid #1B2230;border-left:3px solid var(--teal);
     border-radius:10px;padding:15px 18px;line-height:1.6}
  .crossline{font-family:var(--disp);font-size:clamp(15px,2vw,18px);color:var(--muted);margin-top:22px;text-align:center}
  .crossline b{color:var(--txt);font-weight:600}
  .foot{font-family:var(--mono);font-size:11px;line-height:1.7;color:var(--dim);margin-top:18px;max-width:84ch}
  .foot b{color:var(--muted);font-weight:500}
</style>
</head>
<body>
<div class="wrap">
  <div class="eyebrow"><span class="dot"></span>Cross-domain prognostic early-warning</div>
  <h1>One detector. Three machines.<br>Failure, called early.</h1>
  <p class="lede">The same early-warning detector watches a <b>jet engine</b>, a <b>battery</b>, and a <b>bearing</b> degrade in real time, and flags the failure <b>before it happens</b>. Switch the machine. Press play.</p>

  <div class="console">
    <div class="domainbar">
      <div class="seg" id="seg"></div>
      <div class="source" id="source"></div>
    </div>
    <div class="statusbar" id="statusbar">
      <div class="badge s-nominal" id="badge"><span class="led"></span><span id="badgetext">Nominal</span></div>
      <div class="detail" id="detail">Monitoring health margin…</div>
    </div>
    <div class="plot"><canvas id="cv"></canvas></div>
    <div class="readouts">
      <div class="ro"><div class="k">Reading</div><div class="v" id="r-cycle">—</div></div>
      <div class="ro"><div class="k">Health margin</div><div class="v" id="r-margin">—</div></div>
      <div class="ro"><div class="k">Projected time to failure</div><div class="v" id="r-ttx">—</div></div>
      <div class="ro"><div class="k">Advance warning</div><div class="v" id="r-lead">—</div></div>
    </div>
    <div class="controls">
      <button class="playbtn" id="play" aria-label="Play"></button>
      <input type="range" id="scrub" min="0" max="100" value="0" step="1" aria-label="Scrub">
      <div class="unitsel" id="unitsel"><span class="lbl">Unit</span></div>
    </div>
  </div>

  <div class="summary" id="summary"></div>
  <div class="crossline">One detector. Three systems: <b>jet propulsion</b>, <b>energy storage</b>, <b>rotating machinery</b>.</div>
  <p class="foot">Engine = NASA C-MAPSS turbofan benchmark (high-fidelity simulation). Battery and bearing = <b>real measured</b> run-to-failure data (NASA Li-ion aging; FEMTO PRONOSTIA). The detector is the same in all three; only the result is shown, the internals are not exposed.</p>
</div>

<script>
const DATA = /*__DATA__*/;
const domains = DATA.domains;
const cv=document.getElementById('cv'),ctx=cv.getContext('2d');
const C={bg:'#0B0E14',grid:'#1A2130',muted:'#5C6675',dim:'#39424F',txt:'#D6DBE3',teal:'#35D0BE',amber:'#F2A93B',red:'#E5484D'};
let dom=domains[0], cur=dom.units[0], cyc=0, playing=false, raf=null, last=0;
const RUN_MS=6500;
const reduce=window.matchMedia('(prefers-reduced-motion: reduce)').matches;

// domain segmented control
const seg=document.getElementById('seg');
domains.forEach((d,i)=>{const b=document.createElement('button');b.textContent=d.name;
  b.onclick=()=>{dom=d;cur=d.units[0];buildUnits();syncSeg();resetTo(0);pause();updateSource();updateSummary();size();
    if(!reduce)setTimeout(play,250);};seg.appendChild(b);});
function syncSeg(){[...seg.children].forEach((b,i)=>b.classList.toggle('on',domains[i]===dom));}
function updateSource(){document.getElementById('source').textContent=dom.source;}
function updateSummary(){document.getElementById('summary').textContent=dom.summary;}

const us=document.getElementById('unitsel');
function buildUnits(){
  [...us.querySelectorAll('.chip')].forEach(c=>c.remove());
  dom.units.forEach(u=>{const b=document.createElement('button');b.className='chip';b.textContent=u.label;
    b.onclick=()=>{cur=u;resetTo(0);pause();syncChips();if(!reduce)setTimeout(play,200);};b.dataset.l=u.label;us.appendChild(b);});
  syncChips();
}
function syncChips(){[...us.querySelectorAll('.chip')].forEach(c=>c.classList.toggle('on',c.dataset.l===cur.label));}

function fmtLead(snaps){const v=snaps*dom.leadscale;
  if(dom.leadunit==='s'){return v>=120?(v/60).toFixed(1)+' min':v+' s';} return v+' cyc';}
function fmtTtx(t){const v=t*dom.leadscale;
  if(dom.leadunit==='s'){return v>=120?'~'+(v/60).toFixed(1)+' min':'~'+Math.round(v)+' s';} return '~'+Math.round(v)+' cyc';}

function size(){const w=cv.parentElement.clientWidth-12,h=Math.max(228,Math.min(322,w*0.46)),dpr=window.devicePixelRatio||1;
  cv.width=w*dpr;cv.height=h*dpr;cv.style.height=h+'px';ctx.setTransform(dpr,0,0,dpr,0,0);draw();}
window.addEventListener('resize',size);
function bounds(){let mn=Math.min(0,...cur.margin),mx=Math.max(...cur.margin);const pad=(mx-mn)*0.10;
  return {ymin:mn-pad*1.4,ymax:mx+pad,xmax:cur.life-1};}
function draw(){
  const W=cv.clientWidth,H=cv.clientHeight,L=52,R=14,T=16,B=30,pw=W-L-R,ph=H-T-B;
  const {ymin,ymax,xmax}=bounds(),X=i=>L+(i/xmax)*pw,Y=v=>T+(1-(v-ymin)/(ymax-ymin))*ph;
  ctx.clearRect(0,0,W,H);ctx.font='10px "IBM Plex Mono"';ctx.textBaseline='middle';
  for(let g=0;g<=4;g++){const v=ymin+(ymax-ymin)*g/4,y=Y(v);ctx.strokeStyle=C.grid;ctx.lineWidth=1;
    ctx.beginPath();ctx.moveTo(L,y);ctx.lineTo(W-R,y);ctx.stroke();ctx.fillStyle=C.dim;ctx.textAlign='right';ctx.fillText(v.toFixed(1),L-8,y);}
  ctx.textAlign='center';ctx.textBaseline='top';
  for(let g=0;g<=4;g++){const xi=Math.round(xmax*g/4);ctx.fillStyle=C.dim;ctx.fillText(dom.xtime?Math.round(xi*10/60)+'m':xi,X(xi),H-B+8);}
  ctx.fillStyle=C.muted;ctx.font='9px "IBM Plex Mono"';
  ctx.save();ctx.translate(13,T+ph/2);ctx.rotate(-Math.PI/2);ctx.textAlign='center';ctx.fillText('HEALTH MARGIN',0,0);ctx.restore();
  ctx.textAlign='center';ctx.fillText(dom.xlabel.toUpperCase(),L+pw/2,H-12);
  const y0=Y(0);ctx.strokeStyle=C.red;ctx.globalAlpha=.5;ctx.setLineDash([5,5]);
  ctx.beginPath();ctx.moveTo(L,y0);ctx.lineTo(W-R,y0);ctx.stroke();ctx.setLineDash([]);ctx.globalAlpha=1;
  ctx.fillStyle=C.red;ctx.globalAlpha=.7;ctx.textAlign='left';ctx.font='9px "IBM Plex Mono"';ctx.fillText('FAILURE LEVEL',L+4,y0-7);ctx.globalAlpha=1;
  const upto=Math.max(1,Math.round(cyc)),w=cur.warn,f=cur.fail;
  function seg2(a,b,col){if(b<a||b<0)return;ctx.strokeStyle=col;ctx.lineWidth=2.2;ctx.lineJoin='round';
    ctx.beginPath();for(let i=a;i<=b;i++){const x=X(i),y=Y(cur.margin[i]);i===a?ctx.moveTo(x,y):ctx.lineTo(x,y);}ctx.stroke();}
  if(w===null){seg2(0,Math.min(upto,xmax),C.teal);}
  else{seg2(0,Math.min(upto,w),C.teal);if(upto>w)seg2(w,Math.min(upto,f),C.amber);if(upto>f)seg2(f,Math.min(upto,xmax),C.red);}
  if(w!==null&&upto>=w){const x=X(w),y=Y(cur.margin[w]);ctx.strokeStyle=C.amber;ctx.lineWidth=2;
    ctx.beginPath();ctx.arc(x,y,7,0,7);ctx.stroke();ctx.fillStyle=C.amber;ctx.globalAlpha=.18;ctx.beginPath();ctx.arc(x,y,7,0,7);ctx.fill();ctx.globalAlpha=1;}
  if(upto>=f){const x=X(f),y=Y(cur.margin[f]);ctx.fillStyle=C.red;ctx.beginPath();ctx.moveTo(x,y-8);ctx.lineTo(x-6,y-18);ctx.lineTo(x+6,y-18);ctx.closePath();ctx.fill();}
  const px=X(Math.min(upto,xmax));ctx.strokeStyle='#7d8aa0';ctx.globalAlpha=.55;ctx.lineWidth=1;
  ctx.beginPath();ctx.moveTo(px,T);ctx.lineTo(px,H-B);ctx.stroke();ctx.globalAlpha=1;
  const hy=Y(cur.margin[Math.min(upto,xmax)]);ctx.fillStyle=(w!==null&&upto>=f)?C.red:(w!==null&&upto>=w)?C.amber:C.teal;
  ctx.beginPath();ctx.arc(px,hy,3.4,0,7);ctx.fill();
}
function setStatus(){
  const ci=Math.round(cyc),w=cur.warn,f=cur.fail,lead=(w!==null)?f-w:null;
  const sb=document.getElementById('statusbar'),badge=document.getElementById('badge'),bt=document.getElementById('badgetext'),det=document.getElementById('detail');
  sb.classList.remove('bg-warn','bg-fail');badge.className='badge';
  if(w===null||ci<w){badge.classList.add('s-nominal');bt.textContent='Nominal';det.textContent='Monitoring health margin…';}
  else if(ci<f){badge.classList.add('s-warn');sb.classList.add('bg-warn');bt.textContent='Early warning';det.textContent='Failure approaching · alarm latched at '+w;}
  else{badge.classList.add('s-fail');sb.classList.add('bg-fail');bt.textContent='Failure';det.textContent='Failed · warning was issued '+fmtLead(lead)+' earlier';}
  document.getElementById('r-cycle').textContent=ci+' / '+(cur.life-1);
  document.getElementById('r-margin').textContent=cur.margin[Math.min(ci,cur.fail)].toFixed(2);
  const t=cur.ttx[Math.min(ci,cur.fail)];
  document.getElementById('r-ttx').textContent=(w!==null&&ci>=w)?(ci>=f?'0':fmtTtx(t)):'—';
  const rl=document.getElementById('r-lead');
  if(w===null||ci<w){rl.textContent='—';rl.style.color=C.txt;}
  else if(ci<f){rl.textContent=fmtLead(lead);rl.style.color=C.amber;}
  else{rl.textContent=fmtLead(lead);rl.style.color=C.teal;}
  document.getElementById('scrub').value=Math.round(cyc/(cur.life-1)*100);
}
function frame(t){if(!last)last=t;const dt=t-last;last=t;cyc+=(cur.life-1)*(dt/RUN_MS);
  if(cyc>=cur.fail){cyc=cur.fail;playing=false;render();setIcon();return;}render();raf=requestAnimationFrame(frame);}
function render(){draw();setStatus();}
function play(){if(playing)return;if(Math.round(cyc)>=cur.fail)cyc=0;playing=true;last=0;raf=requestAnimationFrame(frame);setIcon();}
function pause(){playing=false;if(raf)cancelAnimationFrame(raf);setIcon();}
function resetTo(v){cyc=v;render();}
function setIcon(){document.getElementById('play').innerHTML=playing
  ?'<svg viewBox="0 0 24 24" fill="currentColor"><rect x="6" y="5" width="4" height="14" rx="1"/><rect x="14" y="5" width="4" height="14" rx="1"/></svg>'
  :'<svg viewBox="0 0 24 24" fill="currentColor"><path d="M8 5v14l11-7z"/></svg>';}
document.getElementById('play').onclick=()=>playing?pause():play();
document.getElementById('scrub').oninput=e=>{pause();cyc=(+e.target.value/100)*(cur.life-1);render();};

syncSeg();buildUnits();updateSource();updateSummary();size();setIcon();
if(!reduce){setTimeout(play,650);}else{cyc=cur.fail;render();}
</script>
</body>
</html>'''
open(os.path.join(ROOT, "index.html"), "w").write(TEMPLATE.replace("/*__DATA__*/", data_txt))
print("wrote index.html")
