"""Generate the self-contained Aid Desert Finder page from exported Snowflake data."""
import json
import pathlib

SCRATCH = pathlib.Path(
    r"C:\Users\ncai\AppData\Local\Temp\claude"
    r"\c--Users-ncai-Desktop-Weekend-challanges-WhereNeedMeetsNothing"
    r"\71a68099-9b7d-4442-a9fd-265506df551f\scratchpad"
)
# index.html so the folder deploys to any static host (Vercel, Pages) as-is
OUT = pathlib.Path(
    r"c:\Users\ncai\Desktop\Weekend challanges\WhereNeedMeetsNothing"
    r"\standalone\index.html"
)
OUT.parent.mkdir(parents=True, exist_ok=True)

data = json.loads((SCRATCH / "aid_desert_data.json").read_text(encoding="utf-8"))
payload = json.dumps(data, separators=(",", ":"))

HEAD = r"""<title>Aid Desert Finder</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Archivo:wght@600;700;800&family=Public+Sans:wght@400;500;600&family=IBM+Plex+Mono:wght@400;500&display=swap">
<style>
:root{
  color-scheme: light;
  --ground:#f2f5f8; --surface:#ffffff; --surface-2:#f8fafc;
  --ink:#0e1216; --ink-2:#4d5661; --ink-3:#7d8792;
  --hair:#e0e6ec; --hair-2:#eef2f6;
  --accent:#1c5cab;
  --s1:#cde2fb; --s2:#9ec5f4; --s3:#6da7ec; --s4:#3987e5;
  --s5:#256abf; --s6:#184f95; --s7:#0d366b;
  --on-deep:#ffffff;
  --shadow:0 1px 2px rgba(14,18,22,.05), 0 8px 24px -12px rgba(14,18,22,.18);
}
@media (prefers-color-scheme: dark){
  :root:not([data-theme="light"]){
    color-scheme: dark;
    --ground:#0b0e11; --surface:#151a1f; --surface-2:#1b2127;
    --ink:#f4f7fa; --ink-2:#b6bfc9; --ink-3:#828c97;
    --hair:#262d35; --hair-2:#1e242b;
    --accent:#6da7ec;
    --s1:#184f95; --s2:#1c5cab; --s3:#256abf; --s4:#3987e5;
    --s5:#5598e7; --s6:#86b6ef; --s7:#cde2fb;
    --on-deep:#0b0e11;
    --shadow:0 1px 2px rgba(0,0,0,.4), 0 8px 24px -12px rgba(0,0,0,.6);
  }
}
:root[data-theme="dark"]{
  color-scheme: dark;
  --ground:#0b0e11; --surface:#151a1f; --surface-2:#1b2127;
  --ink:#f4f7fa; --ink-2:#b6bfc9; --ink-3:#828c97;
  --hair:#262d35; --hair-2:#1e242b;
  --accent:#6da7ec;
  --s1:#184f95; --s2:#1c5cab; --s3:#256abf; --s4:#3987e5;
  --s5:#5598e7; --s6:#86b6ef; --s7:#cde2fb;
  --on-deep:#0b0e11;
  --shadow:0 1px 2px rgba(0,0,0,.4), 0 8px 24px -12px rgba(0,0,0,.6);
}

*{box-sizing:border-box}
body{
  margin:0; background:var(--ground); color:var(--ink);
  font-family:"Public Sans",system-ui,-apple-system,"Segoe UI",sans-serif;
  font-size:15px; line-height:1.55;
  -webkit-font-smoothing:antialiased;
}
.wrap{max-width:1240px; margin:0 auto; padding:32px 24px 64px; display:flex; flex-direction:column; gap:24px}

/* ---------- header ---------- */
.masthead{display:flex; flex-wrap:wrap; align-items:flex-end; justify-content:space-between; gap:16px}
.eyebrow{
  font-family:"IBM Plex Mono",ui-monospace,monospace; font-size:11px; font-weight:500;
  letter-spacing:.14em; text-transform:uppercase; color:var(--ink-3); margin:0 0 6px;
}
h1{
  font-family:Archivo,system-ui,sans-serif; font-weight:800; font-size:clamp(28px,4vw,40px);
  letter-spacing:-.022em; line-height:1.05; margin:0; text-wrap:balance;
}
.sub{margin:8px 0 0; color:var(--ink-2); max-width:62ch}
.provenance{
  font-family:"IBM Plex Mono",ui-monospace,monospace; font-size:11.5px; color:var(--ink-3);
  text-align:right; line-height:1.7; white-space:nowrap;
}
.provenance b{color:var(--ink-2); font-weight:500}

/* ---------- stat strip ---------- */
.stats{display:grid; grid-template-columns:repeat(auto-fit,minmax(190px,1fr)); gap:1px;
  background:var(--hair); border:1px solid var(--hair); border-radius:10px; overflow:hidden}
.stat{background:var(--surface); padding:16px 18px; display:flex; flex-direction:column; gap:3px}
.stat .k{font-family:"IBM Plex Mono",monospace; font-size:10.5px; letter-spacing:.11em;
  text-transform:uppercase; color:var(--ink-3)}
.stat .v{font-family:Archivo,sans-serif; font-weight:700; font-size:26px; letter-spacing:-.02em; line-height:1.15}
.stat .n{font-size:12.5px; color:var(--ink-2)}

/* ---------- panels ---------- */
.grid{display:grid; grid-template-columns:minmax(0,1.32fr) minmax(0,1fr); gap:20px; align-items:start}
@media (max-width:980px){.grid{grid-template-columns:1fr}}
.panel{background:var(--surface); border:1px solid var(--hair); border-radius:12px; box-shadow:var(--shadow)}
.panel-head{display:flex; align-items:center; justify-content:space-between; gap:12px;
  padding:14px 18px; border-bottom:1px solid var(--hair-2); flex-wrap:wrap}
.panel-head h2{font-family:Archivo,sans-serif; font-size:14px; font-weight:700;
  letter-spacing:.01em; margin:0}
.panel-head .hint{font-size:12px; color:var(--ink-3)}

/* ---------- metric toggle ---------- */
.seg{display:flex; gap:2px; background:var(--surface-2); border:1px solid var(--hair);
  border-radius:8px; padding:2px}
.seg button{
  font:inherit; font-size:12px; font-weight:500; color:var(--ink-2);
  background:transparent; border:0; border-radius:6px; padding:5px 10px; cursor:pointer;
  white-space:nowrap;
}
.seg button:hover{color:var(--ink); background:var(--hair-2)}
.seg button[aria-pressed="true"]{background:var(--accent); color:var(--on-deep); font-weight:600}
.seg button:focus-visible{outline:2px solid var(--accent); outline-offset:2px}

/* ---------- map ---------- */
.mapwrap{position:relative; padding:8px 12px 14px}
svg.map{width:100%; height:auto; display:block}
svg.map path{stroke:var(--surface); stroke-width:.6; cursor:pointer; transition:opacity .12s}
svg.map path:focus{outline:none}
svg.map path.on{stroke:var(--ink); stroke-width:1.6}
svg.map.dim path:not(.on){opacity:.35}

.legend{display:flex; align-items:center; gap:10px; padding:0 18px 16px; flex-wrap:wrap}
.ramp{display:flex; height:9px; border-radius:2px; overflow:hidden; flex:1; min-width:160px; max-width:320px}
.ramp i{flex:1}
.legend .lbl{font-family:"IBM Plex Mono",monospace; font-size:10.5px; color:var(--ink-3);
  letter-spacing:.04em; white-space:nowrap}

.tip{
  position:fixed; z-index:20; pointer-events:none; opacity:0; transform:translateY(-2px);
  transition:opacity .1s; background:var(--surface); border:1px solid var(--hair);
  border-radius:9px; box-shadow:var(--shadow); padding:10px 12px; min-width:184px;
}
.tip.show{opacity:1}
.tip h3{font-family:Archivo,sans-serif; font-size:13.5px; font-weight:700; margin:0 0 7px}
.tip dl{display:grid; grid-template-columns:auto auto; gap:3px 14px; margin:0;
  font-size:12px; font-variant-numeric:tabular-nums}
.tip dt{color:var(--ink-3)}
.tip dd{margin:0; text-align:right; color:var(--ink); font-weight:500}

/* ---------- table ---------- */
.tablescroll{max-height:560px; overflow:auto}
table{width:100%; border-collapse:collapse; font-variant-numeric:tabular-nums}
thead th{
  position:sticky; top:0; background:var(--surface); z-index:1;
  font-family:"IBM Plex Mono",monospace; font-weight:500; font-size:10px; letter-spacing:.09em;
  text-transform:uppercase; color:var(--ink-3); text-align:right;
  padding:9px 12px; border-bottom:1px solid var(--hair);
}
thead th:first-child{text-align:left}
tbody td{padding:8px 12px; border-bottom:1px solid var(--hair-2); font-size:13px; text-align:right}
tbody td:first-child{text-align:left; font-weight:500}
tbody tr{cursor:pointer}
tbody tr:hover{background:var(--surface-2)}
tbody tr.on{background:var(--surface-2)}
tbody tr.on td:first-child{box-shadow:inset 3px 0 0 var(--accent)}
.rank{font-family:"IBM Plex Mono",monospace; font-size:11px; color:var(--ink-3); margin-right:8px}
.chip{display:inline-flex; align-items:center; gap:6px}
.dot{width:9px; height:9px; border-radius:2px; flex:none}

/* ---------- q&a ---------- */
.qa{padding:16px 18px 18px; display:flex; flex-direction:column; gap:12px}
.q{display:flex; gap:10px; align-items:baseline}
.q .mark{font-family:"IBM Plex Mono",monospace; font-size:11px; color:var(--ink-3); flex:none}
.q p{margin:0; font-size:15px; font-weight:500}
pre{
  margin:0; background:var(--surface-2); border:1px solid var(--hair-2); border-radius:8px;
  padding:12px 14px; overflow-x:auto; font-family:"IBM Plex Mono",monospace;
  font-size:11.5px; line-height:1.65; color:var(--ink-2);
}
.answer{font-size:13.5px; color:var(--ink-2); margin:0}
.answer b{color:var(--ink); font-weight:600}

/* ---------- method ---------- */
.method{padding:16px 18px 20px; display:grid; grid-template-columns:repeat(auto-fit,minmax(230px,1fr)); gap:18px}
.method h3{font-family:"IBM Plex Mono",monospace; font-size:10.5px; letter-spacing:.1em;
  text-transform:uppercase; color:var(--ink-3); margin:0 0 6px; font-weight:500}
.method p{margin:0; font-size:13px; color:var(--ink-2)}
.method code{font-family:"IBM Plex Mono",monospace; font-size:11.5px; color:var(--ink)}
footer{color:var(--ink-3); font-size:12px; text-align:center; padding-top:4px}

@media (prefers-reduced-motion:reduce){*{transition:none !important}}
</style>"""

