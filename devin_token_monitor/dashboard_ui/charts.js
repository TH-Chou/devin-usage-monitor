// Each displayed interval has one column: its bar, points, pointer target and
// keyboard value all use the same boundaries.
const charts={};
const tokenSeries=[
  {key:'input',label:'ser_input',color:C.input},
  {key:'output',label:'ser_output',color:C.output},
  {key:'cache_read',label:'ser_cache',color:C.cache},
  {key:'cache_creation',label:'ser_cachew',color:'var(--purple)'},
];
const costSeries=[{key:'cost',label:'ser_cost',color:C.cost}];
const chartTitles={tok:'s_trend',mix:'s_mix',cost:'s_cost',hit:'s_hit',heat:'s_heat'};
const safeMetric=value=>Number.isFinite(value)&&value>0?value:0;
const chartLocale=()=>LOCALE[LANG]||'en-US';
const exactTokens=value=>value.toLocaleString(chartLocale())+' tok';
function buckets(mode){
  const time=Date.parse(DATA.generated_at);
  const now=Number.isFinite(time)?new Date(time):new Date();
  const hourly=mode==='hour',size=hourly?24:14;
  const anchor=new Date(now);
  if(hourly)anchor.setMinutes(0,0,0);else anchor.setHours(0,0,0,0);
  const rows=hourly?DATA.by_hour:DATA.by_day;
  const lookup=new Map((rows||[]).map(row=>[hourly?row.hour:row.day,row]));
  const result=[],seen=new Set();
  const labelFmt=new Intl.DateTimeFormat(chartLocale(),hourly?{hour:'2-digit',minute:'2-digit',hourCycle:'h23'}:{month:'numeric',day:'numeric'});
  const fullFmt=new Intl.DateTimeFormat(chartLocale(),hourly?{year:'numeric',month:'short',day:'numeric',hour:'2-digit',minute:'2-digit',hourCycle:'h23'}:{year:'numeric',month:'short',day:'numeric'});
  for(let ago=size-1;ago>=0;ago--){
    const stamp=new Date(anchor);
    if(hourly)stamp.setTime(anchor.getTime()-ago*3600000);else stamp.setDate(anchor.getDate()-ago);
    const key=hourly?hourKey(stamp):dayKey(stamp);
    // The database groups repeated autumn DST hours by their local hour key.
    if(seen.has(key))continue;
    seen.add(key);
    result.push({key,label:labelFmt.format(stamp),full:fullFmt.format(stamp),row:lookup.get(key)});
  }
  return result;
}
function chartScale(maximum,whole=false){
  if(!(maximum>0)||!Number.isFinite(maximum))return {top:1,step:1,count:1};
  const target=maximum/4,unit=10**Math.floor(Math.log10(target));
  const multiple=[1,2,5,10].find(n=>n*unit>=target)||10;
  const step=Math.max(whole?1:0,unit*multiple);
  const count=Math.max(1,Math.ceil(maximum/step-1e-10));
  return {top:step*count,step,count};
}
function axisLabel(value,step,money=false){
  if(money&&value>0&&value<.0001){
    return '$'+value.toLocaleString(chartLocale(),{notation:'scientific',maximumFractionDigits:2});
  }
  const [unit,suffix]=[[1e9,'B'],[1e6,'M'],[1e3,'k'],[1,'']].find(([size])=>value>=size)||[1,''];
  const digits=Math.min(12,Math.max(0,-Math.floor(Math.log10(step/unit))));
  return (money?'$':'')+(value/unit).toLocaleString(chartLocale(),{maximumFractionDigits:digits})+suffix;
}
function chartLayout(host,n){
  const w=Math.max(220,Math.round(host.clientWidth)||600),h=Math.round(Math.min(196,Math.max(140,w*.26)));
  const left=w<420?57:70,right=17,top=12,bottom=h-26,step=(w-left-right)/n;
  return {w,h,left,right,top,bottom,step,center:i=>left+(i+.5)*step,edge:i=>left+i*step};
}
function timeGrid(box,bs,scale,label){
  let marks='';
  for(let tick=0;tick<=scale.count;tick++){
    const y=box.bottom-(box.bottom-box.top)*tick/scale.count;
    marks+='<line x1="'+box.left+'" y1="'+y+'" x2="'+box.edge(bs.length)+'" y2="'+y+'" stroke="var(--hair)"/>'+
      '<text x="'+(box.left-6)+'" y="'+(y+3)+'" text-anchor="end" fill="var(--dim)" font-size="11">'+esc(label(tick*scale.step))+'</text>';
  }
  const visible=Math.min(bs.length,Math.max(2,Math.floor((box.w-box.left-box.right)/62)));
  for(let k=0;k<visible;k++){
    const i=Math.round(k*(bs.length-1)/(visible-1)),anchor=k===0?'start':k===visible-1?'end':'middle';
    marks+='<text x="'+box.center(i)+'" y="'+(box.h-6)+'" text-anchor="'+anchor+'" fill="var(--dim)" font-size="11">'+esc(bs[i].label)+'</text>';
  }
  return marks;
}
function chartNodes(id){
  const host=document.getElementById('ch-'+id);
  let plot=host.querySelector('svg.time-plot');
  if(!plot){
    host.replaceChildren();
    plot=document.createElementNS('http://www.w3.org/2000/svg','svg');
    plot.setAttribute('class','time-plot');
    plot.setAttribute('aria-hidden','true');
    const input=document.createElement('input');
    input.type='range';input.className='bucket-cursor';input.min='0';input.step='1';
    host.append(plot,input);
  }
  return {host,plot,input:host.querySelector('.bucket-cursor'),tip:document.getElementById('tip-'+id)};
}
function chartEmpty(id,message){
  const host=document.getElementById('ch-'+id);
  host.innerHTML='<div class="chart-empty" role="status">'+esc(t(message))+'</div>';
  document.getElementById('tip-'+id).style.display='none';
}
function showChartTip(tip,heading,values,x,y){
  tip.innerHTML='<b>'+esc(heading)+'</b>'+values.map(({name,value,color})=>
    '<div class="r">'+(color?'<i style="background:'+color+'"></i>':'')+'<span>'+esc(name)+'</span>'+
    '<strong style="margin-left:auto">'+esc(value)+'</strong></div>').join('');
  tip.style.display='block';
  const bounds=tip.offsetParent.getBoundingClientRect();
  tip.style.left=Math.max(0,Math.min(x-bounds.left+10,bounds.width-tip.offsetWidth))+'px';
  tip.style.top=Math.max(0,Math.min(y-bounds.top+5,bounds.height-tip.offsetHeight))+'px';
}
function describeBucket(label,values){
  return [label,...values.map(v=>v.name+' '+v.value)].join(' · ');
}
function drawTimePlot(id,bs,box,content,getValues){
  const {plot,input,tip}=chartNodes(id);
  plot.setAttribute('viewBox','0 0 '+box.w+' '+box.h);
  plot.innerHTML=content+'<g class="bucket-marker" visibility="hidden" pointer-events="none">'+
    '<rect x="0" y="'+box.top+'" width="'+box.step+'" height="'+(box.bottom-box.top)+'" fill="var(--fg)" fill-opacity=".05"/>'+
    '<line x1="'+(box.step/2)+'" x2="'+(box.step/2)+'" y1="'+box.top+'" y2="'+box.bottom+'" stroke="var(--dim)" stroke-dasharray="3 3"/></g>';
  const marker=plot.lastElementChild;
  input.setAttribute('aria-label',t(chartTitles[id])+' · '+t('chart_cursor'));
  input.max=String(bs.length-1);
  let i=bs.findIndex(b=>b.key===input.dataset.key);
  if(i<0)i=bs.length-1;
  function select(index,show){
    const bucket=bs[index],values=getValues(index);
    input.value=String(index);input.dataset.key=bucket.key;
    input.setAttribute('aria-valuetext',describeBucket(bucket.full,values));
    if(!show)return;
    marker.setAttribute('visibility','visible');
    marker.setAttribute('transform','translate('+box.edge(index)+' 0)');
    const bounds=plot.getBoundingClientRect();
    showChartTip(tip,bucket.full,values,bounds.left+box.center(index)*bounds.width/box.w,bounds.top+box.top);
  }
  function hide(){marker.setAttribute('visibility','hidden');tip.style.display='none';}
  hide();select(i,document.activeElement===input);
  const fromPointer=e=>{
    const bounds=plot.getBoundingClientRect();
    if(!bounds.width)return;
    const x=(e.clientX-bounds.left)*box.w/bounds.width;
    const y=(e.clientY-bounds.top)*box.h/bounds.height;
    if(x<box.left||x>box.edge(bs.length)||y<box.top||y>box.bottom){hide();return;}
    select(Math.min(bs.length-1,Math.floor((x-box.left)/box.step)),true);
  };
  plot.onpointermove=fromPointer;plot.onpointerdown=fromPointer;
  plot.onpointerleave=()=>{if(document.activeElement!==input)hide();};
  input.onfocus=input.oninput=()=>select(Number(input.value),true);
  input.onblur=hide;input.onkeydown=e=>{if(e.key==='Escape')hide();};
}
function timeLegend(id,defs){
  const el=document.getElementById('leg-'+id),st=charts[id];
  const signature=JSON.stringify([LANG,defs.map(d=>d.key)]);
  if(st.legend!==signature){
    el.replaceChildren();
    for(const def of defs){
      const button=document.createElement('button');button.type='button';button.dataset.series=def.key;
      const swatch=document.createElement('i');swatch.style.background=def.color;
      button.append(swatch,document.createTextNode(t(def.label)));el.append(button);
      button.onclick=()=>{
        if(st.hidden.has(def.key))st.hidden.delete(def.key);else st.hidden.add(def.key);
        refreshChart(id);
      };
    }
    st.legend=signature;
  }
  for(const button of el.children){
    const pressed=!st.hidden.has(button.dataset.series);
    button.setAttribute('aria-pressed',String(pressed));button.classList.toggle('off',!pressed);
  }
}
function refreshChart(id){
  const st=charts[id],money=id==='cost',defs=money?costSeries:tokenSeries;
  timeLegend(id,defs);
  const bs=buckets(st.mode),visible=defs.filter(def=>!st.hidden.has(def.key));
  if(!visible.length)return chartEmpty(id,'chart_hidden_series');
  if(!bs.some(b=>b.row))return chartEmpty(id,'chart_empty_period');
  const values=visible.map(d=>bs.map(b=>safeMetric(b.row?.[d.key])));
  const max=Math.max(...values.flat());
  if(max===0)return chartEmpty(id,money?'chart_zero_cost':'chart_no_tokens');
  const box=chartLayout(document.getElementById('ch-'+id),bs.length);
  const scale=chartScale(max,!money),y=v=>box.bottom-(box.bottom-box.top)*v/scale.top;
  let content=timeGrid(box,bs,scale,v=>axisLabel(v,scale.step,money));
  for(const [s,def] of visible.entries()){
    const series=values[s];
    if(money){
      const bar=Math.min(box.step*.66,28);
      series.forEach((v,i)=>{if(v)content+='<rect x="'+(box.center(i)-bar/2)+'" y="'+y(v)+'" width="'+bar+
        '" height="'+(box.bottom-y(v))+'" fill="'+def.color+'"/>';});
    }else{
      // A horizontal segment spans the full interval it describes.
      const path=series.map((v,i)=>(i===0?'M'+box.left+' '+y(v):'V'+y(v))+'H'+box.edge(i+1)).join(' ');
      content+='<path class="ln" d="'+path+'" stroke="'+def.color+'" stroke-width="1.8" fill="none"/>';
    }
  }
  drawTimePlot(id,bs,box,content,i=>visible.map((d,s)=>({
    name:t(d.label),color:d.color,value:money?fmtCost(values[s][i]):exactTokens(values[s][i])
  })));
}
function setupChart(id,kind){
  charts[id]={mode:'hour',hidden:new Set(),kind};
  wireSeg(id,()=>refreshChart(id));
}
function segThumb(seg){
  const on=seg.querySelector('button.on'),th=seg.querySelector('.thumb');
  if(on?.offsetWidth&&th){th.style.left=on.offsetLeft+'px';th.style.width=on.offsetWidth+'px';}}
