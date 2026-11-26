// ---------- token analytics ----------
let insightPeriod='7d';
const periodData=()=>{
  const a=DATA.analytics||{},p=a.periods||{};
  if(insightPeriod==='30d')return{data:p.last_30_days||{},change:p.comparison_30d_pct};
  if(insightPeriod==='mtd')return{data:p.month_to_date||{},change:null};
  if(insightPeriod==='all'){
    const active=DATA.by_day.length,total=DATA.total||{};
    const oldest=active?DATA.by_day[active-1].day:DATA.today.day;
    const calendarDays=active?Math.max(1,Math.round((Date.parse(DATA.today.day)-Date.parse(oldest))/reportDayMs)+1):0;
    return{data:{...total,active_days:active,calendar_days:calendarDays,
      avg_tokens_per_active_day:active?Math.round(total.total/active):0},change:null};
  }
  return{data:p.last_7_days||{},change:p.comparison_7d_pct};
};
function drawInsights(){
  if(!DATA)return;
  const analytics=DATA.analytics||{},economics=analytics.economics||{};
  const {data:p,change}=periodData(),forecast=(analytics.periods||{}).month_projection||{};
  const tiles=[
    ['an_period_cost',fmtCost(p.cost||0),t('an_trend')+': '+(change==null?'—':`${change>0?'+':''}${change.toFixed(1)}%`)],
    ['an_period_tokens',fmtTok(p.total||0),`${fmtTok(p.input||0)} ${t('an_input').toLowerCase()} · ${fmtTok(p.output||0)} ${t('an_output').toLowerCase()}`],
    ['an_period_requests',(p.requests||0).toLocaleString(LOCALE[LANG]||'en-US'),`${p.active_days||0} ${t('an_active_days').toLowerCase()}`],
    ['an_active_days',String(p.active_days||0),`${p.calendar_days||0} ${t('an_calendar_days')}`],
    ['an_avg_tokens_active',fmtTok(p.avg_tokens_per_active_day||0),t('an_tokens_per_request')+': '+fmtTok(p.requests?p.total/p.requests:0)],
    ['an_month_projection',fmtCost(forecast.cost||0),fmtTok(forecast.tokens||0)+' tok'],
  ];
  document.getElementById('analysis-kpis').innerHTML=tiles.map(([label,value,extra],i)=>
    `<div class="card${i<2?' rise':''}"><div class="label">${esc(t(label))}</div><div class="value">${esc(value)}</div><div class="extra">${esc(extra)}</div></div>`).join('');
  const values=[
    ['an_cache_saved',fmtCost(economics.cache_savings_estimate||0)],
    ['an_output_input',economics.output_input_ratio==null?'—':`${economics.output_input_ratio.toFixed(2)}×`],
    ['an_tokens_per_request',fmtTok(economics.tokens_per_request||0)],
    ['an_cost_per_1k',economics.cost_per_1k_output==null?'—':fmtCost(economics.cost_per_1k_output)],
  ];
  document.getElementById('analysis-economics').innerHTML=values.map(([label,value])=>
    `<div class="insight-value"><span>${esc(t(label))}</span><b>${esc(value)}</b></div>`).join('');
  const perf=analytics.performance||{},rows=[
    ['an_request_tokens',perf.request_tokens,'tokens'],['an_input',perf.input,'tokens'],
    ['an_output',perf.output,'tokens'],['an_ttft',perf.ttft_ms,'ms'],
    ['an_latency',perf.total_ms,'ms'],['an_speed',perf.tok_per_s,'speed'],
  ];
  const fmtPercentile=(v,kind)=>v==null?'—':kind==='tokens'?fmtTok(v):kind==='speed'?fmtSpeed(v):`${Math.round(v)} ms`;
  document.getElementById('analysis-sample').textContent=tf('an_sample',{n:perf.sample_size||0});
  document.getElementById('analysis-percentiles').innerHTML=rows.map(([label,v,kind])=>
    `<tr><td>${esc(t(label))}</td><td>${fmtPercentile(v&&v.p50,kind)}</td><td>${fmtPercentile(v&&v.p90,kind)}</td></tr>`).join('');
  const models=analytics.models||[];
  document.getElementById('analysis-models').innerHTML=models.slice(0,12).map(m=>
    `<tr data-model="${esc(m.model)}"><td>${esc(m.model)}</td><td>${m.requests.toLocaleString(LOCALE[LANG]||'en-US')}</td><td>${fmtTok(m.tokens_per_request||0)}</td><td>${m.output_input_ratio==null?'—':m.output_input_ratio.toFixed(2)+'×'}</td><td>${fmtCost(m.cache_savings||0)}</td><td>${m.cost_per_1k_output==null?'—':fmtCost(m.cost_per_1k_output)}</td></tr>`).join('');
  document.querySelectorAll('#analysis-models tr[data-model]').forEach(row=>row.onclick=()=>{
    setModelFilter(row.dataset.model);
  });
}
bindSegment(document.getElementById('seg-analysis'),mode=>{
  insightPeriod=mode;drawInsights();
});

