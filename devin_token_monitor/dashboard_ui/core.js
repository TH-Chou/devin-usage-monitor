'use strict';
let DATA=null, started=false;
const C={input:'var(--blue)',output:'var(--green)',cache:'var(--tan)',cost:'var(--red)'};
const MODEL_DOTS=['var(--accent)','var(--blue)','var(--tan)','var(--green)',
                  'var(--purple)','var(--slate)','var(--teal)','var(--fg)',
                  '#a66d75','#808a56'];
const native_=window.__DTM_VSCODE_BRIDGE__||window.webkit?.messageHandlers?.dtm;
window.onerror=function(m,s,l){ if(native_)native_.postMessage(
  {action:'jserr',msg:String(m)+' @'+String(s||'')+':'+l}); };

// window dragging: mousedown on non-interactive chrome asks the native
// side to start an NSWindow drag with the current event
const DRAG_SKIP='a,button,input,select,label,svg,th,td,.seg,.chip,'+
  '.filters,.legend,.donut-legend,.overlay,.drawer,.switch';
document.addEventListener('mousedown',e=>{
  if(!native_||window.__DTM_VSCODE__||e.button!==0)return;
  if(e.target.closest(DRAG_SKIP))return;
  // keep clear of the resize grips so our drag doesn't fight native resize
  if(e.clientX>innerWidth-12||e.clientY>innerHeight-12)return;
  native_.postMessage({action:'drag'});
});

const fmtTok=n=>{if(n>=1e9)return(n/1e9).toFixed(2)+'B';
  if(n>=1e6)return(n/1e6).toFixed(2)+'M';if(n>=1e3)return(n/1e3).toFixed(1)+'k';
  return ''+Math.round(n);};
const fmtCost=c=>'$'+(c>=1?c.toLocaleString('en-US',{minimumFractionDigits:2,
  maximumFractionDigits:2}):c.toFixed(4));
const fmtPrice=p=>p>=1?('$'+p.toFixed(2)):(p>=0.01?('$'+p.toFixed(3)):('$'+p));
const fmtSpeed=v=>v==null?'—':v>=1000?(v/1000).toFixed(1)+'k/s':Math.round(v)+'/s';
const esc=s=>{const d=document.createElement('div');d.textContent=s==null?'':s;return d.innerHTML.replaceAll('"','&quot;').replaceAll("'","&#39;");};
const short=(s,n)=>s.length>n?s.slice(0,n-1)+'…':s;
const pad=n=>String(n).padStart(2,'0');
const hourKey=d=>d.getFullYear()+'-'+pad(d.getMonth()+1)+'-'+pad(d.getDate())+'T'+pad(d.getHours());
const dayKey=d=>d.getFullYear()+'-'+pad(d.getMonth()+1)+'-'+pad(d.getDate());
const easeOut=t=>1-Math.pow(1-t,4);