// WebKit checks observed boxes for feedback within the current layout pass.
// Defer writes to the next frame and keep one update per target during resize.
function observeChartSizes(update){
  const pending=new Map();
  let frame=0;
  return new ResizeObserver(entries=>{
    for(const {target,contentRect} of entries)pending.set(target,Math.round(contentRect.width));
    if(frame)return;
    frame=requestAnimationFrame(()=>{
      frame=0;
      for(const [target,width] of pending)update(target,width);
      pending.clear();
    });
  });
}
const segmentSizes=observeChartSizes((segment,width)=>{if(width)segThumb(segment);});
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
// generic hour/day segmented switch driving a render callback
function wireSeg(id,render){
  bindSegment(document.getElementById('seg-'+id),mode=>{
    charts[id].mode=mode;
    if(DATA)render(true);
  });
}
// ---------- stacked token mix ----------
function drawMix(){
  const order=[tokenSeries[2],tokenSeries[0],tokenSeries[3],tokenSeries[1]];
  document.getElementById('leg-mix').innerHTML=order.map(d=>'<span><i style="background:'+d.color+'"></i>'+esc(t(d.label))+'</span>').join('');
  const bs=buckets(charts.mix.mode);
  if(!bs.some(b=>b.row))return chartEmpty('mix','chart_empty_period');
  const values=bs.map(b=>order.map(d=>safeMetric(b.row?.[d.key])));
  const totals=values.map(v=>v.reduce((a,b)=>a+b,0)),max=Math.max(...totals);
  if(!max)return chartEmpty('mix','chart_no_tokens');
  const box=chartLayout(document.getElementById('ch-mix'),bs.length);
  const scale=chartScale(max,true),bar=Math.min(box.step*.68,29);
  let content=timeGrid(box,bs,scale,v=>axisLabel(v,scale.step));
  values.forEach((col,i)=>{
    let baseline=box.bottom;
    col.forEach((v,j)=>{
      if(!v)return;
      const h=(box.bottom-box.top)*v/scale.top;
      baseline-=h;
      content+='<rect x="'+(box.center(i)-bar/2)+'" y="'+baseline+'" width="'+bar+'" height="'+h+'" fill="'+order[j].color+'"/>';
    });
  });
  drawTimePlot('mix',bs,box,content,i=>[
    ...order.map((d,j)=>({name:t(d.label),value:exactTokens(values[i][j]),color:d.color})),
    {name:t('mix_total'),value:exactTokens(totals[i])}
  ]);
}

