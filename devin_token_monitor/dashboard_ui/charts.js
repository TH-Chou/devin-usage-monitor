// ---------- line charts ----------
const charts={};
const TREND_HEIGHT=230;
function buckets(mode){
  const out=[],now=new Date();
  if(mode==='hour'){const h=new Date(now);h.setMinutes(0,0,0);
    for(let i=23;i>=0;i--){const d=new Date(h-i*36e5);
      out.push({key:hourKey(d),label:d.getHours()+':00'});}}
  else{const d0=new Date(now.getFullYear(),now.getMonth(),now.getDate());
    for(let i=13;i>=0;i--){const d=new Date(d0);d.setDate(d.getDate()-i);
      out.push({key:dayKey(d),label:(d.getMonth()+1)+'/'+d.getDate()});}}
  return out;}
function seriesFor(kind,mode){
  const idx={},src=mode==='hour'?DATA.by_hour:DATA.by_day;
  src.forEach(r=>{idx[mode==='hour'?r.hour:r.day]=r;});
  const defs=kind==='tok'
    ?[{name:t('ser_input'),color:C.input,f:r=>r?r.input:0},
      {name:t('ser_output'),color:C.output,f:r=>r?r.output:0},
      {name:t('ser_cache'),color:C.cache,f:r=>r?r.cache_read:0}]
    :[{name:t('ser_cost'),color:C.cost,f:r=>r?r.cost||0:0}];
  const bs=buckets(mode);
  return{bs,series:defs.map(d=>({name:d.name,color:d.color,
    values:bs.map(b=>d.f(idx[b.key]))}))};}
function drawChart(id,animate){
  const st=charts[id];if(!st)return;
  const el=document.getElementById('ch-'+id);
  const bs=st.bs,vis=st.series.filter(s=>!st.hidden.has(s.name));
  const W=860,H=TREND_HEIGHT,pl=58,pr=14,pt=12,pb=30;
  const iw=W-pl-pr,ih=H-pt-pb,n=bs.length,step=n>1?iw/(n-1):iw;
  const ymax=Math.max(...vis.flatMap(s=>s.values),0)*1.08||1;
  const X=i=>pl+i*step,Y=v=>pt+ih-(v/ymax)*ih;
  let g='';
  for(let k=0;k<=4;k++){const y=pt+ih*k/4;
    g+=`<line x1=${pl} y1=${y} x2=${W-pr} y2=${y} stroke="var(--hair)"/>`;
    g+=`<text x=${pl-8} y=${y+4} text-anchor="end" font-size="10" fill="var(--faint)">${st.fmt(ymax*(1-k/4))}</text>`;}
  const lstep=Math.ceil(n/8);
  bs.forEach((b,i)=>{if(i%lstep===0||i===n-1)
    g+=`<text x=${X(i)} y=${H-8} text-anchor="middle" font-size="10" fill="var(--faint)">${b.label}</text>`;});
  let paths='';
  vis.forEach(s=>{
    if(s.area){
      const d='M'+X(0)+','+Y(0)+' '+s.values.map((v,i)=>'L'+X(i)+','+Y(v)).join(' ')
        +' L'+X(n-1)+','+Y(0)+' Z';
      paths+=`<path class="fill" d="${d}" fill="${s.color}" fill-opacity=".10" opacity="0"/>`;}
    const d='M'+s.values.map((v,i)=>X(i)+','+Y(v)).join(' L');
    paths+=`<path class="ln" d="${d}" fill="none" stroke="${s.color}" stroke-width="2.2"
      stroke-linejoin="round" stroke-linecap="round"/>`;});
  el.innerHTML=`<svg viewBox="0 0 ${W} ${H}">${g}${paths}
    <line id="gl-${id}" y1=${pt} y2=${pt+ih} stroke="var(--faint)" visibility="hidden"/>
    <g id="dots-${id}"></g>
    <rect id="ov-${id}" x=${pl} y=${pt} width=${iw} height=${ih} fill="transparent"/></svg>`;
  if(animate&&!matchMedia('(prefers-reduced-motion: reduce)').matches){
    el.querySelectorAll('path.ln').forEach(p=>{
      const L=p.getTotalLength();
      p.style.strokeDasharray=L;p.style.strokeDashoffset=L;
      p.style.transition='none';
      requestAnimationFrame(()=>{p.style.transition=
        'stroke-dashoffset 1s var(--easeout)';p.style.strokeDashoffset=0;});});
    el.querySelectorAll('path.fill').forEach(p=>{
      p.style.transition='none';
      requestAnimationFrame(()=>{p.style.transition='opacity .8s .5s var(--easeout)';
        p.style.opacity='1';});});
  } else {
    el.querySelectorAll('path.fill').forEach(p=>p.style.opacity='1');
  }
  const tip=document.getElementById('tip-'+id);
  const ov=document.getElementById('ov-'+id);
  ov.addEventListener('mousemove',e=>{
    const r=ov.getBoundingClientRect();
    const i=Math.max(0,Math.min(n-1,Math.round((e.clientX-r.left)/r.width*iw/step)));
    const gl=document.getElementById('gl-'+id);
    gl.setAttribute('x1',X(i));gl.setAttribute('x2',X(i));
    gl.setAttribute('visibility','visible');
    document.getElementById('dots-'+id).innerHTML=vis.map(s=>
      `<circle cx=${X(i)} cy=${Y(s.values[i])} r="3.4" fill="${s.color}" stroke="var(--card)" stroke-width="1.6"/>`).join('');
    tip.innerHTML='<b>'+st.bs[i].label+'</b>'+vis.map(s=>
      `<div class="r"><i style="background:${s.color}"></i><span>${s.name}</span>
       <span style="margin-left:auto;font-weight:600">${st.fmtFull(s.values[i])}</span></div>`).join('');
    tip.style.display='block';
    const cr=el.parentElement.getBoundingClientRect();
    tip.style.left=Math.min(cr.width*(X(i)/W)+14,cr.width-165)+'px';
    tip.style.top='44px';});
  ov.addEventListener('mouseleave',()=>{
    document.getElementById('gl-'+id).setAttribute('visibility','hidden');
    document.getElementById('dots-'+id).innerHTML='';
    tip.style.display='none';});
}
function segThumb(seg){
  const on=seg.querySelector('button.on'),th=seg.querySelector('.thumb');
  if(on?.offsetWidth&&th){th.style.left=on.offsetLeft+'px';th.style.width=on.offsetWidth+'px';}}
