"""Live web dashboard for BMS data and runtime settings."""

from __future__ import annotations

import json
import logging
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import TYPE_CHECKING
from urllib.parse import urlparse

from app.live_settings import LIVE_FIELDS

if TYPE_CHECKING:
    from app.live_settings import LiveSettings

log = logging.getLogger(__name__)

DASHBOARD_HTML = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8"/>
<meta name="viewport" content="width=device-width, initial-scale=1"/>
<title>Tesla BMS + Sunny Island</title>
<style>
  :root {
    --bg: #0f1419; --card: #1a2332; --border: #2d3a4d;
    --text: #e7ecf3; --muted: #8b9cb3; --accent: #3b82f6;
    --green: #22c55e; --amber: #f59e0b; --red: #ef4444;
  }
  * { box-sizing: border-box; margin: 0; padding: 0; }
  body { font-family: system-ui, sans-serif; background: var(--bg); color: var(--text); min-height: 100vh; }
  header { padding: 1rem 1.5rem; border-bottom: 1px solid var(--border); display: flex; justify-content: space-between; align-items: center; }
  header h1 { font-size: 1.1rem; font-weight: 600; }
  .status { font-size: 0.8rem; color: var(--muted); }
  .status.ok { color: var(--green); }
  main { padding: 1rem; max-width: 1100px; margin: 0 auto; display: grid; gap: 1rem; }
  @media (min-width: 768px) { main { grid-template-columns: 1fr 1fr; } }
  .card { background: var(--card); border: 1px solid var(--border); border-radius: 12px; padding: 1rem 1.25rem; }
  .card h2 { font-size: 0.75rem; text-transform: uppercase; letter-spacing: 0.08em; color: var(--muted); margin-bottom: 0.75rem; }
  .metrics { display: grid; grid-template-columns: repeat(2, 1fr); gap: 0.75rem; }
  .metric { background: var(--bg); border-radius: 8px; padding: 0.75rem; }
  .metric .label { font-size: 0.7rem; color: var(--muted); text-transform: uppercase; }
  .metric .value { font-size: 1.5rem; font-weight: 700; margin-top: 0.2rem; }
  .metric .unit { font-size: 0.85rem; color: var(--muted); font-weight: 400; }
  .soc-bar { height: 8px; background: var(--bg); border-radius: 4px; margin-top: 0.5rem; overflow: hidden; }
  .soc-fill { height: 100%; background: linear-gradient(90deg, var(--accent), var(--green)); transition: width 0.4s; }
  .setting { margin-bottom: 1rem; }
  .setting label { display: flex; justify-content: space-between; font-size: 0.85rem; margin-bottom: 0.35rem; }
  .setting .val { color: var(--accent); font-weight: 600; }
  input[type=range] { width: 100%; accent-color: var(--accent); }
  .toggle { display: flex; align-items: center; justify-content: space-between; padding: 0.5rem 0; }
  .toggle input { width: 2.5rem; height: 1.4rem; accent-color: var(--accent); }
  .pack-info { font-size: 0.8rem; color: var(--muted); line-height: 1.6; }
  .pack-info strong { color: var(--text); }
  button.save { width: 100%; margin-top: 0.5rem; padding: 0.65rem; background: var(--accent); color: #fff; border: none; border-radius: 8px; font-weight: 600; cursor: pointer; }
  button.save:disabled { opacity: 0.5; }
  .toast { position: fixed; bottom: 1rem; right: 1rem; background: var(--green); color: #fff; padding: 0.5rem 1rem; border-radius: 8px; font-size: 0.85rem; opacity: 0; transition: opacity 0.3s; pointer-events: none; }
  .toast.show { opacity: 1; }
</style>
</head>
<body>
<header>
  <h1>Tesla BMS + Sunny Island 6048</h1>
  <span class="status" id="conn">Connecting…</span>
</header>
<main>
  <section class="card">
    <h2>Live pack</h2>
    <div class="metrics">
      <div class="metric" style="grid-column: span 2">
        <div class="label">State of charge</div>
        <div class="value"><span id="soc">—</span><span class="unit"> %</span></div>
        <div class="soc-bar"><div class="soc-fill" id="socBar" style="width:0%"></div></div>
      </div>
      <div class="metric"><div class="label">Voltage</div><div class="value"><span id="volts">—</span><span class="unit"> V</span></div></div>
      <div class="metric"><div class="label">Current</div><div class="value"><span id="current">—</span><span class="unit"> A</span></div></div>
      <div class="metric"><div class="label">Power</div><div class="value"><span id="power">—</span><span class="unit"> W</span></div></div>
      <div class="metric"><div class="label">Status</div><div class="value" style="font-size:1rem" id="bstatus">—</div></div>
      <div class="metric"><div class="label">Low / High cell</div><div class="value" style="font-size:1rem"><span id="lowCell">—</span> / <span id="highCell">—</span><span class="unit"> V</span></div></div>
    </div>
    <div class="pack-info" style="margin-top:1rem" id="packInfo"></div>
    <div class="pack-info" style="margin-top:0.5rem" id="smaOut"></div>
  </section>
  <section class="card">
    <h2>Live settings</h2>
    <div id="settings"></div>
    <button class="save" id="saveBtn" disabled>No changes</button>
  </section>
</main>
<div class="toast" id="toast">Settings applied</div>
<script>
const NUM_FIELDS = %NUM_FIELDS%;
let pending = {};
let serverSettings = {};

function fmt(v, d=1) { return v == null ? '—' : Number(v).toFixed(d); }

function renderSettings(settings) {
  serverSettings = settings;
  const el = document.getElementById('settings');
  el.innerHTML = '';
  for (const [key, meta] of Object.entries(NUM_FIELDS)) {
    const val = pending[key] ?? settings[key];
    if (meta.type === 'switch') {
      el.innerHTML += `<div class="toggle"><label>${meta.label}</label>
        <input type="checkbox" data-key="${key}" ${val ? 'checked' : ''}></div>`;
    } else {
      el.innerHTML += `<div class="setting"><label><span>${meta.label}</span>
        <span class="val" id="disp_${key}">${fmt(val, meta.step < 1 ? 2 : 0)} ${meta.unit||''}</span></label>
        <input type="range" data-key="${key}" min="${meta.min}" max="${meta.max}" step="${meta.step}" value="${val}"></div>`;
    }
  }
  el.querySelectorAll('input').forEach(inp => {
    inp.addEventListener('input', e => {
      const k = e.target.dataset.key;
      pending[k] = e.target.type === 'checkbox' ? e.target.checked : Number(e.target.value);
      const disp = document.getElementById('disp_' + k);
      if (disp) disp.textContent = fmt(pending[k], NUM_FIELDS[k].step < 1 ? 2 : 0) + ' ' + (NUM_FIELDS[k].unit||'');
      document.getElementById('saveBtn').disabled = false;
      document.getElementById('saveBtn').textContent = 'Apply changes';
    });
  });
}

async function refresh() {
  try {
    const r = await fetch('/api/status');
    const d = await r.json();
    document.getElementById('conn').textContent = 'Live';
    document.getElementById('conn').className = 'status ok';
    const L = d.live || {};
    document.getElementById('soc').textContent = fmt(L.state_of_charge, 0);
    document.getElementById('socBar').style.width = (L.state_of_charge||0) + '%';
    document.getElementById('volts').textContent = fmt(L.volts);
    document.getElementById('current').textContent = fmt(L.current);
    document.getElementById('power').textContent = fmt(L.power, 0);
    document.getElementById('bstatus').textContent = L.battery_status || '—';
    document.getElementById('lowCell').textContent = fmt(L.lowest_cell, 3);
    document.getElementById('highCell').textContent = fmt(L.highest_cell, 3);
    const P = d.pack || {};
    document.getElementById('packInfo').innerHTML =
      `<strong>${P.pack_size_kwh||'?'} kWh</strong> · ${P.cells_in_series||'?'}S · ` +
      `charge ${fmt(P.charge_voltage)} V · discharge floor ${fmt(P.discharge_voltage_limit)} V`;
    const S = d.sma_output || {};
    document.getElementById('smaOut').innerHTML = S.charge_current_limit != null
      ? `SMA CAN out: charge <strong>${fmt(S.charge_voltage)} V / ${fmt(S.charge_current_limit)} A</strong> · discharge ${fmt(S.discharge_current_limit)} A`
      : 'SMA CAN: waiting for BMS data…';
    if (Object.keys(pending).length === 0) renderSettings(d.settings || {});
  } catch(e) {
    document.getElementById('conn').textContent = 'Offline';
    document.getElementById('conn').className = 'status';
  }
}

document.getElementById('saveBtn').addEventListener('click', async () => {
  const btn = document.getElementById('saveBtn');
  btn.disabled = true;
  btn.textContent = 'Saving…';
  await fetch('/api/settings', { method: 'POST', headers: {'Content-Type':'application/json'}, body: JSON.stringify(pending) });
  pending = {};
  btn.textContent = 'No changes';
  const t = document.getElementById('toast');
  t.classList.add('show');
  setTimeout(() => t.classList.remove('show'), 2000);
  refresh();
});

setInterval(refresh, 2000);
refresh();
</script>
</body>
</html>
"""


class DashboardHandler(BaseHTTPRequestHandler):
    bridge = None  # set by server

    def log_message(self, fmt, *args):
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
            html = DASHBOARD_HTML.replace("%NUM_FIELDS%", json.dumps(LIVE_FIELDS))
            body = html.encode()
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
            return
        if path == "/api/status":
            bridge = self.bridge
            with bridge._lock:
                live = dict(enrich_snapshot(bridge.values, bridge.settings.get_config()))
            snap = bridge.settings.snapshot_for_api(live)
            snap["sma_output"] = bridge.last_sma_limits
            self._json_response(200, snap)
            return
        self.send_error(404)

    def do_POST(self) -> None:
        if urlparse(self.path).path != "/api/settings":
            self.send_error(404)
            return
        length = int(self.headers.get("Content-Length", 0))
        body = self.rfile.read(length)
        try:
            updates = json.loads(body)
        except json.JSONDecodeError:
            self._json_response(400, {"error": "invalid json"})
            return
        errors = self.bridge.apply_settings(updates)
        if errors:
            self._json_response(400, {"errors": errors})
        else:
            self._json_response(200, {"ok": True})


def enrich_snapshot(values: dict, config: dict) -> dict:
    from app.parser import enrich_values

    return enrich_values(values, config)


def start_web_dashboard(bridge, host: str, port: int) -> ThreadingHTTPServer:
    DashboardHandler.bridge = bridge
    server = ThreadingHTTPServer((host, port), DashboardHandler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    log.info("Live dashboard at http://%s:%s/", host, port)
    return server
