const $ = (s) => document.querySelector(s);
const FALLBACK_JOY_MAPPING={name:'Xbox One / Series (xbox_new fallback)',active_commands:['dpad_x','dpad_y','l2','l1'],axes:[['left_x','Left Stick X'],['left_y','Left Stick Y'],['right_x','Right Stick X'],['right_y','Right Stick Y'],['r2','R2 Trigger'],['l2','L2 Trigger'],['dpad_x','D-Pad X'],['dpad_y','D-Pad Y']].map(([logical,label])=>({logical,label})),buttons:[['south','A'],['east','B'],['west','X'],['north','Y'],['l1','LB'],['r1','RB'],['l3','L3'],['r3','R3']].map(([logical,label])=>({logical,label}))};
const command = async (body) => {
  const started = performance.now();
  const response = await fetch('/api/command', {method:'POST', headers:{'content-type':'application/json'}, body:JSON.stringify({protocol:1,...body})});
  const raw = await response.text();
  let result;
  try { result = JSON.parse(raw); }
  catch (_) { throw new Error(`Command response was not JSON (HTTP ${response.status}): ${raw.slice(0, 160)}`); }
  if (!response.ok) {
    const detail = result.detail;
    throw new Error(typeof detail === 'string' ? detail : detail?.message || `Command rejected (HTTP ${response.status})`);
  }
  document.body.dataset.lastCommandLatencyMs = (performance.now() - started).toFixed(2);
  return result;
};
let latest = null, mode = 'textop', frameReady = false, reconnectTimer = 0, selectedGuidance = 0;
let activationSchema = '', joyMappingSchema = '';
let actionError = '', joyError = '', perturbGeneration = null;
let interpolationSchema = '', interpolationTerms = [], interpolationDirty = false;
let interpolationRevision = 0, modeInitialized = false;
const TEXTURE_DENSITY_DEFAULT=75, TEXTURE_DENSITY_KEY='predactor.textureDensity.v2';
const THEME_KEY='predactor.colorTheme.v1';
const clampTextureDensity=value=>Math.max(40,Math.min(100,Number.isFinite(Number(value))?Number(value):TEXTURE_DENSITY_DEFAULT));
const applyTextureDensity=value=>{const density=clampTextureDensity(value),pitch=7.2-density*.04;document.documentElement.style.setProperty('--texture-pitch',`${pitch.toFixed(2)}px`);document.documentElement.dataset.textureDensity=String(density);$('#texture-density').value=String(density);$('#texture-density-out').value=`${density}%`;return density};
let initialTextureDensity=TEXTURE_DENSITY_DEFAULT;try{initialTextureDensity=clampTextureDensity(localStorage.getItem(TEXTURE_DENSITY_KEY))}catch(_error){}
const brandLockup=$('.brand-lockup');
const applyColorTheme=value=>{const theme=value==='light'?'light':'dark';document.documentElement.dataset.theme=theme;document.documentElement.style.colorScheme=theme;$('#theme-light').checked=theme==='light';$('#theme-mode').textContent=theme==='light'?'Light':'Dark';if(brandLockup)brandLockup.src=theme==='light'?brandLockup.dataset.lightSrc:brandLockup.dataset.darkSrc;window.dispatchEvent(new CustomEvent('predactor-theme-change',{detail:{theme}}));return theme};
let initialTheme='dark';try{initialTheme=localStorage.getItem(THEME_KEY)==='light'?'light':'dark'}catch(_error){}
window.addEventListener('mujoco-frame',()=>{frameReady=true;if(latest)render(latest)});
window.addEventListener('mujoco-error',event=>error(event.detail || 'MuJoCo viewport failed'));
const renderError = () => { $('#command-error').textContent = actionError || joyError; };
const error = (message='') => { actionError = message; renderError(); };