const segmentSizes=new ResizeObserver(entries=>entries.forEach(entry=>segThumb(entry.target)));
function bindSegment(seg,change){
  segmentSizes.observe(seg);
  seg.addEventListener('click',event=>{
    const selected=event.target.closest('button');
    if(!selected)return;
    seg.querySelectorAll('button').forEach(button=>setPressed(button,button===selected));
    segThumb(seg);
    change(selected.dataset.v);
  });
}
function setupChart(id,kind){
  charts[id]={mode:'hour',hidden:new Set(),kind,drew:false};
  wireSeg(id,()=>refreshChart(id,true));
  charts[id].renderLegend=()=>{
    const leg=document.getElementById('leg-'+id);
    leg.innerHTML=charts[id].series.map(s=>
      `<span data-n="${s.name}" class="${charts[id].hidden.has(s.name)?'off':''}">
       <i style="background:${s.color}"></i>${s.name}</span>`).join('');
    [...leg.children].forEach(el=>el.onclick=()=>{
      const n=el.dataset.n,h=charts[id].hidden;
      h.has(n)?h.delete(n):h.add(n);
      charts[id].renderLegend();drawChart(id,false);});};
}
function refreshChart(id,animate){
  const st=charts[id],d=seriesFor(st.kind,st.mode);
  st.bs=d.bs;st.series=d.series;
  if(st.kind==='cost')st.series.forEach(s=>s.area=true);
  st.fmt=st.kind==='cost'?(v=>'$'+v.toFixed(2)):fmtTok;
  st.fmtFull=st.kind==='cost'?fmtCost:(v=>v.toLocaleString('en-US')+' tok');
  st.renderLegend();drawChart(id,animate||!st.drew);st.drew=true;
}

// generic hour/day segmented switch driving a render callback
function wireSeg(id,render){
  bindSegment(document.getElementById('seg-'+id),mode=>{
    charts[id].mode=mode;
    if(DATA)render(true);
  });
}
function idxFor(mode){
  const idx={};
  (mode==='hour'?DATA.by_hour:DATA.by_day).forEach(r=>
    idx[mode==='hour'?r.hour:r.day]=r);
  return idx;
}
function gridLines(W,H,pl,pr,pt,ih,fmt){
  let g='';
  for(let k=0;k<=4;k++){const y=pt+ih*k/4;
    g+=`<line x1=${pl} y1=${y} x2=${W-pr} y2=${y} stroke="var(--hair)"/>
    <text x=${pl-8} y=${y+4} text-anchor="end" font-size="10" fill="var(--faint)">${fmt(k)}</text>`;}
  return g;
}

