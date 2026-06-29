"""Live web dashboard for EVTV BMS monitor add-on."""

from __future__ import annotations

import json
import logging
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import TYPE_CHECKING
from urllib.parse import urlparse

if TYPE_CHECKING:
    from app.state import BMSMonitorState

log = logging.getLogger(__name__)

DASHBOARD_HTML = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8"/>
<meta name="viewport" content="width=device-width, initial-scale=1"/>
<title>EVTV BMS Monitor</title>
<style>
  :root {
    --bg: #0f1419; --card: #1a2332; --border: #2d3a4d;
    --text: #e7ecf3; --muted: #8b9cb3; --accent: #3b82f6;
    --green: #22c55e; --amber: #f59e0b; --red: #ef4444;
  }
  * { box-sizing: border-box; margin: 0; padding: 0; }
  body { font-family: system-ui, sans-serif; background: var(--bg); color: var(--text); min-height: 100vh; }
  header { padding: 1rem 1.5rem; border-bottom: 1px solid var(--border); display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap; gap: 0.5rem; }
  header h1 { font-size: 1.1rem; font-weight: 600; }
  .sub { font-size: 0.8rem; color: var(--muted); }
  .badge { font-size: 0.75rem; padding: 0.25rem 0.65rem; border-radius: 999px; background: var(--card); border: 1px solid var(--border); }
  .badge.live { color: var(--green); border-color: var(--green); }
  .badge.wait { color: var(--amber); }
  nav { display: flex; gap: 0.25rem; padding: 0.75rem 1rem; border-bottom: 1px solid var(--border); flex-wrap: wrap; }
  nav button { background: transparent; border: 1px solid transparent; color: var(--muted); padding: 0.45rem 0.85rem; border-radius: 8px; cursor: pointer; font-size: 0.85rem; }
  nav button.active { background: var(--card); color: var(--text); border-color: var(--border); }
  main { padding: 1rem; max-width: 960px; margin: 0 auto; }
  .panel { display: none; }
  .panel.active { display: block; }
  .card { background: var(--card); border: 1px solid var(--border); border-radius: 12px; padding: 1rem 1.25rem; margin-bottom: 1rem; }
  .card h2 { font-size: 0.75rem; text-transform: uppercase; letter-spacing: 0.08em; color: var(--muted); margin-bottom: 0.75rem; }
  .metrics { display: grid; grid-template-columns: repeat(2, 1fr); gap: 0.75rem; }
  @media (min-width: 640px) { .metrics.cols-4 { grid-template-columns: repeat(4, 1fr); } }
  .metric { background: var(--bg); border-radius: 8px; padding: 0.75rem; }
  .metric .label { font-size: 0.7rem; color: var(--muted); text-transform: uppercase; }
  .metric .value { font-size: 1.35rem; font-weight: 700; margin-top: 0.2rem; }
  .metric .unit { font-size: 0.85rem; color: var(--muted); font-weight: 400; }
  .soc-row { display: flex; gap: 1.5rem; align-items: center; flex-wrap: wrap; }
  .soc-ring { width: 130px; height: 130px; position: relative; }
  .soc-ring svg { transform: rotate(-90deg); }
  .soc-center { position: absolute; inset: 0; display: flex; flex-direction: column; align-items: center; justify-content: center; }
  .soc-center .big { font-size: 2rem; font-weight: 700; }
  .soc-bar { height: 8px; background: var(--bg); border-radius: 4px; margin-top: 0.5rem; overflow: hidden; }
  .soc-fill { height: 100%; background: linear-gradient(90deg, var(--accent), var(--green)); transition: width 0.4s; }
  .balance-bar { height: 14px; background: var(--bg); border-radius: 7px; overflow: hidden; margin: 0.5rem 0; }
  .balance-fill { height: 100%; background: linear-gradient(90deg, var(--amber), var(--green)); width: 90%; }
  .step { display: flex; gap: 0.5rem; margin-bottom: 0.5rem; font-size: 0.9rem; line-height: 1.45; }
  .step::before { content: "•"; color: var(--muted); }
  .pin-table { background: var(--bg); border-radius: 8px; font-size: 0.85rem; margin: 0.5rem 0; }
  .pin-row { display: flex; padding: 0.5rem 0.75rem; border-bottom: 1px solid var(--border); }
  .pin-row:last-child { border-bottom: none; }
  .code { font-family: ui-monospace, monospace; font-size: 0.8rem; background: var(--bg); padding: 0.75rem; border-radius: 8px; white-space: pre-wrap; }
  .warn { background: rgba(245,158,11,0.12); border: 1px solid var(--amber); border-radius: 8px; padding: 0.75rem; font-size: 0.9rem; margin-top: 1rem; }
  label { display: block; font-size: 0.85rem; margin-bottom: 0.35rem; color: var(--muted); }
  input[type=text], input[type=number] { width: 100%; padding: 0.5rem; border-radius: 8px; border: 1px solid var(--border); background: var(--bg); color: var(--text); margin-bottom: 0.75rem; }
  button.primary { width: 100%; padding: 0.65rem; background: var(--accent); color: #fff; border: none; border-radius: 8px; font-weight: 600; cursor: pointer; margin-top: 0.25rem; }
  button.secondary { padding: 0.5rem 1rem; background: var(--card); border: 1px solid var(--border); color: var(--text); border-radius: 8px; cursor: pointer; }
  .toast { position: fixed; bottom: 1rem; right: 1rem; background: var(--green); color: #fff; padding: 0.5rem 1rem; border-radius: 8px; opacity: 0; transition: opacity 0.3s; pointer-events: none; }
  .toast.show { opacity: 1; }
</style>
</head>
<body>
<header>
  <div>
    <h1 id="packTitle">EVTV BMS Monitor</h1>
    <div class="sub" id="udpInfo">UDP port —</div>
  </div>
  <span class="badge wait" id="connBadge">Connecting…</span>
</header>
<nav>
  <button type="button" class="active" data-tab="dashboard">Dashboard</button>
  <button type="button" data-tab="cells">Cells</button>
  <button type="button" data-tab="sunny">Sunny Island</button>
  <button type="button" data-tab="settings">Settings</button>
</nav>
<main>
  <section class="panel active" id="tab-dashboard">
    <div class="card">
      <div class="soc-row">
        <div class="soc-ring">
          <svg width="130" height="130" viewBox="0 0 130 130">
            <circle cx="65" cy="65" r="54" fill="none" stroke="#2d3a4d" stroke-width="10"/>
            <circle id="socArc" cx="65" cy="65" r="54" fill="none" stroke="#22c55e" stroke-width="10"
              stroke-dasharray="339.292" stroke-dashoffset="339.292" stroke-linecap="round"/>
          </svg>
          <div class="soc-center">
            <span class="big" id="soc">—</span>
            <span class="sub">SOC %</span>
          </div>
        </div>
        <div>
          <div style="font-size:1.25rem;font-weight:600;margin-bottom:0.35rem" id="summary">—</div>
          <div id="bstatus" style="color:var(--muted)">—</div>
          <div class="sub" style="margin-top:0.5rem" id="available">—</div>
        </div>
      </div>
    </div>
    <div class="metrics cols-4">
      <div class="metric"><div class="label">Voltage</div><div class="value"><span id="volts">—</span><span class="unit"> V</span></div></div>
      <div class="metric"><div class="label">Current</div><div class="value"><span id="current">—</span><span class="unit"> A</span></div></div>
      <div class="metric"><div class="label">Power</div><div class="value"><span id="power">—</span><span class="unit"> W</span></div></div>
      <div class="metric"><div class="label">Pack Temp</div><div class="value" style="font-size:1rem" id="temps">—</div></div>
    </div>
    <div class="metrics" style="margin-top:0.75rem">
      <div class="metric"><div class="label">Charge Energy</div><div class="value"><span id="chargeE">—</span><span class="unit"> kWh</span></div></div>
      <div class="metric"><div class="label">Discharge Energy</div><div class="value"><span id="dischargeE">—</span><span class="unit"> kWh</span></div></div>
    </div>
    <div class="metrics" style="margin-top:0.75rem">
      <div class="metric"><div class="label">Freq Shift</div><div class="value"><span id="freqShift">—</span><span class="unit"> V</span></div></div>
      <div class="metric"><div class="label">TCCH Amps</div><div class="value"><span id="tcch">—</span><span class="unit"> A</span></div></div>
    </div>
    <div style="margin-top:0.75rem">
      <button type="button" class="secondary" id="resetEnergy">Reset energy counters</button>
    </div>
  </section>

  <section class="panel" id="tab-cells">
    <div class="card">
      <h2>Cell voltages</h2>
      <div class="metrics cols-4">
        <div class="metric"><div class="label">Lowest</div><div class="value"><span id="lowCell">—</span><span class="unit"> V</span></div></div>
        <div class="metric"><div class="label">Average</div><div class="value"><span id="avgCell">—</span><span class="unit"> V</span></div></div>
        <div class="metric"><div class="label">Highest</div><div class="value"><span id="highCell">—</span><span class="unit"> V</span></div></div>
        <div class="metric"><div class="label">Spread</div><div class="value"><span id="cellSpread">—</span><span class="unit"> V</span></div></div>
      </div>
      <div class="metrics" style="margin-top:0.75rem">
        <div class="metric"><div class="label">Active cells</div><div class="value" id="activeCells">—</div></div>
        <div class="metric"><div class="label">Max cells</div><div class="value" id="maxCells">—</div></div>
      </div>
      <div style="margin-top:1rem">
        <div class="sub">Cell balance</div>
        <div class="balance-bar"><div class="balance-fill" id="balanceFill"></div></div>
      </div>
    </div>
  </section>

  <section class="panel" id="tab-sunny">
    <div class="card">
      <h2>Sunny Island 6048-US setup</h2>
      <p class="sub" style="margin-bottom:1rem">Connect EVTV BMS to SMA Sunny Island over CAN at 500 kbps.</p>
      <div class="step">Move termination plug from ComSync Out → ComSync In on the inverter.</div>
      <div class="step">CAT5 from EVTV Due CAN (3.5mm) to ComSync In.</div>
      <div class="pin-table">
        <div class="pin-row"><span style="width:60px">Pin 2</span><span>CAN_GND</span></div>
        <div class="pin-row"><span style="width:60px">Pin 4</span><span>CAN_H</span></div>
        <div class="pin-row"><span style="width:60px">Pin 5</span><span>CAN_L</span></div>
      </div>
      <div class="step">EVTV Due: CANSPEED=500000, TERMEN=1</div>
      <div class="step">Sunny Island QCG: LiIon_Ext-BMS, firmware 7.3+</div>
      <div class="step">F952 fault = CAN timeout — check wiring and baud.</div>
      <div class="warn">6048-US requires closed-loop BMS on CAN. Voltage-only mode is not supported for lithium.</div>
    </div>
  </section>

  <section class="panel" id="tab-settings">
    <div class="card">
      <h2>Pack</h2>
      <label for="packName">Pack name</label>
      <input type="text" id="packName" maxlength="64"/>
      <label for="packSize">Pack size (kWh)</label>
      <input type="number" id="packSize" min="1" max="500" step="1"/>
      <button type="button" class="primary" id="saveSettings">Save settings</button>
      <p class="sub" style="margin-top:0.75rem">UDP port is configured in the add-on options page.</p>
    </div>
  </section>
</main>
<div class="toast" id="toast">Saved</div>
<script>
const CIRC = 339.292;
function fmt(v, d=1) { return v == null ? '—' : Number(v).toFixed(d); }

document.querySelectorAll('nav button').forEach(btn => {
  btn.addEventListener('click', () => {
    document.querySelectorAll('nav button').forEach(b => b.classList.remove('active'));
    document.querySelectorAll('.panel').forEach(p => p.classList.remove('active'));
    btn.classList.add('active');
    document.getElementById('tab-' + btn.dataset.tab).classList.add('active');
  });
});

async function refresh() {
  try {
    const r = await fetch('/api/status');
    const d = await r.json();
    const L = d.live || {};
    const P = d.pack || {};
    document.getElementById('packTitle').textContent = P.pack_name || 'EVTV BMS';
    document.getElementById('udpInfo').textContent = 'UDP port ' + (d.udp_port || '—');
    const badge = document.getElementById('connBadge');
    const stale = d.last_update && (Date.now()/1000 - d.last_update) < 5;
    badge.textContent = stale ? 'Live' : 'Waiting';
    badge.className = 'badge ' + (stale ? 'live' : 'wait');
    document.getElementById('soc').textContent = fmt(L.state_of_charge, 0);
    const soc = L.state_of_charge || 0;
    document.getElementById('socArc').style.strokeDashoffset = CIRC * (1 - soc/100);
    document.getElementById('summary').textContent = d.summary || '—';
    document.getElementById('bstatus').textContent = L.battery_status || '—';
    document.getElementById('available').textContent =
      L.available_energy != null ? `${fmt(L.available_energy,1)} / ${fmt(P.pack_size_kwh,0)} kWh available` : '—';
    document.getElementById('volts').textContent = fmt(L.volts);
    document.getElementById('current').textContent = fmt(L.current);
    document.getElementById('power').textContent = fmt(L.power, 0);
    const minT = L.min_temp, maxT = L.max_temp;
    document.getElementById('temps').textContent = minT != null && maxT != null ? `${Math.round(minT)}–${Math.round(maxT)} °F` : '—';
    document.getElementById('chargeE').textContent = fmt(L.charge_energy, 3);
    document.getElementById('dischargeE').textContent = fmt(L.discharge_energy, 3);
    document.getElementById('freqShift').textContent = fmt(L.freq_shift_volts, 2);
    document.getElementById('tcch').textContent = fmt(L.tcch_amps, 1);
    document.getElementById('lowCell').textContent = fmt(L.lowest_cell, 3);
    document.getElementById('avgCell').textContent = fmt(L.average_cell, 3);
    document.getElementById('highCell').textContent = fmt(L.highest_cell, 3);
    document.getElementById('cellSpread').textContent = fmt(L.cell_difference, 4);
    document.getElementById('activeCells').textContent = L.active_cells != null ? L.active_cells : '—';
    document.getElementById('maxCells').textContent = L.max_cells != null ? L.max_cells : '—';
    if (L.lowest_cell != null && L.highest_cell != null && L.highest_cell > L.lowest_cell) {
      const avg = L.average_cell ?? (L.lowest_cell + L.highest_cell) / 2;
      const pct = (avg - L.lowest_cell) / (L.highest_cell - L.lowest_cell);
      document.getElementById('balanceFill').style.width = (Math.min(Math.max(pct, 0), 1) * 90 + 5) + '%';
    }
    if (!document.getElementById('packName').value) {
      document.getElementById('packName').value = P.pack_name || '';
      document.getElementById('packSize').value = P.pack_size_kwh || 75;
    }
  } catch (e) {
    document.getElementById('connBadge').textContent = 'Offline';
    document.getElementById('connBadge').className = 'badge wait';
  }
}

document.getElementById('saveSettings').addEventListener('click', async () => {
  const body = {
    pack_name: document.getElementById('packName').value.trim(),
    pack_size_kwh: Number(document.getElementById('packSize').value)
  };
  await fetch('/api/settings', { method: 'POST', headers: {'Content-Type':'application/json'}, body: JSON.stringify(body) });
  const t = document.getElementById('toast');
  t.classList.add('show');
  setTimeout(() => t.classList.remove('show'), 2000);
  refresh();
});

document.getElementById('resetEnergy').addEventListener('click', async () => {
  await fetch('/api/reset-energy', { method: 'POST' });
  refresh();
});

setInterval(refresh, 2000);
refresh();
</script>
</body>
</html>
"""


class DashboardHandler(BaseHTTPRequestHandler):
    state: BMSMonitorState | None = None
    udp_port: int = 6850

    def log_message(self, fmt, *args) -> None:
        log.debug("HTTP " + fmt, *args)

    def _json_response(self, code: int, data: dict) -> None:
        body = json.dumps(data).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self) -> None:
        path = urlparse(self.path).path
        if path in ("/", "/index.html"):
            body = DASHBOARD_HTML.encode()
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
            return
        if path == "/api/status":
            snap = self.state.snapshot()
            snap["udp_port"] = self.udp_port
            self._json_response(200, snap)
            return
        self.send_error(404)

    def do_POST(self) -> None:
        path = urlparse(self.path).path
        length = int(self.headers.get("Content-Length", 0))
        body = self.rfile.read(length) if length else b"{}"

        if path == "/api/reset-energy":
            self.state.reset_energy()
            self._json_response(200, {"ok": True})
            return

        if path != "/api/settings":
            self.send_error(404)
            return

        try:
            updates = json.loads(body)
        except json.JSONDecodeError:
            self._json_response(400, {"error": "invalid json"})
            return

        pack_name = updates.get("pack_name")
        pack_size = updates.get("pack_size_kwh")
        if pack_name is not None:
            pack_name = str(pack_name).strip()[:64]
        if pack_size is not None:
            try:
                pack_size = float(pack_size)
                if pack_size < 1 or pack_size > 500:
                    self._json_response(400, {"error": "pack_size_kwh out of range"})
                    return
            except (TypeError, ValueError):
                self._json_response(400, {"error": "invalid pack_size_kwh"})
                return

        self.state.save_settings(pack_name=pack_name, pack_size_kwh=pack_size)
        self._json_response(200, {"ok": True})


def start_web_dashboard(state: BMSMonitorState, host: str, port: int, udp_port: int) -> ThreadingHTTPServer:
    DashboardHandler.state = state
    DashboardHandler.udp_port = udp_port
    server = ThreadingHTTPServer((host, port), DashboardHandler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    log.info("Web dashboard at http://%s:%s/", host, port)
    return server