// ---------- settings panel fill ----------
function fillSettings(d){
  const themeSelect=document.getElementById('set-theme');
  if(document.activeElement!==themeSelect)themeSelect.value=(d.settings&&d.settings.theme)||'system';
  if(document.activeElement!==document.getElementById('set-budget'))
    document.getElementById('set-budget').value=d.settings.daily_budget||'';
  const m=d.meta||{};
  document.getElementById('set-dbpath').textContent=m.db_path||'—';
  document.getElementById('set-pricespath').textContent=m.prices_path||'—';
  document.getElementById('set-version').textContent=m.version||'—';
  document.getElementById('native-startup').hidden=!native_||Boolean(window.__DTM_VSCODE__);
  const cb=document.getElementById('set-login');
  if(native_){cb.checked=!!m.login_item;cb.disabled=false;
    document.getElementById('set-login-label').textContent=
      cb.checked?t('st_login_on'):t('st_login');}
  else{cb.checked=false;cb.disabled=true;
    document.getElementById('set-login-label').textContent=t('st_login');}
}

function renderView(view){
  switch(view){
    case 'overview':
      refreshChart('tok',!started);refreshChart('cost',!started);
      drawMix();drawHit();drawDonut();drawHeat();renderTopSessions();break;
    case 'models':renderModels();drawScatter();break;
    case 'sessions':renderSessions();break;
    case 'requests':renderFeed();break;
    case 'insights':drawInsights();refreshUsageReport();break;
    case 'settings':fillSettings(DATA);break;
  }
  document.getElementById('v-'+view).querySelectorAll('.seg').forEach(segThumb);
}

function setSourceHealth(pollError){
  const health=document.getElementById('source-status');
  health.classList.toggle('offline',Boolean(pollError));
  health.title=pollError||'';
  health.querySelector('span').textContent=pollError?(OFFLINE_LABEL[LANG]||OFFLINE_LABEL.en):t('live');
}

function update(d){
  DATA=d;
  LANG=(d.settings&&d.settings.language)||'zh';
  applyTheme((d.settings&&d.settings.theme)||'system');
  applyLang();
  setSourceHealth(d.meta?.poll_error);
  const updated=document.getElementById('updated');
  updated.textContent=new Date(d.generated_at).toLocaleTimeString(LOCALE[LANG]||'zh-CN',
    {hour:'2-digit',minute:'2-digit',hour12:false});
  updated.title=d.generated_at;
  kpis(d);
  donutColors=Object.fromEntries(d.by_model.map((m,i)=>[m.model,MODEL_DOTS[i%MODEL_DOTS.length]]));
  const sel=document.getElementById('f-model'),cur=sel.value;
  sel.innerHTML=`<option value="">${esc(t('f_all_models'))}</option>`+
    d.by_model.map(m=>`<option ${m.model===cur?'selected':''}>${esc(m.model)}</option>`).join('');
  filt.model=sel.value;
  renderView(document.querySelector('.view.on').id.slice(2));
  if(!started)started=true;
}

setupChart('tok','tok');setupChart('cost','cost');
charts.mix={mode:'hour'};charts.hit={mode:'hour'};
wireSeg('mix',()=>drawMix());wireSeg('hit',()=>drawHit());
let pendingWebFetch=null;
async function fetchWebUsage(manual=false){
  if(pendingWebFetch&&(!manual||pendingWebFetch.manual))return;
  const request={manual};
  pendingWebFetch=request;
  try{
    const response=await fetch(manual?'/api/refresh':'/api/usage');
    const snap=await response.json();
    if(!response.ok)throw Error(snap.error||response.statusText);
    if(pendingWebFetch===request)update(snap);
  }catch(error){
    if(pendingWebFetch===request){
      setSourceHealth(error.message);
      if(manual)toast(error.message);
    }
  }finally{
    if(pendingWebFetch===request)pendingWebFetch=null;
  }
}
if(!native_&&location.protocol.indexOf('http')===0){
  fetchWebUsage();setInterval(fetchWebUsage,10000);
}