// ---------- per-bucket cache hit rate ----------
function drawHit(){
  const bs=buckets(charts.hit.mode);
  if(!bs.some(b=>b.row))return chartEmpty('hit','chart_empty_period');
  const rates=bs.map(({row})=>{
    const cached=safeMetric(row?.cache_read),base=safeMetric(row?.input)+cached;
    return base?100*cached/base:null;
  });
  if(rates.every(v=>v===null))return chartEmpty('hit','chart_no_rate');
  const box=chartLayout(document.getElementById('ch-hit'),bs.length);
  let content=timeGrid(box,bs,{step:25,count:4},v=>v+'%'),path='',points='';
  rates.forEach((rate,i)=>{
    if(rate===null)return;
    const x=box.center(i),y=box.bottom-rate/100*(box.bottom-box.top);
    path+=(i&&rates[i-1]!==null?'L':'M')+x+' '+y+' ';
    points+='<circle cx="'+x+'" cy="'+y+'" r="2.4" fill="'+C.cache+'"/>';
  });
  content+='<path d="'+path+'" fill="none" stroke="'+C.cache+'" stroke-width="1.6"/>'+points;
  drawTimePlot('hit',bs,box,content,i=>[
    {name:t('hit_rate'),value:rates[i]===null?'—':rates[i].toFixed(1)+'%'},
    {name:t('ser_cache'),value:exactTokens(safeMetric(bs[i].row?.cache_read))},
    {name:t('hit_reqs'),value:String(safeMetric(bs[i].row?.requests))}
  ]);
}
charts.scatter={};
const timeChartSizes=observeChartSizes((target,width)=>{
  const id=target.id.slice(3),st=charts[id];
  if(!st||!DATA||!width||st.width===width)return;
  st.width=width;
  if(id==='mix')drawMix();else if(id==='hit')drawHit();else if(id==='scatter')drawScatter();else refreshChart(id);
});
for(const id of ['tok','cost','mix','hit','scatter'])timeChartSizes.observe(document.getElementById('ch-'+id));