const setClipMode = nextMode => {
  mode = nextMode === 'interp' ? 'interp' : 'textop';
  document.querySelectorAll('.tabs button').forEach(button=>{
    const active=button.dataset.mode===mode;
    button.classList.toggle('active',active);
    button.setAttribute('aria-selected',String(active));
  });
  $('#text-form').hidden=mode!=='textop';
  $('#interp-form').hidden=mode!=='interp';
  $('.text-console').classList.toggle('interp-active',mode==='interp');
};
const interpolationBounds=term=>{
  const inferred=term.text_a===null||term.text_b===null?[0,1]:[-1,1];
  const lower=Number(term.weight_min),upper=Number(term.weight_max);
  return Number.isFinite(lower)&&Number.isFinite(upper)&&lower<upper?[lower,upper]:inferred;
};
const formatInterpolationWeight=(value,lower)=>`${lower<0&&Number(value)>0?'+':''}${Number(value).toFixed(2)}`;
const cloneInterpolationTerms=terms=>terms.map(term=>{
  const [weight_min,weight_max]=interpolationBounds(term);
  const suppliedDefault=Number(term.weight_default);
  const weight_default=Number.isFinite(suppliedDefault)&&suppliedDefault>=weight_min&&suppliedDefault<=weight_max?suppliedDefault:0;
  return {text_a:term.text_a,text_b:term.text_b,weight:Number(term.weight),weight_min,weight_max,weight_default};
});
function renderInterpolationTerms() {
  const container=$('#interp-terms'),template=$('#interp-term-template');
  container.replaceChildren(...interpolationTerms.map((term,index)=>{
    const row=template.content.firstElementChild.cloneNode(true);
    row.dataset.index=String(index);row.querySelector('.interp-index').textContent=String(index+1).padStart(2,'0');
    for(const side of ['a','b']){
      const value=term[`text_${side}`],input=row.querySelector(`[data-endpoint="${side}"]`),zero=row.querySelector(`[data-zero="${side}"]`);
      const isZero=value===null;input.disabled=isZero;input.value=isZero?'':value;
      input.placeholder=isZero?'ZERO VECTOR':'Motion prompt';zero.classList.toggle('active',isZero);
      zero.setAttribute('aria-pressed',String(isZero));
    }
    const weight=row.querySelector('[data-weight]'),[lower,upper]=interpolationBounds(term),signed=lower<0;
    weight.min=String(lower);weight.max=String(upper);weight.value=String(term.weight);
    weight.setAttribute('aria-label',signed?'Signed semantic direction':'Zero-anchor semantic weight');
    weight.title=signed?'Signed direction: -1 toward start, 0 neutral, +1 toward end':'Zero-anchor weight: 0 neutral, +1 applies the one-sided direction';
    row.querySelector('label span').textContent=signed?'DIRECTION':'WEIGHT';
    const output=row.querySelector('output'),defaultLabel=formatInterpolationWeight(term.weight_default??0,lower);
    output.value=formatInterpolationWeight(term.weight,lower);output.tabIndex=0;output.setAttribute('role','button');
    output.title=`Double-click or press Enter to reset to ${defaultLabel}`;
    output.setAttribute('aria-label',`Reset ${signed?'direction':'weight'} to default ${defaultLabel}`);
    row.querySelector('.interp-remove').disabled=interpolationTerms.length===1;
    return row;
  }));
  $('#interp-add').disabled=interpolationTerms.length>=16;
}
function hydrateInterpolation(snapshot, force=false) {
  const available=!!snapshot?.available, terms=available&&Array.isArray(snapshot.terms)?snapshot.terms:[];
  $('#interp-form').classList.toggle('unavailable',!available);
  $('#interp-add').disabled=!available||terms.length>=16;
  if(!available){if(force||interpolationSchema!=='unavailable'){$('#interp-terms').innerHTML='<p class="empty">Interpolation provider unavailable.</p>';interpolationTerms=[];interpolationSchema='unavailable'}return}
  const schema=JSON.stringify({normalize:!!snapshot.normalize,terms});
  if(!force&&(interpolationDirty||schema===interpolationSchema))return;
  interpolationSchema=schema;interpolationTerms=cloneInterpolationTerms(terms);renderInterpolationTerms();
  $('#interp-summary').textContent=`${snapshot.normalize?'NORMALIZED':'RAW'} VECTOR SUM · ${terms.length} TERMS`;
}
function readInterpolationTerms() {
  return [...document.querySelectorAll('.interp-term')].map(row=>{
    const endpoint=side=>{const input=row.querySelector(`[data-endpoint="${side}"]`);return input.disabled?null:input.value.trim()};
    return {text_a:endpoint('a'),text_b:endpoint('b'),weight:Number(row.querySelector('[data-weight]').value)};
  });
}
const captureInterpolationTerms=()=>readInterpolationTerms().map((term,index)=>({
  ...interpolationTerms[index],...term,
}));
async function applyInterpolationTerms({live=false, rebuild=!live}={}) {
  const terms=readInterpolationTerms();
  if(terms.some(term=>(term.text_a!==null&&!term.text_a)||(term.text_b!==null&&!term.text_b))){
    hydrateInterpolation(latest?.text?.interpolation,true);
    error('Prompts must contain text or be explicitly set to the zero vector');return false
  }
  const revision=++interpolationRevision;interpolationDirty=true;
  try{
    const result=await command({command:'set_interp_terms',terms,live});
    if(revision!==interpolationRevision)return true;
    interpolationDirty=false;
    const accepted=result.text?.interpolation;
    if(rebuild)hydrateInterpolation(accepted,true);
    else{interpolationSchema=JSON.stringify({normalize:!!accepted?.normalize,terms:accepted?.terms||[]});interpolationTerms=cloneInterpolationTerms(accepted?.terms||terms)}
    error();return true;
  }catch(ex){
    if(revision===interpolationRevision){interpolationDirty=false;hydrateInterpolation(latest?.text?.interpolation,true);error(ex.message)}
    return false;
  }
}
async function resetInterpolationTerm(row) {
  const index=Number(row.dataset.index),term=interpolationTerms[index],weightDefault=Number(term?.weight_default);
  if(!Number.isFinite(weightDefault))return false;
  clearTimeout(interpTimer);term.weight=weightDefault;
  const weight=row.querySelector('[data-weight]'),output=row.querySelector('output');
  weight.value=String(weightDefault);output.value=formatInterpolationWeight(weightDefault,Number(weight.min));
  return applyInterpolationTerms();
}

