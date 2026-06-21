# Tesla EVTV BMS + Sunny Island 6048

Home Assistant OS add-on: EVTV BMS monitoring, SMA closed-loop CAN, **live settings dashboard**.

## Install

1. Install **Mosquitto broker** add-on
2. **Settings → Add-ons → Add-on Store → ⋮ → Repositories**
3. Add: `https://github.com/mobiletru/tesla_evtv_bms_v3`
4. Install **Tesla EVTV BMS + Sunny Island** (v1.3+)
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

Only enabled metrics get MQTT discovery entities.

## Configuration defaults (36 module 2S18P)

| | Value |
|---|-------|
| Capacity | 187.2 kWh |
| Charge voltage | 49.2 V |
| CAN bitrate | 500 kbps |
| Web dashboard | port 8099 |

## Sunny Island wiring (ComSync RJ45)

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
