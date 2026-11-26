// ---------- model table ----------
const MCOLS=[
  {k:'model',l:'col_model',cls:'l'},{k:'pin',l:'col_pin'},
  {k:'pout',l:'col_pout'},{k:'pcr',l:'col_pcr'},
  {k:'requests',l:'col_req'},{k:'input',l:'col_input'},{k:'output',l:'col_output'},
  {k:'cache_read',l:'col_cache'},{k:'hit',l:'col_hit'},{k:'spd',l:'col_spd'},
  {k:'avg',l:'col_avg'},{k:'cost',l:'col_cost'},{k:'bar',l:'',cls:'nosort'}];
let msort={k:'cost',d:-1};
function renderModels(){
  const th=document.getElementById('th-models');
  th.innerHTML=MCOLS.map(c=>
    `<th class="${c.cls||''}" data-k="${c.k}">${t(c.l)}${msort.k===c.k?
      ' <span class="arrow">'+(msort.d<0?'▼':'▲')+'</span>':''}</th>`).join('');
  [...th.children].forEach(el=>{if(!el.classList.contains('nosort'))
    el.onclick=()=>{const k=el.dataset.k;
      msort.d=msort.k===k?-msort.d:(k==='model'?1:-1);
      msort.k=k;renderModels();};});
  const rows=DATA.by_model.slice().sort((a,b)=>{
    const gv=(m,k)=>k==='model'?m.model:
      k==='pin'?m.price.input:k==='pout'?m.price.output:
      k==='pcr'?m.price.cache_read:k==='hit'?(m.hit_rate??-1):
      k==='spd'?(m.avg_speed??-1):k==='avg'?(m.cost||0)/Math.max(1,m.requests):
      m[k];
    const va=gv(a,msort.k),vb=gv(b,msort.k);
    return (va>vb?1:va<vb?-1:0)*msort.d;});
  const mx=Math.max(...DATA.by_model.map(m=>m.cost||0),1e-9);
  document.getElementById('t-models').innerHTML=rows.map(m=>
    `<tr><td class="l model">${esc(m.model)}</td>
     <td class="price">${fmtPrice(m.price.input)}</td>
     <td class="price">${fmtPrice(m.price.output)}</td>
     <td class="price">${fmtPrice(m.price.cache_read)}</td>
     <td>${m.requests}</td><td>${fmtTok(m.input)}</td>
     <td>${fmtTok(m.output)}</td><td>${fmtTok(m.cache_read)}</td>
     <td>${m.hit_rate==null?'—':(m.hit_rate*100).toFixed(0)+'%'}</td>
     <td class="fade">${fmtSpeed(m.avg_speed)}</td>
     <td class="fade">${fmtCost((m.cost||0)/Math.max(1,m.requests))}</td>
     <td><b>${fmtCost(m.cost||0)}</b></td>
     <td style="width:10%"><div class="costbar" style="width:${Math.max(2,(m.cost||0)/mx*100)}%"></div></td></tr>`).join('');
}