// ---------- activity by local weekday and hour ----------
function drawHeat(){
  const cellsByKey=new Map((DATA.heatmap||[]).map(row=>[row.dow*24+row.hour,row]));
  if(!cellsByKey.size)return chartEmpty('heat','chart_empty_period');
  const host=document.getElementById('ch-heat'),tip=document.getElementById('tip-heat');
  let matrix=host.querySelector('.heat');
  if(!matrix){
    const hourLabels=Array.from({length:24},(_,h)=>'<span>'+([0,6,12,18,23].includes(h)?h:'')+'</span>').join('');
    host.innerHTML='<div class="heat" aria-hidden="true"></div><input class="bucket-cursor" type="range" min="0" max="167" step="1" value="0">';
    matrix=host.firstElementChild;
    matrix.innerHTML=Array.from({length:7},(_,d)=>'<div class="dl"></div><div class="cells">'+
      Array.from({length:24},(_,h)=>'<i data-slot="'+(d*24+h)+'"></i>').join('')+'</div>').join('')+
      '<div></div><div class="hrs">'+hourLabels+'</div>';
  }
  const dayNames=DOWSL[LANG]||DOWSL.zh;
  const slots=matrix.querySelectorAll('[data-slot]'),input=host.lastElementChild;
  input.setAttribute('aria-label',t('s_heat')+' · '+t('chart_cursor'));
  matrix.querySelectorAll('.dl').forEach((el,i)=>el.textContent=dayNames[i]);
  const max=Math.max(1,...Array.from(cellsByKey.values(),r=>safeMetric(r.requests)));
  for(const [i,cell] of slots.entries()){
    const v=safeMetric(cellsByKey.get(i)?.requests);
    cell.style.background=v?'var(--accent)':'';
    cell.style.opacity=v?String(Math.ceil(Math.sqrt(v/max)*5)/5):'';
  }
  function hide(){
    tip.style.display='none';
    matrix.querySelector('[data-current]')?.removeAttribute('data-current');
  }
  function select(i,show){
    const row=cellsByKey.get(i),label=dayNames[Math.floor(i/24)]+' '+(i%24)+':00';
    const values=row?[{name:t('heat_reqs'),value:String(safeMetric(row.requests))},
      {name:t('d_total'),value:exactTokens(safeMetric(row.total))},
      {name:t('d_cost'),value:fmtCost(safeMetric(row.cost))}]:[{name:t('heat_inactive'),value:''}];
    input.value=String(i);input.setAttribute('aria-valuetext',describeBucket(label,values));
    if(!show)return;
    hide();
    slots[i].setAttribute('data-current','');
    const r=slots[i].getBoundingClientRect();
    showChartTip(tip,label,values,r.left+r.width/2,r.top);
  }
  hide();select(Number(input.value),document.activeElement===input);
  const fromPointer=e=>{const cell=e.target.closest('[data-slot]');if(cell)select(Number(cell.dataset.slot),true);else hide();};
  matrix.onpointermove=fromPointer;matrix.onpointerdown=fromPointer;
  matrix.onpointerleave=()=>{if(document.activeElement!==input)hide();};
  input.oninput=input.onfocus=()=>select(Number(input.value),true);input.onblur=hide;
  input.onkeydown=e=>{
    if(e.key==='Escape'){hide();return;}
    if(e.key==='ArrowDown'||e.key==='ArrowUp'){
      e.preventDefault();
      select(Math.max(0,Math.min(167,Number(input.value)+(e.key==='ArrowDown'?24:-24))),true);
    }
  };
}

