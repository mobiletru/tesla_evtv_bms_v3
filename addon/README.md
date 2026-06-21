## Home Assistant Add-on: Tesla EVTV BMS + Sunny Island

Runs on **Home Assistant OS** with **host network** so it can use **can0** (PCAN / SocketCAN).

### What it does

1. Listens for **EVTV BMS UDP** (port 6850)
2. Publishes **MQTT sensors** to Home Assistant (auto-discovery)
3. Sends **SMA Sunny Island 6048** CAN frames on **can0** (0x351, 0x355, 0x356, 0x35A)

### Requirements

- Home Assistant OS with **can0** available (PCAN USB or CAN HAT)
- **Mosquitto** MQTT broker add-on
- EVTV BMS controller sending UDP to this host

### Default pack

- **36 modules**, **2S18P**
- **12 cells in series** on DC bus (~44 V nominal)
- **187.2 kWh**

### Options

| Option | Default | Description |
|--------|---------|-------------|
| `can_interface` | `can0` | SocketCAN interface |
| `can_bitrate` | `500000` | SMA Sunny Island bitrate |
| `setup_can` | `true` | Run `ip link set can0 up` at start |
| `module_count` | `36` | Total Tesla modules |
| `modules_in_series` | `2` | Modules in series on DC bus |