// ---------- sessions + drawer ----------
function renderSessions(){
  const mx=Math.max(...DATA.sessions.map(s=>s.cost||0),1e-9);
  document.getElementById('t-sessions').innerHTML=DATA.sessions.map(s=>
    `<tr class="clickable" tabindex="0" data-sid="${esc(s.id)}"><td class="l fade">${s.last_ts.slice(5,16)}</td>
     <td class="l" title="${esc(s.dir)}">${esc(short(s.title,36))}</td>
     <td class="l model fade">${esc(short(s.models.join(', '),26))}</td>
     <td>${fmtTok(s.total)}</td><td>${fmtCost(s.cost||0)}</td>
     <td><div class="costbar" style="width:${Math.max(2,(s.cost||0)/mx*100)}%"></div></td></tr>`).join('');
  document.querySelectorAll('#t-sessions tr').forEach(tr=>{
    tr.onclick=()=>openSession(tr.dataset.sid,tr);
    tr.onkeydown=e=>{if(e.key==='Enter'||e.key===' '){e.preventDefault();tr.click();}};
  });
}
let drawerTrigger=null;
function openSession(sid,trigger){
  const s=(DATA.sessions||[]).find(x=>x.id===sid)||
          (DATA.top_sessions||[]).find(x=>x.id===sid);
  if(!s)return;
  const reqs=DATA.requests.filter(r=>r.session_id===sid);
  const inc=s.input||0,outc=s.output||0,cached=s.cache_read||0,cost=s.cost||0;
  document.getElementById('drawer-body').innerHTML=
    `<h3 id="drawer-title">${esc(s.title)}</h3><div class="meta">${esc(s.dir||'')}<br>${esc(s.id)}</div>
     <div class="kpis">
      <div class="card"><div class="label">${t('d_cost')}</div><div class="value">${fmtCost(cost)}</div></div>
      <div class="card"><div class="label">${t('d_reqs')}</div><div class="value">${s.requests}</div></div>
      <div class="card"><div class="label">${t('d_total')}</div><div class="value">${fmtTok(s.total)}</div></div>
      <div class="card"><div class="label">${t('d_input')}</div><div class="value">${fmtTok(inc)}</div></div>
      <div class="card"><div class="label">${t('d_output')}</div><div class="value">${fmtTok(outc)}</div></div>
      <div class="card"><div class="label">${t('d_cache')}</div><div class="value">${fmtTok(cached)}</div></div>
     </div>
     <h2 style="margin-bottom:8px">${tf('d_detail',{n:reqs.length,m:s.requests})}</h2>
     <table><thead><tr><th class="l">${t('col_time')}</th><th class="l">${t('col_model')}</th>
      <th>${t('d_input')}</th><th>${t('d_output')}</th><th>${t('d_cache')}</th><th>${t('d_cost')}</th></tr></thead>
     <tbody id="t-drawer">${reqs.map((r,i)=>
      `<tr class="clickable" data-i="${i}"><td class="l fade">${r.ts.slice(5,19)}</td>
       <td class="l model">${esc(r.model)}</td><td>${fmtTok(r.input)}</td>
       <td>${fmtTok(r.output)}</td><td>${fmtTok(r.cache_read)}</td>
       <td class="reqcost">${fmtCost(r.cost||0)}</td></tr>`).join('')}</tbody></table>`;
  bindReqRows('#t-drawer',reqs,6);
  drawerTrigger=trigger||document.activeElement;
  document.querySelector('.shell').inert=true;
  document.getElementById('overlay').classList.add('open');
  document.getElementById('drawer-x').focus({preventScroll:true});
}
function closeSession(restoreFocus=true){
  const overlay=document.getElementById('overlay');
  if(!overlay.classList.contains('open'))return;
  overlay.classList.remove('open');
  document.querySelector('.shell').inert=false;
  if(restoreFocus){
    const sid=drawerTrigger?.dataset?.sid;
    const trigger=drawerTrigger?.isConnected?drawerTrigger:
      sid&&document.querySelector(`.view.on [data-sid="${CSS.escape(sid)}"]`);
    (trigger||document.getElementById('view-title')).focus({preventScroll:true});
  }
  drawerTrigger=null;
  document.getElementById('drawer-body').replaceChildren();
}
document.getElementById('overlay').addEventListener('click',e=>{
  if(e.target===e.currentTarget)closeSession();});
document.getElementById('drawer-x').onclick=()=>closeSession();