// ---------- stacked token-mix bars ----------
const MIX=[['cache_read','ser_cache','var(--tan)'],['input','ser_input','var(--blue)'],
           ['cache_creation','ser_cachew','var(--purple)'],['output','ser_output','var(--green)']];
function drawMix(){
  document.getElementById('leg-mix').innerHTML=MIX.map(m=>
    `<span><i style="background:${m[2]}"></i>${t(m[1])}</span>`).join('');
  const mode=charts.mix.mode,idx=idxFor(mode);
  const bs=buckets(mode),n=bs.length;
  const vals=bs.map(b=>{const r=idx[b.key];
    return r?MIX.map(m=>r[m[0]]||0):MIX.map(()=>0);});
  const W=860,H=TREND_HEIGHT,pl=58,pr=14,pt=12,pb=30,iw=W-pl-pr,ih=H-pt-pb;
  const step=iw/n,bw=Math.min(36,step*0.62);
  const ymax=Math.max(...vals.map(v=>v.reduce((a,b)=>a+b,0)),0)*1.08||1;
  const X=i=>pl+i*step+step/2,Y=v=>pt+ih-(v/ymax)*ih;
  let g=gridLines(W,H,pl,pr,pt,ih,k=>fmtTok(ymax*(1-k/4)));
  const lstep=Math.ceil(n/8);
  bs.forEach((b,i)=>{if(i%lstep===0||i===n-1)
    g+=`<text x=${X(i)} y=${H-8} text-anchor="middle" font-size="10" fill="var(--faint)">${b.label}</text>`;});
  let bars='';
  vals.forEach((col,i)=>{let acc=0;
    col.forEach((v,mi)=>{if(v<=0)return;
      const y0=Y(acc),y1=Y(acc+v);acc+=v;
      bars+=`<rect x=${X(i)-bw/2} y=${y1.toFixed(1)} width=${bw} height=${Math.max(1,(y0-y1)).toFixed(1)} rx="1.5" fill="${MIX[mi][2]}"/>`;});});
  let hot='';
  bs.forEach((b,i)=>hot+=`<rect data-i="${i}" x=${pl+i*step} y=${pt} width=${step} height=${ih} fill="transparent"/>`);
  document.getElementById('ch-mix').innerHTML=
    `<svg viewBox="0 0 ${W} ${H}">${g}${bars}
     <line id="gl-mix" y1=${pt} y2=${pt+ih} stroke="var(--faint)" visibility="hidden"/>${hot}</svg>`;
  const tip=document.getElementById('tip-mix'),el=document.getElementById('ch-mix');
  el.querySelectorAll('rect[data-i]').forEach(rc=>{
    const i=+rc.dataset.i;
    rc.addEventListener('mousemove',()=>{
      const gl=document.getElementById('gl-mix');
      gl.setAttribute('x1',X(i));gl.setAttribute('x2',X(i));
      gl.setAttribute('visibility','visible');
      const col=vals[i],tot=col.reduce((a,b)=>a+b,0);
      tip.innerHTML='<b>'+bs[i].label+'</b>'+MIX.map((m,mi)=>
        `<div class="r"><i style="background:${m[2]}"></i><span>${t(m[1])}</span>
         <span style="margin-left:auto;font-weight:600">${fmtTok(col[mi])}</span></div>`).join('')+
        `<div class="r"><span>${t('mix_total')}</span><span style="margin-left:auto;font-weight:600">${fmtTok(tot)}</span></div>`;
      tip.style.display='block';
      const cr=el.getBoundingClientRect();
      tip.style.left=Math.min(cr.width*(X(i)/W)+14,cr.width-170)+'px';
      tip.style.top='44px';});
    rc.addEventListener('mouseleave',()=>{
      document.getElementById('gl-mix').setAttribute('visibility','hidden');
      tip.style.display='none';});});
}

