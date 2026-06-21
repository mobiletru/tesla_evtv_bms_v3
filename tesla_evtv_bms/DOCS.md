# Tesla EVTV BMS

This Home Assistant OS app installs the **Tesla EVTV BMS V3** custom integration.

## After install

1. **Restart Home Assistant**
2. **Settings → Devices & Services → Add Integration** → search `Tesla EVTV BMS V3`
3. Configure pack name (use `tesla pack` to match the default dashboard), UDP port `6850`, and pack size

## Dashboard

If "Install Lovelace dashboard" is enabled, import `/config/dashboards/tesla_evtv_bms.yaml` via **Settings → Dashboards**.

## Sunny Island 6048-US

Use the separate **Sunny Island CAN** add-on to bridge EVTV BMS data to the SMA Sunny Island over PCAN. This integration is UDP-only and does not transmit on CAN.

## HACS alternative

You can also install via HACS instead of this app. Do not run both — use one install method.
