// ---------- filtered usage reports ----------
const reportEl=name=>document.getElementById('report-'+name);
const reportUI={queryId:0,key:null,modelOptions:null,report:null,page:0,lang:''};
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
  const key=JSON.stringify([DATA.analytics?.report_revision??DATA.poll?.watermark,today,start,end,model]);
  if(reportUI.key===key){
    if(reportUI.lang!==LANG&&reportUI.report)drawUsageReport();
    return;
  }
  const queryId=++reportUI.queryId;
  reportUI.key=key;reportUI.report=null;
  reportEl('results').hidden=true;reportEl('status').textContent=t('loading');
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
    reportUI.key=null;reportUI.report=null;reportEl('results').hidden=true;
    reportEl('status').textContent=[t('rp_failed'),error].filter(Boolean).join(' · ');
    return;
  }
  reportUI.report=report;
  drawUsageReport();
}
function drawReportTrend(report){
  const el=reportEl('trend'),metric=reportEl('metric').value;
  if(!report.daily.length){el.textContent=t('none');return;}
  const start=Date.parse(report.start+'T00:00:00Z'),end=Date.parse(report.end+'T00:00:00Z');
  const days=Math.round((end-start)/reportDayMs)+1;
  // Bound the number of bars for multi-year reports. Each span covers calendar days, including idle days.
  const span=Math.ceil(days/45),bins=Array(Math.ceil(days/span)).fill(0);
  for(const row of report.daily){
    const offset=Math.round((Date.parse(row.day+'T00:00:00Z')-start)/reportDayMs);
    bins[Math.floor(offset/span)]+=row[metric];
  }
  const width=720,height=156,left=62,right=12,top=12,bottom=26;
  const chartHeight=height-top-bottom,step=(width-left-right)/bins.length,barWidth=Math.min(32,step*.76);
  const max=Math.max(...bins)||1,fmt=metric==='cost'?fmtCost:fmtTok;
  let shapes='';
  for(let i=0;i<=2;i++){
    const y=top+chartHeight*i/2;
    shapes+='<line x1="'+left+'" x2="'+(width-right)+'" y1="'+y+'" y2="'+y+'" stroke="var(--hair)"/>'+
      '<text x="'+(left-8)+'" y="'+(y+3)+'" text-anchor="end" font-size="10" fill="var(--dim)">'+fmt(max*(1-i/2))+'</text>';
  }
  bins.forEach((value,index)=>{
    const x=left+(index+.5)*step,h=value/max*chartHeight;
    const first=isoDay(start+index*span*reportDayMs);
    const last=isoDay(Math.min(end,start+((index+1)*span-1)*reportDayMs));
    const range=first===last?first:first+' – '+last;
    shapes+='<rect x="'+(x-barWidth/2)+'" y="'+(height-bottom-h)+'" width="'+barWidth+'" height="'+h+
      '" rx="2" fill="var(--accent)"><title>'+range+' · '+(metric==='cost'?fmtCost(value):reportCount(value))+'</title></rect>';
    if(index===0||index===bins.length-1||(index%Math.ceil(bins.length/4)===0&&index<bins.length-1-Math.floor(bins.length/8))){
      const anchor=bins.length===1?'middle':index===0?'start':index===bins.length-1?'end':'middle';
      shapes+='<text x="'+x+'" y="'+(height-5)+'" text-anchor="'+anchor+'" font-size="11" fill="var(--dim)">'+
        (days>365?first.slice(0,7):first.slice(5))+'</text>';
    }
  });
  el.innerHTML='<svg viewBox="0 0 '+width+' '+height+'" role="img"><title>'+esc(t('s_trend'))+' · '+report.start+' – '+report.end+'</title>'+shapes+'</svg>';
}
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
