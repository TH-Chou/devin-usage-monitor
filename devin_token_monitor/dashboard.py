"""Shared dashboard page — Apple HIG "System Settings" design.

One HTML page serves both frontends:

- web.py serves it over HTTP; the page detects ``http:`` and polls
  ``/api/usage`` itself (export/refresh/settings via HTTP endpoints).
- gui.py loads it into a WKWebView; there is no server, so the native
  side pushes snapshots via ``window.update(data)`` and receives actions
  through ``window.webkit.messageHandlers.dtm``.

Design language: opaque white, hairline separators, gray sidebar, system
blue accent, near-zero shadows — follows macOS System Settings HIG.
"""

PAGE = """<!DOCTYPE html>
<html lang="zh">
<head>
<meta charset="utf-8">
<title>Devin Token Monitor</title>
<meta name="viewport" content="width=device-width, initial-scale=1">
<style>
:root {
  /* Apple HIG: label / secondaryLabel / tertiaryLabel, hairlines, system blue */
  color-scheme:light dark;
  --fg:#202124; --dim:#6e7076; --faint:#8c8e94;
  --hair:rgba(30,35,45,.07);
  --card:#ffffff; --canvas:#f7f8fa; --sidebar:rgba(244,246,250,.7);
  --brd:rgba(30,35,45,.055);
  --shadow:0 2px 10px rgba(25,35,55,.025);
  --shadow-lg:0 18px 60px rgba(20,30,50,.12),0 2px 8px rgba(20,30,50,.04);
  --accent:#007aff; --acc-dark:#0066d6;
  --blue:#007aff; --green:#34c759; --tan:#ff9500; --slate:#3a3a3c;
  --red:#ff3b30; --purple:#af52de; --teal:#5ac8fa;
  --spring:cubic-bezier(.34,1.4,.4,1);
  --ease:cubic-bezier(.22,.68,.26,1);
  --easeout:cubic-bezier(.16,1,.3,1);
}
@media (prefers-color-scheme:dark) {
  :root:not([data-theme]) {
    --fg:#f2f2f7; --dim:#a4a6ad; --faint:#8c8e96;
    --hair:rgba(255,255,255,.07);
    --card:#242629; --canvas:#1b1d20; --sidebar:rgba(36,38,43,.7);
    --brd:rgba(255,255,255,.055);
    --shadow:0 1px 2px rgba(0,0,0,.4);
    --shadow-lg:0 4px 16px rgba(0,0,0,.5),0 1px 3px rgba(0,0,0,.4);
    --accent:#0a84ff; --acc-dark:#0077ed;
    --blue:#0a84ff; --green:#30d158; --tan:#ff9f0a; --slate:#e5e5ea;
    --red:#ff453a; --purple:#bf5af2; --teal:#64d2ff;
  }
}
html[data-theme="midnight"] {
  color-scheme:dark; --fg:#e7ecfb; --dim:#a2aecb; --faint:#7d8aaa;
  --hair:rgba(179,197,255,.10); --card:#151d32; --canvas:#0b1020;
  --sidebar:rgba(20,29,51,.82); --brd:rgba(179,197,255,.11);
  --shadow:0 3px 18px rgba(0,0,0,.20); --shadow-lg:0 18px 55px rgba(0,0,0,.42);
  --accent:#8ca8ff; --acc-dark:#6c8df2; --blue:#8ca8ff; --green:#54d6ad;
  --tan:#f2bd6d; --slate:#d3d9e9; --red:#ff7185; --purple:#c4a2ff; --teal:#5bd4e8;
}
html[data-theme="graphite"] {
  color-scheme:dark; --fg:#edf0f2; --dim:#a8afb5; --faint:#818b93;
  --hair:rgba(230,237,241,.09); --card:#22272b; --canvas:#171b1e;
  --sidebar:rgba(34,39,43,.84); --brd:rgba(230,237,241,.09);
  --shadow:0 2px 12px rgba(0,0,0,.25); --shadow-lg:0 16px 48px rgba(0,0,0,.42);
  --accent:#b7c3cc; --acc-dark:#93a2ad; --blue:#80b4cf; --green:#8cc7a5;
  --tan:#d8b87a; --slate:#dce2e5; --red:#e88d8d; --purple:#b4a0cf; --teal:#76c9c5;
}
html[data-theme="paper"] {
  color-scheme:light; --fg:#342f28; --dim:#766e62; --faint:#92897c;
  --hair:rgba(85,66,42,.12); --card:#fffdf8; --canvas:#f4efe5;
  --sidebar:rgba(238,229,212,.84); --brd:rgba(85,66,42,.10);
  --shadow:0 2px 12px rgba(74,57,34,.05); --shadow-lg:0 18px 48px rgba(74,57,34,.18);
  --accent:#96613f; --acc-dark:#77492f; --blue:#4f7eaa; --green:#5c8a69;
  --tan:#c28540; --slate:#5e5b55; --red:#bc5d4e; --purple:#8965a0; --teal:#438f91;
}
html[data-theme="ocean"] {
  color-scheme:dark; --fg:#e2f2fb; --dim:#9bb9ca; --faint:#7899ac;
  --hair:rgba(126,198,228,.11); --card:#102b40; --canvas:#071b2b;
  --sidebar:rgba(12,38,57,.88); --brd:rgba(126,198,228,.12);
  --shadow:0 3px 16px rgba(0,0,0,.22); --shadow-lg:0 18px 52px rgba(0,0,0,.42);
  --accent:#59bce9; --acc-dark:#3597c6; --blue:#59bce9; --green:#69d4ba;
  --tan:#f2b86b; --slate:#c6dbe6; --red:#f17f81; --purple:#bb9ce9; --teal:#53d8d0;
}
html[data-theme="forest"] {
  color-scheme:dark; --fg:#e5f0e7; --dim:#a7b9aa; --faint:#809783;
  --hair:rgba(157,205,165,.10); --card:#1b3024; --canvas:#101e16;
  --sidebar:rgba(25,47,34,.86); --brd:rgba(157,205,165,.11);
  --shadow:0 3px 16px rgba(0,0,0,.24); --shadow-lg:0 18px 52px rgba(0,0,0,.40);
  --accent:#88cb96; --acc-dark:#64aa74; --blue:#84b9df; --green:#88cb96;
  --tan:#e1bd78; --slate:#d1dfd2; --red:#ef8580; --purple:#c2a0d7; --teal:#70c9b0;
}
* { box-sizing:border-box; }
html { -webkit-font-smoothing:antialiased; }
body { margin:0; color:var(--fg); background:var(--canvas);
       font:13px/1.5 -apple-system,"SF Pro Text","PingFang SC",sans-serif;
       overflow:hidden; }
body.glass-app aside { padding-top:54px; }
/* window drag regions (WKWebView honours -webkit-app-region) */
body.glass-app { -webkit-app-region: drag; }
body.glass-app a, body.glass-app button, body.glass-app input,
body.glass-app select, body.glass-app label, body.glass-app svg,
body.glass-app th, body.glass-app td, body.glass-app .seg,
body.glass-app .chip, body.glass-app .filters, body.glass-app .legend,
body.glass-app .donut-legend, body.glass-app .overlay,
body.glass-app .drawer, body.glass-app .switch {
  -webkit-app-region: no-drag; }
::-webkit-scrollbar { width:8px; height:8px; }
::-webkit-scrollbar-thumb { background:rgba(0,0,0,.18);
       border-radius:99px; border:2px solid transparent;
       background-clip:padding-box; }
::-webkit-scrollbar-thumb:hover { background:rgba(0,0,0,.32);
       background-clip:padding-box; }
:focus-visible { outline:2px solid rgba(0,122,255,.5); outline-offset:1px; }

/* ---------- shell ---------- */
.shell { display:flex; height:100vh; }
aside { width:210px; flex:none; padding:24px 12px; display:flex;
        flex-direction:column; gap:8px; margin:10px; border-radius:22px;
        background:var(--sidebar); border:1px solid var(--brd);
        -webkit-backdrop-filter:blur(28px) saturate(1.3);
        backdrop-filter:blur(28px) saturate(1.3); }
.logo { display:flex; align-items:center; padding:14px 10px 28px; }
.logo b { font-size:19px; font-weight:600; letter-spacing:-.035em; }
.logo span { display:block; font-size:11px; color:var(--dim); margin-top:4px;
             letter-spacing:.015em; }
nav { display:flex; flex-direction:column; gap:2px; }
nav a { display:flex; align-items:center; gap:10px; padding:8px 12px;
        border-radius:8px; color:var(--fg); font-size:14px; cursor:pointer;
        text-decoration:none; transition:background .15s,
        transform .15s var(--spring); position:relative; }
nav a:hover { background:rgba(0,0,0,.04); }
nav a:active { transform:scale(.98); }
nav a.on { background:rgba(0,0,0,.07); font-weight:560; }
@media (prefers-color-scheme:dark){
  nav a:hover { background:rgba(255,255,255,.06); }
  nav a.on { background:rgba(255,255,255,.10); } }
nav a .ic { width:20px; height:20px; flex:none; opacity:.75;
            display:inline-flex; align-items:center; justify-content:center; }
nav a .ic svg { width:20px; height:20px; display:block; }
.side-foot { margin-top:auto; padding:14px 12px 8px; border-top:1px solid var(--hair); }
.side-foot .t { font-size:11.5px; color:var(--faint); margin-bottom:3px; }
.side-foot .v { font-size:18px; font-weight:600; font-variant-numeric:tabular-nums; }
.side-foot .e { font-size:11.5px; color:var(--dim); }

main { flex:1; min-width:0; overflow-y:auto; padding:0 30px 48px; background:var(--canvas); }
header { display:flex; align-items:center; gap:10px; height:88px; margin-bottom:10px;
         position:sticky; top:0; z-index:6; background:var(--canvas); }
header h1 { font-size:22px; font-weight:650; margin:0; letter-spacing:-.035em; }
.live { display:inline-flex; align-items:center; gap:5px; font-size:11px;
        color:var(--green); }
.live i { width:6px;height:6px;border-radius:50%;background:var(--green);
          box-shadow:0 0 0 3px rgba(52,199,89,.08); }
@keyframes pulse { 50%{opacity:.35;transform:scale(.8);} }
.spacer { flex:1; }
.upd { color:var(--faint); font-size:11.5px; font-variant-numeric:tabular-nums; }

/* Apple push button: white, hairline border, 7px radius, ~24px height */
.btn { border:1px solid var(--brd); background:var(--card); color:var(--fg);
       font-size:12px; padding:7px 15px; border-radius:18px; cursor:pointer;
       font-family:inherit; box-shadow:0 .5px 1px rgba(0,0,0,.04);
       transition:background .12s,transform .12s var(--spring); }
.btn:hover { background:#fafafa; }
@media (prefers-color-scheme:dark){ .btn:hover{background:#3a3a3c;} }
.btn:active { background:#ececec; transform:none; }
@media (prefers-color-scheme:dark){ .btn:active{background:#48484a;} }
.btn.primary { background:var(--accent); border-color:var(--acc-dark);
               color:#fff; }
.btn.primary:hover { background:#1a85ff; }
.btn.primary:active { background:var(--acc-dark); }

/* ---------- views ---------- */
.view { display:none; }
.view.on { display:block; animation:viewIn .2s var(--easeout) both; }
@keyframes viewIn { from{opacity:0;transform:translateY(10px);}
                    to{opacity:1;transform:none;} }

/* ---------- grouped panels ---------- */
.card, .panel { background:var(--card); border:1px solid var(--brd);
    border-radius:18px; box-shadow:var(--shadow); }

.cards { display:grid; grid-template-columns:repeat(4,minmax(0,1fr));
         gap:0; background:var(--card); border:1px solid var(--brd);
         border-radius:20px; overflow:hidden; }
.card { padding:20px; position:relative; overflow:hidden; }
.cards .card { border:0; border-radius:0; box-shadow:none; background:none; }
.cards .card:nth-child(-n+2) { grid-column:span 2; padding:24px 24px 22px;
                            border-bottom:1px solid var(--hair); }
.cards .card:nth-child(-n+2) .value { font-size:38px; font-weight:600; letter-spacing:-.045em; }
.cards .card:nth-child(2) .value { color:var(--dim); }
.card .label { color:var(--dim); font-size:11.5px; font-weight:400; }
.card .value { font-size:20px; font-weight:600; margin-top:8px;
               letter-spacing:-.025em; font-variant-numeric:tabular-nums;
               overflow:hidden; text-overflow:ellipsis; white-space:nowrap; }
.card .extra { color:var(--dim); font-size:10.5px; margin-top:6px;
               font-variant-numeric:tabular-nums; }
.card .ic { position:absolute; top:13px; right:13px; width:20px; height:20px;
            border-radius:6px; display:grid; place-items:center;
            font-size:10.5px; color:var(--dim);
            background:rgba(0,0,0,.05); }
.slate{color:var(--fg)} .green{color:var(--green)} .warn{color:var(--red)}

.sec { margin-top:28px; }
.sec-head { display:flex; align-items:center; margin-bottom:12px; gap:12px; padding:0 4px; }
h2 { font-size:14px; font-weight:600; margin:0; color:var(--fg); }

/* segmented control: gray track + white thumb */
.seg { display:inline-flex; background:rgba(120,125,135,.08); border-radius:16px;
       padding:3px; margin-left:auto; position:relative; }
.seg button { border:0; background:transparent; color:var(--dim);
              font-size:11px; padding:4px 12px; border-radius:14px;
              cursor:pointer; font-family:inherit; position:relative; z-index:1;
              transition:color .2s; }
.seg button.on { color:var(--fg); font-weight:560; }
.seg .thumb { position:absolute; top:3px; bottom:3px; border-radius:14px;
    background:var(--card); box-shadow:0 1px 2px rgba(0,0,0,.14);
    transition:left .3s var(--spring),width .3s var(--spring); }
@media (prefers-color-scheme:dark){ .seg{background:rgba(255,255,255,.08);} }

.panel { padding:20px 20px 14px; position:relative; }
.panel.pad0 { padding:0; overflow:auto; }
#v-models table { min-width:780px; }
#feed { min-width:720px; }
#t-sessions td:first-child { white-space:nowrap; }
#t-sessions td:nth-child(2) { min-width:170px; }
.legend { display:flex; gap:16px; padding:2px 4px 8px; flex-wrap:wrap; }
.legend span { display:inline-flex; align-items:center; gap:6px;
               font-size:12px; color:var(--dim); cursor:pointer;
               user-select:none; transition:opacity .2s; }
.legend span:hover { opacity:.7; }
.legend i { width:9px;height:9px;border-radius:3px; }
.legend span.off { opacity:.32; text-decoration:line-through; }
svg { display:block; width:100%; height:auto; }
.tip { position:absolute; pointer-events:none; z-index:5;
       background:var(--card); border:1px solid var(--brd);
       border-radius:8px; box-shadow:var(--shadow-lg); padding:8px 11px;
       font-size:12px; line-height:1.7; display:none;
       font-variant-numeric:tabular-nums; white-space:nowrap; }
.tip b { display:block; color:var(--dim); font-weight:500; margin-bottom:2px; }
.tip .r { display:flex; gap:10px; }
.tip .r i { width:7px;height:7px;border-radius:50%;align-self:center; }

.duo { display:grid; grid-template-columns:280px 1fr; gap:16px;
       align-items:center; }
.donut-wrap { position:relative; display:flex; justify-content:center; }
.donut-center { position:absolute; inset:0; display:flex; flex-direction:column;
                align-items:center; justify-content:center; pointer-events:none; }
.donut-center b { font-size:21px; font-weight:600; }
.donut-center span { font-size:11px; color:var(--dim); }
.donut-legend { font-size:12.5px; max-height:230px; overflow:auto; }
.donut-legend .row { display:flex; align-items:center; gap:8px; padding:6px 9px;
        border-radius:7px; cursor:pointer; transition:background .15s; }
.donut-legend .row:hover,.donut-legend .row.hl { background:rgba(0,0,0,.04); }
@media (prefers-color-scheme:dark){
  .donut-legend .row:hover,.donut-legend .row.hl { background:rgba(255,255,255,.06); } }
.donut-legend .row i { width:9px;height:9px;border-radius:3px;flex:none; }
.donut-legend .m { font-family:ui-monospace,Menlo,monospace; font-size:12px; }
.donut-legend .v { margin-left:auto; color:var(--dim);
                   font-variant-numeric:tabular-nums; }
.donut-legend .p { width:44px; text-align:right; color:var(--faint);
                   font-variant-numeric:tabular-nums; }

/* ---------- tables ---------- */
table { width:100%; border-collapse:collapse; }
th,td { padding:14px 16px; text-align:right; font-variant-numeric:tabular-nums; }
th { color:var(--dim); font-weight:500; font-size:12px; white-space:nowrap;
     border-bottom:1px solid var(--hair);
     cursor:pointer; user-select:none; }
th.nosort{cursor:default}
th .arrow{font-size:9px}
td { border-bottom:1px solid var(--hair); }
tbody tr:last-child td{border-bottom:none}
tbody tr{transition:background .12s}
tbody tr:hover{background:rgba(0,0,0,.025)}
@media (prefers-color-scheme:dark){tbody tr:hover{background:rgba(255,255,255,.05)}}
tbody tr.clickable{cursor:pointer}
th.l,td.l{text-align:left}
.model{font-family:ui-monospace,SFMono-Regular,Menlo,monospace;font-size:12.5px}
.price{color:var(--dim);font-size:12.5px}
.costbar{height:4px;border-radius:2px;background:var(--accent);opacity:.5}
.dot{display:inline-block;width:7px;height:7px;border-radius:50%;margin-right:6px}
.fade{color:var(--dim)}
.reqbody td{padding:0!important;border-bottom:1px solid var(--hair)}
.reqbody pre{margin:0;padding:12px 16px;max-height:240px;overflow:auto;
      font:11.5px/1.6 ui-monospace,SFMono-Regular,Menlo,monospace;
      color:var(--fg);background:rgba(0,0,0,.025);white-space:pre-wrap;
      word-break:break-word;animation:reqbodyIn .3s var(--easeout) both}
@media (prefers-color-scheme:dark){.reqbody pre{background:rgba(255,255,255,.05)}}
@keyframes reqbodyIn{from{opacity:0}to{opacity:1}}
tbody tr.exp td{border-bottom:none}
tbody tr.exp{background:rgba(0,122,255,.05)}
#feed td{font-size:12.5px}
.reqcost{font-weight:600}
.empty{padding:24px;text-align:center;color:var(--dim)}

/* ---------- filters ---------- */
.filters{display:flex;gap:8px;align-items:center;flex-wrap:wrap;
         padding:10px 14px;border-bottom:1px solid var(--hair)}
.filters select,.filters input{border:1px solid var(--brd);background:var(--card);
    color:var(--fg);font-size:12px;padding:4px 9px;border-radius:7px;
    font-family:inherit;transition:border-color .15s,box-shadow .15s}
.filters input:focus,.filters select:focus{outline:none;
    border-color:var(--accent);box-shadow:0 0 0 3px rgba(0,122,255,.22)}
.filters input[type=search]{width:190px}
.filters input[type=date]{width:135px}
.chip{border:1px solid var(--brd);background:var(--card);color:var(--dim);
      font-size:11.5px;padding:2px 12px;border-radius:99px;cursor:pointer;
      transition:background .15s,color .15s,border-color .15s}
.chip:hover{border-color:rgba(0,0,0,.2)}
.chip.on{background:var(--accent);border-color:var(--accent);color:#fff}
.count{margin-left:auto;font-size:11.5px;color:var(--faint)}

/* ---------- drawer ---------- */
.overlay{position:fixed;inset:0;background:rgba(0,0,0,.22);z-index:10;
         visibility:hidden;opacity:0;
         transition:opacity .3s,visibility 0s .3s}
.overlay.open{visibility:visible;opacity:1;transition:opacity .3s}
.drawer{position:absolute;top:12px;right:12px;bottom:12px;width:min(640px,94vw);
        background:var(--canvas);border:1px solid var(--brd);border-radius:24px;
        box-shadow:var(--shadow-lg);padding:24px;overflow:auto;
        transform:translateX(40px);opacity:0;
        transition:transform .45s var(--spring),opacity .3s}
.overlay.open .drawer{transform:none;opacity:1}
.drawer h3{margin:0 0 2px;font-size:16px;font-weight:600;letter-spacing:-.01em}
.drawer .meta{color:var(--dim);font-size:12px;margin-bottom:14px;word-break:break-all}
.drawer .x{position:absolute;top:16px;right:18px;border:0;background:none;
           font-size:16px;color:var(--dim);cursor:pointer;
           transition:transform .2s var(--spring)}
.drawer .x:hover{transform:scale(1.15)}
.drawer .kpis{display:grid;grid-template-columns:repeat(3,1fr);gap:10px;margin-bottom:18px}
.drawer .kpis .card{padding:10px 13px}
.drawer .kpis .value{font-size:17px;font-weight:600}
.drawer table{background:var(--card);border:1px solid var(--brd);border-radius:12px;overflow:hidden}
.drawer td,.drawer th{padding:7px 11px;font-size:12px}

/* ---------- settings ---------- */
.set-grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(300px,1fr));gap:14px}
.set-card{padding:16px 18px}
.set-card h3{margin:0 0 4px;font-size:13.5px;font-weight:600}
.set-card .desc{color:var(--dim);font-size:12px;margin-bottom:12px;line-height:1.5}
.set-row{display:flex;align-items:center;gap:10px}
.set-row input[type=number]{width:110px;border:1px solid var(--brd);
    background:var(--card);color:var(--fg);border-radius:7px;
    padding:5px 9px;font-size:13px;font-family:inherit}
.switch{position:relative;width:38px;height:22px;flex:none;cursor:pointer}
.switch input{opacity:0;width:0;height:0}
.switch i{position:absolute;inset:0;border-radius:99px;
    background:rgba(120,120,128,.32);transition:background .25s var(--ease)}
.switch i::after{content:"";position:absolute;top:2px;left:2px;width:18px;height:18px;
    border-radius:50%;background:#fff;box-shadow:0 1px 3px rgba(0,0,0,.25);
    transition:transform .3s var(--spring)}
.switch input:checked+i{background:var(--green)}
.switch input:checked+i::after{transform:translateX(16px)}
.switch input:disabled+i{opacity:.4}
.mono{font-family:ui-monospace,Menlo,monospace;font-size:11.5px;
      background:rgba(0,0,0,.05);padding:2px 7px;border-radius:6px;
      word-break:break-all}
@media (prefers-color-scheme:dark){.mono{background:rgba(255,255,255,.08)}}
.kv{font-size:12px;color:var(--dim);margin-bottom:6px;display:flex;gap:8px}
.kv b{color:var(--fg);font-weight:500}

/* ---------- extended visualizations ---------- */
h2 .sub{font-size:11px;font-weight:400;color:var(--faint);margin-left:8px}

/* week x hour heatmap */
.heat{display:grid;grid-template-columns:28px 1fr;gap:4px 8px;align-items:center}
.heat .dl{font-size:10.5px;color:var(--faint);text-align:right}
.heat .cells{display:grid;grid-template-columns:repeat(24,1fr);gap:3px}
.heat .cells i{display:block;aspect-ratio:1.15;border-radius:3px;
   background:rgba(120,125,135,.10);cursor:pointer;
   transition:transform .12s var(--spring)}
.heat .cells i:hover{transform:scale(1.3)}
.heat .hrs{display:grid;grid-template-columns:repeat(24,1fr);gap:3px}
.heat .hrs span{font-size:9.5px;color:var(--faint);text-align:center}

/* horizontal bars (top sessions) */
.hbars{display:flex;flex-direction:column;padding:6px}
.hbars .hr{display:grid;grid-template-columns:190px 1fr 84px;gap:12px;
   align-items:center;padding:8px 10px;border-radius:9px;cursor:pointer;
   transition:background .15s}
.hbars .hr:hover{background:rgba(0,0,0,.04)}
@media (prefers-color-scheme:dark){.hbars .hr:hover{background:rgba(255,255,255,.06)}}
.hbars .nm{font-size:12.5px;white-space:nowrap;overflow:hidden;
   text-overflow:ellipsis}
.hbars .tr{height:13px;border-radius:4px;background:rgba(120,125,135,.10);
   overflow:hidden}
.hbars .tr i{display:block;height:100%;border-radius:4px;
   background:linear-gradient(90deg,var(--accent),#4ea2ff);
   transition:width .7s var(--easeout)}
.hbars .vl{text-align:right;font-size:12.5px;font-weight:560;
   font-variant-numeric:tabular-nums}

/* ---------- toast / skeleton ---------- */
#toast{position:fixed;left:50%;bottom:26px;transform:translate(-50%,60px);
       background:var(--card);border:1px solid var(--brd);color:var(--fg);
       padding:8px 18px;border-radius:10px;font-size:12.5px;
       box-shadow:var(--shadow-lg);opacity:0;z-index:30;
       transition:transform .4s var(--spring),opacity .25s}
#toast.show{transform:translate(-50%,0);opacity:1}
.skel{display:inline-block;width:70%;height:1.1em;border-radius:6px;
      background:linear-gradient(90deg,rgba(0,0,0,.06) 25%,
      rgba(0,0,0,.12) 50%,rgba(0,0,0,.06) 75%);
      background-size:200% 100%;animation:shimmer 1.4s infinite}
@keyframes shimmer{to{background-position:-200% 0}}

.rise{animation:rise .55s var(--easeout) backwards}
@keyframes rise{from{opacity:0;transform:translateY(14px)}to{opacity:1;transform:none}}

.native-shell aside { display:none; }
.native-shell .shell { padding-left:220px; }
.native-shell header { padding-right:108px; }
.native-shell #btn-refresh,.native-shell #btn-export { display:none; }
.native-shell .drawer { top:88px; }
.native-shell .overlay { background:rgba(20,24,32,.14); }
.cards .card .ic { display:none; }
#kv-top { font-size:16px; padding-top:4px; }
.drawer h3 { padding-right:32px; }
nav a { border-radius:12px; padding:10px 12px; }
nav a.on { color:var(--accent); background:rgba(0,122,255,.1); }
.live { color:var(--dim); font-size:10px; }
@media (max-width:650px){
  main { padding-right:20px; padding-left:20px; }
  .cards .card { padding:16px 12px; }
  .cards .card:nth-child(-n+2) { padding:22px 18px; }
  .card .extra { font-size:10px; }
  .duo { grid-template-columns:1fr; }
}
@media (prefers-reduced-transparency:reduce){
  aside { background:var(--canvas); -webkit-backdrop-filter:none; backdrop-filter:none; }
}
@media (prefers-contrast:more){
  :root { --dim:var(--fg); --faint:var(--fg); --brd:currentColor; }
}
@media (prefers-reduced-motion:reduce){
  *{animation:none!important;transition:none!important}
}
.view#v-insights #analysis-kpis{margin-bottom:20px}
.insight-grid{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:14px}
.insight-panel{padding:18px;min-width:0}
.insight-panel h3{margin:0 0 4px;font-size:14px;font-weight:600}
.insight-panel .desc{color:var(--dim);font-size:11.5px;margin-bottom:12px}
.insight-values{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:9px}
.insight-value{padding:10px 12px;border:1px solid var(--brd);border-radius:11px;background:var(--canvas)}
.insight-value span{display:block;color:var(--dim);font-size:11px}
.insight-value b{display:block;margin-top:3px;font-size:16px;font-variant-numeric:tabular-nums}
.insight-table{width:100%;border-collapse:collapse}
.insight-table th,.insight-table td{padding:8px 9px;font-size:11.5px;white-space:nowrap}
.insight-table th{color:var(--dim);font-weight:500;text-align:right}
.insight-table th:first-child,.insight-table td:first-child{text-align:left}
.insight-table td{text-align:right;border-top:1px solid var(--hair);font-variant-numeric:tabular-nums}
#set-theme{min-width:190px;border:1px solid var(--brd);background:var(--card);color:var(--fg);border-radius:8px;padding:7px 10px;font:inherit}
@media(max-width:900px){.insight-grid{grid-template-columns:1fr}.insight-table{display:block;overflow-x:auto}}
html[data-theme="paper"] nav a:hover,html[data-theme="paper"] .btn:hover,
html[data-theme="paper"] .donut-legend .row:hover,html[data-theme="paper"] .donut-legend .row.hl,
html[data-theme="paper"] tbody tr:hover,html[data-theme="paper"] .hbars .hr:hover{background:rgba(73,54,31,.07)}
html[data-theme="paper"] .seg{background:rgba(73,54,31,.10)}
html[data-theme="paper"] .btn:active{background:#e7dece}
html:is([data-theme="midnight"],[data-theme="graphite"],[data-theme="ocean"],[data-theme="forest"]) nav a:hover,
html:is([data-theme="midnight"],[data-theme="graphite"],[data-theme="ocean"],[data-theme="forest"]) .btn:hover,
html:is([data-theme="midnight"],[data-theme="graphite"],[data-theme="ocean"],[data-theme="forest"]) .donut-legend .row:hover,
html:is([data-theme="midnight"],[data-theme="graphite"],[data-theme="ocean"],[data-theme="forest"]) .donut-legend .row.hl,
html:is([data-theme="midnight"],[data-theme="graphite"],[data-theme="ocean"],[data-theme="forest"]) tbody tr:hover,
html:is([data-theme="midnight"],[data-theme="graphite"],[data-theme="ocean"],[data-theme="forest"]) .hbars .hr:hover{background:rgba(255,255,255,.07)}
html:is([data-theme="midnight"],[data-theme="graphite"],[data-theme="ocean"],[data-theme="forest"]) .seg{background:rgba(255,255,255,.09)}
html:is([data-theme="midnight"],[data-theme="graphite"],[data-theme="ocean"],[data-theme="forest"]) .btn:active{background:rgba(255,255,255,.13)}
html:is([data-theme="midnight"],[data-theme="graphite"],[data-theme="ocean"],[data-theme="forest"]) .reqbody pre,
html:is([data-theme="midnight"],[data-theme="graphite"],[data-theme="ocean"],[data-theme="forest"]) .mono{background:rgba(255,255,255,.07)}
</style>
</head>
<body>
<div class="shell">
  <aside>
    <div class="logo"><div><b>Devin Token</b><span data-i18n="logo_sub">用量与费用</span></div></div>
    <nav id="nav">
      <a data-v="overview" class="on"><span class="ic"><svg viewBox="0 0 20 20" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round"><rect x="2.5" y="2.5" width="6.5" height="6.5" rx="1.5"/><rect x="11" y="2.5" width="6.5" height="6.5" rx="1.5"/><rect x="2.5" y="11" width="6.5" height="6.5" rx="1.5"/><rect x="11" y="11" width="6.5" height="6.5" rx="1.5"/></svg></span><span data-i18n="nav_overview">概览</span></a>
      <a data-v="insights"><span class="ic"><svg viewBox="0 0 20 20" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round"><path d="M3 16.5V10M8 16.5V4M13 16.5V7M18 16.5V2"/><path d="M2 17.5h17"/></svg></span><span data-i18n="nav_insights">分析</span></a>
      <a data-v="models"><span class="ic"><svg viewBox="0 0 20 20" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round"><rect x="4.5" y="4.5" width="11" height="11" rx="2"/><rect x="8" y="8" width="4" height="4" rx="1"/><path d="M7 2v2.5M10 2v2.5M13 2v2.5M7 15.5V18M10 15.5V18M13 15.5V18M2 7h2.5M2 10h2.5M2 13h2.5M15.5 7H18M15.5 10H18M15.5 13H18"/></svg></span><span data-i18n="nav_models">模型</span></a>
      <a data-v="sessions"><span class="ic"><svg viewBox="0 0 20 20" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round"><path d="M3.5 3.5h10a2 2 0 012 2v4.5a2 2 0 01-2 2h-4.3l-3.4 2.6v-2.4H4a2 2 0 01-2-2V5.5a2 2 0 011.5-2z"/><circle cx="6.6" cy="8" r="0.9" fill="currentColor" stroke="none"/><circle cx="9.8" cy="8" r="0.9" fill="currentColor" stroke="none"/><circle cx="13" cy="8" r="0.9" fill="currentColor" stroke="none"/></svg></span><span data-i18n="nav_sessions">会话</span></a>
      <a data-v="requests"><span class="ic"><svg viewBox="0 0 20 20" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round"><line x1="6.5" y1="5" x2="17.5" y2="5"/><line x1="6.5" y1="10" x2="17.5" y2="10"/><line x1="6.5" y1="15" x2="17.5" y2="15"/><circle cx="3.5" cy="5" r="1"/><circle cx="3.5" cy="10" r="1"/><circle cx="3.5" cy="15" r="1"/></svg></span><span data-i18n="nav_requests">请求</span></a>
      <a data-v="settings"><span class="ic"><svg viewBox="0 0 20 20" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round"><line x1="2" y1="5.5" x2="18" y2="5.5"/><circle cx="7.5" cy="5.5" r="2" fill="var(--card)"/><line x1="2" y1="10" x2="18" y2="10"/><circle cx="13" cy="10" r="2" fill="var(--card)"/><line x1="2" y1="14.5" x2="18" y2="14.5"/><circle cx="9" cy="14.5" r="2" fill="var(--card)"/></svg></span><span data-i18n="nav_settings">设置</span></a>
    </nav>
    <div class="side-foot">
      <div class="t" data-i18n="sf_today">今日费用</div>
      <div class="v" id="sf-cost">—</div>
      <div class="e" id="sf-req">—</div>
    </div>
  </aside>
  <main>
    <header>
      <h1 id="view-title">概览</h1>
      <span class="live"><i></i><span data-i18n="live">实时</span></span>
      <span class="spacer"></span>
      <span class="upd"><span data-i18n="updated">更新于</span> <span id="updated">—</span></span>
      <button class="btn" id="btn-refresh">↻ <span data-i18n="refresh">刷新</span></button>
      <button class="btn" id="btn-export">⤓ <span data-i18n="export">导出</span></button>
    </header>

    <section class="view on" id="v-overview">
      <div class="cards" id="kpis"></div>
      <div class="sec"><div class="sec-head"><h2 data-i18n="s_trend">用量趋势</h2>
        <div class="seg" id="seg-tok"><i class="thumb"></i>
          <button data-v="hour" class="on" data-i18n="seg_hour">近 24 小时</button>
          <button data-v="day" data-i18n="seg_day">近 14 天</button></div></div>
        <div class="panel"><div class="legend" id="leg-tok"></div>
          <div id="ch-tok"></div><div class="tip" id="tip-tok"></div></div></div>
      <div class="sec"><div class="sec-head"><h2><span data-i18n="s_mix">Token 构成</span><span class="sub" data-i18n="s_mix_sub">输入 / 输出 / 缓存</span></h2>
        <div class="seg" id="seg-mix"><i class="thumb"></i>
          <button data-v="hour" class="on" data-i18n="seg_hour">近 24 小时</button>
          <button data-v="day" data-i18n="seg_day">近 14 天</button></div></div>
        <div class="panel"><div class="legend" id="leg-mix"></div>
          <div id="ch-mix"></div><div class="tip" id="tip-mix"></div></div></div>
      <div class="sec"><div class="sec-head"><h2 data-i18n="s_cost">费用趋势</h2>
        <div class="seg" id="seg-cost"><i class="thumb"></i>
          <button data-v="hour" class="on" data-i18n="seg_hour">近 24 小时</button>
          <button data-v="day" data-i18n="seg_day">近 14 天</button></div></div>
        <div class="panel"><div class="legend" id="leg-cost"></div>
          <div id="ch-cost"></div><div class="tip" id="tip-cost"></div></div></div>
      <div class="sec"><div class="sec-head"><h2><span data-i18n="s_hit">缓存命中率趋势</span><span class="sub" data-i18n="s_hit_sub">缓存读取 ÷ (输入 + 缓存读取)</span></h2>
        <div class="seg" id="seg-hit"><i class="thumb"></i>
          <button data-v="hour" class="on" data-i18n="seg_hour">近 24 小时</button>
          <button data-v="day" data-i18n="seg_day">近 14 天</button></div></div>
        <div class="panel"><div id="ch-hit"></div><div class="tip" id="tip-hit"></div></div></div>
      <div class="sec"><div class="sec-head"><h2 data-i18n="s_donut">模型费用占比</h2></div>
        <div class="panel duo">
          <div class="donut-wrap"><div id="donut"></div>
            <div class="donut-center"><b id="donut-total">—</b><span data-i18n="donut_total">累计费用</span></div></div>
          <div class="donut-legend" id="donut-legend"></div>
          <div class="tip" id="tip-donut"></div></div></div>
      <div class="sec"><div class="sec-head"><h2><span data-i18n="s_heat">活跃热力图</span><span class="sub" data-i18n="s_heat_sub">星期 × 小时 · 全部历史</span></h2></div>
        <div class="panel"><div id="ch-heat"></div><div class="tip" id="tip-heat"></div></div></div>
      <div class="sec"><div class="sec-head"><h2><span data-i18n="s_top">会话费用榜</span><span class="sub" data-i18n="s_top_sub">累计 TOP 8 · 点击看明细</span></h2></div>
        <div class="panel pad0"><div class="hbars" id="ch-top"></div></div></div>
    </section>

    <section class="view" id="v-models">
      <div class="panel pad0"><table><thead><tr id="th-models"></tr></thead>
        <tbody id="t-models"></tbody></table></div>
      <div class="sec"><div class="sec-head"><h2><span data-i18n="s_scatter">单请求 成本 × 速度</span><span class="sub" data-i18n="s_scatter_sub">最近请求采样 · 点击定位会话</span></h2></div>
        <div class="panel"><div id="ch-scatter"></div><div class="tip" id="tip-scatter"></div></div></div>
    </section>

    <section class="view" id="v-insights">
      <div class="sec-head"><h2 data-i18n="an_title">深入分析</h2>
        <div class="seg" id="seg-analysis"><i class="thumb"></i>
          <button data-v="7d" class="on" data-i18n="an_last7">7 天</button>
          <button data-v="30d" data-i18n="an_last30">30 天</button>
          <button data-v="mtd" data-i18n="an_mtd">本月</button>
          <button data-v="all" data-i18n="an_all">累计</button></div></div>
      <div class="cards" id="analysis-kpis"></div>
      <div class="insight-grid">
        <div class="panel insight-panel"><h3 data-i18n="an_economics">Token 效率</h3>
          <div class="desc" data-i18n="an_economics_desc">结合模型单价衡量缓存价值与生成效率。</div>
          <div class="insight-values" id="analysis-economics"></div></div>
        <div class="panel insight-panel"><h3 data-i18n="an_distribution">请求规模与性能分位</h3>
          <div class="desc" id="analysis-sample"></div>
          <table class="insight-table"><thead><tr><th data-i18n="an_metric">指标</th><th>P50</th><th>P90</th></tr></thead>
            <tbody id="analysis-percentiles"></tbody></table></div>
        <div class="panel insight-panel" style="grid-column:1/-1"><h3 data-i18n="an_models">模型效率对比</h3>
          <div class="desc" data-i18n="an_models_desc">区分高产模型、缓存收益与单位输出成本。</div>
          <table class="insight-table"><thead><tr>
            <th data-i18n="col_model">模型</th><th data-i18n="col_req">请求</th>
            <th data-i18n="an_tokens_req">Token/请求</th><th data-i18n="an_out_in">输出/输入</th>
            <th data-i18n="an_cache_saved">估算缓存节省</th><th data-i18n="an_cost_1k">每千输出成本</th>
          </tr></thead><tbody id="analysis-models"></tbody></table></div>
      </div>
    </section>

    <section class="view" id="v-sessions">
      <div class="panel pad0"><table><thead><tr>
        <th class="l nosort" data-i18n="col_last">最后活动</th><th class="l nosort" data-i18n="col_title">标题</th>
        <th class="l nosort" data-i18n="col_model">模型</th><th class="nosort" data-i18n="col_total">总 tokens</th>
        <th class="nosort" data-i18n="col_cost">费用</th><th class="nosort" style="width:12%"></th>
      </tr></thead><tbody id="t-sessions"></tbody></table></div>
    </section>

    <section class="view" id="v-requests">
      <div class="panel pad0">
        <div class="filters">
          <select id="f-model"><option value="" data-i18n="f_all_models">全部模型</option></select>
          <input type="search" id="f-session" data-i18n-ph="f_search" placeholder="搜索会话标题…">
          <input type="date" id="f-date">
          <span class="chip on" data-day="" data-i18n="f_all">全部</span>
          <span class="chip" data-day="today" data-i18n="f_today">今天</span>
          <span class="chip" data-day="7" data-i18n="f_7d">近 7 天</span>
          <span class="count" id="f-count"></span>
        </div>
        <table id="feed"><thead><tr>
          <th class="l nosort" data-i18n="col_time">时间</th><th class="l nosort" data-i18n="col_model">模型</th>
          <th class="l nosort" data-i18n="col_sess">会话</th><th class="nosort" data-i18n="col_input">输入</th>
          <th class="nosort" data-i18n="col_output">输出</th><th class="nosort" data-i18n="col_cache">缓存</th>
          <th class="nosort" data-i18n="col_speed">速度</th><th class="nosort" data-i18n="col_thiscost">本次费用</th>
        </tr></thead><tbody id="t-recent"></tbody></table>
      </div>
    </section>

    <section class="view" id="v-settings">
      <div class="set-grid">
        <div class="panel set-card">
          <h3 data-i18n="st_lang">语言 / Language</h3>
          <div class="desc" data-i18n="st_lang_desc">选择界面语言，自动保存。</div>
          <div class="set-row" id="lang-row" style="flex-wrap:wrap;gap:6px">
            <span class="chip" data-lang="zh">中文</span>
            <span class="chip" data-lang="en">English</span>
            <span class="chip" data-lang="ja">日本語</span>
            <span class="chip" data-lang="ko">한국어</span>
            <span class="chip" data-lang="es">Español</span>
            <span class="chip" data-lang="vi">Tiếng Việt</span>
          </div>
        </div>
        <div class="panel set-card">
          <h3 data-i18n="st_theme">主题外观</h3>
          <div class="desc" data-i18n="st_theme_desc">切换配色预设；系统模式跟随操作系统外观。</div>
          <div class="set-row"><select id="set-theme">
            <option value="system" data-i18n="theme_system">跟随系统</option>
            <option value="midnight" data-i18n="theme_midnight">午夜蓝</option>
            <option value="graphite" data-i18n="theme_graphite">石墨</option>
            <option value="paper" data-i18n="theme_paper">暖纸</option>
            <option value="ocean" data-i18n="theme_ocean">深海</option>
            <option value="forest" data-i18n="theme_forest">森林</option>
          </select></div>
        </div>
        <div class="panel set-card">
          <h3 data-i18n="st_budget">每日预算告警</h3>
          <div class="desc" data-i18n="st_budget_desc">今日费用超过预算时发送 macOS 通知并在标题警示。0 为关闭。</div>
          <div class="set-row">
            <span class="fade" style="font-size:13px" data-i18n="st_budget_lbl">预算 $</span>
            <input type="number" id="set-budget" min="0" step="1" placeholder="0">
            <button class="btn primary" id="set-budget-save" data-i18n="st_save">保存</button>
          </div>
        </div>
        <div class="panel set-card">
          <h3 data-i18n="st_general">通用</h3>
          <div class="desc" data-i18n="st_general_desc">登录 macOS 时自动启动监控应用。</div>
          <div class="set-row">
            <label class="switch"><input type="checkbox" id="set-login"><i></i></label>
            <span id="set-login-label" data-i18n="st_login">登录时启动</span>
          </div>
        </div>
        <div class="panel set-card">
          <h3 data-i18n="st_data">数据</h3>
          <div class="kv"><b data-i18n="st_dbsrc">数据源</b><span class="mono" id="set-dbpath">—</span></div>
          <div class="kv"><b data-i18n="st_prices">价格表</b><span class="mono" id="set-pricespath">—</span></div>
          <div class="set-row" style="margin-top:10px">
            <button class="btn" id="set-open-prices" data-i18n="st_edit">编辑 prices.json</button>
            <button class="btn" id="set-export2" data-i18n="st_export">导出全部 CSV</button>
          </div>
        </div>
        <div class="panel set-card">
          <h3 data-i18n="st_about">关于</h3>
          <div class="kv"><b data-i18n="st_version">版本</b><span id="set-version">—</span></div>
          <div class="desc" data-i18n="st_about_desc">监控本地 Devin CLI 的 token 用量与估算费用。credits/ACU 为服务端数据，本地仅按 token × 单价估算。</div>
        </div>
      </div>
    </section>
  </main>
</div>

<div class="overlay" id="overlay"><div class="drawer">
  <button class="x" id="drawer-x">✕</button><div id="drawer-body"></div>
</div></div>
<div id="toast"></div>

<script>
'use strict';
let DATA=null, started=false;
let C={input:'#007aff',output:'#34c759',cache:'#ff9500',cost:'#ff3b30'};
function syncChartColors(){
  const css=getComputedStyle(document.documentElement);
  C={input:css.getPropertyValue('--blue').trim()||'#007aff',
    output:css.getPropertyValue('--green').trim()||'#34c759',
    cache:css.getPropertyValue('--tan').trim()||'#ff9500',
    cost:css.getPropertyValue('--red').trim()||'#ff3b30'};
}
const MODEL_DOTS=['#007aff','#34c759','#ff9500','#af52de','#ff3b30',
                  '#5ac8fa','#ffcc00','#5856d6','#ff2d55','#64d2ff'];
const native_=window.webkit&&window.webkit.messageHandlers&&
              window.webkit.messageHandlers.dtm;
if(native_)document.body.classList.add('glass-app');
window.onerror=function(m,s,l){ if(native_)native_.postMessage(
  {action:'jserr',msg:String(m)+' @'+String(s||'')+':'+l}); };

// window dragging: mousedown on non-interactive chrome asks the native
// side to start an NSWindow drag with the current event
const DRAG_SKIP='a,button,input,select,label,svg,th,td,.seg,.chip,'+
  '.filters,.legend,.donut-legend,.overlay,.drawer,.switch';
document.addEventListener('mousedown',e=>{
  if(!native_||e.button!==0)return;
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
const esc=s=>{const d=document.createElement('div');d.textContent=s==null?'':s;return d.innerHTML;};
const short=(s,n)=>s.length>n?s.slice(0,n-1)+'…':s;
const pad=n=>String(n).padStart(2,'0');
const hourKey=d=>d.getFullYear()+'-'+pad(d.getMonth()+1)+'-'+pad(d.getDate())+'T'+pad(d.getHours());
const dayKey=d=>d.getFullYear()+'-'+pad(d.getMonth()+1)+'-'+pad(d.getDate());
const easeOut=t=>1-Math.pow(1-t,4);

// ---------- i18n ----------
let LANG='zh';
const LOCALE={zh:'zh-CN',en:'en-US',ja:'ja-JP',ko:'ko-KR',es:'es-ES',vi:'vi-VN'};
const I18N={
zh:{nav_overview:'概览',nav_models:'模型',nav_sessions:'会话',nav_requests:'请求',nav_settings:'设置',
logo_sub:'用量与费用',sf_today:'今日费用',sf_reqs:'{n} 次请求',live:'实时',updated:'更新于',refresh:'刷新',export:'导出',
s_trend:'用量趋势',s_mix:'Token 构成',s_mix_sub:'输入 / 输出 / 缓存',s_cost:'费用趋势',s_hit:'缓存命中率趋势',
s_hit_sub:'缓存读取 ÷ (输入 + 缓存读取)',s_donut:'模型费用占比',s_heat:'活跃热力图',s_heat_sub:'星期 × 小时 · 全部历史',
s_top:'会话费用榜',s_top_sub:'累计 TOP 8 · 点击看明细',s_scatter:'单请求 成本 × 速度',s_scatter_sub:'最近请求采样 · 点击定位会话',
seg_hour:'近 24 小时',seg_day:'近 14 天',
ser_input:'输入',ser_output:'输出',ser_cache:'缓存读取',ser_cachew:'缓存写入',ser_cost:'费用',
mix_total:'合计',hit_rate:'命中率',hit_reqs:'请求数',none:'无数据',heat_inactive:'无活动',heat_reqs:'请求',
col_model:'模型',col_pin:'输入价 $/M',col_pout:'输出价 $/M',col_pcr:'缓存价 $/M',col_req:'请求',col_input:'输入',
col_output:'输出',col_cache:'缓存',col_hit:'命中率',col_spd:'均速',col_avg:'均费/次',col_cost:'总费用',
col_last:'最后活动',col_title:'标题',col_total:'总 tokens',col_time:'时间',col_sess:'会话',col_speed:'速度',col_thiscost:'本次费用',
f_all_models:'全部模型',f_search:'搜索会话标题…',f_all:'全部',f_today:'今天',f_7d:'近 7 天',
f_count:'显示前 {s} 条 · 共 {n} 条 · 点击行看返回体',f_empty:'没有匹配的请求',
d_cost:'费用',d_reqs:'请求数',d_total:'总 tokens',d_input:'输入',d_output:'输出',d_cache:'缓存',
d_detail:'最近请求明细（{n} / {m}）· 点击行看返回体',loading:'加载中…',nobody:'（无返回正文 — 工具调用或未完成请求）',
k_cost:'今日估算费用',k_all:'累计估算费用',k_req:'今日请求',k_hit:'缓存命中率',k_spd:'平均生成速度',k_top:'主要模型',
ke_delta:'较昨日 {v}',ke_avgreq:'平均 {v}/次',ke_cacheread:'{v} 缓存读',ke_recent:'按最近请求',
ke_topv:'{v} · {n} 次',ke_budget:'预算 {v}',
st_budget:'每日预算告警',st_budget_desc:'今日费用超过预算时发送 macOS 通知并在标题警示。0 为关闭。',
st_budget_lbl:'预算 $',st_save:'保存',st_general:'通用',st_general_desc:'登录 macOS 时自动启动监控应用。',
st_login:'登录时启动',st_login_on:'已开启登录自启',st_data:'数据',st_dbsrc:'数据源',st_prices:'价格表',
st_edit:'编辑 prices.json',st_export:'导出全部 CSV',st_about:'关于',st_version:'版本',
st_about_desc:'监控本地 Devin CLI 的 token 用量与估算费用。credits/ACU 为服务端数据，本地仅按 token × 单价估算。',
st_lang:'语言 / Language',st_lang_desc:'选择界面语言，自动保存。',
toast_budget:'每日预算已设为 {v}',toast_budget_off:'已关闭预算告警',toast_native_only:'仅桌面应用内可用',
toast_edit_prices:'请直接编辑项目目录下的 prices.json',
empty_sessions:'暂无会话数据',empty_scatter:'暂无可绘制样本（需要带速度数据的请求）',donut_total:'累计费用',share:'占比'},
en:{nav_overview:'Overview',nav_models:'Models',nav_sessions:'Sessions',nav_requests:'Requests',nav_settings:'Settings',
logo_sub:'Usage & cost',sf_today:'Today',sf_reqs:'{n} requests',live:'Live',updated:'Updated',refresh:'Refresh',export:'Export',
s_trend:'Usage Trend',s_mix:'Token Mix',s_mix_sub:'input / output / cache',s_cost:'Cost Trend',s_hit:'Cache Hit Rate',
s_hit_sub:'cache read ÷ (input + cache read)',s_donut:'Cost by Model',s_heat:'Activity Heatmap',s_heat_sub:'weekday × hour · all time',
s_top:'Top Sessions',s_top_sub:'top 8 by cost · click for details',s_scatter:'Cost × Speed per Request',s_scatter_sub:'recent requests · click to locate session',
seg_hour:'Last 24h',seg_day:'Last 14d',
ser_input:'Input',ser_output:'Output',ser_cache:'Cache read',ser_cachew:'Cache write',ser_cost:'Cost',
mix_total:'Total',hit_rate:'Hit rate',hit_reqs:'Requests',none:'No data',heat_inactive:'No activity',heat_reqs:'Requests',
col_model:'Model',col_pin:'In $/M',col_pout:'Out $/M',col_pcr:'Cache $/M',col_req:'Reqs',col_input:'Input',
col_output:'Output',col_cache:'Cache',col_hit:'Hit %',col_spd:'Avg speed',col_avg:'Avg/req',col_cost:'Cost',
col_last:'Last active',col_title:'Title',col_total:'Tokens',col_time:'Time',col_sess:'Session',col_speed:'Speed',col_thiscost:'Cost',
f_all_models:'All models',f_search:'Search sessions…',f_all:'All',f_today:'Today',f_7d:'7 days',
f_count:'Showing {s} of {n} · click a row for reply',f_empty:'No matching requests',
d_cost:'Cost',d_reqs:'Requests',d_total:'Tokens',d_input:'Input',d_output:'Output',d_cache:'Cache',
d_detail:'Recent requests ({n} / {m}) · click a row for reply',loading:'Loading…',nobody:'(no reply body — tool call or unfinished request)',
k_cost:"Today's est. cost",k_all:'Total est. cost',k_req:"Today's requests",k_hit:'Cache hit rate',k_spd:'Avg. gen. speed',k_top:'Top model',
ke_delta:'vs yesterday {v}',ke_avgreq:'avg {v}/req',ke_cacheread:'{v} cached',ke_recent:'recent requests',
ke_topv:'{v} · {n} reqs',ke_budget:'budget {v}',
st_budget:'Daily Budget Alert',st_budget_desc:"Send a macOS notification when today's cost exceeds the budget. 0 disables.",
st_budget_lbl:'Budget $',st_save:'Save',st_general:'General',st_general_desc:'Launch the monitor automatically at login.',
st_login:'Launch at login',st_login_on:'Launch at login: on',st_data:'Data',st_dbsrc:'Source',st_prices:'Prices',
st_edit:'Edit prices.json',st_export:'Export all CSV',st_about:'About',st_version:'Version',
st_about_desc:'Monitors local Devin CLI token usage and estimated cost. Credits/ACU are server-side; local cost = tokens × price.',
st_lang:'Language / 语言',st_lang_desc:'Choose interface language. Saved automatically.',
toast_budget:'Daily budget set to {v}',toast_budget_off:'Budget alert off',toast_native_only:'Desktop app only',
toast_edit_prices:'Edit prices.json in the project folder',
empty_sessions:'No sessions yet',empty_scatter:'No samples to plot (needs speed data)',donut_total:'Total cost',share:'Share'},
ja:{nav_overview:'概要',nav_models:'モデル',nav_sessions:'セッション',nav_requests:'リクエスト',nav_settings:'設定',
logo_sub:'使用量と費用',sf_today:'今日の費用',sf_reqs:'{n} リクエスト',live:'ライブ',updated:'更新',refresh:'更新',export:'書き出し',
s_trend:'使用量の推移',s_mix:'トークン構成',s_mix_sub:'入力 / 出力 / キャッシュ',s_cost:'費用の推移',s_hit:'キャッシュ命中率',
s_hit_sub:'キャッシュ読取 ÷（入力＋キャッシュ読取）',s_donut:'モデル別費用',s_heat:'アクティビティ',s_heat_sub:'曜日 × 時間 · 全期間',
s_top:'セッション費用 TOP',s_top_sub:'累計 TOP 8 · クリックで詳細',s_scatter:'リクエスト 費用 × 速度',s_scatter_sub:'最近のリクエスト · クリックでセッションへ',
seg_hour:'過去 24 時間',seg_day:'過去 14 日',
ser_input:'入力',ser_output:'出力',ser_cache:'キャッシュ読取',ser_cachew:'キャッシュ書込',ser_cost:'費用',
mix_total:'合計',hit_rate:'命中率',hit_reqs:'リクエスト数',none:'データなし',heat_inactive:'なし',heat_reqs:'リクエスト',
col_model:'モデル',col_pin:'入力 $/M',col_pout:'出力 $/M',col_pcr:'キャッシュ $/M',col_req:'回数',col_input:'入力',
col_output:'出力',col_cache:'キャッシュ',col_hit:'命中率',col_spd:'平均速度',col_avg:'平均/回',col_cost:'合計費用',
col_last:'最終活動',col_title:'タイトル',col_total:'総トークン',col_time:'時刻',col_sess:'セッション',col_speed:'速度',col_thiscost:'費用',
f_all_models:'すべてのモデル',f_search:'セッションを検索…',f_all:'すべて',f_today:'今日',f_7d:'過去 7 日',
f_count:'{n} 件中 {s} 件表示 · 行クリックで返信を表示',f_empty:'一致するリクエストがありません',
d_cost:'費用',d_reqs:'リクエスト数',d_total:'総トークン',d_input:'入力',d_output:'出力',d_cache:'キャッシュ',
d_detail:'最近のリクエスト（{n} / {m}）· 行クリックで返信を表示',loading:'読み込み中…',nobody:'（返信本文なし — ツール呼び出しまたは未完了）',
k_cost:'今日の推定費用',k_all:'累計推定費用',k_req:'今日のリクエスト',k_hit:'キャッシュ命中率',k_spd:'平均生成速度',k_top:'主なモデル',
ke_delta:'昨日比 {v}',ke_avgreq:'平均 {v}/回',ke_cacheread:'キャッシュ読取 {v}',ke_recent:'最近のリクエスト',
ke_topv:'{v} · {n} 回',ke_budget:'予算 {v}',
st_budget:'1日の予算アラート',st_budget_desc:'今日の費用が予算を超えたら macOS 通知で警告します。0 で無効。',
st_budget_lbl:'予算 $',st_save:'保存',st_general:'一般',st_general_desc:'macOS ログイン時に自動起動します。',
st_login:'ログイン時に起動',st_login_on:'ログイン時に起動：オン',st_data:'データ',st_dbsrc:'データソース',st_prices:'価格表',
st_edit:'prices.json を編集',st_export:'すべて CSV 書き出し',st_about:'情報',st_version:'バージョン',
st_about_desc:'ローカルの Devin CLI トークン使用量と推定費用を監視。credits/ACU はサーバー側の値で、ローカルは トークン × 単価 の推定です。',
st_lang:'言語 / Language',st_lang_desc:'表示言語を選択（自動保存）。',
toast_budget:'1日の予算を {v} に設定しました',toast_budget_off:'予算アラートをオフにしました',toast_native_only:'デスクトップアプリでのみ利用可能',
toast_edit_prices:'プロジェクトの prices.json を直接編集してください',
empty_sessions:'セッションがありません',empty_scatter:'描画できるデータがありません（速度データが必要）',donut_total:'累計費用',share:'割合'},
ko:{nav_overview:'개요',nav_models:'모델',nav_sessions:'세션',nav_requests:'요청',nav_settings:'설정',
logo_sub:'사용량 및 비용',sf_today:'오늘 비용',sf_reqs:'{n}개 요청',live:'실시간',updated:'업데이트',refresh:'새로고침',export:'보내기',
s_trend:'사용량 추이',s_mix:'토큰 구성',s_mix_sub:'입력 / 출력 / 캐시',s_cost:'비용 추이',s_hit:'캐시 적중률',
s_hit_sub:'캐시 읽기 ÷ (입력 + 캐시 읽기)',s_donut:'모델별 비용',s_heat:'활동 히트맵',s_heat_sub:'요일 × 시간 · 전체 기록',
s_top:'세션 비용 TOP',s_top_sub:'누적 TOP 8 · 클릭하여 상세 보기',s_scatter:'요청 비용 × 속도',s_scatter_sub:'최근 요청 · 클릭하여 세션으로',
seg_hour:'최근 24시간',seg_day:'최근 14일',
ser_input:'입력',ser_output:'출력',ser_cache:'캐시 읽기',ser_cachew:'캐시 쓰기',ser_cost:'비용',
mix_total:'합계',hit_rate:'적중률',hit_reqs:'요청 수',none:'데이터 없음',heat_inactive:'활동 없음',heat_reqs:'요청',
col_model:'모델',col_pin:'입력 $/M',col_pout:'출력 $/M',col_pcr:'캐시 $/M',col_req:'요청',col_input:'입력',
col_output:'출력',col_cache:'캐시',col_hit:'적중률',col_spd:'평균 속도',col_avg:'평균/회',col_cost:'총 비용',
col_last:'마지막 활동',col_title:'제목',col_total:'총 토큰',col_time:'시간',col_sess:'세션',col_speed:'속도',col_thiscost:'비용',
f_all_models:'모든 모델',f_search:'세션 제목 검색…',f_all:'전체',f_today:'오늘',f_7d:'최근 7일',
f_count:'{n}개 중 {s}개 표시 · 행 클릭 시 응답 보기',f_empty:'일치하는 요청이 없습니다',
d_cost:'비용',d_reqs:'요청 수',d_total:'총 토큰',d_input:'입력',d_output:'출력',d_cache:'캐시',
d_detail:'최근 요청 ({n} / {m}) · 행 클릭 시 응답 보기',loading:'불러오는 중…',nobody:'(응답 본문 없음 — 도구 호출 또는 미완료 요청)',
k_cost:'오늘 예상 비용',k_all:'누적 예상 비용',k_req:'오늘 요청',k_hit:'캐시 적중률',k_spd:'평균 생성 속도',k_top:'주요 모델',
ke_delta:'어제 대비 {v}',ke_avgreq:'평균 {v}/회',ke_cacheread:'캐시 읽기 {v}',ke_recent:'최근 요청 기준',
ke_topv:'{v} · {n}회',ke_budget:'예산 {v}',
st_budget:'일일 예산 알림',st_budget_desc:'오늘 비용이 예산을 초과하면 macOS 알림을 보냅니다. 0은 해제.',
st_budget_lbl:'예산 $',st_save:'저장',st_general:'일반',st_general_desc:'macOS 로그인 시 자동 실행합니다.',
st_login:'로그인 시 시작',st_login_on:'로그인 시 시작: 켜짐',st_data:'데이터',st_dbsrc:'데이터 소스',st_prices:'가격표',
st_edit:'prices.json 편집',st_export:'전체 CSV보내기',st_about:'정보',st_version:'버전',
st_about_desc:'로컬 Devin CLI의 토큰 사용량과 예상 비용을 모니터링합니다. credits/ACU는 서버 값이며 로컬은 토큰 × 단가 추정입니다.',
st_lang:'언어 / Language',st_lang_desc:'인터페이스 언어 선택 (자동 저장).',
toast_budget:'일일 예산을 {v}(으)로 설정',toast_budget_off:'예산 알림 해제',toast_native_only:'데스크톱 앱에서만 사용 가능',
toast_edit_prices:'프로젝트 폴더의 prices.json을 직접 편집하세요',
empty_sessions:'세션 데이터 없음',empty_scatter:'표시할 샘플 없음(속도 데이터 필요)',donut_total:'누적 비용',share:'비중'},
es:{nav_overview:'Resumen',nav_models:'Modelos',nav_sessions:'Sesiones',nav_requests:'Solicitudes',nav_settings:'Ajustes',
logo_sub:'Uso y costo',sf_today:'Costo de hoy',sf_reqs:'{n} solicitudes',live:'En vivo',updated:'Actualizado',refresh:'Actualizar',export:'Exportar',
s_trend:'Tendencia de uso',s_mix:'Composición de tokens',s_mix_sub:'entrada / salida / caché',s_cost:'Tendencia de costo',s_hit:'Aciertos de caché',
s_hit_sub:'lectura caché ÷ (entrada + lectura caché)',s_donut:'Costo por modelo',s_heat:'Mapa de actividad',s_heat_sub:'día × hora · histórico',
s_top:'Sesiones más caras',s_top_sub:'TOP 8 acumulado · clic para detalles',s_scatter:'Costo × velocidad por solicitud',s_scatter_sub:'solicitudes recientes · clic para ir a la sesión',
seg_hour:'Últimas 24 h',seg_day:'Últimos 14 días',
ser_input:'Entrada',ser_output:'Salida',ser_cache:'Lectura caché',ser_cachew:'Escritura caché',ser_cost:'Costo',
mix_total:'Total',hit_rate:'Aciertos',hit_reqs:'Solicitudes',none:'Sin datos',heat_inactive:'Sin actividad',heat_reqs:'Solicitudes',
col_model:'Modelo',col_pin:'Entrada $/M',col_pout:'Salida $/M',col_pcr:'Caché $/M',col_req:'Solic.',col_input:'Entrada',
col_output:'Salida',col_cache:'Caché',col_hit:'Aciertos',col_spd:'Vel. media',col_avg:'Media/solic.',col_cost:'Costo total',
col_last:'Última actividad',col_title:'Título',col_total:'Tokens',col_time:'Hora',col_sess:'Sesión',col_speed:'Velocidad',col_thiscost:'Costo',
f_all_models:'Todos los modelos',f_search:'Buscar sesiones…',f_all:'Todo',f_today:'Hoy',f_7d:'Últimos 7 días',
f_count:'Mostrando {s} de {n} · clic en la fila para ver la respuesta',f_empty:'Sin solicitudes coincidentes',
d_cost:'Costo',d_reqs:'Solicitudes',d_total:'Tokens',d_input:'Entrada',d_output:'Salida',d_cache:'Caché',
d_detail:'Solicitudes recientes ({n} / {m}) · clic para ver la respuesta',loading:'Cargando…',nobody:'(sin respuesta — llamada a herramienta o solicitud incompleta)',
k_cost:'Costo estimado hoy',k_all:'Costo estimado total',k_req:'Solicitudes hoy',k_hit:'Aciertos de caché',k_spd:'Velocidad media',k_top:'Modelo principal',
ke_delta:'vs ayer {v}',ke_avgreq:'media {v}/solic.',ke_cacheread:'{v} de caché',ke_recent:'solicitudes recientes',
ke_topv:'{v} · {n} solic.',ke_budget:'presupuesto {v}',
st_budget:'Alerta de presupuesto diario',st_budget_desc:'Envía una notificación de macOS cuando el costo de hoy supera el presupuesto. 0 desactiva.',
st_budget_lbl:'Presupuesto $',st_save:'Guardar',st_general:'General',st_general_desc:'Iniciar el monitor automáticamente al iniciar sesión.',
st_login:'Abrir al iniciar sesión',st_login_on:'Abrir al iniciar sesión: activado',st_data:'Datos',st_dbsrc:'Fuente',st_prices:'Precios',
st_edit:'Editar prices.json',st_export:'Exportar todo a CSV',st_about:'Acerca de',st_version:'Versión',
st_about_desc:'Monitorea el uso de tokens del Devin CLI local y estima el costo. Los créditos/ACU son del servidor; localmente = tokens × precio.',
st_lang:'Idioma / Language',st_lang_desc:'Elige el idioma de la interfaz (se guarda solo).',
toast_budget:'Presupuesto diario: {v}',toast_budget_off:'Alerta desactivada',toast_native_only:'Solo en la app de escritorio',
toast_edit_prices:'Edita prices.json en la carpeta del proyecto',
empty_sessions:'Sin sesiones',empty_scatter:'Sin muestras (se requieren datos de velocidad)',donut_total:'Costo total',share:'Parte'},
vi:{nav_overview:'Tổng quan',nav_models:'Mô hình',nav_sessions:'Phiên',nav_requests:'Yêu cầu',nav_settings:'Cài đặt',
logo_sub:'Mức dùng & chi phí',sf_today:'Chi phí hôm nay',sf_reqs:'{n} yêu cầu',live:'Trực tiếp',updated:'Cập nhật',refresh:'Làm mới',export:'Xuất',
s_trend:'Xu hướng sử dụng',s_mix:'Cấu trúc token',s_mix_sub:'nhập / xuất / bộ đệm',s_cost:'Xu hướng chi phí',s_hit:'Tỷ lệ trúng cache',
s_hit_sub:'đọc cache ÷ (nhập + đọc cache)',s_donut:'Chi phí theo mô hình',s_heat:'Bản đồ hoạt động',s_heat_sub:'thứ × giờ · toàn bộ lịch sử',
s_top:'Phiên tốn kém nhất',s_top_sub:'TOP 8 lũy kế · bấm xem chi tiết',s_scatter:'Chi phí × tốc độ mỗi yêu cầu',s_scatter_sub:'yêu cầu gần đây · bấm để tới phiên',
seg_hour:'24 giờ qua',seg_day:'14 ngày qua',
ser_input:'Nhập',ser_output:'Xuất',ser_cache:'Đọc cache',ser_cachew:'Ghi cache',ser_cost:'Chi phí',
mix_total:'Tổng',hit_rate:'Tỷ lệ trúng',hit_reqs:'Số yêu cầu',none:'Không có dữ liệu',heat_inactive:'Không hoạt động',heat_reqs:'Yêu cầu',
col_model:'Mô hình',col_pin:'Nhập $/M',col_pout:'Xuất $/M',col_pcr:'Cache $/M',col_req:'Lượt',col_input:'Nhập',
col_output:'Xuất',col_cache:'Cache',col_hit:'Trúng',col_spd:'Tốc độ TB',col_avg:'TB/lượt',col_cost:'Tổng chi phí',
col_last:'Hoạt động cuối',col_title:'Tiêu đề',col_total:'Tổng token',col_time:'Thời gian',col_sess:'Phiên',col_speed:'Tốc độ',col_thiscost:'Chi phí',
f_all_models:'Tất cả mô hình',f_search:'Tìm tiêu đề phiên…',f_all:'Tất cả',f_today:'Hôm nay',f_7d:'7 ngày qua',
f_count:'Hiển thị {s} / {n} · bấm dòng để xem phản hồi',f_empty:'Không có yêu cầu phù hợp',
d_cost:'Chi phí',d_reqs:'Số yêu cầu',d_total:'Tổng token',d_input:'Nhập',d_output:'Xuất',d_cache:'Cache',
d_detail:'Yêu cầu gần đây ({n} / {m}) · bấm dòng để xem phản hồi',loading:'Đang tải…',nobody:'(không có nội dung phản hồi — lệnh gọi công cụ hoặc chưa hoàn tất)',
k_cost:'Chi phí ước tính hôm nay',k_all:'Tổng chi phí ước tính',k_req:'Yêu cầu hôm nay',k_hit:'Tỷ lệ trúng cache',k_spd:'Tốc độ tạo TB',k_top:'Mô hình chính',
ke_delta:'so với hôm qua {v}',ke_avgreq:'TB {v}/lượt',ke_cacheread:'đọc cache {v}',ke_recent:'theo yêu cầu gần đây',
ke_topv:'{v} · {n} lượt',ke_budget:'ngân sách {v}',
st_budget:'Cảnh báo ngân sách ngày',st_budget_desc:'Gửi thông báo macOS khi chi phí hôm nay vượt ngân sách. 0 để tắt.',
st_budget_lbl:'Ngân sách $',st_save:'Lưu',st_general:'Chung',st_general_desc:'Tự động chạy khi đăng nhập macOS.',
st_login:'Khởi động cùng đăng nhập',st_login_on:'Đã bật tự khởi động',st_data:'Dữ liệu',st_dbsrc:'Nguồn dữ liệu',st_prices:'Bảng giá',
st_edit:'Sửa prices.json',st_export:'Xuất toàn bộ CSV',st_about:'Giới thiệu',st_version:'Phiên bản',
st_about_desc:'Theo dõi token Devin CLI cục bộ và ước tính chi phí. credits/ACU là dữ liệu máy chủ; cục bộ chỉ tính token × đơn giá.',
st_lang:'Ngôn ngữ / Language',st_lang_desc:'Chọn ngôn ngữ giao diện (tự lưu).',
toast_budget:'Đã đặt ngân sách ngày {v}',toast_budget_off:'Đã tắt cảnh báo ngân sách',toast_native_only:'Chỉ trong app desktop',
toast_edit_prices:'Hãy sửa prices.json trong thư mục dự án',
empty_sessions:'Chưa có dữ liệu phiên',empty_scatter:'Chưa có mẫu để vẽ (cần dữ liệu tốc độ)',donut_total:'Tổng chi phí',share:'Tỷ trọng'}};
const EXTRA_I18N={
zh:{nav_insights:'分析',st_theme:'主题外观',st_theme_desc:'选择配色方案；系统模式跟随系统外观。',theme_system:'跟随系统',theme_midnight:'午夜蓝',theme_graphite:'石墨',theme_paper:'暖纸',theme_ocean:'深海',theme_forest:'森林',an_title:'深入分析',an_last7:'7 天',an_last30:'30 天',an_mtd:'本月',an_all:'累计',an_period_cost:'所选周期费用',an_period_tokens:'所选周期 Tokens',an_period_requests:'所选周期请求',an_active_days:'活跃天数',an_avg_tokens_active:'活跃日均 Tokens',an_month_projection:'本月费用预测',an_trend:'较上一周期',an_economics:'Token 效率',an_economics_desc:'结合模型单价衡量缓存价值与生成效率。',an_cache_saved:'估算缓存节省',an_output_input:'输出 / 输入比例',an_tokens_per_request:'平均 Tokens / 请求',an_cost_per_1k:'每千输出 Tokens 成本',an_distribution:'请求规模与性能分位',an_sample:'最近 {n} 个请求样本',an_metric:'指标',an_request_tokens:'请求总 Tokens',an_input:'输入 Tokens',an_output:'输出 Tokens',an_ttft:'首字延迟',an_latency:'完整请求耗时',an_speed:'生成速度',an_models:'模型效率对比',an_models_desc:'比较请求规模、输出效率、缓存收益与单位输出成本。'},
en:{nav_insights:'Insights',st_theme:'Appearance',st_theme_desc:'Choose a palette; System follows the operating-system appearance.',theme_system:'System',theme_midnight:'Midnight',theme_graphite:'Graphite',theme_paper:'Warm Paper',theme_ocean:'Deep Ocean',theme_forest:'Forest',an_title:'Token Analytics',an_last7:'7 days',an_last30:'30 days',an_mtd:'Month to date',an_all:'All time',an_period_cost:'Cost in period',an_period_tokens:'Tokens in period',an_period_requests:'Requests in period',an_active_days:'Active days',an_calendar_days:'calendar days',an_avg_tokens_active:'Tokens per active day',an_month_projection:'Projected month cost',an_trend:'Change vs prior period',an_economics:'Token efficiency',an_economics_desc:'Cache value and output efficiency estimated from configured model prices.',an_cache_saved:'Estimated cache savings',an_output_input:'Output / input ratio',an_tokens_per_request:'Tokens per request',an_cost_per_1k:'Cost per 1K output tokens',an_distribution:'Request size and performance percentiles',an_sample:'Sample of the most recent {n} requests',an_metric:'Metric',an_request_tokens:'Request tokens',an_input:'Input tokens',an_output:'Output tokens',an_ttft:'Time to first token',an_latency:'Request duration',an_speed:'Generation speed',an_models:'Model efficiency',an_models_desc:'Compare request size, output efficiency, cache value and unit-output cost.'},
ja:{nav_insights:'分析',st_theme:'外観',st_theme_desc:'配色を選択します。システムは OS の外観に従います。',theme_system:'システム',theme_midnight:'ミッドナイト',theme_graphite:'グラファイト',theme_paper:'ウォームペーパー',theme_ocean:'深海',theme_forest:'フォレスト',an_title:'トークン分析',an_last7:'7日間',an_last30:'30日間',an_mtd:'今月',an_all:'全期間',an_period_cost:'期間内の費用',an_period_tokens:'期間内のトークン',an_period_requests:'期間内のリクエスト',an_active_days:'利用日数',an_avg_tokens_active:'利用日あたりのトークン',an_month_projection:'今月の費用予測',an_trend:'前期間との比較',an_economics:'トークン効率',an_economics_desc:'設定価格に基づくキャッシュ価値と出力効率。',an_cache_saved:'推定キャッシュ節約額',an_output_input:'出力 / 入力比',an_tokens_per_request:'リクエストあたりのトークン',an_cost_per_1k:'出力1Kトークンあたりの費用',an_distribution:'リクエスト規模と性能のパーセンタイル',an_sample:'直近 {n} 件のサンプル',an_metric:'指標',an_request_tokens:'リクエストトークン',an_input:'入力トークン',an_output:'出力トークン',an_ttft:'初回トークン時間',an_latency:'リクエスト所要時間',an_speed:'生成速度',an_models:'モデル効率',an_models_desc:'リクエスト規模、出力効率、キャッシュ価値、単位出力コストを比較。'},
ko:{nav_insights:'분석',st_theme:'테마',st_theme_desc:'색상 테마를 선택합니다. 시스템은 OS 모양을 따릅니다.',theme_system:'시스템',theme_midnight:'미드나잇',theme_graphite:'그래파이트',theme_paper:'웜 페이퍼',theme_ocean:'딥 오션',theme_forest:'포레스트',an_title:'토큰 분석',an_last7:'7일',an_last30:'30일',an_mtd:'이번 달',an_all:'전체',an_period_cost:'기간 비용',an_period_tokens:'기간 토큰',an_period_requests:'기간 요청',an_active_days:'활성 일수',an_avg_tokens_active:'활성일당 토큰',an_month_projection:'월 비용 예상',an_trend:'이전 기간 대비',an_economics:'토큰 효율',an_economics_desc:'설정된 모델 가격으로 캐시 가치와 출력 효율을 추정합니다.',an_cache_saved:'예상 캐시 절감액',an_output_input:'출력 / 입력 비율',an_tokens_per_request:'요청당 토큰',an_cost_per_1k:'출력 토큰 1K당 비용',an_distribution:'요청 규모 및 성능 백분위',an_sample:'최근 {n}개 요청 표본',an_metric:'지표',an_request_tokens:'요청 토큰',an_input:'입력 토큰',an_output:'출력 토큰',an_ttft:'첫 토큰 시간',an_latency:'요청 소요 시간',an_speed:'생성 속도',an_models:'모델 효율',an_models_desc:'요청 규모, 출력 효율, 캐시 가치와 단위 출력 비용을 비교합니다.'},
es:{nav_insights:'Análisis',st_theme:'Apariencia',st_theme_desc:'Elige una paleta; Sistema sigue la apariencia del sistema operativo.',theme_system:'Sistema',theme_midnight:'Medianoche',theme_graphite:'Grafito',theme_paper:'Papel cálido',theme_ocean:'Océano profundo',theme_forest:'Bosque',an_title:'Análisis de tokens',an_last7:'7 días',an_last30:'30 días',an_mtd:'Este mes',an_all:'Todo',an_period_cost:'Costo del período',an_period_tokens:'Tokens del período',an_period_requests:'Solicitudes del período',an_active_days:'Días activos',an_avg_tokens_active:'Tokens por día activo',an_month_projection:'Costo mensual previsto',an_trend:'Cambio frente al período anterior',an_economics:'Eficiencia de tokens',an_economics_desc:'Valor de caché y eficiencia de salida estimados con los precios configurados.',an_cache_saved:'Ahorro estimado por caché',an_output_input:'Proporción salida / entrada',an_tokens_per_request:'Tokens por solicitud',an_cost_per_1k:'Costo por 1K tokens de salida',an_distribution:'Percentiles de tamaño y rendimiento',an_sample:'Muestra de las {n} solicitudes recientes',an_metric:'Métrica',an_request_tokens:'Tokens por solicitud',an_input:'Tokens de entrada',an_output:'Tokens de salida',an_ttft:'Tiempo hasta el primer token',an_latency:'Duración de solicitud',an_speed:'Velocidad de generación',an_models:'Eficiencia por modelo',an_models_desc:'Compara tamaño de solicitud, eficiencia de salida, valor de caché y costo unitario.'},
vi:{nav_insights:'Phân tích',st_theme:'Giao diện',st_theme_desc:'Chọn bảng màu; Hệ thống theo giao diện hệ điều hành.',theme_system:'Hệ thống',theme_midnight:'Nửa đêm',theme_graphite:'Than chì',theme_paper:'Giấy ấm',theme_ocean:'Đại dương sâu',theme_forest:'Rừng',an_title:'Phân tích token',an_last7:'7 ngày',an_last30:'30 ngày',an_mtd:'Trong tháng',an_all:'Toàn bộ',an_period_cost:'Chi phí kỳ này',an_period_tokens:'Token kỳ này',an_period_requests:'Yêu cầu kỳ này',an_active_days:'Ngày hoạt động',an_avg_tokens_active:'Token mỗi ngày hoạt động',an_month_projection:'Dự báo chi phí tháng',an_trend:'Thay đổi so với kỳ trước',an_economics:'Hiệu quả token',an_economics_desc:'Ước tính giá trị bộ nhớ đệm và hiệu quả đầu ra theo bảng giá.',an_cache_saved:'Tiết kiệm cache ước tính',an_output_input:'Tỷ lệ đầu ra / đầu vào',an_tokens_per_request:'Token mỗi yêu cầu',an_cost_per_1k:'Chi phí mỗi 1K token đầu ra',an_distribution:'Phân vị quy mô và hiệu suất yêu cầu',an_sample:'Mẫu {n} yêu cầu gần đây',an_metric:'Chỉ số',an_request_tokens:'Token mỗi yêu cầu',an_input:'Token đầu vào',an_output:'Token đầu ra',an_ttft:'Thời gian đến token đầu tiên',an_latency:'Thời lượng yêu cầu',an_speed:'Tốc độ tạo',an_models:'Hiệu quả mô hình',an_models_desc:'So sánh quy mô yêu cầu, hiệu quả đầu ra, giá trị cache và chi phí đơn vị.'}
};
const DOWSL={zh:['一','二','三','四','五','六','日'],en:['Mo','Tu','We','Th','Fr','Sa','Su'],
  ja:['月','火','水','木','金','土','日'],ko:['월','화','수','목','금','토','일'],
  es:['lu','ma','mi','ju','vi','sá','do'],vi:['T2','T3','T4','T5','T6','T7','CN']};
const t=k=>(I18N[LANG]&&I18N[LANG][k])||(EXTRA_I18N[LANG]&&EXTRA_I18N[LANG][k])||
  I18N.zh[k]||EXTRA_I18N.en[k]||k;
const tf=(k,o)=>t(k).replace(/\\{(\\w+)\\}/g,(m,p)=>o[p]!=null?o[p]:m);
const THEMES=new Set(['system','midnight','graphite','paper','ocean','forest']);
function applyTheme(theme){
  theme=THEMES.has(theme)?theme:'system';
  if(theme==='system')document.documentElement.removeAttribute('data-theme');
  else document.documentElement.dataset.theme=theme;
  syncChartColors();
}
function setTheme(theme){
  if(!THEMES.has(theme))return;
  applyTheme(theme);
  if(native_)native_.postMessage({action:'setTheme',value:theme});
  else fetch('/api/settings',{method:'POST',headers:{'Content-Type':'application/json'},
    body:JSON.stringify({theme})}).catch(()=>{});
  if(DATA){DATA.settings.theme=theme;update(DATA);}
}
function applyLang(){
  document.documentElement.lang=LOCALE[LANG]||'zh-CN';
  document.querySelectorAll('[data-i18n]').forEach(el=>{
    const v=t(el.dataset.i18n);if(el.textContent!==v)el.textContent=v;});
  document.querySelectorAll('[data-i18n-ph]').forEach(el=>el.placeholder=t(el.dataset.i18nPh));
  document.querySelectorAll('#lang-row .chip').forEach(c=>
    c.classList.toggle('on',c.dataset.lang===LANG));
  const cur=document.querySelector('.view.on');
  if(cur)document.getElementById('view-title').textContent=TKEYS[cur.id.slice(2)]?t(TKEYS[cur.id.slice(2)]):'';
}
function setLang(l){
  if(!I18N[l])return;LANG=l;
  if(native_)native_.postMessage({action:'setLanguage',value:l});
  else fetch('/api/settings',{method:'POST',headers:{'Content-Type':'application/json'},
    body:JSON.stringify({language:l})}).catch(()=>{});
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
  document.querySelectorAll('nav a').forEach(x=>x.classList.toggle('on',x.dataset.v===v));
  document.querySelectorAll('.view').forEach(x=>
    x.classList.toggle('on',x.id==='v-'+v));
  document.getElementById('view-title').textContent=t(TKEYS[v]);
  document.querySelector('main').scrollTop=0;
  document.getElementById('overlay').classList.remove('open');
  if(native_)native_.postMessage({action:'navigate',view:v});
}
document.getElementById('nav').addEventListener('click',e=>{
  const a=e.target.closest('a');if(a)navigateTo(a.dataset.v);
});
document.addEventListener('keydown',e=>{
  if(e.key==='Escape')document.getElementById('overlay').classList.remove('open');
  if(e.metaKey&&e.key>='1'&&e.key<='6'){
    document.querySelectorAll('nav a')[+e.key-1].click();}
  if(e.key==='/'&&document.activeElement.tagName!=='INPUT'){
    e.preventDefault();
    document.querySelector('nav a[data-v="requests"]').click();
    document.getElementById('f-session').focus();}
});

// ---------- line charts ----------
const charts={};
function buckets(mode){
  const out=[],now=new Date();
  if(mode==='hour'){const h=new Date(now);h.setMinutes(0,0,0);
    for(let i=23;i>=0;i--){const d=new Date(h-i*36e5);
      out.push({key:hourKey(d),label:d.getHours()+':00'});}}
  else{const d0=new Date(now.getFullYear(),now.getMonth(),now.getDate());
    for(let i=13;i>=0;i--){const d=new Date(d0-i*864e5);
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
  const W=860,H=230,pl=58,pr=14,pt=12,pb=30;
  const iw=W-pl-pr,ih=H-pt-pb,n=bs.length,step=n>1?iw/(n-1):iw;
  const ymax=Math.max(...vis.flatMap(s=>s.values),0)*1.08||1;
  const X=i=>pl+i*step,Y=v=>pt+ih-(v/ymax)*ih;
  let g='';
  for(let k=0;k<=4;k++){const y=pt+ih*k/4;
    g+=`<line x1=${pl} y1=${y} x2=${W-pr} y2=${y} stroke="rgba(127,140,160,.16)"/>`;
    g+=`<text x=${pl-8} y=${y+4} text-anchor="end" font-size="10" fill="var(--faint)">${st.fmt(ymax*(1-k/4))}</text>`;}
  const lstep=Math.ceil(n/8);
  bs.forEach((b,i)=>{if(i%lstep===0||i===n-1)
    g+=`<text x=${X(i)} y=${H-8} text-anchor="middle" font-size="10" fill="var(--faint)">${b.label}</text>`;});
  let defs='',paths='';
  vis.forEach((s,si)=>{
    if(s.area){
      defs+=`<linearGradient id="ag-${id}-${si}" x1="0" y1="0" x2="0" y2="1">
        <stop offset="0" stop-color="${s.color}" stop-opacity=".28"/>
        <stop offset="1" stop-color="${s.color}" stop-opacity="0"/></linearGradient>`;
      const d='M'+X(0)+','+Y(0)+' '+s.values.map((v,i)=>'L'+X(i)+','+Y(v)).join(' ')
        +' L'+X(n-1)+','+Y(0)+' Z';
      paths+=`<path class="fill" d="${d}" fill="url(#ag-${id}-${si})" opacity="0"/>`;}
    const d='M'+s.values.map((v,i)=>X(i)+','+Y(v)).join(' L');
    paths+=`<path class="ln" d="${d}" fill="none" stroke="${s.color}" stroke-width="2.2"
      stroke-linejoin="round" stroke-linecap="round"/>`;});
  el.innerHTML=`<svg viewBox="0 0 ${W} ${H}"><defs>${defs}</defs>${g}${paths}
    <line id="gl-${id}" y1=${pt} y2=${pt+ih} stroke="rgba(140,150,165,.6)" visibility="hidden"/>
    <g id="dots-${id}"></g>
    <rect id="ov-${id}" x=${pl} y=${pt} width=${iw} height=${ih} fill="transparent"/></svg>`;
  if(animate){
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
      `<circle cx=${X(i)} cy=${Y(s.values[i])} r="3.4" fill="${s.color}" stroke="var(--glass2)" stroke-width="1.6"/>`).join('');
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
  if(on&&th){th.style.left=on.offsetLeft+'px';th.style.width=on.offsetWidth+'px';}}
function setupChart(id,kind){
  charts[id]={mode:'hour',hidden:new Set(),kind,drew:false};
  const seg=document.getElementById('seg-'+id);
  seg.addEventListener('click',e=>{
    if(e.target.tagName!=='BUTTON')return;
    [...seg.querySelectorAll('button')].forEach(b=>b.classList.toggle('on',b===e.target));
    charts[id].mode=e.target.dataset.v;segThumb(seg);refreshChart(id,true);});
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
  const seg=document.getElementById('seg-'+id);if(!seg)return;
  seg.addEventListener('click',e=>{
    if(e.target.tagName!=='BUTTON')return;
    [...seg.querySelectorAll('button')].forEach(b=>
      b.classList.toggle('on',b===e.target));
    charts[id].mode=e.target.dataset.v;segThumb(seg);render(true);});
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
    g+=`<line x1=${pl} y1=${y} x2=${W-pr} y2=${y} stroke="rgba(127,140,160,.16)"/>
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
  const W=860,H=200,pl=58,pr=14,pt=12,pb=30,iw=W-pl-pr,ih=H-pt-pb;
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
     <line id="gl-mix" y1=${pt} y2=${pt+ih} stroke="rgba(140,150,165,.6)" visibility="hidden"/>${hot}</svg>`;
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
  const W=860,H=170,pl=58,pr=14,pt=12,pb=30,iw=W-pl-pr,ih=H-pt-pb;
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
     <line id="gl-hit" y1=${pt} y2=${pt+ih} stroke="rgba(140,150,165,.6)" visibility="hidden"/>${hot}</svg>`;
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
      const a=v?0.15+0.85*Math.sqrt(v/mx):0;
      cells+=`<i data-d="${d}" data-h="${h}" style="background:${v?'rgba(0,122,255,'+a.toFixed(2)+')':''}"></i>`;
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
    `<div class="hr" data-sid="${esc(s.id)}">
      <span class="nm" title="${esc(s.dir||'')}">${esc(short(s.title,28))}</span>
      <span class="tr"><i style="width:${Math.max(2,(s.cost||0)/mx*100).toFixed(1)}%"></i></span>
      <span class="vl">${fmtCost(s.cost||0)}</span></div>`).join('')
    ||`<div class="empty">${t('empty_sessions')}</div>`;
  el.querySelectorAll('.hr').forEach(r=>
    r.onclick=()=>openSession(r.dataset.sid));
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
    g+=`<line x1=${pl} y1=${y} x2=${W-pr} y2=${y} stroke="rgba(127,140,160,.16)"/>
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
      if((DATA.sessions||[]).some(s=>s.id===r.session_id))openSession(r.session_id);});});
}

// ---------- donut ----------
let donutColors={};
function drawDonut(){
  const rows=DATA.by_model.filter(m=>(m.cost||0)>0);
  const total=rows.reduce((a,m)=>a+m.cost,0)||1;
  animateValue(document.getElementById('donut-total'),total,fmtCost);
  const R=76,CI=2*Math.PI*R;let acc=0,g='';
  donutColors={};
  rows.forEach((m,i)=>{
    const col=MODEL_DOTS[i%MODEL_DOTS.length];donutColors[m.model]=col;
    const frac=m.cost/total,len=frac*CI;
    g+=`<circle data-m="${esc(m.model)}" cx="110" cy="110" r="${R}" fill="none"
      stroke="${col}" stroke-width="30" stroke-dasharray="${len} ${CI-len}"
      stroke-dashoffset="${-acc}" transform="rotate(-90 110 110)"
      style="transition:stroke-dashoffset .9s var(--easeout),stroke-dasharray .9s var(--easeout)"/>`;
    acc+=len;});
  document.getElementById('donut').innerHTML=
    `<svg viewBox="0 0 220 220" style="width:220px;height:220px">${g}</svg>`;
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
  document.getElementById('t-sessions').innerHTML=DATA.sessions.slice(0,15).map(s=>
    `<tr class="clickable" data-sid="${esc(s.id)}"><td class="l fade">${s.last_ts.slice(5,16)}</td>
     <td class="l" title="${esc(s.dir)}">${esc(short(s.title,36))}</td>
     <td class="l model fade">${esc(short(s.models.join(', '),26))}</td>
     <td>${fmtTok(s.total)}</td><td>${fmtCost(s.cost||0)}</td>
     <td><div class="costbar" style="width:${Math.max(2,(s.cost||0)/mx*100)}%"></div></td></tr>`).join('');
  document.querySelectorAll('#t-sessions tr').forEach(tr=>
    tr.onclick=()=>openSession(tr.dataset.sid));
}
function openSession(sid){
  const s=(DATA.sessions||[]).find(x=>x.id===sid)||
          (DATA.top_sessions||[]).find(x=>x.id===sid);
  if(!s)return;
  const reqs=DATA.requests.filter(r=>r.session_id===sid);
  const inc=s.input||0,outc=s.output||0,cached=s.cache_read||0,cost=s.cost||0;
  document.getElementById('drawer-body').innerHTML=
    `<h3>${esc(s.title)}</h3><div class="meta">${esc(s.dir||'')}<br>${esc(s.id)}</div>
     <div class="kpis">
      <div class="card"><div class="label">${t('d_cost')}</div><div class="value">${fmtCost(cost)}</div></div>
      <div class="card"><div class="label">${t('d_reqs')}</div><div class="value">${s.requests}</div></div>
      <div class="card"><div class="label">${t('d_total')}</div><div class="value">${fmtTok(inc+outc+cached)}</div></div>
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
  document.getElementById('overlay').classList.add('open');
}
document.getElementById('overlay').addEventListener('click',e=>{
  if(e.target.id==='overlay')e.currentTarget.classList.remove('open');});
document.getElementById('drawer-x').onclick=()=>
  document.getElementById('overlay').classList.remove('open');

// ---------- request feed ----------
const filt={model:'',q:'',date:'',day:''};
function setModelFilter(m){
  filt.model=m;document.getElementById('f-model').value=m;
  document.querySelectorAll('nav a')[3].click();renderFeed();}
const reqDay=r=>r.ts.slice(0,10);
function filteredReqs(){
  const today=dayKey(new Date()),lim=dayKey(new Date(Date.now()-6*864e5));
  return DATA.requests.filter(r=>{
    if(filt.model&&r.model!==filt.model)return false;
    if(filt.q&&!r.session_title.toLowerCase().includes(filt.q))return false;
    if(filt.date&&reqDay(r)!==filt.date)return false;
    if(filt.day==='today'&&reqDay(r)!==today)return false;
    if(filt.day==='7'&&reqDay(r)<lim)return false;
    return true;});}
function toggleReq(tr,r,cols){
  const next=tr.nextElementSibling;
  if(next&&next.classList.contains('reqbody')){next.remove();tr.classList.remove('exp');return;}
  tr.classList.add('exp');
  const row=document.createElement('tr');row.className='reqbody';
  const rid=r.request_id||r.message_id||'';
  row.dataset.rid=rid;
  row.innerHTML=`<td colspan="${cols}"><pre>${t('loading')}</pre></td>`;
  tr.after(row);
  if(native_)native_.postMessage({action:'getBody',rid:r.request_id||'',mid:r.message_id||''});
  else fetch('/api/body?rid='+encodeURIComponent(r.request_id||'')+
             '&mid='+encodeURIComponent(r.message_id||''))
        .then(x=>x.json()).then(d=>showBody(rid,d.body||''))
        .catch(()=>showBody(rid,''));
}
function showBody(rid,text){
  document.querySelectorAll('.reqbody').forEach(row=>{
    if(row.dataset.rid===rid)
      row.querySelector('pre').textContent=
        (text||'').trim()||t('nobody');
  });
}
function bindReqRows(sel,rows,cols){
  document.querySelectorAll(sel+' tr.clickable').forEach(tr=>
    tr.onclick=()=>toggleReq(tr,rows[+tr.dataset.i],cols));
}
function renderFeed(){
  const rows=filteredReqs();
  document.getElementById('f-count').textContent=
    tf('f_count',{s:Math.min(50,rows.length),n:rows.length});
  const shown=rows.slice(0,50);
  document.getElementById('t-recent').innerHTML=shown.map((r,i)=>{
    const col=donutColors[r.model]||'#aab';
    return `<tr class="clickable" data-i="${i}"><td class="l fade">${r.ts.slice(5,19)}</td>
     <td class="l model"><span class="dot" style="background:${col}"></span>${esc(r.model)}</td>
     <td class="l fade" title="${esc(r.session_title)}">${esc(short(r.session_title,20))}</td>
     <td>${fmtTok(r.input)}</td><td>${fmtTok(r.output)}</td>
     <td>${fmtTok(r.cache_read)}</td><td class="fade">${fmtSpeed(r.tok_per_s)}</td>
     <td class="reqcost">${fmtCost(r.cost||0)}</td></tr>`;}).join('')
    ||`<tr><td colspan="8" class="empty" style="text-align:center;padding:22px">${t('f_empty')}</td></tr>`;
  bindReqRows('#t-recent',shown,8);
}
document.getElementById('f-model').onchange=e=>{filt.model=e.target.value;renderFeed();};
document.getElementById('f-session').oninput=e=>{filt.q=e.target.value.trim().toLowerCase();renderFeed();};
document.getElementById('f-date').onchange=e=>{filt.date=e.target.value;renderFeed();};
document.querySelectorAll('.chip').forEach(c=>c.onclick=()=>{
  document.querySelectorAll('.chip').forEach(x=>x.classList.toggle('on',x===c));
  filt.day=c.dataset.day;renderFeed();});

// ---------- header + settings actions ----------
function doRefresh(){
  if(native_)native_.postMessage({action:'refresh'});
  else fetch('/api/refresh').then(r=>r.json()).then(update);}
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
let kpiInit=false;
function kpis(d){
  const td=d.today,a=d.total,budget=d.settings&&d.settings.daily_budget;
  const warn=budget&&(td.cost||0)>budget;
  const speeds=d.requests.map(r=>r.tok_per_s).filter(v=>v!=null);
  const avgSpd=speeds.length?speeds.reduce((x,y)=>x+y,0)/speeds.length:0;
  const topM=d.by_model[0];
  const yday=d.by_day[1];  // by_day is desc; index 1 = yesterday
  const delta=yday&&yday.cost?( (t.cost-yday.cost)/yday.cost*100 ):null;
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

// ---------- token analytics ----------
let insightPeriod='7d';
const periodData=()=>{
  const a=DATA.analytics||{},p=a.periods||{};
  if(insightPeriod==='30d')return{data:p.last_30_days||{},change:p.comparison_30d_pct};
  if(insightPeriod==='mtd')return{data:p.month_to_date||{},change:null};
  if(insightPeriod==='all'){
    const active=DATA.by_day.length,total=DATA.total||{};
    return{data:{...total,active_days:active,calendar_days:active,
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
    ['an_avg_tokens_active',fmtTok(p.avg_tokens_per_active_day||0),t('an_tokens_per_request')+': '+fmtTok(economics.tokens_per_request||0)],
    ['an_month_projection',fmtCost(forecast.cost||0),fmtTok(forecast.tokens||0)+' tok'],
  ];
  document.getElementById('analysis-kpis').innerHTML=tiles.map(([label,value,extra],i)=>
    `<div class="card${i<2?' rise':''}"><div class="label">${esc(t(label))}</div><div class="value">${esc(value)}</div><div class="extra">${esc(extra)}</div></div>`).join('');
  const values=[
    ['an_cache_saved',fmtCost(economics.cache_savings_estimate||0)],
    ['an_output_input',economics.output_input_ratio==null?'—':`${economics.output_input_ratio.toFixed(2)}×`],
    ['an_tokens_per_request',fmtTok(economics.tokens_per_request||0)],
    ['an_cost_per_1k',economics.cost_per_1k_output==null?'—':fmtCost(economics.cost_per_1k_output)],
    ['an_trend',change==null?'—':`${change>0?'+':''}${change.toFixed(1)}%`],
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
    const select=document.getElementById('f-model');
    navigateTo('requests');select.value=row.dataset.model;filt.model=select.value;renderFeed();
  });
}
const analysisSeg=document.getElementById('seg-analysis');
analysisSeg.addEventListener('click',e=>{
  if(e.target.tagName!=='BUTTON')return;
  [...analysisSeg.querySelectorAll('button')].forEach(b=>b.classList.toggle('on',b===e.target));
  insightPeriod=e.target.dataset.v;segThumb(analysisSeg);drawInsights();
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
  const cb=document.getElementById('set-login');
  if(native_){cb.checked=!!m.login_item;cb.disabled=false;
    document.getElementById('set-login-label').textContent=
      cb.checked?t('st_login_on'):t('st_login');}
  else{cb.checked=false;cb.disabled=true;
    document.getElementById('set-login-label').textContent=t('st_login');}
}

function update(d){
  DATA=d;
  LANG=(d.settings&&d.settings.language)||'zh';
  applyTheme((d.settings&&d.settings.theme)||'system');
  applyLang();
  const updated=document.getElementById('updated');
  updated.textContent=new Date(d.generated_at).toLocaleTimeString(LOCALE[LANG]||'zh-CN',
    {hour:'2-digit',minute:'2-digit',hour12:false});
  updated.title=d.generated_at;
  kpis(d);refreshChart('tok',!started);refreshChart('cost',!started);
  drawMix();drawHit();drawDonut();
  drawHeat();renderTopSessions();drawScatter();
  renderModels();renderSessions();
  const sel=document.getElementById('f-model'),cur=sel.value;
  sel.innerHTML=`<option value="">${esc(t('f_all_models'))}</option>`+
    d.by_model.map(m=>`<option ${m.model===cur?'selected':''}>${esc(m.model)}</option>`).join('');
  filt.model=cur;renderFeed();fillSettings(d);drawInsights();
  ['seg-tok','seg-cost','seg-mix','seg-hit','seg-analysis'].forEach(id=>
    segThumb(document.getElementById(id)));
  if(!started)started=true;
}

setupChart('tok','tok');setupChart('cost','cost');
charts.mix={mode:'hour'};charts.hit={mode:'hour'};
wireSeg('mix',()=>drawMix());wireSeg('hit',()=>drawHit());
if(location.protocol.indexOf('http')===0){
  const refresh=async()=>update(await(await fetch('/api/usage')).json());
  refresh();setInterval(refresh,10000);}
</script>
</body></html>
"""
