from flask import Flask, jsonify, request, render_template_string
from datetime import datetime

app = Flask(__name__)

tickets = {}
ticket_counter = {"count": 0}

def generate_id():
    ticket_counter["count"] += 1
    return f"INC{ticket_counter['count']:06d}"

HTML = """
<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8"/>
<meta name="viewport" content="width=device-width, initial-scale=1.0"/>
<title>NOC Engineer Desk</title>
<link href="https://fonts.googleapis.com/css2?family=DM+Mono:wght@400;500&family=Fraunces:ital,wght@0,300;0,600;0,800;1,300&display=swap" rel="stylesheet"/>
<style>
  :root {
    --bg: #f4f1ec;
    --surface: #ffffff;
    --surface2: #f9f7f4;
    --border: #e2ddd6;
    --border2: #ccc7be;
    --blue: #1a5fcc;
    --blue-light: #e8f0fc;
    --orange: #c94f1a;
    --orange-light: #fdf0ea;
    --green: #1a7a4a;
    --green-light: #e8f5ee;
    --amber: #a06010;
    --amber-light: #fdf5e0;
    --red: #b91c1c;
    --text: #1c1917;
    --text2: #57534e;
    --muted: #9c9189;
    --font: 'DM Mono', monospace;
    --font-display: 'Fraunces', serif;
  }
  * { box-sizing: border-box; margin: 0; padding: 0; }
  body { background: var(--bg); color: var(--text); font-family: var(--font); font-size: 13px; height: 100vh; overflow: hidden; }

  header {
    background: var(--surface); border-bottom: 1px solid var(--border);
    padding: 0 1.8rem; height: 54px;
    display: flex; align-items: center; justify-content: space-between;
  }
  .logo { font-family: var(--font-display); font-size: 1.1rem; font-weight: 800; color: var(--text); }
  .logo span { color: var(--blue); }
  .header-right { display: flex; align-items: center; gap: 1.4rem; }
  .clock { font-size: 0.7rem; color: var(--muted); }
  .live { display: flex; align-items: center; gap: 5px; font-size: 0.68rem; color: var(--green); font-weight: 500; }
  .live-dot { width: 6px; height: 6px; border-radius: 50%; background: var(--green); animation: blink 2s infinite; }
  .eng-badge { font-size: 0.62rem; padding: 3px 10px; border-radius: 3px; background: var(--blue-light); color: var(--blue); font-weight: 500; border: 1px solid #c7d9f5; }
  @keyframes blink { 0%,100%{opacity:1} 50%{opacity:0.3} }

  .main { display: grid; grid-template-columns: 310px 1fr; height: calc(100vh - 54px); overflow: hidden; }

  .panel-left { background: var(--surface); border-right: 1px solid var(--border); display: flex; flex-direction: column; overflow: hidden; }

  .stats-row { display: grid; grid-template-columns: 1fr 1fr 1fr; border-bottom: 1px solid var(--border); }
  .stat { padding: 0.85rem 0.7rem; text-align: center; border-right: 1px solid var(--border); }
  .stat:last-child { border-right: none; }
  .stat-n { font-family: var(--font-display); font-size: 1.55rem; font-weight: 800; line-height: 1; }
  .stat-l { font-size: 0.58rem; text-transform: uppercase; letter-spacing: 0.08em; color: var(--muted); margin-top: 3px; }
  .n-open { color: var(--orange); }
  .n-total { color: var(--blue); }
  .n-done { color: var(--green); }

  .queue-header { padding: 0.85rem 1.1rem 0.45rem; display: flex; justify-content: space-between; align-items: center; }
  .queue-title { font-size: 0.6rem; text-transform: uppercase; letter-spacing: 0.12em; color: var(--muted); }
  .cnt { background: var(--blue); color: #fff; font-size: 0.58rem; padding: 1px 6px; border-radius: 10px; }

  /* New customer message indicator */
  .has-customer { position: relative; }
  .has-customer::after { content: ''; position: absolute; top: 8px; right: 8px; width: 7px; height: 7px; border-radius: 50%; background: var(--amber); }

  .filter-row { padding: 0 1.1rem 0.65rem; display: flex; gap: 4px; flex-wrap: wrap; }
  .filter-btn { font-family: var(--font); font-size: 0.6rem; padding: 3px 8px; border-radius: 3px; border: 1px solid var(--border); background: transparent; color: var(--muted); cursor: pointer; transition: all 0.1s; }
  .filter-btn.active { background: var(--blue); color: #fff; border-color: var(--blue); }

  .ticket-list { flex: 1; overflow-y: auto; }
  .ticket-list::-webkit-scrollbar { width: 3px; }
  .ticket-list::-webkit-scrollbar-thumb { background: var(--border2); border-radius: 2px; }

  .ticket-item { padding: 0.8rem 1.1rem; border-bottom: 1px solid var(--border); cursor: pointer; transition: background 0.1s; border-left: 3px solid transparent; position: relative; }
  .ticket-item:hover { background: var(--surface2); }
  .ticket-item.active { background: var(--blue-light); border-left-color: var(--blue); }
  .ti-top { display: flex; justify-content: space-between; align-items: center; margin-bottom: 4px; }
  .ti-id { font-size: 0.68rem; font-weight: 500; color: var(--blue); }
  .ti-desc { font-size: 0.76rem; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; margin-bottom: 4px; }
  .ti-meta { display: flex; justify-content: space-between; }
  .ti-ip { font-size: 0.63rem; color: var(--muted); }
  .ti-time { font-size: 0.6rem; color: var(--muted); }
  /* Amber dot for unread customer messages */
  .cust-dot { display: inline-block; width: 6px; height: 6px; border-radius: 50%; background: var(--amber); margin-left: 5px; vertical-align: middle; title: 'Customer update'; }

  .p-bar { display: inline-block; width: 7px; height: 7px; border-radius: 1px; margin-right: 4px; vertical-align: middle; }
  .p-critical { background: var(--red); }
  .p-high { background: var(--orange); }
  .p-medium { background: var(--amber); }
  .p-low { background: var(--green); }

  .spill { font-size: 0.58rem; padding: 2px 6px; border-radius: 2px; font-weight: 500; white-space: nowrap; }
  .s-open { background: var(--orange-light); color: var(--orange); }
  .s-in_progress { background: var(--blue-light); color: var(--blue); }
  .s-resolved { background: var(--green-light); color: var(--green); }
  .s-closed { background: var(--surface2); color: var(--muted); border: 1px solid var(--border); }

  .panel-right { display: flex; flex-direction: column; overflow: hidden; }
  .detail-area { flex: 1; overflow-y: auto; padding: 1.6rem 2rem; }
  .detail-area::-webkit-scrollbar { width: 3px; }
  .detail-area::-webkit-scrollbar-thumb { background: var(--border2); border-radius: 2px; }

  .empty-state { height: 100%; display: flex; flex-direction: column; align-items: center; justify-content: center; gap: 0.5rem; color: var(--muted); }
  .empty-state .e-title { font-family: var(--font-display); font-size: 1rem; font-weight: 300; font-style: italic; color: var(--text2); }

  .dh { display: flex; justify-content: space-between; align-items: flex-start; margin-bottom: 1.3rem; }
  .dh-left .d-id { font-family: var(--font-display); font-size: 1.45rem; font-weight: 800; color: var(--blue); }
  .dh-left .d-desc { font-size: 0.85rem; color: var(--text2); margin-top: 3px; }

  .detail-grid { display: grid; grid-template-columns: repeat(3, 1fr); gap: 0.7rem; margin-bottom: 1.3rem; }
  .dc { background: var(--surface2); border: 1px solid var(--border); border-radius: 4px; padding: 0.65rem 0.85rem; }
  .dc label { font-size: 0.57rem; text-transform: uppercase; letter-spacing: 0.1em; color: var(--muted); display: block; margin-bottom: 3px; }
  .dc .dv { font-size: 0.8rem; font-weight: 500; }
  .dc .dv.blue { color: var(--blue); }

  .log-header { font-size: 0.6rem; text-transform: uppercase; letter-spacing: 0.12em; color: var(--muted); margin-bottom: 1rem; padding-bottom: 0.5rem; border-bottom: 1px solid var(--border); display: flex; justify-content: space-between; align-items: center; }
  .log-legend { display: flex; gap: 1rem; }
  .legend-item { display: flex; align-items: center; gap: 4px; font-size: 0.58rem; color: var(--muted); }
  .legend-dot { width: 8px; height: 8px; border-radius: 50%; }

  /* Two-sided bubbles */
  .update-row { display: flex; gap: 0.7rem; margin-bottom: 0.85rem; }
  .update-row.engineer { flex-direction: row; }
  .update-row.customer { flex-direction: row-reverse; }

  .update-avatar { width: 26px; height: 26px; border-radius: 50%; flex-shrink: 0; display: flex; align-items: center; justify-content: center; font-size: 0.58rem; font-weight: 600; margin-top: 2px; }
  .av-eng { background: var(--blue-light); color: var(--blue); border: 1px solid #c7d9f5; }
  .av-cust { background: var(--amber-light); color: var(--amber); border: 1px solid #f0ddb0; }

  .update-bubble { max-width: 68%; }
  .bubble-header { font-size: 0.58rem; color: var(--muted); margin-bottom: 3px; }
  .bubble-header .who { font-weight: 500; color: var(--text2); }
  .update-row.customer .bubble-header { text-align: right; }

  .bubble-body { border: 1px solid var(--border); border-radius: 6px; padding: 0.55rem 0.75rem; font-size: 0.78rem; line-height: 1.55; color: var(--text); background: var(--surface); }
  .update-row.engineer .bubble-body { border-radius: 2px 6px 6px 6px; }
  .update-row.customer .bubble-body { border-radius: 6px 2px 6px 6px; background: var(--amber-light); border-color: #f0ddb0; }

  .bubble-status { font-size: 0.57rem; margin-top: 4px; }

  /* Engineer reply toolbar */
  .toolbar { background: var(--surface); border-top: 1px solid var(--border); padding: 0.85rem 1.8rem; }
  .toolbar-label { font-size: 0.58rem; text-transform: uppercase; letter-spacing: 0.1em; color: var(--muted); margin-bottom: 0.5rem; }
  .toolbar-row { display: flex; gap: 0.55rem; align-items: center; }
  .toolbar input, .toolbar select {
    font-family: var(--font); font-size: 0.76rem; padding: 0.42rem 0.65rem;
    border: 1px solid var(--border); border-radius: 4px; background: var(--surface2);
    color: var(--text); outline: none; transition: border-color 0.12s;
  }
  .toolbar input:focus, .toolbar select:focus { border-color: var(--blue); }
  .toolbar select option { background: var(--surface); }

  .btn { font-family: var(--font); font-size: 0.7rem; font-weight: 500; padding: 0.42rem 0.95rem; border-radius: 4px; border: none; cursor: pointer; transition: all 0.1s; }
  .btn-blue { background: var(--blue); color: #fff; }
  .btn-blue:hover { background: #154faa; }
  .btn-outline { background: transparent; border: 1px solid var(--border); color: var(--text2); }
  .btn-outline:hover { border-color: var(--blue); color: var(--blue); }
  .btn-green { background: var(--green); color: #fff; }
  .btn-green:hover { background: #155f3a; }

  .overlay { position: fixed; inset: 0; background: rgba(28,25,23,0.4); display: flex; align-items: center; justify-content: center; z-index: 200; }
  .overlay.hidden { display: none; }
  .modal { background: var(--surface); border: 1px solid var(--border); border-radius: 6px; padding: 1.7rem; width: 460px; box-shadow: 0 6px 28px rgba(0,0,0,0.1); }
  .modal h2 { font-family: var(--font-display); font-size: 0.95rem; font-weight: 800; color: var(--text); margin-bottom: 1.2rem; }
  .fr { margin-bottom: 0.8rem; }
  .fr label { display: block; font-size: 0.58rem; text-transform: uppercase; letter-spacing: 0.1em; color: var(--muted); margin-bottom: 0.3rem; }
  .fr input, .fr select, .fr textarea { width: 100%; font-family: var(--font); font-size: 0.78rem; padding: 0.48rem 0.65rem; border: 1px solid var(--border); border-radius: 4px; background: var(--surface2); color: var(--text); outline: none; }
  .fr input:focus, .fr select:focus, .fr textarea:focus { border-color: var(--blue); }
  .fr textarea { resize: vertical; min-height: 70px; }
  .modal-actions { display: flex; gap: 0.55rem; justify-content: flex-end; margin-top: 1.1rem; }

  .no-items { padding: 2rem; text-align: center; color: var(--muted); font-size: 0.76rem; }
  @keyframes fadeUp { from{opacity:0;transform:translateY(5px)} to{opacity:1;transform:translateY(0)} }
  .ticket-item, .update-row { animation: fadeUp 0.16s ease; }

  /* Customer update banner */
  .cust-banner { background: var(--amber-light); border: 1px solid #f0ddb0; border-radius: 4px; padding: 0.5rem 0.8rem; margin-bottom: 1rem; font-size: 0.72rem; color: var(--amber); display: flex; align-items: center; gap: 0.5rem; }
  .cust-banner strong { font-weight: 600; }
</style>
</head>
<body>

<header>
  <div class="logo">NOC <span>Engineer Desk</span></div>
  <div class="header-right">
    <div class="eng-badge">Engineer View</div>
    <div class="live"><div class="live-dot"></div> Live</div>
    <div class="clock" id="clock-el"></div>
  </div>
</header>

<div class="main">
  <div class="panel-left">
    <div class="stats-row">
      <div class="stat"><div class="stat-n n-open" id="s-open">0</div><div class="stat-l">Open</div></div>
      <div class="stat"><div class="stat-n n-total" id="s-total">0</div><div class="stat-l">Total</div></div>
      <div class="stat"><div class="stat-n n-done" id="s-done">0</div><div class="stat-l">Resolved</div></div>
    </div>
    <div class="queue-header">
      <span class="queue-title">Incident Queue</span>
      <span class="cnt" id="q-count">0</span>
    </div>
    <div class="filter-row">
      <button class="filter-btn active" onclick="setFilter('all',this)">All</button>
      <button class="filter-btn" onclick="setFilter('open',this)">Open</button>
      <button class="filter-btn" onclick="setFilter('in_progress',this)">In Progress</button>
      <button class="filter-btn" onclick="setFilter('resolved',this)">Resolved</button>
    </div>
    <div class="ticket-list" id="ticket-list"></div>
  </div>

  <div class="panel-right">
    <div class="detail-area" id="detail-area">
      <div class="empty-state">
        <div class="e-title">Select an incident to view details</div>
        <div style="font-size:0.73rem">Tickets created by customers appear here automatically</div>
      </div>
    </div>

    <!-- Engineer reply toolbar -->
    <div class="toolbar" id="update-toolbar" style="display:none">
      <div class="toolbar-label">Engineer Reply</div>
      <div class="toolbar-row">
        <select id="upd-status" style="width:148px">
          <option value="">Status unchanged</option>
          <option value="open">Open</option>
          <option value="in_progress">In Progress</option>
          <option value="resolved">Resolved</option>
          <option value="closed">Closed</option>
        </select>
        <input id="upd-engineer" placeholder="Your name" style="width:148px"/>
        <input id="upd-text" placeholder="Type your update for the customer..." style="flex:1"/>
        <button class="btn btn-blue" onclick="postEngineerUpdate()">Post Update</button>
        <button class="btn btn-green" onclick="openModal()">New Ticket</button>
      </div>
    </div>
    <div class="toolbar" id="empty-toolbar">
      <div class="toolbar-row" style="justify-content:flex-end">
        <button class="btn btn-green" onclick="openModal()">New Ticket</button>
      </div>
    </div>
  </div>
</div>

<!-- New Ticket Modal -->
<div class="overlay hidden" id="modal">
  <div class="modal">
    <h2>New Incident</h2>
    <div class="fr"><label>Device IP</label><input id="f-ip" placeholder="10.x.x.x"/></div>
    <div class="fr"><label>Issue Description</label><textarea id="f-desc" placeholder="Describe the issue..."></textarea></div>
    <div class="fr"><label>Priority</label>
      <select id="f-priority">
        <option value="critical">Critical</option>
        <option value="high">High</option>
        <option value="medium" selected>Medium</option>
        <option value="low">Low</option>
      </select>
    </div>
    <div class="fr"><label>Assigned Engineer</label><input id="f-eng" placeholder="Optional"/></div>
    <div class="modal-actions">
      <button class="btn btn-outline" onclick="closeModal()">Cancel</button>
      <button class="btn btn-blue" onclick="createTicket()">Open Incident</button>
    </div>
  </div>
</div>

<script>
let tickets = [];
let selectedId = null;
let activeFilter = 'all';

async function load() {
  const res = await fetch('/api/tickets');
  tickets = await res.json();
  renderList();
  updateStats();
  if (selectedId) {
    const t = tickets.find(t => t.id === selectedId);
    if (t) renderDetail(t);
  }
}

function updateStats() {
  const open = tickets.filter(t => ['open','in_progress'].includes(t.status)).length;
  const done = tickets.filter(t => ['resolved','closed'].includes(t.status)).length;
  document.getElementById('s-open').textContent = open;
  document.getElementById('s-total').textContent = tickets.length;
  document.getElementById('s-done').textContent = done;
  document.getElementById('q-count').textContent = tickets.length;
}

function hasUnreadCustomer(t) {
  return (t.updates || []).some(u => u.source === 'customer');
}

function setFilter(f, btn) {
  activeFilter = f;
  document.querySelectorAll('.filter-btn').forEach(b => b.classList.remove('active'));
  btn.classList.add('active');
  renderList();
}

function renderList() {
  const el = document.getElementById('ticket-list');
  let list = [...tickets].reverse();
  if (activeFilter !== 'all') list = list.filter(t => t.status === activeFilter);
  if (!list.length) { el.innerHTML = '<div class="no-items">No incidents match this filter.</div>'; return; }
  el.innerHTML = list.map(t => {
    const custDot = hasUnreadCustomer(t) ? '<span class="cust-dot" title="Customer has added info"></span>' : '';
    return `
    <div class="ticket-item ${t.id === selectedId ? 'active' : ''}" onclick="select('${t.id}')">
      <div class="ti-top">
        <span class="ti-id">${t.id}${custDot}</span>
        <span class="spill s-${t.status}">${t.status.replace('_',' ')}</span>
      </div>
      <div class="ti-desc"><span class="p-bar p-${t.priority}"></span>${t.description}</div>
      <div class="ti-meta"><span class="ti-ip">${t.device_ip}</span><span class="ti-time">${fmt(t.created_at)}</span></div>
    </div>`;
  }).join('');
}

function select(id) {
  selectedId = id;
  const t = tickets.find(t => t.id === id);
  renderDetail(t);
  renderList();
}

function renderDetail(t) {
  document.getElementById('empty-toolbar').style.display = 'none';
  document.getElementById('update-toolbar').style.display = 'block';

  const allUpdates = t.updates || [];
  const customerUpdates = allUpdates.filter(u => u.source === 'customer');

  // Banner if there are customer messages
  const bannerHtml = customerUpdates.length
    ? `<div class="cust-banner"><strong>Customer has added ${customerUpdates.length} message(s)</strong> — review the conversation below and reply.</div>`
    : '';

  const updatesHtml = allUpdates.length
    ? allUpdates.map(u => {
        const isCust = u.source === 'customer';
        const side = isCust ? 'customer' : 'engineer';
        const initials = (u.engineer || (isCust ? 'CU' : 'EN')).slice(0,2).toUpperCase();
        const who = u.engineer || (isCust ? 'Customer' : 'Engineer');
        const statusTag = u.status_change
          ? `<div class="bubble-status"><span class="spill s-${u.status_change}">Status: ${u.status_change.replace('_',' ')}</span></div>`
          : '';
        return `
          <div class="update-row ${side}">
            <div class="update-avatar av-${isCust ? 'cust' : 'eng'}">${initials}</div>
            <div class="update-bubble">
              <div class="bubble-header"><span class="who">${who}</span> &middot; ${fmt(u.timestamp)}</div>
              <div class="bubble-body">${u.text}</div>
              ${statusTag}
            </div>
          </div>`;
      }).join('')
    : '<div style="color:var(--muted);font-size:0.76rem;padding:0.4rem 0">No activity yet. Post the first update below.</div>';

  document.getElementById('detail-area').innerHTML = `
    <div class="dh">
      <div class="dh-left">
        <div class="d-id">${t.id}</div>
        <div class="d-desc">${t.description}</div>
      </div>
      <span class="spill s-${t.status}" style="font-size:0.65rem;padding:3px 9px">${t.status.replace('_',' ')}</span>
    </div>
    <div class="detail-grid">
      <div class="dc"><label>Device IP</label><div class="dv blue">${t.device_ip}</div></div>
      <div class="dc"><label>Priority</label><div class="dv"><span class="p-bar p-${t.priority}"></span>${t.priority}</div></div>
      <div class="dc"><label>Engineer</label><div class="dv">${t.assigned_engineer || 'Unassigned'}</div></div>
      <div class="dc"><label>Opened</label><div class="dv">${fmt(t.created_at)}</div></div>
      <div class="dc"><label>Last Update</label><div class="dv">${t.updated_at ? fmt(t.updated_at) : 'None'}</div></div>
      <div class="dc"><label>Updates</label><div class="dv">${allUpdates.length}</div></div>
    </div>
    ${bannerHtml}
    <div class="log-header">
      <span>Activity Log — ${allUpdates.length} entries</span>
      <div class="log-legend">
        <div class="legend-item"><div class="legend-dot" style="background:var(--blue)"></div>Engineer</div>
        <div class="legend-item"><div class="legend-dot" style="background:var(--amber)"></div>Customer</div>
      </div>
    </div>
    ${updatesHtml}
  `;
  const da = document.getElementById('detail-area');
  setTimeout(() => { da.scrollTop = da.scrollHeight; }, 50);
}

async function postEngineerUpdate() {
  if (!selectedId) return;
  const status = document.getElementById('upd-status').value;
  const engineer = document.getElementById('upd-engineer').value.trim();
  const text = document.getElementById('upd-text').value.trim();
  if (!text) { alert('Please enter an update note.'); return; }
  await fetch(`/api/tickets/${selectedId}/update`, {
    method: 'POST', headers: {'Content-Type':'application/json'},
    body: JSON.stringify({ text, engineer, status: status || undefined, source: 'engineer' })
  });
  document.getElementById('upd-status').value = '';
  document.getElementById('upd-text').value = '';
  await load();
}

function openModal() { document.getElementById('modal').classList.remove('hidden'); }
function closeModal() { document.getElementById('modal').classList.add('hidden'); }

async function createTicket() {
  const ip = document.getElementById('f-ip').value.trim();
  const desc = document.getElementById('f-desc').value.trim();
  const priority = document.getElementById('f-priority').value;
  const eng = document.getElementById('f-eng').value.trim();
  if (!ip || !desc) { alert('Device IP and description required.'); return; }
  const res = await fetch('/api/tickets', {
    method: 'POST', headers: {'Content-Type':'application/json'},
    body: JSON.stringify({ device_ip: ip, description: desc, priority, assigned_engineer: eng || null })
  });
  const ticket = await res.json();
  closeModal();
  ['f-ip','f-desc','f-eng'].forEach(id => document.getElementById(id).value = '');
  await load();
  select(ticket.id);
}

function fmt(iso) {
  if (!iso) return '-';
  const d = new Date(iso);
  return d.toLocaleString('en-GB', {day:'2-digit',month:'short',hour:'2-digit',minute:'2-digit'});
}

function tick() { document.getElementById('clock-el').textContent = new Date().toLocaleTimeString('en-GB'); }
load();
setInterval(load, 5000);
setInterval(tick, 1000);
tick();
document.getElementById('update-toolbar').style.display = 'none';
</script>
</body>
</html>
"""