// ---------- cache hit-rate trend ----------
function drawHit(){
  const mode=charts.hit.mode,idx=idxFor(mode);
  const bs=buckets(mode),n=bs.length;
  const vs=bs.map(b=>{const r=idx[b.key];if(!r)return null;
    const d=(r.input||0)+(r.cache_read||0);return d?r.cache_read/d*100:null;});
  const W=860,H=TREND_HEIGHT,pl=58,pr=14,pt=12,pb=30,iw=W-pl-pr,ih=H-pt-pb;
  const X=i=>pl+i*(n>1?iw/(n-1):iw),Y=v=>pt+ih-(v/100)*ih;
  let g=gridLines(W,H,pl,pr,pt,ih,k=>(100-25*k)+'%');
  const lstep=Math.ceil(n/8);
  bs.forEach((b,i)=>{if(i%lstep===0||i===n-1)
    g+=`<text x=${X(i)} y=${H-8} text-anchor="middle" font-size="10" fill="var(--faint)">${b.label}</text>`;});
  let d='';
  vs.forEach((v,i)=>{if(v==null)return;
    d+=((i>0&&vs[i-1]!=null)?'L':'M')+X(i).toFixed(1)+','+Y(v).toFixed(1)+' ';});
  let hot='';
  bs.forEach((b,i)=>hot+=`<rect data-i="${i}" x=${pl+i*iw/n} y=${pt} width=${iw/n} height=${ih} fill="transparent"/>`);
  document.getElementById('ch-hit').innerHTML=
    `<svg viewBox="0 0 ${W} ${H}">${g}
     <path d="${d}" fill="none" stroke="${C.cache}" stroke-width="2.2"
       stroke-linejoin="round" stroke-linecap="round"/>
     <g id="dots-hit"></g>
     <line id="gl-hit" y1=${pt} y2=${pt+ih} stroke="var(--faint)" visibility="hidden"/>${hot}</svg>`;
  const tip=document.getElementById('tip-hit'),el=document.getElementById('ch-hit');
  el.querySelectorAll('rect[data-i]').forEach(rc=>{
    const i=+rc.dataset.i;
    rc.addEventListener('mousemove',()=>{
      const gl=document.getElementById('gl-hit');
      gl.setAttribute('x1',X(i));gl.setAttribute('x2',X(i));
      gl.setAttribute('visibility','visible');
      const r=idx[bs[i].key];
      document.getElementById('dots-hit').innerHTML=vs[i]==null?'':
        `<circle cx=${X(i)} cy=${Y(vs[i])} r="3.6" fill="${C.cache}" stroke="var(--card)" stroke-width="1.6"/>`;
      tip.innerHTML='<b>'+bs[i].label+'</b>'+
        (vs[i]==null?`<div class="r"><span>${t('none')}</span></div>`:
        `<div class="r"><span>${t('hit_rate')}</span><span style="margin-left:auto;font-weight:600">${vs[i].toFixed(1)}%</span></div>
         <div class="r"><span>${t('ser_cache')}</span><span style="margin-left:auto">${fmtTok(r?r.cache_read:0)}</span></div>
         <div class="r"><span>${t('hit_reqs')}</span><span style="margin-left:auto">${r?r.requests:0}</span></div>`);
      tip.style.display='block';
      const cr=el.getBoundingClientRect();
      tip.style.left=Math.min(cr.width*(X(i)/W)+14,cr.width-165)+'px';
      tip.style.top='40px';});
    rc.addEventListener('mouseleave',()=>{
      document.getElementById('gl-hit').setAttribute('visibility','hidden');
      document.getElementById('dots-hit').innerHTML='';
      tip.style.display='none';});});
}