// ---------- request feed ----------
const filt={model:'',q:'',date:'',day:'',sort:'newest'};
const pageSize=50;
let feedPage=0;
let previousFeed=null;
let previousFeedScope=null;
function setModelFilter(m,sessionQuery=''){
  feedPage=0;
  Object.assign(filt,{model:m,q:sessionQuery.trim().toLowerCase(),date:'',day:''});
  document.getElementById('f-model').value=m;
  document.getElementById('f-session').value=sessionQuery;
  document.getElementById('f-date').value='';
  document.querySelectorAll('[data-day]').forEach(chip=>setPressed(chip,chip.dataset.day===''));
  navigateTo('requests');
}
const reqDay=r=>r.ts.slice(0,10);
function filteredReqs(){
  const now=new Date(),today=dayKey(now);
  now.setDate(now.getDate()-6);
  const lim=dayKey(now);
  const rows=(DATA?.requests||[]).filter(r=>{
    if(filt.model&&r.model!==filt.model)return false;
    if(filt.q&&![r.session_title,r.model,r.session_id,r.request_id,r.message_id]
      .some(v=>String(v||'').toLowerCase().includes(filt.q)))return false;
    if(filt.date&&reqDay(r)!==filt.date)return false;
    if(filt.day==='today'&&reqDay(r)!==today)return false;
    if(filt.day==='7'&&reqDay(r)<lim)return false;
    return true;});
  const value=r=>{
    if(filt.sort==='cost')return r.cost;
    if(filt.sort==='tokens')return r.input+r.output+r.cache_read+r.cache_creation;
    if(filt.sort==='latency')return r.total_ms??-1;
    return Date.parse(r.ts);
  };
  return rows.sort((a,b)=>value(b)-value(a));
}
function toggleReq(tr,r,cols){
  const next=tr.nextElementSibling;
  if(next&&next.classList.contains('reqbody')){next.remove();tr.classList.remove('exp');return;}
  tr.classList.add('exp');
  const row=document.createElement('tr');row.className='reqbody';
  const rid=r.request_id||r.message_id||'';
  row.dataset.rid=rid;
  const ms=v=>v==null?'—':Number(v).toLocaleString(LOCALE[LANG])+' ms';
  const meta=[[t('ser_cachew'),fmtTok(r.cache_creation)],[t('an_ttft'),ms(r.ttft_ms)],
    [t('an_latency'),ms(r.total_ms)],['ID',rid||'—']];
  row.innerHTML=`<td colspan="${cols}"><div class="request-meta">${meta.map(([k,v])=>
    `<span><b>${esc(k)}</b> ${esc(v)}</span>`).join(' · ')}</div><pre>${t('loading')}</pre></td>`;
  tr.after(row);
  const pre=row.querySelector('pre');
  if(!rid){pre.textContent=t('nobody');return;}
  if(native_)native_.postMessage({action:'getBody',rid:r.request_id||'',mid:r.message_id||''});
  else fetch('/api/body?rid='+encodeURIComponent(r.request_id||'')+
             '&mid='+encodeURIComponent(r.message_id||''))
        .then(async response=>{
          const data=await response.json();
          if(!response.ok)throw Error(data.error||response.statusText);
          pre.textContent=data.body?.trim()?data.body:t('nobody');
        }).catch(error=>{pre.textContent=error.message;});
}
function showBody(rid,text){
  setBodyText(rid,text?.trim()?text:t('nobody'));
}
function showBodyError(rid,error){
  setBodyText(rid,error);
}
function setBodyText(rid,text){
  document.querySelectorAll('.reqbody').forEach(row=>{
    if(row.dataset.rid===rid)row.querySelector('pre').textContent=text;
  });
}
function bindReqRows(sel,rows,cols){
  document.querySelectorAll(sel+' tr.clickable').forEach(tr=>{
    tr.tabIndex=0;
    const request=rows[Number(tr.dataset.i)];
    tr.dataset.requestKey=JSON.stringify([request.session_id,request.request_id,request.message_id,request.ts]);
    tr.onclick=()=>toggleReq(tr,request,cols);
    tr.onkeydown=e=>{if(e.key==='Enter'||e.key===' '){e.preventDefault();tr.click();}};
  });
}
function renderFeed(){
  const rows=filteredReqs();
  feedPage=Math.min(feedPage,Math.max(0,Math.ceil(rows.length/pageSize)-1));
  const offset=feedPage*pageSize, shown=rows.slice(offset,offset+pageSize);
  const count=tf('log_count',{first:rows.length?offset+1:0,last:offset+shown.length,n:rows.length});
  const sampled=DATA&&DATA.total.requests>DATA.requests.length;
  document.getElementById('f-count').textContent=count+(sampled?' · '+
    tf('log_sample',{n:DATA.requests.length,m:DATA.total.requests}):'');
  document.getElementById('f-prev').disabled=feedPage===0;
  document.getElementById('f-next').disabled=offset+pageSize>=rows.length;
  const scope=JSON.stringify([LANG,DATA?.meta?.db_path]);
  const signature=JSON.stringify(shown);
  if(previousFeedScope===scope&&previousFeed===signature)return;
  const tbody=document.getElementById('t-recent'),expanded=new Map();
  if(previousFeedScope===scope){
    for(const detail of tbody.querySelectorAll('tr.reqbody')){
      expanded.set(detail.previousElementSibling.dataset.requestKey,detail);
    }
  }
  previousFeedScope=scope;previousFeed=signature;
  tbody.innerHTML=shown.map((r,i)=>{
    const col=donutColors[r.model]||'var(--slate)';
    return `<tr class="clickable" data-i="${i}"><td class="l fade">${r.ts.slice(5,19)}</td>
     <td class="l model"><span class="dot" style="background:${col}"></span>${esc(r.model)}</td>
     <td class="l fade" title="${esc(r.session_title)}">${esc(short(r.session_title,20))}</td>
     <td>${fmtTok(r.input)}</td><td>${fmtTok(r.output)}</td>
     <td>${fmtTok(r.cache_read)}</td><td class="fade">${fmtSpeed(r.tok_per_s)}</td>
     <td class="reqcost">${fmtCost(r.cost||0)}</td></tr>`;}).join('')
    ||`<tr><td colspan="8" class="empty" style="text-align:center;padding:22px">${t('f_empty')}</td></tr>`;
  bindReqRows('#t-recent',shown,8);
  for(const tr of tbody.querySelectorAll('tr.clickable')){
    const detail=expanded.get(tr.dataset.requestKey);
    if(detail){tr.classList.add('exp');tr.after(detail);}
  }
}
document.getElementById('f-prev').onclick=()=>{feedPage=Math.max(0,feedPage-1);renderFeed();};
document.getElementById('f-next').onclick=()=>{feedPage++;renderFeed();};
document.getElementById('f-sort').onchange=e=>{feedPage=0;filt.sort=e.target.value;renderFeed();};
document.getElementById('f-model').onchange=e=>{feedPage=0;filt.model=e.target.value;renderFeed();};
document.getElementById('f-session').oninput=e=>{feedPage=0;filt.q=e.target.value.trim().toLowerCase();renderFeed();};
document.getElementById('f-date').onchange=e=>{feedPage=0;filt.date=e.target.value;filt.day='';
  document.querySelectorAll('[data-day]').forEach(x=>setPressed(x,!filt.date&&x.dataset.day===''));renderFeed();};
document.querySelectorAll('[data-day]').forEach(c=>c.onclick=()=>{
  feedPage=0;filt.date='';document.getElementById('f-date').value='';
  document.querySelectorAll('[data-day]').forEach(x=>setPressed(x,x===c));
  filt.day=c.dataset.day;renderFeed();});