# ─── REST API (used by both GUI and MCP) ──────────────────────────────────────

@app.route("/")
def index():
    return render_template_string(HTML)

@app.route("/api/tickets", methods=["GET"])
def list_tickets():
    return jsonify(list(tickets.values()))

@app.route("/api/tickets", methods=["POST"])
def create_ticket():
    data = request.json
    tid = generate_id()
    ticket = {
        "id": tid,
        "device_ip": data.get("device_ip", "unknown"),
        "description": data.get("description", ""),
        "priority": data.get("priority", "medium"),
        "status": "open",
        "assigned_engineer": data.get("assigned_engineer"),
        "created_at": datetime.now().isoformat(),
        "updated_at": None,
        "updates": []
    }
    tickets[tid] = ticket
    return jsonify(ticket), 201

@app.route("/api/tickets/<tid>", methods=["GET"])
def get_ticket(tid):
    t = tickets.get(tid)
    if not t:
        return jsonify({"error": f"Ticket {tid} not found"}), 404
    return jsonify(t)

@app.route("/api/tickets/<tid>/update", methods=["POST"])
def update_ticket(tid):
    """
    Accepts updates from both the engineer GUI (source='engineer')
    and the customer MCP tools (source='customer').
    The GUI only posts source='engineer'. The MCP only posts source='customer'.
    """
    t = tickets.get(tid)
    if not t:
        return jsonify({"error": f"Ticket {tid} not found"}), 404
    data = request.json
    entry = {
        "timestamp": datetime.now().isoformat(),
        "engineer": data.get("engineer", ""),
        "text": data.get("text", ""),
        "source": data.get("source", "engineer"),
        "status_change": None,
    }
    # Only engineers can change status (source == 'engineer')
    if data.get("status") and data.get("source", "engineer") == "engineer":
        entry["status_change"] = data["status"]
        t["status"] = data["status"]
    if data.get("assigned_engineer"):
        t["assigned_engineer"] = data["assigned_engineer"]
    t["updates"].append(entry)
    t["updated_at"] = entry["timestamp"]
    return jsonify(t)

@app.route("/api/tickets/<tid>/status", methods=["PATCH"])
def patch_status(tid):
    t = tickets.get(tid)
    if not t:
        return jsonify({"error": f"Ticket {tid} not found"}), 404
    data = request.json
    if "status" in data:
        t["status"] = data["status"]
    t["updated_at"] = datetime.now().isoformat()
    return jsonify(t)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8765, debug=False)