// ---------- top sessions bar list ----------
function renderTopSessions(){
  const rows=(DATA.top_sessions||[]).slice(0,8);
  const mx=Math.max(0,...rows.map(s=>safeMetric(s.cost)))||1;
  const el=document.getElementById('ch-top');
  el.innerHTML=rows.map(s=>
    `<button type="button" class="hr" data-sid="${esc(s.id)}">
      <span class="nm" title="${esc(s.dir||'')}">${esc(short(s.title,28))}</span>
      <span class="tr"><i style="width:${(safeMetric(s.cost)/mx*100).toFixed(2)}%"></i></span>
      <span class="vl">${fmtCost(safeMetric(s.cost))}</span></button>`).join('')
    ||`<div class="empty">${t('empty_sessions')}</div>`;
  el.querySelectorAll('.hr').forEach(r=>
    r.onclick=()=>openSession(r.dataset.sid,r));
}

// ---------- per-request cost and measured output speed ----------
function drawScatter(){
  const rows=(DATA.requests||[]).filter(r=>Number.isFinite(r.tok_per_s)&&r.tok_per_s>=0&&
    Number.isFinite(r.cost)&&r.cost>=0).slice(0,900);
  if(!rows.length)return chartEmpty('scatter','empty_scatter');
  const {host,plot,input,tip}=chartNodes('scatter'),box=chartLayout(host,1);
  const {w,h,left,right,top,bottom}=box,plotRight=w-right;
  const maxSpeed=Math.max(...rows.map(r=>r.tok_per_s));
  const xScale=chartScale(maxSpeed),x=v=>left+(plotRight-left)*v/xScale.top;
  const costs=rows.map(r=>r.cost),maxCost=Math.max(...costs),minCost=Math.min(...costs);
  const logCost=minCost>0&&maxCost/minCost>=100;
  let ticks,tickLabel,y;
  if(logCost){
    const lo=Math.floor(Math.log10(minCost)),hi=Math.ceil(Math.log10(maxCost));
    const count=Math.min(4,hi-lo);
    ticks=Array.from({length:count+1},(_,i)=>10**(lo+Math.round((hi-lo)*i/count)));
    y=v=>bottom-(bottom-top)*(Math.log10(v)-lo)/(hi-lo);
    tickLabel=v=>axisLabel(v,v,true);
  }else{
    const scale=chartScale(maxCost);
    ticks=Array.from({length:maxCost?scale.count+1:1},(_,i)=>i*scale.step);
    y=v=>bottom-(bottom-top)*v/scale.top;
    tickLabel=v=>axisLabel(v,scale.step,true);
  }
  let marks='';
  for(const tick of ticks){
    const py=y(tick);
    marks+='<line x1="'+left+'" x2="'+plotRight+'" y1="'+py+'" y2="'+py+'" stroke="var(--hair)"/>'+
      '<text x="'+(left-6)+'" y="'+(py+3)+'" text-anchor="end" font-size="11" fill="var(--dim)">'+esc(tickLabel(tick))+'</text>';
  }
  for(let i=0;i<=(maxSpeed?xScale.count:0);i++){
    const v=i*xScale.step,anchor=i===0?'start':i===xScale.count?'end':'middle';
    marks+='<text x="'+x(v)+'" y="'+(h-6)+'" text-anchor="'+anchor+'" font-size="11" fill="var(--dim)">'+esc(axisLabel(v,xScale.step)+'/s')+'</text>';
  }
  const dots=rows.map((r,i)=>'<circle data-point="'+i+'" cx="'+x(r.tok_per_s)+'" cy="'+y(r.cost)+
    '" r="3.1" fill="'+(donutColors[r.model]||'var(--accent)')+'" opacity=".75" style="cursor:pointer"/>').join('');
  plot.setAttribute('viewBox','0 0 '+w+' '+h);
  plot.innerHTML=marks+dots+'<circle r="5.1" stroke="var(--fg)" stroke-width="1.5" fill="none" visibility="hidden" pointer-events="none"/>';
  const ring=plot.lastElementChild;
  input.max=String(rows.length-1);
  input.setAttribute('aria-label',t('s_scatter')+' · '+t('chart_scatter_cursor'));
  const key=r=>r.request_id||r.message_id||JSON.stringify([r.ts,r.session_id,r.model]);
  const prev=rows.findIndex(r=>String(key(r))===input.dataset.key);
  function hide(){ring.setAttribute('visibility','hidden');tip.style.display='none';}
  function select(i,show){
    const row=rows[i],label=row.model;
    const values=[
      {name:t('col_time'),value:(row.ts||'').slice(0,19).replace('T',' ')},
      {name:t('d_cost'),value:fmtCost(row.cost)},
      {name:t('col_speed'),value:row.tok_per_s.toLocaleString(chartLocale(),{maximumFractionDigits:3})+' tok/s'},
      {name:t('col_sess'),value:row.session_title||row.session_id||'—'}
    ];
    input.value=String(i);input.dataset.key=String(key(row));
    input.setAttribute('aria-valuetext',describeBucket(label,values));
    if(!show)return;
    const px=x(row.tok_per_s),py=y(row.cost),bounds=plot.getBoundingClientRect();
    ring.setAttribute('visibility','visible');ring.setAttribute('cx',px);ring.setAttribute('cy',py);
    showChartTip(tip,label,values,bounds.left+px*bounds.width/w,bounds.top+py*bounds.height/h);
  }
  function inspect(i){
    const sid=rows[i].session_id;
    const available=(DATA.sessions||[]).some(s=>s.id===sid)||(DATA.top_sessions||[]).some(s=>s.id===sid);
    if(available)openSession(sid,input);else setModelFilter('',sid);
  }
  hide();select(Math.max(0,prev),document.activeElement===input);
  plot.onpointermove=e=>{const point=e.target.closest('[data-point]');if(point)select(Number(point.dataset.point),true);else hide();};
  plot.onpointerleave=()=>{if(document.activeElement!==input)hide();};
  plot.onclick=e=>{
    const point=e.target.closest('[data-point]');
    if(point){const i=Number(point.dataset.point);select(i,false);inspect(i);}
  };
  input.onfocus=input.oninput=()=>select(Number(input.value),true);input.onblur=hide;
  input.onkeydown=e=>{
    if(e.key==='Escape')hide();
    if(e.key==='Enter'){e.preventDefault();inspect(Number(input.value));}
  };
}