function render(state) {
  latest = state;
  $('#connection').textContent = state.error ? 'DEGRADED' : state.status.toUpperCase();
  $('#step').textContent = state.step; $('#fps').textContent = state.fps.toFixed(1);
  $('#pause').classList.toggle('active', state.paused);
  $('#pause').innerHTML = state.paused ? '&#9654;' : '&#10074;&#10074;';
  $('#pause').setAttribute('aria-label', state.paused ? 'Resume evaluation' : 'Pause evaluation');
  const simulation=state.simulation||{auto_reset:true,reset_pending:false};
  $('#sim-auto-reset').checked=!!simulation.auto_reset;
  $('#sim-reset').disabled=!!simulation.reset_pending;
  $('#sim-reset').classList.toggle('pending',!!simulation.reset_pending);
  $('#sim-reset').title=simulation.reset_pending?'Reset pending':'Reset MuJoCo robot';
  const perturbStatus=$('#perturb-status');
  if(!state.perturb?.enabled)perturbStatus.textContent='PERTURB OFF';
  else if(state.perturb.active){const vector=state.perturb.mode==='force'?state.perturb.force:state.perturb.torque,unit=state.perturb.mode==='force'?'N':'Nm',magnitude=Math.hypot(...(vector||[]));perturbStatus.textContent=`${state.perturb.mode.toUpperCase()} ACTIVE · ${magnitude.toFixed(1)} ${unit} · #${state.perturb.sequence}`}
  else if(!perturbStatus.textContent.includes('SELECTED'))perturbStatus.textContent='PERTURB READY';
  if(perturbGeneration===null)perturbGeneration=state.perturb?.generation;
  else if(perturbGeneration!==state.perturb?.generation){perturbGeneration=state.perturb?.generation;window.dispatchEvent(new Event('mujoco-perturb-clear'))}
  if(state.paused||state.status==='stopped')window.dispatchEvent(new Event('mujoco-perturb-clear'));
  if(Number.isInteger(state.perturb?.sequence))window.dispatchEvent(new CustomEvent('mujoco-perturb-sequence',{detail:state.perturb.sequence}));
  $('#wbg-enabled').checked = state.wbg.enabled;
  const destination = state.destination || {available:false, enabled:false, target:null, status:'unavailable'};
  // The browser MuJoCo renderer owns the world-space target ball. Keep this
  // event separate from the binary simulation stream so marker updates do not
  // change the snapshot protocol or model handshake.
  window.dispatchEvent(new CustomEvent('mujoco-destination', {detail: destination}));
  $('#destination-enabled').checked = !!destination.enabled;
  $('#destination-enabled-label').textContent = destination.enabled ? 'On' : 'Off';
  const target = destination.target || [];
  ['x','y','z'].forEach((axis,index)=>{
    const input = $(`#destination-${axis}`);
    if (document.activeElement !== input && Number.isFinite(Number(target[index]))) input.value = Number(target[index]).toFixed(2);
  });
  const distance = Number.isFinite(destination.distance) ? ` · ${destination.distance.toFixed(2)} m` : '';
  const heading = Number.isFinite(destination.heading_error) ? ` · ${(destination.heading_error * 180 / Math.PI).toFixed(0)}°` : '';
  const status = destination.available ? `${String(destination.status || 'idle').replaceAll('_',' ')}${distance}${heading}` : 'Unavailable';
  $('#destination-status').value = status;
  $('#destination-status').className = destination.status || '';
  const command = destination.command || {};
  const commandText = destination.available
    ? `vx ${Number(command.vx || 0).toFixed(2)} · vy ${Number(command.vy || 0).toFixed(2)} · wz ${Number(command.wz || 0).toFixed(2)}`
    : 'Command unavailable';
  $('#destination-command').textContent = commandText;
  const config = destination.config || {};
  document.querySelectorAll('[data-destination-config]').forEach(input=>{
    const key=input.dataset.destinationConfig;
    if (document.activeElement !== input && Number.isFinite(Number(config[key]))) input.value=Number(config[key]).toFixed(2);
  });
  document.querySelectorAll('[data-destination-range]').forEach(input=>{
    const bounds=config[input.dataset.destinationRange],index=Number(input.dataset.rangeIndex);
    if(document.activeElement!==input&&Array.isArray(bounds)&&Number.isFinite(Number(bounds[index])))input.value=Number(bounds[index]).toFixed(2);
  });
  $('#current-motion').textContent = state.text.current || '--';
  if(!modeInitialized){setClipMode(state.text.mode);modeInitialized=true}
  hydrateInterpolation(state.text.interpolation);
  renderActivation(state.wbg.activation, state.wbg.enabled);
  document.querySelectorAll('.source-select button').forEach(button=>button.classList.toggle('active',button.dataset.source===state.source));
  const joyPath=state.joy.device_path||'auto',joyName=joyPath.split('/').pop();
  $('#joy-status').textContent = state.joy.connected ? `CONNECTED · ${joyName}` : `SEARCHING · ${joyName}`;
  $('#joy-status').title=state.joy.connection_error?`${joyPath}: ${state.joy.connection_error}`:joyPath;
  ensureJoyMapping(state.joy.mapping||FALLBACK_JOY_MAPPING);
  document.querySelectorAll('.sliders input').forEach(input => {
    const key=input.dataset.key, value = key === 'kp' ? state.wbg.kp : state.wbg.values[key];
    const range=state.wbg.ranges?.[key];
    if(Array.isArray(range)&&range.length===2){input.min=range[0];input.max=range[1]}
    if (document.activeElement !== input && Number.isFinite(value)) input.value=value;
    $(`#${key}-out`).value=Number(input.value).toFixed(2);
  });
  const axes=state.joy.axes || {};
  setStick('left', axes.left_x || 0, axes.left_y || 0); setStick('right', axes.right_x || 0, axes.right_y || 0);
  const trigger=value=>Math.max(0,Math.min(1,((Number.isFinite(value)?value:-1)+1)/2));
  $('#lt').style.height=`${trigger(axes.l2)*100}%`;
  $('#rt').style.height=`${trigger(axes.r2)*100}%`;
  const dx=state.joy.dpad?.[0]||0, dy=state.joy.dpad?.[1]||0;
  const dpadDirections={up:dy<-.5,right:dx>.5,down:dy>.5,left:dx<-.5};
  document.querySelectorAll('.dpad [data-direction]').forEach(node=>node.classList.toggle('on',dpadDirections[node.dataset.direction]));
  const buttons=state.joy.buttons || {};
  document.querySelectorAll('[data-button]').forEach(node=>node.classList.toggle('on',!!buttons[node.dataset.button]));
  document.querySelectorAll('#mapped-axes [data-axis]').forEach(node=>{
    const value=Number.isFinite(axes[node.dataset.axis])?axes[node.dataset.axis]:0;
    node.querySelector('b').style.width=`${(value+1)*50}%`;
    node.querySelector('output').value=value.toFixed(2);
  });
  joyError=state.joy.command_error || ''; renderError();
  const history=state.text.history || [];
  $('#history').innerHTML = history.length ? history.map(item=>`<article><small>${item.mode.toUpperCase()}</small><p>${escapeHtml(item.text)}</p><time>${item.latency_ms.toFixed(1)} ms</time></article>`).join('') : '<p class="empty">Commands will appear here.</p>';
  const viewport=$('#viewport-state');
  if (state.paused) { viewport.classList.remove('hidden'); viewport.innerHTML='<span>PAUSED</span>'; }
  else if (frameReady || $('#sim-canvas').dataset.phase === 'rendering') viewport.classList.add('hidden');
  else { viewport.classList.remove('hidden'); viewport.innerHTML='<span class="spinner"></span> WAITING FOR SIMULATOR'; }
}
function ensureJoyMapping(mapping) {
  const schema=JSON.stringify(mapping || null);if(schema===joyMappingSchema)return;joyMappingSchema=schema;
  const axes=new Map((mapping?.axes||[]).map(item=>[item.logical,item]));
  const activeCommands=new Set(mapping?.active_commands||[]), hiddenRaw=new Set(['select','start','button10','button11','button13','button14','back']);
  const visibleButton=item=>activeCommands.has(item.logical)||!hiddenRaw.has(item.logical.toLowerCase().replaceAll('_',''))&&!hiddenRaw.has(item.label.toLowerCase().replaceAll(' ',''));
  const buttons=new Map((mapping?.buttons||[]).filter(visibleButton).map(item=>[item.logical,item]));
  document.querySelectorAll('.triggers [data-axis]').forEach(node=>node.hidden=!axes.has(node.dataset.axis));
  document.querySelectorAll('.stick').forEach(node=>{const side=node.dataset.stick;node.hidden=!axes.has(`${side}_x`)&&!axes.has(`${side}_y`)});
  $('.dpad').hidden=!axes.has('dpad_x')&&!axes.has('dpad_y');
  const face=['south','east','west','north'];
  [...$('#buttons').children].forEach((node,index)=>{const item=buttons.get(face[index]);node.dataset.button=face[index];node.hidden=!item;if(item)node.title=item.label});
  document.querySelectorAll('.shoulders [data-button],.stick [data-button]').forEach(node=>{const item=buttons.get(node.dataset.button);node.hidden=!item;if(item)node.title=item.label});
  const coreButtons=new Set([...face,'l1','r1','l3','r3']);
  $('#mapped-buttons').innerHTML=[...buttons.values()].filter(item=>!coreButtons.has(item.logical)).map(item=>`<i data-button="${escapeHtml(item.logical)}" title="${escapeHtml(item.label)}">${escapeHtml(item.label)}</i>`).join('');
  const coreAxes=new Set(['left_x','left_y','right_x','right_y','l2','r2','dpad_x','dpad_y']);
  $('#mapped-axes').innerHTML=[...axes.values()].filter(item=>!coreAxes.has(item.logical)).map(item=>`<label data-axis="${escapeHtml(item.logical)}" title="${escapeHtml(item.label)}"><span>${escapeHtml(item.label)}</span><i><b></b></i><output>0.00</output></label>`).join('');
  $('#joy-help-content').innerHTML=`<p><b>${escapeHtml(mapping?.name||'No active mapping')}</b></p><dl><dt>D-pad</dt><dd>Up stand · Right walk · Down jog · Left squat down</dd><dt>L2</dt><dd>Released Kp 1 · Pressed Kp 0</dd><dt>LB</dt><dd>Toggle whole-body guidance</dd></dl><h3>Axes</h3><p>${[...axes.values()].map(item=>escapeHtml(item.label)).join(' · ')||'None'}</p><h3>Buttons</h3><p>${[...buttons.values()].map(item=>escapeHtml(item.label)).join(' · ')||'None'}</p>`;
}
function renderActivation(activation, masterEnabled) {
  const panel=$('#activation-manager'), guidances=activation?.guidances || [];
  panel.hidden=!masterEnabled || !activation?.available || !guidances.length;
  if(panel.hidden)return;
  if(!guidances.some(item=>item.index===selectedGuidance))selectedGuidance=guidances[0].index;
  const select=$('#guidance-select');
  if(select.options.length!==guidances.length || [...select.options].some((option,i)=>option.value!==String(guidances[i].index))){
    select.replaceChildren(...guidances.map(item=>new Option(item.name,item.index)));
  }
  select.value=String(selectedGuidance);
  const guidance=guidances.find(item=>item.index===selectedGuidance);if(!guidance)return;
  const schema=JSON.stringify({index:guidance.index,groups:guidance.groups.map(x=>x.name),bodies:guidance.bodies.map(x=>x.index),terms:guidance.terms.map(x=>[x.name,x.guided])});
  if(schema!==activationSchema){
    activationSchema=schema;
    $('#guidance-summary').innerHTML='<span></span><label class="switch"><input id="guidance-enabled" type="checkbox"><span></span><em>Enabled</em></label>';
    $('#guidance-groups').innerHTML=guidance.groups.map(group=>`<label title="${escapeHtml(group.name.replaceAll('_',' '))}"><span>${escapeHtml(group.name.replaceAll('_',' '))}</span><output></output><input aria-label="${escapeHtml(group.name.replaceAll('_',' '))} activation" data-group="${escapeHtml(group.name)}" type="range" min="0" max="1" step="0.05"></label>`).join('');
    $('#guidance-bodies').innerHTML=guidance.bodies.map(body=>`<button type="button" title="${escapeHtml(body.name)}" data-body="${body.index}"></button>`).join('');
    $('#guidance-terms').innerHTML=guidance.terms.map(term=>`<label class="${term.guided?'':'unavailable'}"><input type="checkbox" data-term="${escapeHtml(term.name)}" ${term.guided?'':'disabled'}><span>${escapeHtml(term.name)}</span></label>`).join('');
  }
  $('#guidance-summary > span').textContent=`${guidance.enabled?'Active':'Disabled'} · Kp ${guidance.kp.toFixed(2)}`;
  $('#guidance-enabled').checked=guidance.enabled;
  guidance.groups.forEach(group=>{const input=$(`#guidance-groups input[data-group="${CSS.escape(group.name)}"]`);if(!input)return;input.previousElementSibling.value=group.value.toFixed(2);if(document.activeElement!==input)input.value=group.value});
  guidance.bodies.forEach(body=>{const button=$(`#guidance-bodies [data-body="${body.index}"]`);if(!button)return;button.dataset.weight=body.weight;button.classList.toggle('on',body.weight>0);button.classList.toggle('override',body.override);button.textContent=`${body.label} · ${body.weight.toFixed(1)}`});
  guidance.terms.forEach(term=>{const input=$(`#guidance-terms input[data-term="${CSS.escape(term.name)}"]`);if(input)input.checked=term.enabled});
}
function setStick(side,x,y){document.querySelector(`[data-stick=${side}] i`).style.transform=`translate(${x*22}px,${y*22}px)`}
function escapeHtml(value){const node=document.createElement('span');node.textContent=value;return node.innerHTML}
function connect(){
  const protocol=location.protocol==='https:'?'wss':'ws', socket=new WebSocket(`${protocol}://${location.host}/ws`);
  socket.onmessage=e=>render(JSON.parse(e.data));
  socket.onopen=()=>{error();clearTimeout(reconnectTimer)};
  socket.onclose=()=>{ $('#connection').textContent='RECONNECTING'; reconnectTimer=setTimeout(connect,900); };
  socket.onerror=()=>socket.close();
}
let sliderTimer;
document.querySelectorAll('.sliders input').forEach(input=>input.addEventListener('input',()=>{
  $(`#${input.dataset.key}-out`).value=Number(input.value).toFixed(2);clearTimeout(sliderTimer);
  sliderTimer=setTimeout(()=>command({command:'set_wbg',values:{[input.dataset.key]:Number(input.value)}}).catch(e=>error(e.message)),28);
}));
$('#wbg-enabled').addEventListener('change',e=>command({command:'set_wbg_enabled',enabled:e.target.checked}).catch(e=>error(e.message)));
$('#destination-form').addEventListener('submit',async e=>{
  e.preventDefault();
  const target=['x','y','z'].map(axis=>Number($(`#destination-${axis}`).value));
  if(target.some(value=>!Number.isFinite(value))){error('Destination coordinates must be finite numbers');return}
  try{await command({command:'set_destination',target,enabled:true});error()}catch(ex){error(ex.message)}
});
$('#destination-enabled').addEventListener('change',e=>command({command:'set_destination_enabled',enabled:e.target.checked}).catch(ex=>{e.target.checked=!e.target.checked;error(ex.message)}));
$('#destination-cancel').addEventListener('click',()=>command({command:'cancel_destination'}).catch(ex=>error(ex.message)));
$('#destination-config-form').addEventListener('submit',async e=>{
  e.preventDefault();
  const values={};
  document.querySelectorAll('[data-destination-config]').forEach(input=>{values[input.dataset.destinationConfig]=Number(input.value)});
  document.querySelectorAll('[data-destination-range]').forEach(input=>{
    const key=input.dataset.destinationRange,index=Number(input.dataset.rangeIndex);
    if(!values[key])values[key]=[0,0];values[key][index]=Number(input.value);
  });
  if(Object.values(values).flat().some(value=>!Number.isFinite(value))){error('Destination tuning values must be finite numbers');return}
  try{await command({command:'set_destination_config',values});error()}catch(ex){error(ex.message)}
});
document.querySelectorAll('.source-select button').forEach(button=>button.addEventListener('click',()=>command({command:'set_source',source:button.dataset.source}).catch(e=>error(e.message))));
$('#pause').addEventListener('click',()=>command({command:latest?.paused?'resume':'pause'}).catch(e=>error(e.message)));
$('#sim-reset').addEventListener('click',()=>command({command:'reset_simulation'}).catch(e=>error(e.message)));
$('#sim-auto-reset').addEventListener('change',e=>command({command:'set_auto_reset',enabled:e.target.checked}).catch(ex=>{e.target.checked=!e.target.checked;error(ex.message)}));
const appearanceDialog=$('#appearance-dialog');applyTextureDensity(initialTextureDensity);applyColorTheme(initialTheme);
$('#appearance').addEventListener('click',()=>appearanceDialog.showModal());
$('#appearance-close').addEventListener('click',()=>appearanceDialog.close());
appearanceDialog.addEventListener('click',event=>{if(event.target===appearanceDialog)appearanceDialog.close()});
$('#texture-density').addEventListener('input',event=>{const density=applyTextureDensity(event.target.value);try{localStorage.setItem(TEXTURE_DENSITY_KEY,String(density))}catch(_error){}});
$('#texture-density-reset').addEventListener('click',()=>{const density=applyTextureDensity(TEXTURE_DENSITY_DEFAULT);try{localStorage.setItem(TEXTURE_DENSITY_KEY,String(density))}catch(_error){}});
$('#theme-light').addEventListener('change',event=>{const theme=applyColorTheme(event.target.checked?'light':'dark');try{localStorage.setItem(THEME_KEY,theme)}catch(_error){}});
const simHelp=$('#sim-help-dialog');
$('#sim-help').addEventListener('click',()=>simHelp.showModal());
$('#sim-help-close').addEventListener('click',()=>simHelp.close());
simHelp.addEventListener('click',event=>{if(event.target===simHelp)simHelp.close()});
$('#text-form').addEventListener('submit',async e=>{e.preventDefault();const input=$('#prompt'),text=input.value.trim();if(!text)return;input.value='';try{await command({command:'set_text',text});error()}catch(ex){input.value=text;error(ex.message)}});
$('#prompt').addEventListener('keydown',e=>{if(e.key==='Enter'&&!e.shiftKey){e.preventDefault();$('#text-form').requestSubmit()}});
$('#interp-form').addEventListener('submit',async e=>{e.preventDefault();await applyInterpolationTerms()});
let interpTimer;
$('#interp-add').addEventListener('click',async()=>{
  interpolationTerms=captureInterpolationTerms();
  if(interpolationTerms.length>=16)return;
  interpolationTerms.push({text_a:null,text_b:'stand',weight:0,weight_min:0,weight_max:1,weight_default:0});
  renderInterpolationTerms();await applyInterpolationTerms();
});
$('#interp-terms').addEventListener('click',async e=>{
  const row=e.target.closest('.interp-term');if(!row)return;
  if(e.target.closest('.interp-remove')){
    if(document.querySelectorAll('.interp-term').length<=1)return;
    interpolationTerms=captureInterpolationTerms();interpolationTerms.splice(Number(row.dataset.index),1);
    renderInterpolationTerms();await applyInterpolationTerms();return;
  }
  const zero=e.target.closest('.interp-zero');if(!zero)return;
  const input=row.querySelector(`[data-endpoint="${zero.dataset.zero}"]`);
  if(input.disabled){input.disabled=false;input.value=input.dataset.previous||'stand';input.placeholder='Motion prompt'}
  else{
    input.dataset.previous=input.value;input.value='';input.disabled=true;input.placeholder='ZERO VECTOR';
    const weight=row.querySelector('[data-weight]');if(Number(weight.value)<0)weight.value='0';
  }
  zero.classList.toggle('active',input.disabled);zero.setAttribute('aria-pressed',String(input.disabled));
  await applyInterpolationTerms();
});
$('#interp-terms').addEventListener('input',e=>{
  if(!e.target.matches('[data-weight]'))return;
  e.target.closest('label').querySelector('output').value=formatInterpolationWeight(e.target.value,Number(e.target.min));
  clearTimeout(interpTimer);interpTimer=setTimeout(()=>applyInterpolationTerms({live:true}),60);
});
$('#interp-terms').addEventListener('dblclick',async e=>{
  const output=e.target.closest('output');if(output)await resetInterpolationTerm(output.closest('.interp-term'));
});
$('#interp-terms').addEventListener('keydown',async e=>{
  const output=e.target.closest('output');if(!output||!['Enter',' '].includes(e.key))return;
  e.preventDefault();await resetInterpolationTerm(output.closest('.interp-term'));
});
$('#interp-terms').addEventListener('change',e=>{
  if(e.target.matches('[data-weight]')){clearTimeout(interpTimer);interpTimer=setTimeout(()=>applyInterpolationTerms(),65);return}
  if(e.target.matches('[data-endpoint]'))applyInterpolationTerms();
});
$('#guidance-select').addEventListener('change',e=>{selectedGuidance=Number(e.target.value);if(latest)renderActivation(latest.wbg.activation,latest.wbg.enabled)});
$('#activation-reset').addEventListener('click',()=>command({command:'reset_guidance_activation',index:selectedGuidance}).catch(ex=>error(ex.message)));
$('#guidance-summary').addEventListener('change',e=>{if(e.target.id==='guidance-enabled')command({command:'set_guidance_enabled',index:selectedGuidance,enabled:e.target.checked}).catch(ex=>error(ex.message))});
let activationTimer;
$('#guidance-groups').addEventListener('input',e=>{if(!e.target.dataset.group)return;e.target.previousElementSibling.value=Number(e.target.value).toFixed(2);clearTimeout(activationTimer);activationTimer=setTimeout(()=>command({command:'set_guidance_group',index:selectedGuidance,group:e.target.dataset.group,value:Number(e.target.value)}).catch(ex=>error(ex.message)),32)});
$('#guidance-bodies').addEventListener('click',e=>{const button=e.target.closest('[data-body]');if(!button)return;command({command:'toggle_guidance_body',index:selectedGuidance,body:Number(button.dataset.body)}).catch(ex=>error(ex.message))});
$('#guidance-terms').addEventListener('change',e=>{if(!e.target.dataset.term)return;command({command:'set_guidance_term',index:selectedGuidance,term:e.target.dataset.term,enabled:e.target.checked}).catch(ex=>error(ex.message))});
document.querySelectorAll('.tabs button').forEach(button=>button.addEventListener('click',()=>setClipMode(button.dataset.mode)));
const joyHelp=$('#joy-help-dialog');
$('#joy-help').addEventListener('click',()=>joyHelp.showModal());
$('#joy-help-close').addEventListener('click',()=>joyHelp.close());
joyHelp.addEventListener('click',event=>{if(event.target===joyHelp)joyHelp.close()});
document.addEventListener('keydown',event=>{if(event.key==='Escape'&&joyHelp.open)joyHelp.close()});
connect();
