# Tesla EVTV BMS + Sunny Island 6048

Home Assistant OS add-on for **EVTV Tesla BMS** monitoring and **SMA Sunny Island 6048** closed-loop CAN control.

One add-on handles everything:

- **EVTV BMS** UDP listener (port 6850)
- **MQTT sensors** (Home Assistant auto-discovery)
- **SMA closed-loop CAN** transmit on `can0` (0x351, 0x355, 0x356, 0x35A)
- **CAN bus monitor** — decodes BMS + Sunny Island traffic in the add-on log

## Install

1. Install **Mosquitto broker** add-on
2. **Settings → Add-ons → Add-on Store → ⋮ → Repositories**
3. Add: `https://github.com/mobiletru/tesla_evtv_bms_v3`
4. Install **Tesla EVTV BMS + Sunny Island**
5. Configure and **Start**

## Configuration

| Option | Default | Description |
|--------|---------|-------------|
| `can_interface` | `can0` | SocketCAN interface (PCAN USB) |
| `can_bitrate` | `500000` | CAN bitrate (SMA = 500 kbps) |
| `setup_can` | `true` | Bring up `can0` with `/sbin/ip` (iproute2) |
| `sma_enabled` | `true` | Send closed-loop BMS frames to Sunny Island |
| `can_watch_enabled` | `true` | Decode incoming CAN traffic in logs |
| `can_watch_filter` | `sma` | `sma`, `bms`, or `all` |
| `can_watch_mqtt` | `false` | Publish decoded CAN frames to MQTT |
| `module_count` | `36` | Tesla modules (2S18P) |
| `modules_in_series` | `2` | Modules in series on DC bus |

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

## CAN troubleshooting (HA OS)

BusyBox `ip` does not support CAN. The add-on uses **`/sbin/ip`** from iproute2.

Manual check on the host:

```bash
/sbin/ip link set dev can0 down
/sbin/ip link set dev can0 type can bitrate 500000 restart-ms 100
/sbin/ip link set dev can0 up
/sbin/ip -details link show dev can0
candump can0,351:7FF,355:7FF,356:7FF,35A:7FF
```

Watch add-on logs for decoded frames:

```bash
ha addons logs local_tesla_evtv_sunny_island -f
```

Look for lines like:

```text
[watch] 0x351 BMS limits | charge 49.2V/100.0A | ...
[watch] 0x305 SI DC bus | DC 48.5V 12.3A
```

## Standalone CAN monitor (CLI)

Inside the add-on shell or any machine with `can0`:

```bash
python3 -m app.can_monitor --interface can0 --setup-can --filter sma
```

## Requirements

- Home Assistant OS with PCAN USB (or CAN HAT) as **can0**
- EVTV BMS controller → UDP to HA host **:6850**
- Sunny Island 6048 on same CAN bus (500 kbps, 120 Ω termination)

## Repository layout

```
tesla_evtv_sunny_island/   ← Home Assistant OS add-on (install this)
repository.yaml
```

The `custom_components/` HACS integration is legacy; use the add-on on HA OS.