// ---------- all-time model cost shares ----------
let donutColors={};
function drawDonut(){
  const rows=(DATA.by_model||[]).slice().sort((a,b)=>safeMetric(b.cost)-safeMetric(a.cost));
  // Backend sums unrounded model costs into total.cost. Adding published row
  // values back together can accumulate rounding error, especially in old snapshots.
  const total=Number.isFinite(DATA.total?.cost)?Math.max(0,DATA.total.cost):
    rows.reduce((sum,row)=>sum+safeMetric(row.cost),0);
  document.getElementById('donut-total').textContent=fmtCost(total);
  const list=document.getElementById('donut-legend');
  const focused=list.contains(document.activeElement)?document.activeElement.dataset.model:undefined;
  const rowsHtml=rows.map(row=>{
    const cost=safeMetric(row.cost),share=total>0?Math.min(100,100*cost/total):null;
    const text=share==null?'—':share>0&&share<0.1?'<0.1%':share.toFixed(1)+'%';
    const color=donutColors[row.model]||'var(--accent)';
    return '<button type="button" class="model-share-row" data-model="'+esc(row.model)+'" title="'+esc(row.model)+'">'+
      '<span class="share-name"><i style="background:'+color+'"></i>'+esc(row.model)+'</span>'+
      '<span class="share-cost">'+esc(fmtCost(cost))+'</span><span class="share-percent">'+esc(text)+'</span>'+
      '<span class="share-track" aria-hidden="true"><i style="width:'+(share||0)+'%;background:'+color+'"></i></span></button>';
  }).join('');
  list.innerHTML=(!rows.length||!total?'<div class="chart-empty">'+esc(t(rows.length?'chart_zero_cost':'none'))+'</div>':'')+rowsHtml;
  if(focused!==undefined)Array.from(list.querySelectorAll('button')).find(b=>b.dataset.model===focused)?.focus({preventScroll:true});
  list.onclick=e=>{const button=e.target.closest('button[data-model]');if(button)setModelFilter(button.dataset.model);};
}
