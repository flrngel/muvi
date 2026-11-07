/* Muvi's interface renders measurements returned by the local engine. No simulated analysis. */
'use strict';
const $ = (id) => document.getElementById(id);
const esc = (value) => String(value ?? '').replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const fmt = (seconds, precise = false) => {
  const value = Math.max(0, Number(seconds) || 0);
  return `${Math.floor(value / 60)}:${(precise ? (value % 60).toFixed(2) : Math.floor(value % 60).toString()).padStart(precise ? 5 : 2, '0')}`;
};
const state = {g: null, visuals: null, tracks: [], view: 'spectrum', start: 0, end: 1,
  section: null, loop: false, auditionStart: 0, auditionEnd: null, busy: false, loadTicket: 0, inspectorTicket: 0, connection: null};
const audio = $('audio');
audio.volume = 0.8;
let toastTimer, dragDepth = 0;

async function request(url, options = {}) {
  const response = await fetch(url, options);
  if (!response.ok) {
    let message = `Request failed (${response.status})`;
    try { const data = await response.json(); message = typeof data.detail === 'string' ? data.detail : message; } catch { /* retain status */ }
    throw new Error(message);
  }
  return response.json();
}
const post = (url, data) => request(url, {method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify(data)});
const tool = (name, args = {}) => post(`/api/tools/${name}`, {arguments: {track_id: state.g.track_id, ...args}});
const route = (suffix) => `/api/tracks/${state.g.source_sha256}/${suffix}`;
function toast(message, error = false) {
  clearTimeout(toastTimer); $('toast').textContent = message; $('toast').classList.toggle('error', error); $('toast').hidden = false;
  toastTimer = setTimeout(() => { $('toast').hidden = true; }, error ? 6500 : 3500);
}
function run(action) { return (...args) => Promise.resolve().then(() => action(...args)).catch(error => toast(error.message, true)); }
function screen(name) {
  for (const id of ['welcome', 'analysis-progress', 'explorer']) $(id).hidden = id !== name;
  $('player').hidden = name !== 'explorer';
}
function setBusy(value) {
  state.busy = value;
  ['import-top', 'import-welcome', 'add-track', 'demo-sidebar', 'demo-welcome'].forEach(id => $(id).disabled = value);
}
function openImport() { if (!state.busy) $('file-input').click(); }
async function refreshLibrary() {
  const data = await request('/api/tracks'); state.tracks = data.tracks;
  $('track-count').textContent = data.tracks.length;
  $('library-list').innerHTML = data.tracks.length ? data.tracks.map(t => `<button class="track-item ${t.track_id === state.g?.track_id ? 'active' : ''}" data-track="${esc(t.track_id)}" aria-label="Open ${esc(t.title)}"><span class="track-art" aria-hidden="true">≋</span><span><strong>${esc(t.title)}</strong><small>${fmt(t.duration_s)} · ${t.tempo_bpm ? `${Math.round(t.tempo_bpm)} BPM?` : 'No tempo'}</small></span></button>`).join('') : '<p class="library-empty">A new perspective<br>on every track.</p>';
}
async function analyze(file, demo = false) {
  if (state.busy) return toast('A track is already being analyzed.');
  if (!demo && file.size > 200 * 1024 * 1024) throw new Error('Choose a file smaller than 200 MiB.');
  if (!demo && !file.size) throw new Error('That file is empty. Choose an audio recording.');
  setBusy(true); audio.pause(); state.loadTicket++; state.inspectorTicket++;
  document.querySelector('.sidebar').classList.remove('open');
  screen('analysis-progress'); $('progress-title').textContent = demo ? 'After hours.' : file.name;
  $('progress-stage').textContent = demo ? 'Making an original example…' : 'Importing your audio…'; $('progress-fill').style.width = '3%';
  try {
    let created;
    if (demo) created = await post('/api/demo', {});
    else { const body = new FormData(); body.append('file', file); created = await request('/api/upload', {method: 'POST', body}); }
    sessionStorage.setItem('muvi-job', created.job_id);
    await watchJob(created.job_id);
  } catch (error) {
    screen(state.g ? 'explorer' : 'welcome'); throw error;
  } finally { setBusy(false); }
}
async function watchJob(jobId) {
  for (;;) {
    const job = await request(`/api/jobs/${jobId}`);
    $('progress-stage').textContent = job.stage; $('progress-fill').style.width = `${Math.max(3, job.progress * 100)}%`;
    if (job.status === 'failed') { sessionStorage.removeItem('muvi-job'); throw new Error(job.error); }
    if (job.status === 'complete') {
      sessionStorage.removeItem('muvi-job');
      await loadTrack(job.track_id); await refreshLibrary(); toast('Your track is ready. Take a closer listen.'); return;
    }
    await new Promise(resolve => setTimeout(resolve, 650));
  }
}
async function loadTrack(id) {
  const ticket = ++state.loadTicket;
  const [g, visuals] = await Promise.all([request(`/api/tracks/${id}`), request(`/api/tracks/${id}/visuals`)]);
  if (ticket !== state.loadTicket) return;
  if (g.analysis_id !== visuals.analysis_id) throw new Error('Analysis versions do not match. Reload the track.');
  state.g = g; state.visuals = visuals; state.start = 0; state.end = g.duration_s; state.section = null;
  state.auditionEnd = null; state.loop = false; state.inspectorTicket++;
  audio.pause(); audio.src = route('artifacts/audio/preview.wav'); audio.load();
  $('loop').setAttribute('aria-pressed', 'false'); $('play').textContent = '▶'; $('play').setAttribute('aria-label', 'Play');
  $('track-title').textContent = g.title; $('breadcrumb-track').textContent = g.title; $('player-title').textContent = g.title;
  $('track-meta').textContent = `${fmt(g.duration_s)} duration   ·   ${(g.sample_rate / 1000).toFixed(2).replace(/0$/, '')} kHz ${g.channels === 2 ? 'stereo' : 'mono'}   ·   ${g.source_format}   ·   Analyzed on your device`;
  $('total-time').textContent = fmt(g.duration_s); $('current-time').textContent = '0:00'; $('seek').max = g.duration_s; $('seek').value = 0;
  $('player-subtitle').textContent = 'Original mix · playback preview';
  const bpm = g.tempo.preferred_bpm;
  $('readouts').innerHTML = `<div class="readout"><div class="readout-label">THE PULSE</div><strong>${bpm ? bpm.toFixed(1) : '—'}<small>BPM</small></strong><p>${bpm ? `Also plausible: ${g.tempo.candidates_bpm.slice(1).map(x => Math.round(x)).join(' / ')} BPM` : 'No reliable periodicity detected'}</p></div><div class="readout"><div class="readout-label">SOUND FAMILIES</div><strong>${g.sound_objects.length}<small>objects</small></strong><p>Acoustic shapes, source unresolved</p></div><div class="readout"><div class="readout-label">THE ARRANGEMENT</div><strong>${g.sections.length}<small>sections</small></strong><p>Candidate changes in the mix</p></div><div class="readout"><div class="readout-label">EVERY CLAIM HAS A TRAIL</div><strong>${g.evidence.length} evidence records</strong><p>Measured, versioned, inspectable</p></div>`;
  $('sound-count').textContent = `${g.sound_objects.length} FAMILIES`;
  $('sound-list').innerHTML = g.sound_objects.map(s => `<div class="sound-row"><button class="sound-audition" data-audition="${s.id}" aria-label="Listen to ${esc(s.name)} ${s.id}">▶</button><button class="sound-info" data-sound="${s.id}"><strong>${esc(s.name)}</strong><span>${s.id} · ${esc(s.form.replaceAll('_', ' '))} · inferred role</span></button><span class="sound-events">${s.occurrence_count}<small>occurrences</small></span><button class="sound-more icon-button" data-sound="${s.id}" aria-label="Inspect ${esc(s.name)} ${s.id}">↗</button></div>`).join('') || '<p class="empty-sounds">No salient acoustic objects detected. Try a recording with more audible activity.</p>';
  const options = g.sections.map(s => `<option value="${s.id}">${s.structure_group} · ${fmt(s.start_s)}</option>`).join('');
  $('compare-a').innerHTML = $('compare-b').innerHTML = options;
  $('compare-b').selectedIndex = Math.min(1, g.sections.length - 1); $('compare').disabled = g.sections.length < 2;
  $('analysis-meta').textContent = `${g.analysis_id} · ${g.elapsed_s.toFixed(2)}s extraction`;
  screen('explorer'); showOverview(); renderTimeline();
  localStorage.setItem('muvi-last-track', id);
  document.querySelector('.sidebar').classList.remove('open');
  document.querySelectorAll('[data-track]').forEach(el => el.classList.toggle('active', el.dataset.track === id));
}
function refs(ids) { return ids.map(id => `<button class="evidence-ref" data-evidence="${esc(id)}" aria-label="Inspect evidence ${esc(id)}">${esc(id)} ↗</button>`).join(''); }
function fact(label, value) { return `<div class="fact"><span>${esc(label)}</span><strong>${esc(value)}</strong></div>`; }
function inspector(html) { $('inspector-content').innerHTML = html; }
function showOverview() {
  document.querySelector('.inspector').classList.remove('mobile-active');
  const g = state.g;
  const e = g.evidence.find(x => x.kind === 'source_metrics');
  inspector(`<span class="status-tag">MEASURED + INFERRED</span><h2>The shape of<br>your sound.</h2><p class="intro">A track is more than a list of instruments. Explore its pulse, recurring textures, and the moments where something shifts.</p><div class="divider"></div><div class="micro-label">FROM THE ORIGINAL RECORDING</div>${fact('Sample peak', e.measurements.sample_peak_dbfs === null ? 'Silence' : `${e.measurements.sample_peak_dbfs.toFixed(1)} dBFS`)}${fact('Detected onsets', g.evidence.find(x => x.kind === 'rhythm').measurements.onset_count)}${fact('Recurring patterns', g.patterns.length)}<div class="divider"></div><div class="micro-label">FOLLOW THE EVIDENCE</div>${refs([e.id, 'E0002'])}<div class="note">Select a section or sound to inspect it. A recurring acoustic shape can contain several overlapping sources.</div>`);
}
async function inspectAsync(action) {
  const ticket = ++state.inspectorTicket;
  $('inspector-content').setAttribute('aria-busy', 'true');
  try {
    const result = await action();
    if (ticket === state.inspectorTicket) {
      inspector(result);
      document.querySelector('.inspector').classList.add('mobile-active');
      if (innerWidth <= 1000) document.querySelector('.inspector').scrollIntoView({behavior: 'smooth', block: 'start'});
    }
  } finally {
    if (ticket === state.inspectorTicket) $('inspector-content').removeAttribute('aria-busy');
  }
}
async function showSound(id) {
  await inspectAsync(async () => {
    const p = await tool('get_sound', {sound_object_id: id, limit: 6}); const s = p.sound;
    return `<span class="status-tag">INFERRED ACOUSTIC FAMILY</span><h2>${esc(s.name)}</h2><p class="intro">${s.id} groups similar measurements in the mix. The original instrument or production source is unresolved.</p><div class="divider"></div>${fact('Acoustic form', s.form.replaceAll('_', ' '))}${fact('Occurrences', s.occurrence_count)}${fact('Possible role', s.function_candidates.join(' / '))}${s.fingerprint.centroid_hz ? fact('Prototype centroid', `${Math.round(s.fingerprint.centroid_hz)} Hz`) : ''}<div class="divider"></div><div class="micro-label">HEAR IT IN CONTEXT</div>${p.occurrences.map(o => `<button class="interval-button" data-start="${Math.max(0, o.start_s - 0.04)}" data-end="${Math.min(state.g.duration_s, o.end_s + 0.35)}">▶ Original mix <span>${fmt(o.start_s, true)}</span></button>`).join('')}<div class="divider"></div>${refs(p.evidence_ids)}<div class="note">These are original-mixture excerpts. No isolated stem or instrument identity is implied.</div>`;
  });
}
async function showEvidence(id) {
  await inspectAsync(async () => {
    const p = await tool('get_evidence', {evidence_ids: [id]}); const e = p.evidence[0];
    return `<span class="status-tag">MEASURED EVIDENCE</span><h2>${esc(e.kind.replaceAll('_', ' '))}</h2><p class="intro">${esc(e.observation)}</p><div class="divider"></div>${fact('Record', e.id)}${fact('Original interval', `${fmt(e.start_s, true)}–${fmt(e.end_s, true)}`)}<div class="micro-label">VALUES + UNITS</div><pre>${esc(JSON.stringify({measurements: e.measurements, units: e.units}, null, 2))}</pre><div class="divider"></div><div class="micro-label">PROVENANCE</div><p class="intro">${esc(e.method)}<br>Pipeline ${esc(e.method_version)}</p><button class="button outline small" data-start="${e.start_s}" data-end="${Math.min(e.end_s, e.start_s + 8)}">▶ Listen to original context</button>`;
  });
}
async function selectSection(id) {
  const section = state.g.sections.find(s => s.id === id); if (!section) return;
  state.section = id; state.start = section.start_s; state.end = section.end_s; state.auditionEnd = null;
  seek(section.start_s); renderTimeline();
  await inspectAsync(async () => {
    const p = await tool('get_section', {section_id: id}); const s = p.section;
    return `<span class="status-tag">CANDIDATE SECTION</span><h2>Section ${esc(s.structure_group)}.<br>A change in perspective.</h2><p class="intro">${fmt(s.start_s, true)}–${fmt(s.end_s, true)} in the original track. Groups describe similar features; musical names like “drop” remain unassigned.</p><div class="divider"></div>${fact('Detected onsets', s.onset_count)}${fact('Acoustic families', s.sound_object_ids.length)}${fact('Entrants vs previous', p.entrants.join(', ') || 'None')}${fact('Exits vs previous', p.exits.join(', ') || 'None')}<button class="button primary small" data-start="${s.start_s}" data-end="${s.end_s}">▶ Listen to this section</button><div class="divider"></div>${refs(p.evidence_ids)}<div class="note">Use ↻ in the player to loop the selected interval. Full track restores the complete timeline.</div>`;
  });
}
async function showQuestion(kind) {
  await inspectAsync(async () => {
    if (kind === 'bass') {
      const [claim, sounds] = await Promise.all([tool('verify_hypothesis', {hypothesis: 'independent_bass'}), tool('find_sound', {query: 'bass'})]);
      return `<span class="status-tag uncertain">SOURCE UNRESOLVED</span><h2>Low end.<br>Open possibilities.</h2><p class="intro">${esc(claim.conclusion)} Low-frequency energy may come from a bass layer, a reverberant pulse, or an overlapping mix.</p><div class="divider"></div><div class="micro-label">ACOUSTIC CANDIDATES</div>${sounds.matches.map(s => `<button class="interval-button" data-sound="${s.sound_object_id}">${esc(s.name)}<span>${s.sound_object_id} ↗</span></button>`).join('') || '<p class="intro">No prominent low-band object was found.</p>'}<div class="divider"></div>${refs(claim.evidence_ids.slice(0, 6))}<div class="note">${esc(claim.next_check)}</div>`;
    }
    if (kind === 'rhythm') {
      const p = await tool('verify_hypothesis', {hypothesis: 'recurring_pattern'});
      return `<span class="status-tag">${p.verdict === 'supported' ? 'RECURRENCE DETECTED' : 'NO CLEAR RECURRENCE'}</span><h2>The things<br>that return.</h2><p class="intro">${esc(p.conclusion)} The rhythmic grid is provisional; half and double tempo can both be plausible.</p><div class="divider"></div>${state.g.patterns.map(pattern => `<div class="micro-label">${pattern.id} / ${pattern.sound_object_id}</div>${fact('Typical interval', `${pattern.interval_s.toFixed(3)} seconds`)}${fact('Occurrences / gaps', `${pattern.repeat_count} / ${pattern.exceptions_s.length}`)}${refs(pattern.evidence_ids)}<div class="divider"></div>`).join('')}<div class="note">Repeated timing and timbre do not prove reuse of an identical isolated sound. Audition the examples to check.</div>`;
    }
    const p = await tool('verify_hypothesis', {hypothesis: 'section_change'});
    return `<span class="status-tag">INFERRED ARRANGEMENT</span><h2>Follow<br>the changes.</h2><p class="intro">${esc(p.conclusion)} Select a section to zoom in and compare what enters or leaves.</p><div class="divider"></div>${state.g.sections.map(s => `<button class="interval-button" data-section="${s.id}">Section ${s.structure_group}<span>${fmt(s.start_s)}–${fmt(s.end_s)} ↗</span></button>`).join('')}<div class="note">Boundaries are feature-change proposals. Listening is the final check for musical meaning.</div>`;
  });
}
async function compareSections() {
  await inspectAsync(async () => {
    const p = await tool('compare_sections', {section_a: $('compare-a').value, section_b: $('compare-b').value});
    return `<span class="status-tag">MEASURED COMPARISON</span><h2>${esc(p.section_a.structure_group)} → ${esc(p.section_b.structure_group)}<br>What moved?</h2><p class="intro">Energy in the second section relative to the first, on the same measurement scale.</p><div class="divider"></div>${Object.entries(p.band_energy_delta_db).map(([band, value]) => fact(`${band[0].toUpperCase() + band.slice(1)}-band energy`, `${value >= 0 ? '+' : ''}${value.toFixed(1)} dB`)).join('')}${fact('Onset density change', `${p.onset_density_delta_per_s.toFixed(2)} /s`)}<div class="divider"></div>${fact('Shared families', p.shared_objects.join(', ') || 'None')}${fact('New families', p.new_objects.join(', ') || 'None')}${fact('Absent families', p.absent_objects.join(', ') || 'None')}<div class="divider"></div>${refs(p.evidence_ids)}<div class="note">${esc(p.interpretation)}</div>`;
  });
}

