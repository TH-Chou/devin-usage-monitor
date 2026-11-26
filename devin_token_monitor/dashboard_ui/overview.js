// ---------- header + settings actions ----------
function doRefresh(){
  if(native_)native_.postMessage({action:'refresh'});
  else fetch('/api/refresh').then(async r=>{const d=await r.json();
    if(!r.ok)throw new Error(d.error||'Refresh failed');return d;})
    .then(update).catch(e=>toast(e.message));}
function doExport(){
  if(native_)native_.postMessage({action:'export'});
  else location.href='/api/export.csv?what=requests';}
document.getElementById('btn-refresh').onclick=doRefresh;
document.getElementById('btn-export').onclick=doExport;
document.getElementById('set-export2').onclick=doExport;
document.getElementById('set-open-prices').onclick=()=>{
  if(native_)native_.postMessage({action:'editPrices'});
  else toast(t('toast_edit_prices'));};
document.getElementById('set-theme').onchange=e=>setTheme(e.target.value);
document.getElementById('set-budget-save').onclick=()=>{
  const v=parseFloat(document.getElementById('set-budget').value)||0;
  if(native_)native_.postMessage({action:'setBudget',value:v});
  else fetch('/api/settings',{method:'POST',headers:{'Content-Type':'application/json'},
    body:JSON.stringify({daily_budget:v})}).then(r=>r.json()).then(update);
  toast(v>0?t('toast_budget').replace('{v}',fmtCost(v)):t('toast_budget_off'));};
document.getElementById('set-login').onchange=e=>{
  if(native_)native_.postMessage({action:'toggleLoginItem',on:e.target.checked});
  else{e.target.checked=false;toast(t('toast_native_only'));}
  document.getElementById('set-login-label').textContent=
    e.target.checked?t('st_login_on'):t('st_login');};
document.querySelectorAll('#lang-row .chip').forEach(c=>
  c.onclick=()=>setLang(c.dataset.lang));

// ---------- KPI cards (persistent for count-up) ----------
const KPI_DEFS=[
  {id:'cost',l:'k_cost',c:'slate'},{id:'all',l:'k_all'},
  {id:'req',l:'k_req'},{id:'hit',l:'k_hit'},
  {id:'spd',l:'k_spd'},{id:'top',l:'k_top'}];
const dayOverDayDelta=(today,yesterday)=>
  Number.isFinite(today)&&Number.isFinite(yesterday)&&yesterday>0
    ? (today-yesterday)/yesterday*100 : null;
let kpiInit=false;
function kpis(d){
  const td=d.today,a=d.total,budget=d.settings&&d.settings.daily_budget;
  const warn=budget&&(td.cost||0)>budget;
  const speeds=d.requests.map(r=>r.tok_per_s).filter(v=>v!=null);
  const avgSpd=speeds.length?speeds.reduce((x,y)=>x+y,0)/speeds.length:0;
  const topM=d.by_model[0];
  const yesterday=new Date();yesterday.setDate(yesterday.getDate()-1);
  const yday=d.by_day.find(day=>day.day===dayKey(yesterday));
  const delta=yday?dayOverDayDelta(td.cost||0,yday.cost||0):null;
  if(!kpiInit){
    document.getElementById('kpis').innerHTML=KPI_DEFS.map(k=>
      `<div class="card">
       <div class="label" id="kl-${k.id}">${t(k.l)}</div>
       <div class="value ${k.c||''}" id="kv-${k.id}"><span class="skel">&nbsp;</span></div>
       <div class="extra" id="ke-${k.id}"></div></div>`).join('');
    kpiInit=true;}
  const setTxt=(id,v)=>{const el=document.getElementById(id);
    if(el._raf)cancelAnimationFrame(el._raf);el.textContent=v;};
  KPI_DEFS.forEach(k=>{if(k.id!=='cost')setTxt('kl-'+k.id,t(k.l));});
  setTxt('kl-cost',t('k_cost')+(budget?' · '+tf('ke_budget',{v:fmtCost(budget)}):''));
  animateValue(document.getElementById('kv-cost'),td.cost||0,fmtCost);
  document.getElementById('kv-cost').className='value '+(warn?'warn':'slate');
  setTxt('ke-cost',(delta==null?'—':tf('ke_delta',{v:(delta>=0?'+':'')+delta.toFixed(0)+'%'}))
      +' · '+fmtTok(td.total)+' tok');
  animateValue(document.getElementById('kv-req'),td.requests,v=>Math.round(v).toString());
  setTxt('ke-req',tf('ke_avgreq',{v:fmtCost(td.requests?(td.cost||0)/td.requests:0)}));
  const hit=(td.input+td.cache_read)?td.cache_read/(td.input+td.cache_read)*100:0;
  animateValue(document.getElementById('kv-hit'),hit,v=>v.toFixed(1)+'%');
  setTxt('ke-hit',tf('ke_cacheread',{v:fmtTok(td.cache_read)}));
  setTxt('kv-spd',speeds.length?fmtSpeed(avgSpd):'—');
  setTxt('ke-spd',t('ke_recent'));
  animateValue(document.getElementById('kv-all'),a.cost||0,fmtCost);
  setTxt('ke-all',fmtTok(a.total)+' tok');
  setTxt('kv-top',topM?short(topM.model,14):'—');
  setTxt('ke-top',topM?tf('ke_topv',{v:fmtCost(topM.cost),n:topM.requests}):'');
  // sidebar footer
  animateValue(document.getElementById('sf-cost'),td.cost||0,fmtCost);
  setTxt('sf-req',tf('sf_reqs',{n:td.requests}));
}
