'use strict';
const $ = id => document.getElementById(id);
let connection, current = null, baseline = null, running = false, canceled = false, confirmationRevision = 0;
const examples = {
  balanced: [-8, -21, -58, -15, 0], clipping: [-0.2, -8, -40, -3, 18], quiet: [-78, -86, -96, -82, 0]
};
const line = s => `RxAudioStats: Pk ${s.peak}  Avg Pwr ${s.average}  Min ${s.minimum}  Max ${s.maximum}  dBFS  ClipCnt ${s.clips}`;
const demoLine = v => `RxAudioStats: Pk ${v[0]}  Avg Pwr ${v[1]}  Min ${v[2]}  Max ${v[3]}  dBFS  ClipCnt ${v[4]}`;
function error(message) { $('error').textContent = message || ''; $('error').hidden = !message; }
async function api(path, data) {
  const controller = new AbortController();
  const timeout = setTimeout(() => controller.abort(), 14000);
  try {
    const response = await fetch(path, {method:'POST', headers:{'Content-Type':'application/json', 'X-BlueTune-Token':connection.token}, body:JSON.stringify(data), signal:controller.signal});
    const payload = await response.json();
    if (!response.ok) throw new Error(payload.error || 'The check could not finish. Please retry.');
    return payload;
  } finally { clearTimeout(timeout); }
}
function source() { const x = $('scenario').value; return x === 'live' ? 'live' : x === 'paste' ? 'imported' : 'demo'; }
function prepare() {
  if (running) return;
  const type = source();
  $('paste-area').hidden = type !== 'imported';
  $('speech').checked = false;
  $('speech').disabled = type === 'demo';
  $('speech').closest('label').hidden = type === 'demo';
  $('instructions').textContent = type === 'demo' ? 'Explore an example first. Demo readings are synthetic and do not measure your radio.' : type === 'live' ? 'Confirm the intended interface in ASL3 and close other tuning sessions. Use an appropriate test frequency. Start, then speak normally for 10 seconds.' : 'Collect receive statistics while speaking into the node receiver. Paste the output and confirm that the sample contains your speech.';
  $('measure').textContent = type === 'demo' ? 'Run demo checkup ↗' : type === 'live' ? 'Measure for 10 seconds ↗' : 'Analyze pasted sample ↗';
  clearCurrent(); error('');
}
function clearCurrent() {
  confirmationRevision++;
  current = null;
  $('peak').textContent = $('average').textContent = $('clips').textContent = $('count').textContent = '—';
  $('sample-badge').textContent = 'AWAITING SAMPLE'; $('meter-fill').style.width = '100%'; $('meter-fill').style.clipPath = 'inset(0 100% 0 0)'; $('meter').removeAttribute('aria-valuenow');
  $('verdict').className = 'verdict unknown'; $('verdict-icon').textContent = '○';
  $('result-title').textContent = 'Ready for your next sample'; $('advice').textContent = 'Results appear after a complete checkup.';
  $('save').disabled = $('export').disabled = true;
  $('step1').className = 'current'; $('step2').className = $('step3').className = '';
  compare();
}
function render() {
  const r = current.result;
  $('peak').textContent = r.peak.toFixed(1); $('average').textContent = r.max_average.toFixed(0) + ' dBFS';
  $('clips').textContent = r.max_clip_count; $('count').textContent = r.sample_count;
  $('sample-badge').textContent = `${current.source.toUpperCase()} / ${new Date(current.created_at).toLocaleTimeString([], {hour:'2-digit',minute:'2-digit'})}`;
  $('meter-fill').style.clipPath = `inset(0 ${100-Math.min(100,Math.max(0,(r.peak+60)/60*100))}% 0 0)`;
  $('meter').setAttribute('aria-valuenow', Math.max(-60,r.peak));
  $('verdict').className = 'verdict ' + r.status; $('verdict-icon').textContent = r.status === 'good' ? '✓' : r.status === 'warning' ? '!' : '○';
  $('result-title').textContent = r.title; $('advice').textContent = r.advice;
  $('result-note').textContent = r.note;
  $('save').disabled = $('export').disabled = false;
  $('step1').className = ''; $('step2').className = 'current';
  compare();
}
function compare() {
  $('step3').className = '';
  $('clear').disabled = !baseline;
  $('compare-empty').hidden = !!(baseline && current);
  $('comparison').hidden = !(baseline && current);
  $('comparison').replaceChildren();
  if (!baseline || !current) {
    $('compare-empty').textContent = baseline ? `Baseline saved: ${baseline.label} (${baseline.source}). Take another sample to compare.` : 'Save a baseline, make one deliberate adjustment in ASL3, then take another sample.';
    return;
  }
  const parent = $('comparison');
  if (baseline.source !== current.source || baseline.device !== current.device) {
    const p = document.createElement('p'); p.textContent = 'These samples use different sources or devices. Save a matching baseline before comparing.'; parent.append(p); return;
  }
  const grid = document.createElement('div'); grid.className = 'compare-grid';
  [['Peak', baseline.result.peak.toFixed(1), current.result.peak.toFixed(1), ' dBFS'],['Highest avg. power',baseline.result.max_average,current.result.max_average,' dBFS'],['Max. window ClipCnt',baseline.result.max_clip_count,current.result.max_clip_count,'']].forEach(([label,a,b,unit]) => {
    const cell = document.createElement('div'), title = document.createElement('span'), value = document.createElement('strong');
    title.textContent = label; value.textContent = `${a} → ${b}${unit}`; cell.append(title,value); grid.append(cell);
  });
  const note = document.createElement('p'); note.className = 'hint'; note.textContent = `${baseline.source.toUpperCase()} · ${baseline.label} → ${current.label}.` + (current.source === 'imported' ? ' Imported device identity and measurement times are not verified.' : '');
  parent.append(grid,note); $('step3').className = 'current';
}
function download(name, data) {
  const url = URL.createObjectURL(new Blob([JSON.stringify(data,null,2)],{type:'application/json'}));
  const a = document.createElement('a'); a.href=url; a.download=name; a.click(); setTimeout(()=>URL.revokeObjectURL(url),1000);
}
$('scenario').addEventListener('change',prepare);
$('measure').addEventListener('click', async () => {
  if (running || !connection) return;
  error(''); clearCurrent(); running = true; canceled = false;
  const type = source(), label = $('session-name').value.trim() || 'Receive check';
  if (type === 'live') $('speech').checked = false;
  $('measure').disabled = $('scenario').disabled = true; $('stop').hidden = type !== 'live';
  try {
    let text;
    if (type === 'demo') text = demoLine(examples[$('scenario').value]);
    else if (type === 'imported') text = $('stats').value;
    else {
      const samples = []; const started = performance.now();
      while (performance.now() - started < 10000) {
        if (canceled) break;
        const result = await api('/api/sample',{});
        if (canceled) break;
        samples.push(result.sample);
        $('progress').textContent = `Listening to ASL3 measurements · ${samples.length} observations · keep speaking normally`;
        await new Promise(resolve=>setTimeout(resolve,1000));
      }
      if (canceled) { $('progress').textContent = 'Measurement canceled. No partial result was saved.'; return; }
      if (samples.length < 5) throw new Error('Too few observations arrived. Check the connection and repeat.');
      text = samples.map(line).join('\n');
    }
    const result = await api('/api/analyze',{text, speech_confirmed:type === 'demo' || $('speech').checked});
    current = {...result, source:type, device:type === 'live' ? connection.device : null, label, created_at:new Date().toISOString(), version:connection.version};
    render(); $('progress').textContent = type === 'demo' ? 'Demo complete · synthetic readings, not your radio.' : type === 'imported' ? 'Imported sample analyzed · original collection time is unknown.' : 'Measurement complete. Confirm that you spoke during this sample using the checkbox.';
  } catch(e) { error(e.name === 'AbortError' ? 'The connection timed out. Checkup was discarded; please retry.' : e.message); $('progress').textContent='Checkup incomplete. No result was saved.'; }
  finally { running=false; $('measure').disabled=$('scenario').disabled=false; $('stop').hidden=true; }
});
$('stop').addEventListener('click',()=>{canceled=true; $('progress').textContent='Canceling measurement…';});
$('speech').addEventListener('change', async()=>{
  if (!current || running || current.source === 'demo') return;
  const prior = current; $('save').disabled = $('export').disabled = true;
  const revision = ++confirmationRevision;
  try {
    const result = await api('/api/analyze',{text:prior.samples.map(line).join('\n'),speech_confirmed:$('speech').checked});
    if (current === prior && revision === confirmationRevision) { current={...prior,...result}; render(); }
  } catch(e) { if (revision === confirmationRevision) { clearCurrent(); error(e.message); } }
});
$('save').addEventListener('click',()=>{baseline=structuredClone(current); compare();});
$('clear').addEventListener('click',()=>{baseline=null; compare();});
$('export').addEventListener('click',()=>download('bluetune-checkup.json',{current,baseline, scope:'Receive statistics only. Demo data is synthetic. Imported time and device are unverified. No RF deviation or audio-quality certification.'}));
$('settings').addEventListener('click',async()=>{
  error(''); $('settings').disabled=true;
  try { download('bluetune-settings-reference.json',await api('/api/settings',{})); } catch(e) {error(e.message);} finally {$('settings').disabled=false;}
});
(async()=>{
  $('measure').disabled=true;
  try {
    const response=await fetch('/api/status'); if (!response.ok) throw new Error('Cannot connect to BlueTune.'); connection=await response.json();
    $('connection').textContent=connection.mode === 'demo' ? 'Demo workspace · no node connected' : `SimpleUSB · ${connection.device}`;
    $('mode-note').textContent=connection.mode === 'demo' ? 'DEMO WORKSPACE — Try synthetic examples or analyze pasted ASL3 statistics. Nothing here is connected to your radio.' : `READ-ONLY CONNECTION — SimpleUSB device ${connection.device}. Live adapter is experimental; hardware validation is still required.`;
    if(connection.mode === 'live') {const option=$('scenario').querySelector('[value=live]'); option.disabled=false; $('scenario').value='live'; $('settings').disabled=false;}
    prepare(); $('measure').disabled=false;
  } catch(e) {error(e.message); $('connection').textContent='Connection unavailable'; $('mode-note').textContent='BlueTune could not connect. Start the local app and reload this page.';}
})();
