# Tesla EVTV BMS V3 + Sunny Island 6048

Home Assistant package for **EVTV Tesla BMS** monitoring and **SMA Sunny Island 6048** closed-loop CAN control.

## Two ways to install on Home Assistant OS

### Option A — Add-on (recommended for HA OS + can0)

Best when using **PCAN on can0**. The add-on runs with **host network** and **NET_ADMIN** so it can configure and use SocketCAN directly.

1. Install **Mosquitto broker** add-on
2. **Settings → Add-ons → Add-on Store → ⋮ → Repositories**
3. Add: `https://github.com/mobiletru/tesla_evtv_bms_v3`
4. Install **Tesla EVTV BMS + Sunny Island**
5. Configure:
   - `can_interface`: `can0`
   - `can_bitrate`: `500000`
   - `module_count`: `36`
   - `modules_in_series`: `2`
6. **Start** the add-on

Sensors appear automatically via **MQTT discovery** under device `tesla_bms`.

The add-on:
- Listens for EVTV BMS **UDP** (port 6850)
- Publishes **MQTT sensors** (SoC, voltage, current, cells, temps)
- Sends **SMA CAN** frames on **can0** every 250 ms

### Option B — HACS custom integration

Install `custom_components/tesla_evtv_bms_v3` via HACS for sensors inside Home Assistant Core. Enable **SocketCAN / can0** in integration options for SMA output (works if Core can access can0).

## Your pack (defaults)

| | Value |
|---|-------|
| Modules | **36** (2S18P) |
| Capacity | **187.2 kWh** |
| Cells in series (DC bus) | **12** |
| Nominal voltage | **44.4 V** |
| SMA charge voltage | **49.2 V** |

## Sunny Island wiring (ComSync RJ45)

| Pin | Signal |
|-----|--------|
| 4 | CAN-H |
| 5 | CAN-L |
| 2 | GND |

Set Sunny Island battery type to **LiIon Ext-BMS** and all battery preservation SOC levels to **0%**.

## Repository layout

```
custom_components/tesla_evtv_bms_v3/   ← HACS integration
tesla_evtv_sunny_island/             ← HA OS add-on
repository.yaml                      ← Add-on store manifest
```

## Requirements

- EVTV BMS controller → UDP to Home Assistant host:6850
- PCAN USB (or CAN HAT) as **can0** on Home Assistant OS
- Sunny Island 6048 on same CAN bus (500 kbps)