// ---------- week x hour heatmap ----------
function drawHeat(){
  const DOWS=DOWSL[LANG]||DOWSL.zh;
  const map={};(DATA.heatmap||[]).forEach(c=>map[c.dow+'-'+c.hour]=c);
  const mx=Math.max(1,...Object.values(map).map(c=>c.requests));
  let rows='';
  for(let d=0;d<7;d++){
    let cells='';
    for(let h=0;h<24;h++){
      const c=map[d+'-'+h],v=c?c.requests:0;
      const level=Math.ceil(Math.sqrt(v/mx)*5);
      const paint=v?` style="background:var(--accent);opacity:${level/5}"`:'';
      cells+=`<i data-d="${d}" data-h="${h}"${paint}></i>`;
    }
    rows+=`<div class="dl">${DOWS[d]}</div><div class="cells">${cells}</div>`;
  }
  document.getElementById('ch-heat').innerHTML=
    `<div class="heat">${rows}<div></div>
      <div class="cells" style="grid-auto-rows:auto">${[...Array(24)].map((_,h)=>
        `<span style="font-size:9.5px;color:var(--faint);text-align:center">${h%6===0||h===23?h:''}</span>`).join('')}</div></div>`;
  const tip=document.getElementById('tip-heat'),el=document.getElementById('ch-heat');
  el.querySelectorAll('.cells i').forEach(c=>{
    c.addEventListener('mousemove',e=>{
      const k=c.dataset.d+'-'+c.dataset.h,v=map[k];
      tip.innerHTML=`<b>${DOWS[c.dataset.d]} ${c.dataset.h}:00</b>`+
        (v?`<div class="r"><span>${t('heat_reqs')}</span><span style="margin-left:auto;font-weight:600">${v.requests}</span></div>
            <div class="r"><span>tokens</span><span style="margin-left:auto">${fmtTok(v.total||0)}</span></div>
            <div class="r"><span>${t('d_cost')}</span><span style="margin-left:auto">${fmtCost(v.cost||0)}</span></div>`
           :`<div class="r"><span>${t('heat_inactive')}</span></div>`);
      tip.style.display='block';
      const cr=el.getBoundingClientRect();
      tip.style.left=Math.min(e.clientX-cr.left+16,cr.width-150)+'px';
      tip.style.top=Math.max(e.clientY-cr.top-14,4)+'px';});
    c.addEventListener('mouseleave',()=>tip.style.display='none');});
}

// ---------- top sessions bar list ----------
function renderTopSessions(){
  const rows=(DATA.top_sessions||[]).slice(0,8);
  const mx=Math.max(...rows.map(s=>s.cost||0),1e-9);
  const el=document.getElementById('ch-top');
  el.innerHTML=rows.map(s=>
    `<button type="button" class="hr" data-sid="${esc(s.id)}">
      <span class="nm" title="${esc(s.dir||'')}">${esc(short(s.title,28))}</span>
      <span class="tr"><i style="width:${Math.max(2,(s.cost||0)/mx*100).toFixed(1)}%"></i></span>
      <span class="vl">${fmtCost(s.cost||0)}</span></button>`).join('')
    ||`<div class="empty">${t('empty_sessions')}</div>`;
  el.querySelectorAll('.hr').forEach(r=>
    r.onclick=()=>openSession(r.dataset.sid,r));
}

// ---------- cost x speed scatter ----------
function drawScatter(){
  const pts=DATA.requests.filter(r=>r.tok_per_s!=null&&(r.cost||0)>0).slice(0,900);
  const el=document.getElementById('ch-scatter');
  if(!pts.length){el.innerHTML=`<div class="empty">${t('empty_scatter')}</div>`;return;}
  const sx=pts.map(r=>r.tok_per_s).sort((a,b)=>a-b);
  const xmax=sx[Math.min(sx.length-1,Math.floor(sx.length*0.98))]*1.08||1;
  const ly=pts.map(r=>Math.log10(r.cost));
  const lmin=Math.min(...ly)-0.25,lmax=Math.max(...ly)+0.25;
  const W=860,H=250,pl=58,pr=14,pt=12,pb=32,iw=W-pl-pr,ih=H-pt-pb;
  const X=v=>pl+Math.min(1,v/xmax)*iw;
  const Y=v=>pt+ih-((Math.log10(v)-lmin)/(lmax-lmin))*ih;
  let g='';
  for(let k=Math.ceil(lmin);k<=Math.floor(lmax);k++){
    const v=Math.pow(10,k),y=Y(v);
    g+=`<line x1=${pl} y1=${y} x2=${W-pr} y2=${y} stroke="var(--hair)"/>
    <text x=${pl-8} y=${y+4} text-anchor="end" font-size="10" fill="var(--faint)">${fmtCost(v)}</text>`;}
  for(let k=0;k<=4;k++){const x=pl+iw*k/4;
    g+=`<text x=${x} y=${H-10} text-anchor="middle" font-size="10" fill="var(--faint)">${fmtSpeed(xmax*k/4)}</text>`;}
  let dots='';
  pts.forEach((r,i)=>{
    dots+=`<circle data-i="${i}" cx=${X(r.tok_per_s).toFixed(1)} cy=${Y(r.cost).toFixed(1)} r="3.4"
      fill="${donutColors[r.model]||'var(--accent)'}" fill-opacity=".62" style="cursor:pointer"/>`;});
  el.innerHTML=`<svg viewBox="0 0 ${W} ${H}">${g}${dots}
    <text x=${W-pr} y=${H-10} text-anchor="end" font-size="10" fill="var(--faint)">${t('col_speed')} →</text></svg>`;
  const tip=document.getElementById('tip-scatter');
  el.querySelectorAll('circle').forEach(c=>{
    const r=pts[+c.dataset.i];
    c.addEventListener('mousemove',e=>{
      tip.innerHTML=`<b>${esc(r.model)}</b>
        <div class="r"><span>${r.ts.slice(5,19)}</span></div>
        <div class="r"><span>${t('d_cost')}</span><span style="margin-left:auto;font-weight:600">${fmtCost(r.cost)}</span></div>
        <div class="r"><span>${t('col_speed')}</span><span style="margin-left:auto">${fmtSpeed(r.tok_per_s)}</span></div>
        <div class="r"><span>${t('col_sess')}</span><span style="margin-left:auto">${esc(short(r.session_title,18))}</span></div>`;
      tip.style.display='block';
      const cr=el.getBoundingClientRect();
      tip.style.left=Math.min(e.clientX-cr.left+16,cr.width-190)+'px';
      tip.style.top=Math.max(e.clientY-cr.top-20,4)+'px';});
    c.addEventListener('mouseleave',()=>tip.style.display='none');
    c.addEventListener('click',()=>{
      if((DATA.sessions||[]).some(s=>s.id===r.session_id))openSession(r.session_id,document.getElementById('view-title'));});});
}