function renderTimeline() {
  if (!state.g || $('explorer').hidden) return;
  const g = state.g, span = state.end - state.start;
  $('reset-view').hidden = !state.section;
  $('viewport-label').textContent = `${fmt(state.start)}–${fmt(state.end)} · original time`;
  $('section-strip').innerHTML = g.sections.filter(s => s.end_s > state.start && s.start_s < state.end).map(s => `<button data-section="${s.id}" class="${s.id === state.section ? 'active' : ''}" style="flex:${(Math.min(s.end_s, state.end) - Math.max(s.start_s, state.start)) / span}" title="Section ${s.structure_group}: ${fmt(s.start_s)}–${fmt(s.end_s)}" aria-label="Explore section ${s.structure_group}, ${fmt(s.start_s)} to ${fmt(s.end_s)}">${s.structure_group}<span> · ${fmt(s.start_s)}</span></button>`).join('');
  $('time-axis').innerHTML = Array.from({length: 6}, (_, i) => `<span>${fmt(state.start + span * i / 5)}</span>`).join('');
  $('chart-hint').textContent = {spectrum: '30 Hz — 11 kHz · log scale', waveform: 'Amplitude · relative to track peak', rhythm: 'Detected attacks · provisional beats'}[state.view];
  drawPlot(); renderRoles(); updateCursor();
}
function contextFor(canvas) {
  const rect = canvas.getBoundingClientRect(), dpr = Math.min(2, devicePixelRatio || 1);
  canvas.width = Math.max(1, Math.round(rect.width * dpr)); canvas.height = Math.max(1, Math.round(rect.height * dpr));
  const ctx = canvas.getContext('2d'); ctx.scale(dpr, dpr); return {ctx, w: rect.width, h: rect.height};
}
function drawPlot() {
  const {ctx, w, h} = contextFor($('plot')), v = state.visuals, span = state.end - state.start;
  const x = time => (time - state.start) / span * w;
  ctx.fillStyle = '#121910'; ctx.fillRect(0, 0, w, h);
  if (state.view === 'spectrum') {
    const selected = v.times_s.map((t, i) => ({t, i})).filter(({t, i}) => t < state.end && (v.times_s[i + 1] || state.g.duration_s) > state.start);
    const off = document.createElement('canvas'); off.width = Math.max(1, selected.length); off.height = v.spectrogram_db.length;
    const oc = off.getContext('2d'), img = oc.createImageData(off.width, off.height);
    for (let column = 0; column < selected.length; column++) {
      for (let row = 0; row < off.height; row++) {
        const val = Math.max(0, Math.min(1, (v.spectrogram_db[row][selected[column].i] + 90) / 70));
        const at = ((off.height - row - 1) * off.width + column) * 4;
        img.data[at] = 15 + val ** 1.8 * 181; img.data[at + 1] = 25 + val * 196; img.data[at + 2] = 17 + val ** 1.5 * 119; img.data[at + 3] = 255;
      }
    }
    oc.putImageData(img, 0, 0); ctx.imageSmoothingEnabled = false;
    const first = selected[0]?.t ?? state.start;
    const lastIndex = selected.at(-1)?.i ?? 0;
    const last = v.times_s[lastIndex + 1] ?? state.g.duration_s;
    ctx.drawImage(off, x(first), 0, (last - first) / span * w, h);
    ctx.fillStyle = '#d8ebc1aa'; ctx.font = '8px Consolas,monospace';
    for (const hz of [10000, 1000, 100]) { const y = h * (1 - Math.log(hz / 30) / Math.log(11025 / 30)); ctx.fillText(hz >= 1000 ? `${hz / 1000}k` : `${hz}`, 8, y + 3); }
  } else if (state.view === 'waveform') {
    const peak = Math.max(0.00001, ...v.waveform);
    const width = Math.max(1, w / Math.max(1, v.waveform.length * span / state.g.duration_s) * 0.65);
    for (let i = 0; i < v.waveform.length; i++) {
      const t = v.waveform_times_s[i]; if (t < state.start || t > state.end) continue;
      const height = Math.max(1, v.waveform[i] / peak * h * 0.84);
      ctx.fillStyle = '#b8df8c'; ctx.fillRect(x(t), h / 2 - height / 2, width, height);
    }
  } else {
    for (const beat of state.g.tempo.beat_times_s) {
      if (beat < state.start || beat > state.end) continue;
      ctx.strokeStyle = '#6c8b5044'; ctx.setLineDash([2, 4]); ctx.beginPath(); ctx.moveTo(x(beat), 0); ctx.lineTo(x(beat), h); ctx.stroke();
    }
    ctx.setLineDash([]);
    for (const t of v.onset_times_s) { if (t >= state.start && t <= state.end) { ctx.fillStyle = '#c6f39755'; ctx.fillRect(x(t), h * 0.25, 2, h * 0.65); } }
    ctx.strokeStyle = '#d5f4ad'; ctx.lineWidth = 1.5; ctx.beginPath(); let first = true;
    v.times_s.forEach((t, i) => { if (t >= state.start && t <= state.end) { const y = h * .9 - v.onset_strength[i] * h * .8; if (first) ctx.moveTo(x(t), y); else ctx.lineTo(x(t), y); first = false; } }); ctx.stroke();
  }
  for (let i = 1; i < 6; i++) { ctx.strokeStyle = '#e1f3cc10'; ctx.lineWidth = 1; ctx.beginPath(); ctx.moveTo(w * i / 6, 0); ctx.lineTo(w * i / 6, h); ctx.stroke(); }
}
function renderRoles() {
  $('role-lanes').innerHTML = ['LOW', 'MID', 'HIGH'].map((label, i) => `<div class="role-lane"><span class="role-label">${label}</span><canvas class="role-track" id="role-${i}" aria-label="${label.toLowerCase()} acoustic object occurrences"></canvas></div>`).join('');
  const span = state.end - state.start;
  for (let lane = 0; lane < 3; lane++) {
    const {ctx, w, h} = contextFor($(`role-${lane}`));
    ctx.fillStyle = ['#bbdf8e', '#8cb2d6', '#b799cf'][lane];
    const ids = state.g.sound_objects.filter(s => {
      const f = s.fingerprint; return lane === (f.low_fraction > .55 ? 0 : f.high_fraction > .55 ? 2 : 1);
    }).map(s => s.id);
    state.g.occurrences.filter(o => ids.includes(o.sound_object_id) && o.start_s < state.end && o.end_s > state.start).forEach(o => {
      ctx.globalAlpha = .6; ctx.fillRect((Math.max(o.start_s, state.start) - state.start) / span * w, h / 2 - 2,
        Math.max(2, (Math.min(o.end_s, state.end) - Math.max(o.start_s, state.start)) / span * w), 4);
    });
  }
}
function updateCursor() {
  if (!state.g) return;
  const fraction = (audio.currentTime - state.start) / (state.end - state.start);
  $('plot-cursor').hidden = fraction < 0 || fraction > 1;
  $('plot-cursor').style.left = `${Math.max(0, Math.min(1, fraction)) * 100}%`;
  $('cursor-label').textContent = fmt(audio.currentTime, true);
}
function seek(time) { audio.currentTime = Math.min(state.g.duration_s, Math.max(0, time)); updatePlayback(); }
function updatePlayback() {
  $('seek').value = audio.currentTime; $('current-time').textContent = fmt(audio.currentTime); updateCursor();
  const end = state.auditionEnd ?? state.end;
  if (!audio.paused && audio.currentTime >= end - .02) {
    if (state.loop) audio.currentTime = state.auditionEnd === null ? state.start : state.auditionStart;
    else if (state.auditionEnd !== null) { audio.pause(); state.auditionEnd = null; }
  }
}
async function audition(start, end) {
  state.auditionStart = start; state.auditionEnd = end; seek(start); await audio.play();
}
async function togglePlay() {
  if (!state.g) return;
  if (!audio.paused) audio.pause();
  else { if (audio.currentTime >= state.g.duration_s - .02 || (state.loop && audio.currentTime >= state.end - .02)) seek(state.start); await audio.play(); }
}
async function connect() {
  state.connection ||= await request('/api/tools');
  $('mcp-config').textContent = JSON.stringify(state.connection.mcp_config, null, 2); $('connect-dialog').showModal();
}
async function copy(text, message) {
  try { await navigator.clipboard.writeText(text); toast(message); }
  catch { throw new Error('Clipboard access is unavailable. Select and copy the configuration text.'); }
}
async function saveTile() {
  const id = state.g.track_id; $('save-tile').disabled = true; $('save-tile').textContent = 'Rendering…';
  try {
    const p = await tool('render_tile', {start_s: state.start, end_s: state.end});
    if (id !== state.g.track_id) return;
    $('tile-image').src = p.image.url; $('tile-download').href = p.image.url; $('legend-download').href = p.legend.url;
    $('tile-dialog').showModal();
  } finally { $('save-tile').disabled = false; $('save-tile').textContent = '↓ Image + evidence'; }
}