BODY = r"""
<div class="wrap">

  <header class="masthead">
    <div>
      <p class="eyebrow">Snowflake Public Data &middot; zero ETL</p>
      <h1>Where need meets nothing</h1>
      <p class="sub">Florida counties ranked by disaster exposure, poverty, and how few
      doctors are actually there. Aid deserts are where all three line up.</p>
    </div>
    <div class="provenance">
      <b>FEMA</b> disaster declarations &middot; 10 yr<br>
      <b>Census ACS</b> 5-year &middot; __ACS__<br>
      <b>NPPES</b> active practitioners<br>
      67 counties &middot; one joined view
    </div>
  </header>

  <section class="stats" id="stats"></section>

  <div class="grid">
    <section class="panel">
      <div class="panel-head">
        <h2>Aid desert map</h2>
        <div class="seg" id="seg" role="group" aria-label="Colour the map by"></div>
      </div>
      <div class="mapwrap"><svg class="map" id="map" role="img"
           aria-label="Choropleth of Florida counties"></svg></div>
      <div class="legend">
        <span class="lbl" id="lo"></span>
        <span class="ramp" id="ramp"></span>
        <span class="lbl" id="hi"></span>
        <span class="lbl" id="metricname"></span>
      </div>
    </section>

    <section class="panel">
      <div class="panel-head">
        <h2 id="tabletitle">Ranked counties</h2>
        <span class="hint">hover to locate</span>
      </div>
      <div class="tablescroll">
        <table>
          <thead><tr>
            <th>County</th><th>Disasters</th><th>Poverty</th><th>Docs&nbsp;/10k</th><th>Need</th>
          </tr></thead>
          <tbody id="tbody"></tbody>
        </table>
      </div>
    </section>
  </div>

  <section class="panel">
    <div class="panel-head">
      <h2>Asked in plain English</h2>
      <span class="hint">recorded from Cortex Analyst on the live warehouse</span>
    </div>
    <div class="qa">
      <div class="q"><span class="mark">Q</span><p>Which counties had disasters but fewest doctors?</p></div>
      <p class="answer">Cortex Analyst chose <b>doctors per 10,000 residents</b> over the raw
      headcount on its own, then wrote and ran this:</p>
      <pre>SELECT county_name, disaster_count, providers_per_10k, poverty_rate_pct, aid_desert_score
FROM aid_desert
WHERE disaster_count &gt; 0
ORDER BY providers_per_10k ASC
LIMIT 10</pre>
      <p class="answer">Top answer: <b>Glades County</b> &mdash; 14 disaster declarations,
      20.7 doctors per 10k, the thinnest coverage in the state.</p>
    </div>
  </section>

  <section class="panel">
    <div class="panel-head"><h2>How the score is built</h2></div>
    <div class="method">
      <div><h3>Composite</h3><p>Percentile rank across the 67 counties, weighted
        35% disaster frequency, 35% poverty rate, 30% scarcity of doctors per capita.
        Percentiles rather than divide-by-max, so one extreme county can't compress the scale.</p></div>
      <div><h3>Joining three datasets</h3><p>FEMA, Census and NPPES all carry a shared
        <code>GEO_ID</code>, so the join runs on that spine rather than FIPS codes.
        NPPES has no county id, so providers roll up from ZIP through the geography hierarchy.</p></div>
      <div><h3>Two traps</h3><p>NPPES stores mailing <em>and</em> practice addresses &mdash;
        counting both double-credits a doctor to two counties. And two counties have no ZIP
        children at all, so a ZIP-only rollup reports them as having zero doctors.</p></div>
      <div><h3>Check</h3><p>County population sums to <code>22.4M</code> against Florida's
        actual <code>22.6M</code> &mdash; the joins line up.</p></div>
    </div>
  </section>

  <footer>Built on the free Snowflake Public Data share. No ETL, no external geodata &mdash;
  county boundaries ship in the same share.</footer>
</div>

<div class="tip" id="tip" role="tooltip">
  <h3 id="tipname"></h3>
  <dl>
    <dt>Need score</dt><dd id="tscore"></dd>
    <dt>Disasters (10yr)</dt><dd id="tdis"></dd>
    <dt>Poverty</dt><dd id="tpov"></dd>
    <dt>Doctors</dt><dd id="tdoc"></dd>
    <dt>Doctors / 10k</dt><dd id="tper"></dd>
    <dt>Population</dt><dd id="tpop"></dd>
  </dl>
</div>

<script>
const DATA = __DATA__;
const C = DATA.counties;

const METRICS = [
  {id:'score', label:'Need score',   get:d=>d.score,  fmt:v=>v.toFixed(0),
   lo:'lower need', hi:'higher need', dir:1},
  {id:'per10k', label:'Doctors / 10k', get:d=>d.per10k, fmt:v=>v.toFixed(0),
   lo:'more doctors', hi:'fewer doctors', dir:-1},
  {id:'poverty', label:'Poverty rate', get:d=>d.poverty, fmt:v=>v.toFixed(1)+'%',
   lo:'lower', hi:'higher', dir:1},
  {id:'disasters', label:'Disasters', get:d=>d.disasters, fmt:v=>v.toFixed(0),
   lo:'fewer', hi:'more', dir:1}
];
let metric = METRICS[0];

const STEPS = ['--s1','--s2','--s3','--s4','--s5','--s6','--s7'];
const css = v => getComputedStyle(document.documentElement).getPropertyValue(v).trim();

/* Colour by QUANTILE, not equal interval. Doctor density is heavily right-skewed --
   Alachua has 351 per 10k against a median of 118 -- so equal-interval bins would put
   almost every county in one or two shades and hide the whole distribution. Quantile
   bins give each of the 7 steps roughly a seventh of the counties.
   dir = -1 means a LOW value is the severe end (few doctors = dark). */
const rankCache = new Map();
function ranksFor(m){
  if (!rankCache.has(m.id)){
    const order = [...C].sort((a,b) =>
      m.dir === -1 ? m.get(b) - m.get(a) : m.get(a) - m.get(b));
    const r = new Map();
    order.forEach((c,i) => r.set(c.id, i));
    rankCache.set(m.id, r);
  }
  return rankCache.get(m.id);
}
function binOf(d){
  const rank = ranksFor(metric).get(d.id);
  return Math.min(6, Math.floor(rank / C.length * 7));
}
const colorOf = d => css(STEPS[binOf(d)]);

/* ---- projection: equirectangular with cos(lat) correction ---- */
const W = 900, H = 620, PAD = 14;
function ringsOf(g){
  return g.type === 'Polygon' ? g.coordinates : g.coordinates.flat();
}
let lo0=180, la0=90, lo1=-180, la1=-90;
C.forEach(c => ringsOf(c.geom).forEach(r => r.forEach(p => {
  if(p[0]<lo0)lo0=p[0]; if(p[0]>lo1)lo1=p[0];
  if(p[1]<la0)la0=p[1]; if(p[1]>la1)la1=p[1];
})));
const kx = Math.cos((la0+la1)/2 * Math.PI/180);
const sx = (lo1-lo0) * kx, sy = (la1-la0);
const scale = Math.min((W-2*PAD)/sx, (H-2*PAD)/sy);
const ox = (W - sx*scale)/2, oy = (H - sy*scale)/2;
const px = lon => ox + (lon-lo0)*kx*scale;
const py = lat => oy + (la1-lat)*scale;

function pathOf(g){
  return ringsOf(g).map(r =>
    'M' + r.map(p => px(p[0]).toFixed(1)+','+py(p[1]).toFixed(1)).join('L') + 'Z'
  ).join('');
}

/* ---- render map ---- */
const map = document.getElementById('map');
/* crop the viewBox to the projected content so the state fills the panel
   instead of floating in dead space */
map.setAttribute('viewBox',
  `${ox-PAD} ${oy-PAD} ${sx*scale+2*PAD} ${sy*scale+2*PAD}`);
const paths = new Map();
C.forEach(c => {
  const p = document.createElementNS('http://www.w3.org/2000/svg','path');
  p.setAttribute('d', pathOf(c.geom));
  p.setAttribute('tabindex','0');
  p.setAttribute('role','img');
  p.dataset.id = c.id;
  p.addEventListener('mouseenter', e => focusCounty(c, e));
  p.addEventListener('mousemove', moveTip);
  p.addEventListener('mouseleave', blurCounty);
  p.addEventListener('focus', () => focusCounty(c, null));
  p.addEventListener('blur', blurCounty);
  map.appendChild(p);
  paths.set(c.id, p);
});

/* ---- tooltip ---- */
const tip = document.getElementById('tip');
const nf = n => n.toLocaleString('en-US');
function focusCounty(c, e){
  document.getElementById('tipname').textContent = c.name + ' County';
  document.getElementById('tscore').textContent = c.score.toFixed(0) + ' / 100';
  document.getElementById('tdis').textContent = c.disasters;
  document.getElementById('tpov').textContent = c.poverty.toFixed(1) + '%';
  document.getElementById('tdoc').textContent = nf(c.providers);
  document.getElementById('tper').textContent = c.per10k.toFixed(1);
  document.getElementById('tpop').textContent = nf(c.population);
  tip.classList.add('show');
  if (e) moveTip(e); else {
    const r = paths.get(c.id).getBoundingClientRect();
    place(r.left + r.width/2, r.top);
  }
  highlight(c.id);
}
function moveTip(e){ place(e.clientX + 16, e.clientY - 12); }
function place(x, y){
  const r = tip.getBoundingClientRect();
  tip.style.left = Math.min(x, innerWidth - r.width - 12) + 'px';
  tip.style.top  = Math.max(8, Math.min(y, innerHeight - r.height - 12)) + 'px';
}
function blurCounty(){ tip.classList.remove('show'); highlight(null); }

function highlight(id){
  map.classList.toggle('dim', !!id);
  paths.forEach((p,k) => p.classList.toggle('on', k === id));
  document.querySelectorAll('#tbody tr').forEach(tr =>
    tr.classList.toggle('on', tr.dataset.id === id));
}

/* ---- paint + table ---- */
function paint(){
  C.forEach(c => paths.get(c.id).setAttribute('fill', colorOf(c)));
  const ramp = document.getElementById('ramp');
  ramp.innerHTML = STEPS.map(s => `<i style="background:${css(s)}"></i>`).join('');
  document.getElementById('lo').textContent = metric.lo;
  document.getElementById('hi').textContent = metric.hi;
  document.getElementById('metricname').textContent = '\u2014 ' + metric.label;
}

function rows(){
  const sorted = [...C].sort((a,b) =>
    metric.dir === -1 ? metric.get(a)-metric.get(b) : metric.get(b)-metric.get(a));
  document.getElementById('tbody').innerHTML = sorted.map((c,i) => `
    <tr data-id="${c.id}">
      <td><span class="chip"><span class="rank">${String(i+1).padStart(2,'0')}</span>
        <span class="dot" style="background:${colorOf(c)}"></span>${c.name}</span></td>
      <td>${c.disasters}</td>
      <td>${c.poverty.toFixed(1)}%</td>
      <td>${c.per10k.toFixed(0)}</td>
      <td>${c.score.toFixed(0)}</td>
    </tr>`).join('');
  document.querySelectorAll('#tbody tr').forEach(tr => {
    const c = C.find(x => x.id === tr.dataset.id);
    tr.addEventListener('mouseenter', e => focusCounty(c, e));
    tr.addEventListener('mousemove', moveTip);
    tr.addEventListener('mouseleave', blurCounty);
  });
  document.getElementById('tabletitle').textContent =
    metric.id === 'score' ? 'Ranked counties' : 'Ranked by ' + metric.label.toLowerCase();
}

/* ---- stat strip ---- */
function stats(){
  const worst = [...C].sort((a,b)=>b.score-a.score)[0];
  const thin  = [...C].sort((a,b)=>a.per10k-b.per10k)[0];
  const poor  = [...C].sort((a,b)=>b.poverty-a.poverty)[0];
  const maxD  = [...C].sort((a,b)=>b.disasters-a.disasters)[0];
  document.getElementById('stats').innerHTML = [
    ['Counties analysed', '67', 'every Florida county'],
    ['Highest need', worst.name, `score ${worst.score.toFixed(0)} of 100`],
    ['Thinnest coverage', thin.name, `${thin.per10k.toFixed(1)} doctors per 10k`],
    ['Deepest poverty', poor.name, `${poor.poverty.toFixed(1)}% below the line`],
    ['Most disasters', maxD.name, `${maxD.disasters} declarations in 10 yr`]
  ].map(([k,v,n]) => `<div class="stat"><span class="k">${k}</span>
      <span class="v">${v}</span><span class="n">${n}</span></div>`).join('');
}

/* ---- metric toggle ---- */
document.getElementById('seg').innerHTML = METRICS.map(m =>
  `<button type="button" data-m="${m.id}" aria-pressed="${m.id===metric.id}">${m.label}</button>`
).join('');
document.getElementById('seg').addEventListener('click', e => {
  const b = e.target.closest('button'); if(!b) return;
  metric = METRICS.find(m => m.id === b.dataset.m);
  document.querySelectorAll('#seg button').forEach(x =>
    x.setAttribute('aria-pressed', String(x.dataset.m === metric.id)));
  paint(); rows();
});

stats(); paint(); rows();
matchMedia('(prefers-color-scheme: dark)').addEventListener('change', () => { paint(); rows(); });
</script>"""

html = HEAD + BODY.replace("__DATA__", payload).replace("__ACS__", data["acs_date"][:4])
OUT.write_text(html, encoding="utf-8")
print(f"wrote {OUT}  ({OUT.stat().st_size/1024:.0f} KB)")