// ---------- donut ----------
let donutColors={};
function drawDonut(){
  const rows=DATA.by_model.filter(m=>(m.cost||0)>0);
  const total=rows.reduce((a,m)=>a+m.cost,0);
  animateValue(document.getElementById('donut-total'),total,fmtCost);
  const R=76,CI=2*Math.PI*R;let acc=0,g='';
  rows.forEach(m=>{
    const col=donutColors[m.model];
    const frac=m.cost/total,len=frac*CI;
    g+=`<circle data-m="${esc(m.model)}" cx="110" cy="110" r="${R}" fill="none"
      stroke="${col}" stroke-width="30" stroke-dasharray="${len} ${CI-len}"
      stroke-dashoffset="${-acc}" transform="rotate(-90 110 110)"
      style="transition:stroke-dashoffset .9s var(--easeout),stroke-dasharray .9s var(--easeout)"/>`;
    acc+=len;});
  document.getElementById('donut').innerHTML=
    `<svg viewBox="0 0 220 220">${g}</svg>`;
  const leg=document.getElementById('donut-legend');
  leg.innerHTML=rows.map(m=>
    `<div class="row" data-m="${esc(m.model)}">
      <i style="background:${donutColors[m.model]}"></i>
      <span class="m">${esc(short(m.model,22))}</span>
      <span class="v">${fmtCost(m.cost)}</span>
      <span class="p">${(m.cost/total*100).toFixed(1)}%</span></div>`).join('');
  const tip=document.getElementById('tip-donut');
  const hlt=name=>{[...leg.children].forEach(r=>r.classList.toggle('hl',r.dataset.m===name));};
  document.getElementById('donut').querySelectorAll('circle').forEach(a=>{
    a.addEventListener('mousemove',e=>{
      const m=a.dataset.m,mm=rows.find(x=>x.model===m);if(!mm)return;
      tip.innerHTML=`<b>${esc(m)}</b><div class="r"><span>${t('d_cost')}</span>
        <span style="margin-left:auto;font-weight:600">${fmtCost(mm.cost)}</span></div>
        <div class="r"><span>${t('share')}</span><span style="margin-left:auto">${(mm.cost/total*100).toFixed(1)}%</span></div>`;
      tip.style.display='block';
      const host=a.ownerSVGElement.getBoundingClientRect(),
            par=a.ownerSVGElement.parentElement.getBoundingClientRect();
      tip.style.left=(e.clientX-par.left+18)+'px';
      tip.style.top=(e.clientY-par.top-10)+'px';
      hlt(m);});
    a.addEventListener('mouseleave',()=>{tip.style.display='none';hlt(null);});
    a.addEventListener('click',()=>{setModelFilter(a.dataset.m);});});
  [...leg.children].forEach(r=>{
    r.onclick=()=>setModelFilter(r.dataset.m);
    r.onmouseenter=()=>hlt(r.dataset.m);
    r.onmouseleave=()=>hlt(null);});
}
