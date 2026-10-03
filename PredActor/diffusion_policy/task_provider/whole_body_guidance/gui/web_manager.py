"""WebGuiManager — lightweight HTTP-server-based GUI for WholeBodyGuidance v2.

Serves a clean dark-themed HTML page on ``http://localhost:<port>`` and opens
the system browser.  Uses zero external dependencies (``http.server``,
``json``, ``threading``, ``webbrowser`` — all stdlib).

Why web instead of tkinter:
  - Native OS font rendering (Freetype/HarfBuzz) → clean on HiDPI
  - Runs in browser — completely separate GPU context from MuJoCo viewer
  - CSS gives us GNOME-quality theming with minimal code
  - Natural 1.5× scaling via CSS ``rem`` units
"""

from __future__ import annotations

import json
import threading
import time
import webbrowser
from http.server import HTTPServer, BaseHTTPRequestHandler
from typing import Optional

from ..guidance_activation_manager import GuidanceActivationManager
from ..guidance_types.vel_based import VelBasedGuidance
from ..guidance_types.pos_based import PosBasedGuidance
from ..guidance_types.point_reach import PointReachGuidance
from ..guidance_types.axes_vel import VxGuidance, VyGuidance, VzGuidance, WzGuidance
from ..guidance_types.hz_guide import HzGuidance
from ..guidance_types.wrist_guide import WristGuidance


# ── Inline HTML/CSS/JS (served as a single page) ──────────────────────────
# The page polls GET /api/state every 100ms for current values and POSTs
# to /api/cmd when any slider or switch changes.

