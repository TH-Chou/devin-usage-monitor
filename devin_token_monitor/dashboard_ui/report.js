// ---------- filtered usage reports ----------
const reportEl=name=>document.getElementById('report-'+name);
const reportUI={queryId:0,key:null,scope:null,modelOptions:null,report:null,page:0,lang:''};
const reportCount=n=>n.toLocaleString(LOCALE[LANG]);
const reportDayMs=86400000;
const isoDay=ms=>new Date(ms).toISOString().slice(0,10);

function reportRange(period,today){
  if(period==='all')return {start:'',end:''};
  if(period==='custom')return {start:reportEl('start').value,end:reportEl('end').value};
  const days=period==='7d'?7:period==='30d'?30:1;
  const start=period==='mtd'?today.slice(0,7)+'-01':isoDay(Date.parse(today+'T00:00:00Z')-(days-1)*reportDayMs);
  return {start,end:today};
}
function syncReportModels(){
  const models=DATA.by_model.map(row=>row.model).sort();
  const key=JSON.stringify([LANG,models]);
  if(key===reportUI.modelOptions)return;
  reportUI.modelOptions=key;
  const select=reportEl('model'),selected=select.value;
  select.replaceChildren(new Option(t('f_all_models'),''));
  for(const model of models)select.add(new Option(model,model));
  if(models.includes(selected))select.value=selected;
}
function refreshUsageReport(){
  if(!DATA||!document.getElementById('v-insights').classList.contains('on'))return;
  syncReportModels();
  const period=reportEl('period').value,today=DATA.today.day;
  const {start,end}=reportRange(period,today),model=reportEl('model').value;
  reportEl('dates').hidden=period!=='custom';
  if(period==='custom'&&(!start||!end||start>end)){
    reportUI.queryId++;reportUI.key=null;reportUI.report=null;
    reportEl('results').hidden=true;
    reportEl('status').textContent=t('rp_invalid');
    return;
  }
  const scope=JSON.stringify([today,start,end,model]);
  const key=JSON.stringify([scope,DATA.analytics?.report_revision??DATA.poll?.watermark]);
  if(reportUI.key===key){
    if(reportUI.lang!==LANG&&reportUI.report)drawUsageReport();
    return;
  }
  const queryId=++reportUI.queryId;
  reportUI.key=key;
  if(reportUI.scope!==scope||!reportUI.report){
    reportUI.report=null;
    reportEl('results').hidden=true;
    reportEl('status').textContent=t('loading');
  }
  reportUI.scope=scope;
  if(native_){
    native_.postMessage({action:'usageReport',queryId,start,end,model});
  }else{
    const params=new URLSearchParams({start,end,model});
    fetch('/api/usage-report?'+params).then(async response=>{
      const body=await response.json();
      if(!response.ok)throw Error(body.error||response.statusText);
      showUsageReport(queryId,body,'');
    }).catch(err=>showUsageReport(queryId,null,err.message));
  }
}
function showUsageReport(queryId,report,error){
  if(queryId!==reportUI.queryId)return;
  if(error||!report){
    reportUI.key=null;reportEl('results').hidden=!reportUI.report;
    reportEl('status').textContent=[t('rp_failed'),error].filter(Boolean).join(' · ');
    return;
  }
  reportUI.report=report;
  drawUsageReport();
}
function buildReportBins(report,metric,limit){
  const start=Date.parse(report.start+'T00:00:00Z'),end=Date.parse(report.end+'T00:00:00Z');
  const dayCount=Math.round((end-start)/reportDayMs)+1;
  const span=Math.max(1,Math.ceil(dayCount/limit));
  const bins=Array.from({length:Math.ceil(dayCount/span)},(_,index)=>({
    first:isoDay(start+index*span*reportDayMs),
    last:isoDay(Math.min(end,start+((index+1)*span-1)*reportDayMs)),
    value:0
  }));
  for(const row of report.daily){
    const day=Math.round((Date.parse(row.day+'T00:00:00Z')-start)/reportDayMs);
    bins[Math.floor(day/span)].value+=row[metric];
  }
  return bins;
}
function drawReportTrend(report){
  const el=reportEl('trend'),metric=reportEl('metric').value;
  const width=Math.max(240,Math.floor(el.clientWidth));
  const bins=buildReportBins(report,metric,Math.max(8,Math.min(60,Math.floor(width/15))));
  const peak=Math.max(...bins.map(bin=>bin.value));
  if(!report.daily.length||!peak){
    const key=!report.daily.length?'chart_empty_period':metric==='cost'?'chart_zero_cost':'chart_no_tokens';
    el.innerHTML='<p class="chart-empty">'+esc(t(key))+'</p>';
    return;
  }
  const format=metric==='cost'?fmtCost:fmtTok;
  const ticks=metric!=='cost'&&peak===1?[0,1]:[0,metric==='cost'?peak/2:Math.ceil(peak/2),peak];
  const left=12+Math.max(...ticks.map(tick=>format(tick).length))*7;
  const top=10,baseline=134,step=(width-left-14)/bins.length;
  const barWidth=Math.min(42,Math.max(1,step-3));
  const x=index=>left+(index+.5)*step;
  const y=value=>baseline-(baseline-top)*value/peak;
  const metricLabel=reportEl('metric').selectedOptions[0].text;
  const parts=ticks.map(tick=>
    `<line x1="${left}" x2="${width-10}" y1="${y(tick)}" y2="${y(tick)}" stroke="var(--hair)"/>
     <text x="${left-7}" y="${y(tick)+4}" text-anchor="end">${esc(format(tick))}</text>`);
  const labelStep=Math.max(1,Math.ceil(bins.length/Math.max(2,Math.floor((width-left)/92))));
  bins.forEach((bin,i)=>{
    const range=bin.first===bin.last?bin.first:bin.first+' – '+bin.last;
    const value=metric==='cost'?fmtCost(bin.value):reportCount(bin.value);
    // A full-height transparent target keeps zero-usage intervals inspectable.
    parts.push(`<g><title>${range} · ${esc(metricLabel)} · ${esc(value)}</title>
      <rect x="${left+i*step}" y="${top}" width="${step}" height="${baseline-top}" fill="transparent"/>
      <rect x="${x(i)-barWidth/2}" y="${y(bin.value)}" width="${barWidth}" height="${baseline-y(bin.value)}" fill="var(--accent)"/></g>`);
    const last=bins.length-1;
    if(i===0||i===last||(i%labelStep===0&&i*step>=72&&(last-i)*step>=72)){
      const anchor=bins.length===1?'middle':i===0?'start':i===last?'end':'middle';
      const label=report.start.slice(0,4)===report.end.slice(0,4)?bin.first.slice(5):bin.first;
      parts.push(`<text x="${x(i)}" y="153" text-anchor="${anchor}">${label}</text>`);
    }
  });
  el.innerHTML=`<svg viewBox="0 0 ${width} 160" role="img"><title>${esc(metricLabel)} · ${report.start} – ${report.end}</title>${parts.join('')}</svg>`;
}
let reportTrendWidth=0;
let reportTrendFrame=0;
new ResizeObserver(([entry])=>{
  const width=Math.round(entry.contentRect.width);
  if(width>0&&width!==reportTrendWidth){
    reportTrendWidth=width;
    if(!reportTrendFrame)reportTrendFrame=requestAnimationFrame(()=>{
      reportTrendFrame=0;
      if(reportUI.report&&reportEl('trend').clientWidth)drawReportTrend(reportUI.report);
    });
  }
}).observe(reportEl('trend'));
function drawReportLedger(){
  const report=reportUI.report;
  if(!report||!reportEl('detail').open)return;
  const pageSize=12,pageCount=Math.max(1,Math.ceil(report.daily.length/pageSize));
  reportUI.page=Math.min(reportUI.page,pageCount-1);
  const end=report.daily.length-reportUI.page*pageSize,rows=report.daily.slice(Math.max(0,end-pageSize),end).reverse();
  reportEl('ledger').innerHTML=rows.map(r=>'<tr><td>'+esc(r.day)+'</td><td>'+reportCount(r.requests)+
    '</td><td>'+reportCount(r.total)+'</td><td>'+fmtCost(r.cost)+'</td></tr>').join('');
  reportEl('page').textContent=(reportUI.page+1)+' / '+pageCount;
  reportEl('prev').disabled=reportUI.page===0;reportEl('next').disabled=reportUI.page===pageCount-1;
}
function drawUsageReport(){
  const r=reportUI.report,s=r.summary;
  reportUI.lang=LANG;
  reportEl('status').textContent=r.start+' – '+r.end+' · '+(r.model||t('f_all_models'));
  reportEl('results').hidden=false;
  const hit=s.input+s.cache_read?s.cache_read*100/(s.input+s.cache_read):null;
  const cards=[
    ['rp_est_cost',fmtCost(s.cost),s.requests?fmtCost(s.cost/s.requests)+' '+t('rp_est_unit'):''],
    ['d_total',fmtTok(s.total),reportCount(s.total)+' tok'],
    ['d_reqs',reportCount(s.requests),reportCount(r.session_count)+' '+t('rp_sessions')],
    ['k_hit',hit===null?'—':hit.toFixed(1)+'%',tf('ke_cacheread',{v:fmtTok(s.cache_read)})],
  ];
  reportEl('summary').innerHTML=cards.map(([label,value,note])=>'<div class="card"><div class="label">'+esc(t(label))+
    '</div><div class="value">'+esc(value)+'</div><div class="extra">'+esc(note)+'</div></div>').join('');
  const parts=[['ser_input',s.input,'--blue'],['ser_output',s.output,'--green'],['ser_cache',s.cache_read,'--tan'],['ser_cachew',s.cache_creation,'--purple']];
  reportEl('composition').innerHTML=parts.map(([,v,color])=>'<span style="width:'+(s.total?v*100/s.total:0)+'%;background:var('+color+')"></span>').join('');
  reportEl('composition-key').innerHTML=parts.map(([label,v,color])=>'<span><i class="dot" style="background:var('+color+')"></i>'+
    esc(t(label))+' <b>'+reportCount(v)+'</b></span>').join('');
  for(const [key,rows] of [['models',r.models],['sessions',r.sessions]]){
    reportEl(key).innerHTML=rows.map((row,i)=>{
      const name=key==='models'?'<button type="button" class="report-model-link" data-row="'+i+'">'+esc(row.model)+'</button>':esc(row.title||row.id);
      return '<tr><td>'+name+'</td><td>'+fmtTok(row.total)+'</td><td>'+fmtCost(row.cost)+'</td></tr>';
    }).join('')||'<tr><td colspan="3" class="empty">'+esc(t('none'))+'</td></tr>';
  }
  drawReportTrend(r);reportEl('detail').hidden=!r.daily.length;drawReportLedger();
}
reportEl('models').addEventListener('click',e=>{
  const button=e.target.closest('button[data-row]');
  if(button&&reportUI.report){reportEl('model').value=reportUI.report.models[Number(button.dataset.row)].model;reportUI.page=0;refreshUsageReport();}
});
reportEl('period').addEventListener('change',()=>{
  if(reportEl('period').value==='custom'&&!reportEl('start').value&&!reportEl('end').value){
    const range=reportRange('7d',DATA?.today.day||dayKey(new Date()));
    reportEl('start').value=range.start;reportEl('end').value=range.end;
  }
  reportUI.page=0;refreshUsageReport();
});
for(const name of ['start','end','model'])reportEl(name).addEventListener('change',()=>{
  reportUI.page=0;refreshUsageReport();
});
reportEl('metric').addEventListener('change',()=>{if(reportUI.report)drawReportTrend(reportUI.report);});
reportEl('detail').addEventListener('toggle',drawReportLedger);
reportEl('prev').onclick=()=>{reportUI.page=Math.max(0,reportUI.page-1);drawReportLedger();};
reportEl('next').onclick=()=>{reportUI.page++;drawReportLedger();};
