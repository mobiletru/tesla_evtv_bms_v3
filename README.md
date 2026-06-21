# Tesla EVTV BMS + Sunny Island 6048

Home Assistant OS add-on: EVTV BMS monitoring, SMA closed-loop CAN, **live settings dashboard**.

## Install

1. Install **Mosquitto broker** add-on
2. **Settings → Add-ons → Add-on Store → ⋮ → Repositories**
3. Add: `https://github.com/mobiletru/tesla_evtv_bms_v3`
4. Install **Tesla EVTV BMS + Sunny Island** (v1.5+)
5. Start the add-on

## Live settings dashboard (web)

The add-on serves a **live web UI** on port **8099**:

- Open from the add-on page: **Open web UI**
- Or browse to `http://<home-assistant-ip>:8099/`

You can change these **instantly** (no restart):

| Setting | Effect |
|---------|--------|
| Charge / discharge current limit | SMA 0x351 closed-loop limits |
| Min / max cell voltage | Recalculates charge & discharge voltage |
| SMA CAN transmit | Enable/disable Sunny Island CAN output |
| CAN bus monitor | Enable/disable CAN decode logging |
| Invert current sign | Flip current on 0x356 |

Live pack data (SOC, V, I, cells) refreshes every 2 seconds.

## Home Assistant dashboard

Import the Lovelace dashboard for phone/tablet control via MQTT sliders:

1. **Settings → Dashboards → Add dashboard → Import**
2. Paste contents of [`dashboard/tesla-bms-live.yaml`](dashboard/tesla-bms-live.yaml)

The **Settings** tab has the same live controls as the web UI (number + switch entities).

### Choose which data to publish

In the add-on configuration, edit the lists:

- `publish_bms` — pack/cell/temp sensors
- `publish_sma_limits` — outbound CAN limit sensors
- `publish_sunny_island` — inverter CAN metrics (DC V/I, grid power, etc.)
- `publish_modbus` — Sunny Island Modbus registers
- `publish_webbox` — Sunny WebBox RPC plant / inverter data

Only enabled metrics get MQTT discovery entities.

## Configuration defaults (36 module 2S18P)

| | Value |
|---|-------|
| Capacity | 187.2 kWh |
| Charge voltage | 49.2 V |
| CAN bitrate | 500 kbps |
| Web dashboard | port 8099 |

## Sunny Island Modbus (RS485 / TCP)

**Closed-loop Ext-BMS charge control stays on CAN** — SMA requires CAN for LiIon Ext-BMS limits.

**Modbus** adds inverter monitoring (and optional TCP if your SI has Ethernet/Com module):

| Add-on option | Default | Description |
|---------------|---------|-------------|
| `modbus_enabled` | `false` | Enable Modbus polling |
| `modbus_mode` | `rtu` | `rtu` (RS485 USB) or `tcp` |
| `modbus_serial` | `/dev/ttyUSB0` | RS485 adapter on HA host |
| `modbus_baudrate` | `9600` | SMA default RS485 |
| `modbus_unit_id` | `3` | SMA default unit ID |
| `modbus_host` | — | IP for Modbus TCP |
| `modbus_port` | `502` | Modbus TCP port |
| `publish_modbus` | multiselect | Which SI Modbus sensors to publish |

### RS485 wiring (6048-US piggy-back)

Install SMA **RS485 Piggy-Back** on the Sunny Island → USB-RS485 adapter on HA host → `modbus_serial: /dev/ttyUSB0`.

Enable **Modbus** in the inverter communication menu (see SMA operating manual).

### Registers read (unit ID 3)

| Register | Value |
|----------|--------|
| 30851 | Battery voltage |
| 30843 | Battery current |
| 30845 | Battery SOC |
| 30775 | Active power |
| 30865 | Grid purchase power |

## Sunny WebBox RPC (data logger)

If your plant uses an **SMA Sunny WebBox** (or WebBox with data logger), the add-on can poll plant and Sunny Island metrics over **JSON-RPC** instead of (or alongside) CAN/Modbus.

| Add-on option | Default | Description |
|---------------|---------|-------------|
| `webbox_enabled` | `false` | Enable WebBox polling |
| `webbox_mode` | `http` | `http` (`POST http://<ip>/rpc`) or `udp` (port 34268) |
| `webbox_host` | `192.168.0.168` | WebBox IP address |
| `webbox_port` | `80` | HTTP port (ignored for UDP mode) |
| `webbox_password` | *(empty)* | WebBox password — required only for `GetParameter` / `SetParameter` |
| `webbox_poll_interval` | `30` | Seconds between polls (SMA minimum **30 s**) |
| `webbox_device_key` | *(empty)* | Sunny Island device key — auto-discovered if blank |
| `webbox_device_filter` | `sunny island` | Name filter for auto-discovery |
| `publish_webbox` | multiselect | Which WebBox sensors to publish |

### Typical setup

1. Set `webbox_enabled: true` and `webbox_host` to your WebBox IP.
2. Leave `webbox_device_key` empty — the add-on calls `GetDevices` and picks the Sunny Island.
3. Choose metrics under `publish_webbox` (plant power, energy today, SI SOC, DC V/I, etc.).
4. Open the live dashboard — WebBox plant power and SOC appear under the SMA output line when data is flowing.

**Note:** Closed-loop **LiIon Ext-BMS charge control still requires CAN**. WebBox is for monitoring and plant-level data, not charge limits.

## Sunny Island wiring (ComSync CAN — required for Ext-BMS)

| Pin | Signal |
|-----|--------|
| 4 | CAN-H |
| 5 | CAN-L |
| 2 | GND |

Battery type: **LiIon Ext-BMS**, preservation SOC: **0%**.

## Repository layout

```
tesla_evtv_sunny_island/   ← HA OS add-on
dashboard/                 ← Lovelace import YAML
```