_HTML = r"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1.0">
<title>Whole-Body Guidance v2</title>
<style>
:root{--bg:#1e1e1e;--surface:#2a2a2a;--border:#3a3a3a;
      --text:#e0e0e0;--muted:#999;--accent:#4CAF50;--blue:#8ab4f8;
      --danger:#e53935;--orange:#FF9800;font-size:12px} /* 1.0x scale */
body{font-family:Arial,Helvetica,sans-serif;background:var(--bg);color:var(--text);
     margin:0;padding:12px;min-width:420px;max-width:600px;margin:0 auto}
h1{font-size:1.15rem;font-weight:700;margin:0 0 8px;color:var(--blue)}
.panel{background:var(--surface);border:1px solid var(--border);border-radius:6px;
       padding:12px;margin-bottom:10px}
.panel-title{font-size:0.85rem;font-weight:700;color:var(--blue);margin:0 0 8px}
.switch-row{display:flex;flex-wrap:wrap;gap:8px;align-items:center}
.switch-group{display:flex;flex-direction:column;align-items:center;gap:2px}
.switch-group label{font-size:0.75rem;font-weight:600}
.switch-group .status{font-size:0.65rem}
.switch-group .status.on{color:var(--accent)}.switch-group .status.off{color:var(--muted)}
/* toggle switch */
.tgl{display:inline-block;position:relative;width:40px;height:22px;cursor:pointer}
.tgl input{opacity:0;width:0;height:0}
.tgl .slider{position:absolute;inset:0;background:#555;border-radius:11px;transition:.2s}
.tgl .slider::before{content:"";position:absolute;height:16px;width:16px;left:3px;bottom:3px;
    background:#fff;border-radius:50%;transition:.2s}
.tgl input:checked+.slider{background:var(--accent)}
.tgl input:checked+.slider::before{transform:translateX(18px)}
/* tabs */
.tabs{display:flex;gap:2px;margin-bottom:0}
.tab-btn{flex:1;padding:6px 12px;border:none;background:var(--surface);color:var(--muted);
    font-size:0.8rem;font-weight:600;cursor:pointer;border-radius:6px 6px 0 0;
    border:1px solid var(--border);border-bottom:none;transition:.15s}
.tab-btn.active{background:var(--bg);color:var(--text);border-color:var(--border)}
.tab-content{display:none;background:var(--bg);border:1px solid var(--border);
    border-top:none;border-radius:0 0 6px 6px;padding:10px 12px}
.tab-content.active{display:block}
/* sliders */
.slider-row{display:flex;align-items:center;gap:8px;margin-bottom:6px}
.slider-row .lbl{width:36px;font-size:0.8rem;font-weight:600;text-align:right}
.slider-row input[type=range]{flex:1;height:6px;-webkit-appearance:none;
    appearance:none;background:#444;border-radius:3px;outline:none}
.slider-row input[type=range]::-webkit-slider-thumb{-webkit-appearance:none;
    width:18px;height:18px;border-radius:50%;background:var(--accent);cursor:pointer}
.slider-row input[type=range]::-moz-range-thumb{width:18px;height:18px;
    border-radius:50%;background:var(--accent);cursor:pointer;border:none}
.slider-row .val{width:52px;font-size:0.75rem;text-align:right;font-variant-numeric:tabular-nums}
/* wrist sub-section */
.wrist-section{margin:6px 0 6px 12px;padding:6px 0 6px 12px;
    border-left:2px solid var(--border)}
.wrist-section .wrist-label{font-size:0.75rem;font-weight:600;margin-bottom:4px}
/* buttons */
.btn-row{display:flex;gap:6px;margin-top:6px}
.btn{padding:5px 14px;border:none;border-radius:4px;font-size:0.75rem;font-weight:600;
    cursor:pointer;transition:.15s}
.btn-dark{background:#555;color:#e0e0e0}.btn-dark:hover{background:#777}
.btn-accent{background:var(--accent);color:#fff}.btn-accent:hover{background:#66BB6A}
/* status bar */
.status-bar{background:var(--surface);border-radius:4px;padding:6px 10px;
    font-size:0.7rem;color:var(--muted);margin-top:8px}
.status-bar .key{color:var(--blue)}.status-bar .val{color:var(--text)}
.status-bar .on{color:var(--accent)}.status-bar .off{color:var(--danger)}
</style>
</head>
<body>
<h1>Whole-Body Guidance</h1>

<!-- Activation Manager -->
<div class="panel">
  <div class="panel-title">Activation Manager</div>
  <div class="switch-row" id="switches"></div>
</div>

<!-- Tabs -->
<div class="tabs" id="tab-buttons"></div>
<div id="tab-contents"></div>

<!-- Status bar -->
<div class="status-bar" id="status">Ready</div>

<script>
const GUIDANCES = /*GUIDANCES_JSON*/[];
const GROUPS = /*GROUPS_JSON*/{};

function el(id){return document.getElementById(id)}
function make(k,tag){var e=document.createElement(tag||'div');if(k)e.id=k;return e}

// -- switches --
function buildSwitches(){
  var row=el('switches');
  GUIDANCES.forEach(function(g,i){
    var grp=make(null);grp.className='switch-group';
    var lbl=document.createElement('label');lbl.textContent=g.name;
    var tgl=make(null);tgl.className='tgl';
    var inp=document.createElement('input');inp.type='checkbox';
    inp.checked=g.enabled;inp.dataset.idx=i;
    inp.onchange=function(){postCmd('toggle',{idx:parseInt(this.dataset.idx),enabled:this.checked})};
    var s=make(null);s.className='slider';
    tgl.appendChild(inp);tgl.appendChild(s);
    var st=make(null);st.className='status '+(g.enabled?'on':'off');
    st.textContent=g.enabled?'ON':'OFF';st.dataset.idx=i;
    grp.appendChild(lbl);grp.appendChild(tgl);grp.appendChild(st);
    row.appendChild(grp);
  });
  // Master toggle
  var mgrp=make(null);mgrp.className='switch-group';
  var mlbl=document.createElement('label');mlbl.textContent='All';
  mlbl.style.color='#8ab4f8';
  var mtgl=make(null);mtgl.className='tgl';
  var minp=document.createElement('input');minp.type='checkbox';minp.checked=true;minp.id='master-sw';
  minp.onchange=function(){
    var en=this.checked;GUIDANCES.forEach(function(g,i){g.enabled=en});
    postCmd('master_toggle',{enabled:en});
    refreshSwitches();
  };
  var ms=make(null);ms.className='slider';ms.style.background='#8ab4f8';
  mtgl.appendChild(minp);mtgl.appendChild(ms);
  var mst=make(null);mst.className='status on';mst.textContent='ALL';
  mgrp.appendChild(mlbl);mgrp.appendChild(mtgl);mgrp.appendChild(mst);
  row.appendChild(mgrp);
}

function refreshSwitches(){
  GUIDANCES.forEach(function(g,i){
    var st=document.querySelector('.status[data-idx="'+i+'"]');
    if(st){st.textContent=g.enabled?'ON':'OFF';st.className='status '+(g.enabled?'on':'off')}
  });
}

// -- tabs --
function buildTabs(){
  var btnRow=el('tab-buttons'), contentRow=el('tab-contents');
  var groups=groupGuidances();
  var first=true;
  for(var name in groups){
    var guides=groups[name];
    // button
    var btn=document.createElement('button');
    btn.className='tab-btn'+(first?' active':'');
    btn.textContent=name;
    btn.onclick=function(n){return function(){switchTab(n)}}(name);
    btnRow.appendChild(btn);
    // content
    var ct=make(null);ct.className='tab-content'+(first?' active':'');
    ct.dataset.tab=name;
    buildTabContent(ct,guides);
    contentRow.appendChild(ct);
    first=false;
  }
}

function groupGuidances(){
  var groups={};
  GUIDANCES.forEach(function(g){
    var key;
    if(g.kind==='vel') key='Velocity';
    else if(g.kind==='hz'||g.kind==='wrist') key='Position';
    else if(g.kind==='pr') key='PointReach';
    else key='Other';
    if(!groups[key]) groups[key]=[];
    groups[key].push(g);
  });
  return groups;
}

function buildTabContent(ct,guides){
  // collect by subtype
  var velGuides={},hzG=null,wristGs=[],prG=null;
  guides.forEach(function(g){
    if(g.kind==='vel') velGuides[g.name]=g;
    else if(g.kind==='hz') hzG=g;
    else if(g.kind==='wrist') wristGs.push(g);
    else if(g.kind==='pr') prG=g;
  });

  // velocity sliders
  ['vx','vy','vz','wz'].forEach(function(axis){
    var g=velGuides[axis];if(!g)return;
    var row=make(null);row.className='slider-row';
    var lbl=document.createElement('span');lbl.className='lbl';lbl.textContent=axis;
    var rng=document.createElement('input');rng.type='range';
    rng.min=g.range[0];rng.max=g.range[1];rng.step=0.01;rng.value=g.value||0;
    rng.dataset.idx=GUIDANCES.indexOf(g);
    rng.oninput=function(){postCmd('set_value',{idx:parseInt(this.dataset.idx),value:parseFloat(this.value)});
      this.nextSibling.textContent=parseFloat(this.value).toFixed(2)};
    var val=document.createElement('span');val.className='val';val.textContent=parseFloat(rng.value).toFixed(2);
    row.appendChild(lbl);row.appendChild(rng);row.appendChild(val);
    ct.appendChild(row);
  });
  if(Object.keys(velGuides).length>0){
    var btnRow=make(null);btnRow.className='btn-row';
    var rst=document.createElement('button');rst.className='btn btn-dark';rst.textContent='Reset';
    rst.onclick=function(){postCmd('reset_vel',{});['vx','vy','vz','wz'].forEach(function(a){
      var g2=velGuides[a];if(g2)g2.value=0})};
    btnRow.appendChild(rst);ct.appendChild(btnRow);
  }

  // hz slider
  if(hzG){
    var row=make(null);row.className='slider-row';
    var lbl=document.createElement('span');lbl.className='lbl';lbl.textContent='hz';
    var rng=document.createElement('input');rng.type='range';
    rng.min=hzG.z_range?hzG.z_range[0]:0.3;rng.max=hzG.z_range?hzG.z_range[1]:1.1;
    rng.step=0.01;rng.value=hzG.value||0.75;
    rng.dataset.idx=GUIDANCES.indexOf(hzG);
    rng.oninput=function(){postCmd('set_hz',{idx:parseInt(this.dataset.idx),value:parseFloat(this.value)});
      this.nextSibling.textContent=parseFloat(this.value).toFixed(2)};
    var val=document.createElement('span');val.className='val';val.textContent=parseFloat(rng.value).toFixed(2);
    row.appendChild(lbl);row.appendChild(rng);row.appendChild(val);
    ct.appendChild(row);
  }

  // wrist sliders
  wristGs.forEach(function(wg){
    var ws=make(null);ws.className='wrist-section';
    var wlbl=document.createElement('div');wlbl.className='wrist-label';
    wlbl.textContent=(wg.side||'?')+' wrist';
    var tgl=make(null);tgl.className='tgl';tgl.style.display='inline-block';tgl.style.marginLeft='8px';
    var inp=document.createElement('input');inp.type='checkbox';inp.checked=wg.enabled;
    inp.dataset.idx=GUIDANCES.indexOf(wg);
    inp.onchange=function(){postCmd('toggle',{idx:parseInt(this.dataset.idx),enabled:this.checked})};
    var s=make(null);s.className='slider';tgl.appendChild(inp);tgl.appendChild(s);
    wlbl.appendChild(tgl);ws.appendChild(wlbl);
    var sides={'dx':'X','dy':'Y','dz':'Z'};
    for(var k in sides){if(!wg[k])continue;
      var rw=make(null);rw.className='slider-row';
      var lb=document.createElement('span');lb.className='lbl';lb.textContent=sides[k];lb.style.width='20px';
      var rng=document.createElement('input');rng.type='range';
      rng.min=wg[k+'_range']?wg[k+'_range'][0]:-0.5;rng.max=wg[k+'_range']?wg[k+'_range'][1]:0.5;
      rng.step=0.01;rng.value=wg[k]||0;
      rng.dataset.idx=GUIDANCES.indexOf(wg);rng.dataset.axis=k;
      rng.oninput=function(){postCmd('set_wrist',{idx:parseInt(this.dataset.idx),
        axis:this.dataset.axis,value:parseFloat(this.value)});
        this.nextSibling.textContent=parseFloat(this.value).toFixed(2)};
      var vl=document.createElement('span');vl.className='val';vl.textContent=parseFloat(rng.value).toFixed(2);
      rw.appendChild(lb);rw.appendChild(rng);rw.appendChild(vl);ws.appendChild(rw);
    }
    ct.appendChild(ws);
  });

  // point-reach sliders
  if(prG){
    ['target_x','target_y','target_z'].forEach(function(axis,i){
      var row=make(null);row.className='slider-row';
      var lbl=document.createElement('span');lbl.className='lbl';
      lbl.textContent=['tX','tY','tZ'][i];
      var rng=document.createElement('input');rng.type='range';
      var defs=[[-3,3,0],[-3,3,0],[0,2,0.8]];
      rng.min=defs[i][0];rng.max=defs[i][1];rng.step=0.01;
      rng.value=prG[axis]||defs[i][2];
      rng.dataset.axis=axis;
      rng.oninput=function(){postCmd('set_pr_target',{axis:parseInt(this.dataset.axis),value:parseFloat(this.value)});
        this.nextSibling.textContent=parseFloat(this.value).toFixed(2)};
      var val=document.createElement('span');val.className='val';val.textContent=parseFloat(rng.value).toFixed(2);
      row.appendChild(lbl);row.appendChild(rng);row.appendChild(val);
      ct.appendChild(row);
    });
  }
}

function switchTab(name){
  document.querySelectorAll('.tab-btn').forEach(function(b){b.classList.toggle('active',b.textContent===name)});
  document.querySelectorAll('.tab-content').forEach(function(c){c.classList.toggle('active',c.dataset.tab===name)});
}

// -- polling --
function pollState(){
  fetch('/api/state').then(function(r){return r.json()}).then(function(s){
    el('status').innerHTML=s.status_html||'Ready';
    if(s.guidances){
      s.guidances.forEach(function(gs,i){if(i<GUIDANCES.length){
        GUIDANCES[i].enabled=gs.enabled;GUIDANCES[i].value=gs.value;
      }});
      refreshSwitches();
    }
  }).catch(function(){}).finally(function(){setTimeout(pollState,100)});
}

// -- commands --
function postCmd(cmd,data){
  fetch('/api/cmd',{method:'POST',headers:{'Content-Type':'application/json'},
    body:JSON.stringify({cmd:cmd,data:data})}).catch(function(){});
}

// -- init --
buildSwitches();buildTabs();pollState();
</script>
</body>
</html>"""


# ── Request handler ───────────────────────────────────────────────────────

class _Handler(BaseHTTPRequestHandler):
    """Serves the single-page app and the REST API endpoints."""

    def log_message(self, fmt, *args):
        pass  # silence access logs

    def do_GET(self):
        if self.path == '/' or self.path == '/index.html':
            self._serve_html()
        elif self.path == '/api/state':
            self._serve_state()
        else:
            self.send_error(404)

    def do_POST(self):
        if self.path == '/api/cmd':
            self._handle_cmd()
        else:
            self.send_error(404)

    def _serve_html(self):
        manager = self.server.manager  # type: WebGuiManager
        guidances_json, groups_json = manager._build_guidances_json()
        html = _HTML.replace('/*GUIDANCES_JSON*/[]', json.dumps(guidances_json))
        html = html.replace('/*GROUPS_JSON*/{}', json.dumps(groups_json))
        data = html.encode('utf-8')
        self.send_response(200)
        self.send_header('Content-Type', 'text/html; charset=utf-8')
        self.send_header('Content-Length', str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def _serve_state(self):
        manager = self.server.manager
        state = manager._build_state()
        data = json.dumps(state).encode('utf-8')
        self.send_response(200)
        self.send_header('Content-Type', 'application/json')
        self.send_header('Content-Length', str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def _handle_cmd(self):
        length = int(self.headers.get('Content-Length', 0))
        body = self.rfile.read(length)
        try:
            msg = json.loads(body)
        except json.JSONDecodeError:
            self.send_error(400)
            return
        manager = self.server.manager
        manager._dispatch_cmd(msg.get('cmd', ''), msg.get('data', {}))
        self.send_response(200)
        self.send_header('Content-Length', '2')
        self.end_headers()
        self.wfile.write(b'{}')


# ── Manager ───────────────────────────────────────────────────────────────

class WebGuiManager:
    """HTTP-server-based GUI manager for WholeBodyGuidance v2.

    Starts a lightweight HTTP server on a random port, opens the system
    browser, and serves a clean dark-themed SPA with sliders, switches,
    tabs, and a status bar.
    """

    def __init__(
        self,
        activation_manager: GuidanceActivationManager,
        gui_enabled: bool = True,
    ):
        self._manager = activation_manager
        self._gui_enabled = gui_enabled
        self._server: Optional[HTTPServer] = None
        self._port: int = 0
        self._thread: Optional[threading.Thread] = None
        self._running = False

    # ── JSON builders (called from request handler) ───────────────────────

    def _build_guidances_json(self) -> tuple[list, dict]:
        """Build initial guidance state for the HTML page."""
        items = []
        for g in self._manager.guidances:
            entry = {
                'name': g.guidance_name,
                'enabled': g.activation.enabled,
                'value': 0.0,
                'kind': 'other',
            }

            if isinstance(g, (VxGuidance, VyGuidance, VzGuidance, WzGuidance)):
                entry['kind'] = 'vel'
                entry['value'] = g.get_value()
                entry['range'] = list(g.value_range)
            elif isinstance(g, PointReachGuidance):
                entry['kind'] = 'pr'
                pt = g.get_point_target()
                entry['target_x'] = pt['x']
                entry['target_y'] = pt['y']
                entry['target_z'] = pt['z']
            elif isinstance(g, HzGuidance):
                entry['kind'] = 'hz'
                entry['value'] = g.get_target()
                entry['z_range'] = list(g.z_range)
            elif isinstance(g, WristGuidance):
                entry['kind'] = 'wrist'
                entry['side'] = g.side
                dx, dy, dz = g.get_target()
                entry['dx'] = dx; entry['dy'] = dy; entry['dz'] = dz
                entry['dx_range'] = list(g.dx_range)
                entry['dy_range'] = list(g.dy_range)
                entry['dz_range'] = list(g.dz_range)

            items.append(entry)

        return items, {}

    def _build_state(self) -> dict:
        """Build current state JSON for polling."""
        gs_list = []
        for g in self._manager.guidances:
            gs = {'name': g.guidance_name, 'enabled': g.activation.enabled,
                  'value': 0.0}
            if isinstance(g, (VxGuidance, VyGuidance, VzGuidance, WzGuidance)):
                gs['value'] = g.get_value()
            elif isinstance(g, HzGuidance):
                gs['value'] = g.get_target()
            gs_list.append(gs)

        # Status bar HTML
        parts = []
        for g in self._manager.guidances:
            en = g.activation.enabled
            cls = 'on' if en else 'off'
            parts.append(f'<span class="key">[{g.guidance_name}]</span> <span class="{cls}">{"on" if en else "off"}</span>')
        pr = self._manager.get_point_reach_guidance()
        if pr is not None:
            pt = pr.get_point_target()
            if pt.get('has_world_data'):
                parts.append(f'tgt=<span class="val">({pt["x"]:+.1f},{pt["y"]:+.1f},{pt["z"]:+.2f})</span>')
            else:
                parts.append('<span class="off">pelvis=?</span>')

        return {'guidances': gs_list, 'status_html': '  |  '.join(parts)}

    def _dispatch_cmd(self, cmd: str, data: dict) -> None:
        """Handle a command from the web page."""
        guidances = self._manager.guidances

        if cmd == 'toggle':
            idx = int(data.get('idx', -1))
            if 0 <= idx < len(guidances):
                self._manager.set_guidance_enabled(idx, bool(data.get('enabled', True)))

        elif cmd == 'master_toggle':
            self._manager.set_all_enabled(bool(data.get('enabled', True)))

        elif cmd == 'set_value':
            idx = int(data.get('idx', -1))
            val = float(data.get('value', 0))
            if 0 <= idx < len(guidances):
                g = guidances[idx]
                if isinstance(g, (VxGuidance, VyGuidance, VzGuidance, WzGuidance)):
                    g.set_value(val)

        elif cmd == 'reset_vel':
            for g in guidances:
                if isinstance(g, (VxGuidance, VyGuidance, VzGuidance, WzGuidance)):
                    g.set_value(0.0)

        elif cmd == 'set_hz':
            idx = int(data.get('idx', -1))
            val = float(data.get('value', 0))
            if 0 <= idx < len(guidances):
                g = guidances[idx]
                if isinstance(g, HzGuidance):
                    g.set_target(val)

        elif cmd == 'set_wrist':
            idx = int(data.get('idx', -1))
            axis = data.get('axis', 'dx')
            val = float(data.get('value', 0))
            if 0 <= idx < len(guidances):
                g = guidances[idx]
                if isinstance(g, WristGuidance):
                    cur = list(g.get_target())
                    idx_map = {'dx': 0, 'dy': 1, 'dz': 2}
                    cur[idx_map.get(axis, 0)] = val
                    g.set_target(*cur)

        elif cmd == 'set_pr_target':
            axis = int(data.get('axis', 0))
            val = float(data.get('value', 0))
            pr = self._manager.get_point_reach_guidance()
            if pr is not None:
                t = list(pr.get_point_target().values())
                if axis == 0:
                    pr.set_target(val, t[1] if len(t) > 1 else 0, t[2] if len(t) > 2 else 0.8)
                elif axis == 1:
                    pr.set_target(t[0] if t else 0, val, t[2] if len(t) > 2 else 0.8)
                elif axis == 2:
                    pr.set_target(t[0] if t else 0, t[1] if len(t) > 1 else 0, val)

    # ── Lifecycle ─────────────────────────────────────────────────────────

    def start(self) -> None:
        if not self._gui_enabled or self._running:
            return
        self._running = True

        # Thread 1: HTTP server
        self._srv_thread = threading.Thread(target=self._run_server, daemon=True)
        self._srv_thread.start()

        # Thread 2: GUI window (pywebview or browser)
        self._gui_thread = threading.Thread(target=self._run_gui, daemon=True)
        self._gui_thread.start()

    def stop(self) -> None:
        self._running = False
        try:
            import webview as _wv
            for w in list(_wv.windows):
                _wv.destroy_window(w)
        except Exception:
            pass
        try:
            if self._server is not None:
                self._server.shutdown()
        except Exception:
            pass

    def _run_server(self) -> None:
        """HTTP server loop — runs on daemon thread."""
        for port in range(8765, 8790):
            try:
                self._server = HTTPServer(('127.0.0.1', port), _Handler)
                self._server.manager = self
                self._server.timeout = 0.5
                self._port = port
                break
            except OSError:
                continue
        else:
            self._running = False
            return

        while self._running:
            try:
                self._server.handle_request()
            except Exception:
                break

    def _run_gui(self) -> None:
        """Open a clean window: Chromium app-mode, or pywebview, or browser."""
        import time as _t, subprocess, sys

        for _ in range(20):
            if self._port != 0:
                break
            _t.sleep(0.1)
        if self._port == 0:
            print("[WholeBodyGuidance] Server failed to start", flush=True)
            return

        url = f'http://localhost:{self._port}'
        print(f"[WholeBodyGuidance] Web GUI → {url}", flush=True)

        # Try strategies in order: app-mode browser > pywebview > webbrowser
        opened = False

        # 1. Chromium/Chrome app-mode: clean window, no tabs/address bar
        for browser in ['google-chrome', 'chromium', 'chromium-browser']:
            try:
                subprocess.Popen([browser, f'--app={url}', '--window-size=620,820'],
                                 stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                print(f"[WholeBodyGuidance] Opened in {browser} app-mode", flush=True)
                opened = True
                break
            except FileNotFoundError:
                continue

        # 2. pywebview subprocess (native GTK window)
        if not opened:
            wv_script = (
                "import sys, webview; "
                f"webview.create_window('Whole-Body Guidance v2', '{url}', "
                "width=620, height=820, resizable=True, confirm_close=False); "
                "webview.start(gui='gtk')"
            )
            try:
                subprocess.Popen([sys.executable, '-c', wv_script],
                                 stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                print("[WholeBodyGuidance] Opened in pywebview (native GTK window)", flush=True)
                opened = True
            except Exception:
                pass

        # 3. System browser
        if not opened:
            import webbrowser
            webbrowser.open(url)
            print("[WholeBodyGuidance] Opened in system browser", flush=True)

        # Wait until stopped
        while self._running:
            _t.sleep(0.5)

        print("[WholeBodyGuidance] Web GUI exited", flush=True)

    @property
    def root_tk(self):
        return None  # no Tk root in web mode
