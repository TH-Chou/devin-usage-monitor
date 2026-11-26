const THEMES=new Set(Array.from(document.getElementById('set-theme').options, option=>option.value));
function applyTheme(theme){
  theme=THEMES.has(theme)?theme:'system';
  if(theme==='system')document.documentElement.removeAttribute('data-theme');
  else document.documentElement.dataset.theme=theme;
}
async function saveWebSettings(patch){
  const response=await fetch('/api/settings',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(patch)});
  const snapshot=await response.json();
  if(!response.ok)throw Error(snapshot.error||response.statusText);
  return snapshot;
}
async function setTheme(theme){
  if(!THEMES.has(theme))return;
  if(!native_){
    try{update(await saveWebSettings({theme}));}
    catch(error){document.getElementById('set-theme').value=DATA?.settings.theme||'system';toast(error.message);}
    return;
  }
  applyTheme(theme);
  native_.postMessage({action:'setTheme',value:theme});
  if(DATA){DATA.settings.theme=theme;update(DATA);}
}
function setPressed(button, pressed){
  button.classList.toggle('on',pressed);
  button.setAttribute('aria-pressed',String(pressed));
}
function applyLang(){
  document.documentElement.lang=LOCALE[LANG]||'zh-CN';
  document.querySelectorAll('[data-label]').forEach(el=>{
    el.setAttribute('aria-label',t(el.dataset.label));el.title=t(el.dataset.label);});
  document.querySelectorAll('[data-i18n]').forEach(el=>{
    const v=t(el.dataset.i18n);if(el.textContent!==v)el.textContent=v;});
  document.querySelectorAll('[data-i18n-ph]').forEach(el=>el.placeholder=t(el.dataset.i18nPh));
  document.querySelectorAll('#lang-row .chip').forEach(c=>
    setPressed(c,c.dataset.lang===LANG));
  const cur=document.querySelector('.view.on');
  if(cur)document.getElementById('view-title').textContent=TKEYS[cur.id.slice(2)]?t(TKEYS[cur.id.slice(2)]):'';
}
async function setLang(l){
  if(!I18N[l])return;
  if(!native_){
    try{update(await saveWebSettings({language:l}));}catch(error){toast(error.message);}
    return;
  }
  LANG=l;
  native_.postMessage({action:'setLanguage',value:l});
  applyLang();if(DATA){DATA.settings.language=l;update(DATA);}}

function toast(msg){const t=document.getElementById('toast');
  t.textContent=msg;t.classList.add('show');
  clearTimeout(t._h);t._h=setTimeout(()=>t.classList.remove('show'),2200);}

// number count-up with ease-out curve
function animateValue(el,to,fmt){
  const from=el._v||0,dur=350,t0=performance.now();
  el._v=to;
  if(el._raf)cancelAnimationFrame(el._raf);
  if(started||matchMedia('(prefers-reduced-motion: reduce)').matches){
    el.textContent=fmt(to);return;
  }
  const step=now=>{const t=Math.min(1,(now-t0)/dur);
    el.textContent=fmt(from+(to-from)*easeOut(t));
    if(t<1)el._raf=requestAnimationFrame(step);};
  el._raf=requestAnimationFrame(step);
}

// ---------- nav / views ----------
const TKEYS={overview:'nav_overview',insights:'nav_insights',models:'nav_models',
             sessions:'nav_sessions',requests:'nav_requests',settings:'nav_settings'};
function navigateTo(v){
  if(!TKEYS[v])return;
  document.querySelectorAll('nav a').forEach(x=>{x.classList.toggle('on',x.dataset.v===v);if(x.dataset.v===v)x.setAttribute('aria-current','page');else x.removeAttribute('aria-current');});
  document.querySelectorAll('.view').forEach(x=>
    x.classList.toggle('on',x.id==='v-'+v));
  document.getElementById('view-title').textContent=t(TKEYS[v]);
  document.querySelector('main').scrollTop=0;
  closeSession(false);
  if(native_)native_.postMessage({action:'navigate',view:v});
  if(DATA)renderView(v);
}
document.getElementById('nav').addEventListener('click',e=>{
  const a=e.target.closest('a');if(a){e.preventDefault();navigateTo(a.dataset.v);}
});
document.addEventListener('keydown',e=>{
  if(e.key==='Escape')closeSession();
  if((e.ctrlKey||e.metaKey)&&e.key>='1'&&e.key<='6'){
    e.preventDefault();document.querySelectorAll('nav a')[+e.key-1].click();}
  if(e.key==='/'&&document.activeElement.tagName!=='INPUT'){
    e.preventDefault();
    document.querySelector('nav a[data-v="requests"]').click();
    document.getElementById('f-session').focus();}
});
