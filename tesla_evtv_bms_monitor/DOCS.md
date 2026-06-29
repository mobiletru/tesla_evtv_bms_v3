# Tesla EVTV BMS Monitor

Lightweight Home Assistant OS add-on that listens for EVTV LiteCAN UDP packets and serves a live web dashboard. UDP-only — no MQTT broker or CAN hardware required.

## Features

- Live pack dashboard (SOC, voltage, current, power, temperatures)
- Cell voltage summary and balance view
- Charge / discharge energy counters (session)
- SMA freq-shift and TCCH amps when present on the CAN stream
- Sunny Island 6048-US wiring and QCG setup guide

## Configuration

| Option | Default | Description |
|--------|---------|-------------|
| `udp_port` | 6850 | UDP port for LiteCAN packets |
| `web_port` | 8100 | Web dashboard port |
| `pack_name` | Tesla Pack | Display name on dashboard |
| `pack_size_kwh` | 75 | Pack capacity for available-energy estimate |

Point your EVTV Due / LiteCAN UDP forwarder at the Home Assistant host on `udp_port`.

Open the dashboard from the add-on page (**Open web UI**) or `http://<ha-ip>:8100/`.

## Related add-ons

- **Tesla EVTV BMS** — installs the HA integration for entity sensors
- **Tesla EVTV BMS + Sunny Island** — full MQTT/CAN bridge with charge control