['import-top', 'import-welcome', 'add-track'].forEach(id => $(id).addEventListener('click', openImport));
['demo-sidebar', 'demo-welcome'].forEach(id => $(id).addEventListener('click', run(() => analyze(null, true))));
['connect-sidebar', 'connect-main'].forEach(id => $(id).addEventListener('click', run(connect)));
$('file-input').addEventListener('change', run(async e => { const file = e.target.files[0]; e.target.value = ''; if (file) await analyze(file); }));
$('export').addEventListener('click', () => { const a = document.createElement('a'); a.href = route('export'); a.download = 'music-genome.json'; a.click(); toast('Genome exported with timestamps and evidence.'); });
$('save-tile').addEventListener('click', run(saveTile));
$('compare').addEventListener('click', run(compareSections));
$('reset-view').addEventListener('click', () => { state.start = 0; state.end = state.g.duration_s; state.section = null; state.auditionEnd = null; renderTimeline(); });
$('play').addEventListener('click', run(togglePlay));
$('seek').addEventListener('input', e => { state.auditionEnd = null; seek(Number(e.target.value)); });
$('loop').addEventListener('click', () => { state.loop = !state.loop; $('loop').setAttribute('aria-pressed', state.loop); toast(state.loop ? `Looping ${fmt(state.auditionEnd === null ? state.start : state.auditionStart)}–${fmt(state.auditionEnd ?? state.end)}` : 'Loop off'); });
$('mute').addEventListener('click', () => { audio.muted = !audio.muted; $('mute').setAttribute('aria-pressed', audio.muted); $('mute').setAttribute('aria-label', audio.muted ? 'Unmute audio' : 'Mute audio'); });
$('volume').addEventListener('input', e => { audio.volume = Number(e.target.value); });
audio.addEventListener('timeupdate', updatePlayback);
audio.addEventListener('play', () => { $('play').textContent = 'Ⅱ'; $('play').setAttribute('aria-label', 'Pause'); });
audio.addEventListener('pause', () => { $('play').textContent = '▶'; $('play').setAttribute('aria-label', 'Play'); });
audio.addEventListener('error', () => { if (audio.getAttribute('src')) toast('Audio preview could not load. Reopen the track to try again.', true); });
audio.addEventListener('ended', run(async () => { if (state.loop) { seek(state.start); await audio.play(); } }));
$('copy-config').addEventListener('click', run(() => copy(JSON.stringify(state.connection.mcp_config, null, 2), 'MCP configuration copied.')));
$('copy-prompt').addEventListener('click', run(() => copy(state.connection.system_prompt, 'Evidence guidance copied.')));
$('mobile-library').addEventListener('click', () => document.querySelector('.sidebar').classList.toggle('open'));
$('close-inspector').addEventListener('click', () => { document.querySelector('.inspector').classList.remove('mobile-active'); $('timeline-title').scrollIntoView({behavior:'smooth', block:'start'}); });
$('library-toggle').addEventListener('click', () => { $('library-list').focus(); });
document.querySelectorAll('.dialog-close').forEach(button => button.addEventListener('click', () => button.closest('dialog').close()));
document.querySelectorAll('dialog').forEach(dialog => dialog.addEventListener('click', e => { if (e.target === dialog) { const r = dialog.getBoundingClientRect(); if (e.clientX < r.left || e.clientX > r.right || e.clientY < r.top || e.clientY > r.bottom) dialog.close(); } }));
document.addEventListener('click', run(async e => {
  const button = e.target.closest('button'); if (!button) return;
  if (button.dataset.track) { if (state.busy) return toast('Finish the current analysis first.'); await loadTrack(button.dataset.track); }
  if (button.dataset.view) { state.view = button.dataset.view; document.querySelectorAll('[data-view]').forEach(b => b.setAttribute('aria-pressed', b === button)); renderTimeline(); }
  if (button.dataset.section) await selectSection(button.dataset.section);
  if (button.dataset.sound) await showSound(button.dataset.sound);
  if (button.dataset.evidence) await showEvidence(button.dataset.evidence);
  if (button.dataset.question) await showQuestion(button.dataset.question);
  if (button.dataset.audition) { const sound = state.g.sound_objects.find(s => s.id === button.dataset.audition); await audition(sound.prototype_crop.start_s, sound.prototype_crop.end_s); await showSound(sound.id); }
  if (button.dataset.start !== undefined) await audition(Number(button.dataset.start), Number(button.dataset.end));
}));
document.addEventListener('keydown', e => {
  if (e.code === 'Escape') document.querySelector('.sidebar').classList.remove('open');
  if ((e.code === 'Space' || e.code === 'KeyK') && state.g && !e.target.closest('input,button,select,textarea,a,dialog')) { e.preventDefault(); run(togglePlay)(); }
});
$('plot-wrap').addEventListener('pointermove', e => {
  const r = $('plot-wrap').getBoundingClientRect(), f = Math.max(0, Math.min(1, (e.clientX - r.left) / r.width));
  $('plot-tooltip').hidden = false; $('plot-tooltip').textContent = `${fmt(state.start + f * (state.end - state.start), true)} · click to seek`;
  $('plot-tooltip').style.left = `${Math.min(r.width - 150, Math.max(0, f * r.width + 9))}px`;
});
$('plot-wrap').addEventListener('pointerleave', () => $('plot-tooltip').hidden = true);
$('plot-wrap').addEventListener('click', e => { const r = $('plot-wrap').getBoundingClientRect(); state.auditionEnd = null; seek(state.start + (e.clientX - r.left) / r.width * (state.end - state.start)); });
document.addEventListener('dragenter', e => { if (e.dataTransfer.types.includes('Files')) { e.preventDefault(); dragDepth++; $('drop-zone').hidden = false; } });
document.addEventListener('dragover', e => { if (e.dataTransfer.types.includes('Files')) e.preventDefault(); });
document.addEventListener('dragleave', () => { if (--dragDepth <= 0) { dragDepth = 0; $('drop-zone').hidden = true; } });
document.addEventListener('drop', e => { e.preventDefault(); dragDepth = 0; $('drop-zone').hidden = true; const file = e.dataTransfer.files[0]; if (file) run(() => analyze(file))(); });
new ResizeObserver(() => { if (state.g) renderTimeline(); }).observe($('plot-wrap'));
$('signal-lines').innerHTML = Array.from({length: 150}, (_, i) => `<i style="height:${8 + (Math.sin(i * .31) ** 2 * .55 + Math.sin(i * 1.7) ** 2 * .45) * (35 + Math.sin(i * .07) ** 2 * 65)}px"></i>`).join('');
run(async () => {
  const [health] = await Promise.all([request('/api/health'), refreshLibrary()]); $('app-version').textContent = `MUSIC GENOME / ${health.version}`;
  const job = sessionStorage.getItem('muvi-job');
  if (job) {
    setBusy(true); screen('analysis-progress');
    try { await watchJob(job); } catch (error) { sessionStorage.removeItem('muvi-job'); screen('welcome'); toast(error.message, true); } finally { setBusy(false); }
  } else if (state.tracks.length) {
    const last = localStorage.getItem('muvi-last-track');
    await loadTrack(state.tracks.find(t => t.track_id === last)?.track_id ?? state.tracks[0].track_id);
  }
})();
