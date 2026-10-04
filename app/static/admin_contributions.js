const byId = id => document.getElementById(id);
const ui = {records: null, view: null, draft: null, dirty: false, busy: false, selection: 0};
const actions = ['review-augment','review-save','review-approve','review-return','review-withdraw'];
function element(tag, text, className) {
  const el = document.createElement(tag);
  if (text !== undefined) el.textContent = text;
  if (className) el.className = className;
  return el;
}
function message(text) { byId('review-status').textContent = text; }
function date(value) { return value ? new Date(value).toLocaleString() : 'Not recorded'; }
async function api(path, body) {
  const response = await fetch(path, {method: body === undefined ? 'GET' : 'POST', headers:{'Content-Type':'application/json'}, ...(body === undefined ? {} : {body:JSON.stringify(body)})});
  const data = await response.json().catch(() => ({}));
  if (response.status === 401) window.location.assign('/login?next=/admin/contributions');
  if (!response.ok) throw Error(typeof data.detail === 'string' ? data.detail : JSON.stringify(data.detail || 'Request failed'));
  return data;
}
function path(suffix='') { return `/api/admin/contributions/${encodeURIComponent(ui.view.case_id)}/${ui.view.version}${suffix}`; }
function busy(value) {
  ui.busy = value;
  for (const id of actions) byId(id).disabled = value;
  byId('review-refresh').disabled = value;
  byId('review-filter').disabled = value;
  document.querySelectorAll('#review-rows button').forEach(button => { button.disabled = value; });
  document.querySelectorAll('#review-editors input, #review-editors textarea').forEach(input => { input.disabled = value; });
  if (!value && ui.view) {
    byId('review-approve').disabled = ui.dirty || !(ui.view.validation?.passed);
    byId('review-augment').disabled = !ui.view.original_available;
    byId('review-withdraw').disabled = ui.view.status !== 'published';
  }
}
function rows() {
  const records = ui.records?.[byId('review-filter').value] || [];
  byId('review-rows').replaceChildren();
  if (!records.length) {
    const row = element('tr'); const cell = element('td','No cases in this view.'); cell.colSpan = 6; row.append(cell); byId('review-rows').append(row);
  }
  for (const record of records) {
    const row = element('tr');
    for (const text of [`${record.title} · v${record.version}`,record.contributor_name || 'Not recorded',(record.firm_tags || []).join(', ') || 'Not recorded',date(record.contributed_at),record.status.replaceAll('_',' ')]) row.append(element('td',text));
    const cell = element('td'); const button = element('button','Review','btn btn-secondary btn-sm');
    button.addEventListener('click', () => open(record.case_id, record.version)); cell.append(button); row.append(cell); byId('review-rows').append(row);
  }
}
async function load() { ui.records = await api('/api/admin/contributions'); rows(); }
const labels = {candidate_opening:'Case setup', objective_function:'Decision and objective',case_essence:'Cause, insight and learning',common_traps:'Plausible wrong paths',core_mechanism:'Underlying cause',primary_metric:'Success metric',facts:'Evidence and exhibits',conversation_policy:'Interviewer guidance',provenance:'Firm and interview details'};
const label = key => labels[key] || key.replaceAll('_',' ').replace(/^./, c=>c.toUpperCase());
const protectedKeys = new Set(['schema_version','case_id','source','contributor_id','contributor_name','attribution_mode','contributed_at','metadata_source','firm_tags','synthesized_fields']);
function editor(parent, object, key, caption) {
  if (protectedKeys.has(key)) return;
  const value = object[key];
  if (value && typeof value === 'object' && !Array.isArray(value)) {
    const details = element('details', undefined,'card'); details.open = ['candidate_opening','objective_function','case_essence'].includes(key);
    details.append(element('summary',caption || label(key)));
    for (const child of Object.keys(value)) editor(details,value,child);
    parent.append(details); return;
  }
  if (Array.isArray(value) && value.some(v => v && typeof v === 'object')) {
    const details = element('details', undefined,'card'); details.append(element('summary',caption || label(key)));
    value.forEach((item,index) => editor(details,value,index,item.id || `Item ${index+1}`));
    parent.append(details); return;
  }
  const wrap = element('label',caption || label(String(key)),'review-field');
  const input = element(typeof value === 'number' ? 'input' : 'textarea');
  if (typeof value === 'number') input.type = 'number';
  input.value = Array.isArray(value) ? value.join('\n') : value ?? '';
  input.addEventListener('input', () => {
    object[key] = Array.isArray(value) ? input.value.split('\n').filter(Boolean) : typeof value === 'number' ? Number(input.value) : input.value;
    ui.dirty = true; busy(false); message('Unsaved edits. Save the draft before approving it.');
  });
  wrap.append(input); parent.append(wrap);
}
function render(view) {
  ui.view = view; ui.draft = structuredClone(view.package); ui.dirty = false;
  byId('review-detail').hidden = false;
  byId('review-title').textContent = `${view.title} · version ${view.version}`;
  byId('review-meta').textContent = `${view.contributor_name || 'Contributor not recorded'}${view.contributor_email ? ` (${view.contributor_email})` : ''} · ${date(view.contributed_at)} · ${view.status.replaceAll('_',' ')}`;
  byId('review-original').replaceChildren();
  if (!view.original_available) byId('review-original').append(element('p','The original contribution was not retained for this legacy case. The existing case draft is available on the right.'));
  for (const section of view.original_sections) {
    const card = element('article',undefined,'card'); card.append(element('h3',section.label));
    card.append(element('p',(Array.isArray(section.value) ? section.value.join('\n') : section.value) || 'Not recorded'));
    if (section.discussion) card.append(element('p',`Contributor finished this section: “${section.discussion.quote}”`,'muted'));
    for (const evidence of section.evidence) if (evidence.evidence_quote) card.append(element('blockquote',evidence.evidence_quote));
    byId('review-original').append(card);
  }
  byId('review-transcript').replaceChildren(...view.transcript.map(turn => element('p',`${turn.role === 'agent' ? 'Leo' : 'Contributor'}: ${turn.content}`)));
  byId('review-editors').replaceChildren();
  for (const key of Object.keys(ui.draft.case)) editor(byId('review-editors'),ui.draft.case,key);
  editor(byId('review-editors'),ui.draft,'facts','Evidence and exhibits');
  editor(byId('review-editors'),ui.draft,'conversation_policy','Interviewer guidance');
  const findings = view.validation?.findings || [];
  byId('review-validation').replaceChildren(element('strong',view.validation?.passed ? 'Validation passed — ready for your review' : 'Resolve validation errors before approving'), ...findings.map(f=>element('p',`${f.severity}: ${f.message}`)));
  busy(false);
}
async function open(caseId, version) {
  if (ui.busy) return;
  if (ui.dirty && !window.confirm('Discard unsaved edits and open this case?')) return;
  const token = ++ui.selection; busy(true);
  try { const view = await api(`/api/admin/contributions/${encodeURIComponent(caseId)}/${version}`); if (token === ui.selection) {render(view); message('Review the original account and AI draft below.');} }
  catch(error) { message(error.message); }
  finally { if (token === ui.selection) busy(false); }
}
async function act(action) {
  if (ui.busy || !ui.view) return;
  if (ui.dirty && action !== 'save') { message('Save your edits before taking this action.'); return; }
  busy(true); message(action === 'augment' ? 'Building a new AI draft from the original contribution…' : 'Saving…');
  try {
    if (action === 'save') {
      render(await api(path('/draft'), {expected_revision:ui.view.revision,case:ui.draft.case,facts:ui.draft.facts,conversation_policy:ui.draft.conversation_policy}));
    } else if (action === 'augment') {
      render(await api(path('/augment'), {expected_revision:ui.view.revision}));
    } else {
      await api(path('/decide'),{decision:action,note:byId('review-note').value,expected_revision:ui.view.revision});
      render(await api(path()));
    }
    await load(); message(action === 'publish' ? 'Approved. This case is now in the case library.' : 'Saved. The original contribution is preserved.');
  } catch(error) { message(error.message); }
  finally { busy(false); }
}
byId('review-save').addEventListener('click',()=>act('save'));
byId('review-augment').addEventListener('click',()=>act('augment'));
byId('review-approve').addEventListener('click',()=>act('publish'));
byId('review-return').addEventListener('click',()=>act('return'));
byId('review-withdraw').addEventListener('click',()=>act('withdraw'));
byId('review-filter').addEventListener('change',rows);
byId('review-refresh').addEventListener('click',()=>load().catch(e=>message(e.message)));
load().catch(e=>message(e.message));
