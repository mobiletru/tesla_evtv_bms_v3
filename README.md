# Tesla EVTV BMS + Sunny Island 6048

Home Assistant OS add-on for **EVTV Tesla BMS** monitoring and **SMA Sunny Island 6048** closed-loop CAN control.

**You choose what data appears** — pick BMS sensors, SMA limits, and Sunny Island CAN metrics in the add-on configuration. Only selected metrics are published to MQTT and available for dashboards.

## Install

1. Install **Mosquitto broker** add-on
2. **Settings → Add-ons → Add-on Store → ⋮ → Repositories**
3. Add: `https://github.com/mobiletru/tesla_evtv_bms_v3`
4. Install **Tesla EVTV BMS + Sunny Island** (v1.2.0+)
5. Configure which metrics to publish (see below)
6. **Start** the add-on

## Choose your data (add-on config)

| Option | What it controls |
|--------|------------------|
| `publish_mqtt` | Master switch for all MQTT publishing |
| `publish_bms` | BMS pack, cells, temps, status (multiselect) |
| `publish_sma_limits` | Closed-loop charge/discharge limits sent on CAN |
| `publish_sunny_island` | Sunny Island CAN metrics (DC, grid, inverter, load) |
| `device_name` | HA device for BMS entities (default `tesla_bms`) |
| `sunny_island_device_name` | HA device for inverter entities (default `sunny_island`) |

### BMS options (`publish_bms`)

| Key | Entity ID |
|-----|-----------|
| `state_of_charge` | `sensor.tesla_bms_state_of_charge` |
| `volts` | `sensor.tesla_bms_volts` |
| `current` | `sensor.tesla_bms_current` |
| `power` | `sensor.tesla_bms_power` |
| `lowest_cell` | `sensor.tesla_bms_lowest_cell` |
| `highest_cell` | `sensor.tesla_bms_highest_cell` |
| `average_cell` | `sensor.tesla_bms_average_cell` |
| `max_temp` | `sensor.tesla_bms_max_temp` |
| `min_temp` | `sensor.tesla_bms_min_temp` |
| `battery_status` | `sensor.tesla_bms_battery_status` |

### SMA limits (`publish_sma_limits`)

| Key | Entity ID |
|-----|-----------|
| `charge_voltage` | `sensor.tesla_bms_sma_charge_voltage` |
| `charge_current` | `sensor.tesla_bms_sma_charge_current` |
| `discharge_voltage` | `sensor.tesla_bms_sma_discharge_voltage` |
| `discharge_current` | `sensor.tesla_bms_sma_discharge_current` |

### Sunny Island CAN (`publish_sunny_island`)

Requires `can_watch_enabled: true`. Metrics come from decoded CAN traffic.

| Key | Entity ID |
|-----|-----------|
| `dc_voltage` | `sensor.sunny_island_dc_voltage` |
| `dc_current` | `sensor.sunny_island_dc_current` |
| `grid_power` | `sensor.sunny_island_grid_power` |
| `inverter_power` | `sensor.sunny_island_inverter_power` |
| `load_power` | `sensor.sunny_island_load_power` |
| `input_voltage` | `sensor.sunny_island_input_voltage` |
| `grid_frequency` | `sensor.sunny_island_grid_frequency` |
| `output_voltage` | `sensor.sunny_island_output_voltage` |

Remove items from a list in add-on config to hide them from Home Assistant.

## Dashboard

Pre-built Lovelace dashboards are in `dashboard/`:

| File | Description |
|------|-------------|
| `tesla-bms-sunny-island.yaml` | Full dashboard — Battery, Cells, Sunny Island, Closed Loop |
| `tesla-bms-minimal.yaml` | Single-page overview |

### Import dashboard

1. Copy YAML from the repo `dashboard/` folder
2. In Home Assistant: **Settings → Dashboards → Add Dashboard → New from scratch**
3. Open the new dashboard → **⋮ → Edit Dashboard → Raw configuration editor**
4. Paste the YAML contents and **Save**

Or use **Developer Tools → YAML** and add to `configuration.yaml`:

```yaml
lovelace:
  mode: storage
  dashboards:
    tesla-bms:
      mode: yaml
      title: Tesla BMS
      icon: mdi:battery-high
      show_in_sidebar: true
      filename: dashboard/tesla-bms-sunny-island.yaml
```

Then copy the YAML file to your HA `config/dashboard/` folder and restart.

> Entity IDs assume default device names `tesla_bms` and `sunny_island`. If you change `device_name`, update entity IDs in the dashboard YAML to match (e.g. `sensor.my_bms_state_of_charge`).

## Other config

| Option | Default | Description |
|--------|---------|-------------|
| `can_interface` | `can0` | SocketCAN interface (PCAN USB) |
| `can_bitrate` | `500000` | CAN bitrate (SMA = 500 kbps) |
| `setup_can` | `true` | Bring up `can0` with `/sbin/ip` |
| `sma_enabled` | `true` | Send closed-loop BMS frames to Sunny Island |
| `can_watch_enabled` | `true` | Decode CAN traffic in add-on logs |

## Pack defaults (36 module 2S18P)

| | Value |
|---|-------|
| Capacity | **187.2 kWh** |
| Cells in series | **12** |
| Nominal voltage | **44.4 V** |
| Charge voltage (0x351) | **49.2 V** |

## Wiring (Sunny Island ComSync RJ45)

| Pin | Signal |
|-----|--------|
| 4 | CAN-H |
| 5 | CAN-L |
| 2 | GND |

Set Sunny Island battery type to **LiIon Ext-BMS** and all battery preservation SOC levels to **0%**.

## Requirements

- Home Assistant OS with PCAN USB as **can0**
- EVTV BMS → UDP to HA host **:6850**
- Sunny Island 6048 on same CAN bus (500 kbps, 120 Ω termination)

## Repository layout

```
tesla_evtv_sunny_island/   ← Home Assistant OS add-on
dashboard/                 ← Lovelace dashboards (import manually)
repository.yaml
```

The `custom_components/` HACS integration is legacy; use the add-on on HA OS.
