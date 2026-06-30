# Changelog

## Unreleased
- Fix **Tesla EVTV BMS + Sunny Island** add-on schema: multiselect publish options use valid `list(a|b|...)` array syntax (Supervisor 2026+).
- Add **Tesla EVTV BMS Monitor** HA OS add-on (`tesla_evtv_bms_monitor`) — UDP-only live web dashboard on port 8100.
- Add native **macOS SwiftUI monitor** (`macos/TeslaEVTVBMS`) for EVTV BMS UDP/CAN decode.
- Ignore Cursor `agent-tools/` and `terminals/` artifacts in `.gitignore`.

## 3.3.5
- **Removed PCAN / Sunny Island CAN transmit** from the integration (`pcan_transmitter`, `sma_transmitter`, `sma_can`, `charge_control`). UDP listen-only again — fixes errno 105 TX queue errors when HA Core and add-on both touched `can0`.
- Removed SMA metrics sensors (`freq_shift_volts`, `tcch_amps`) and Sunny Island dashboard tab.
- Dropped `python-can` dependency from the integration manifest.
- Config flow v2: pack layout only, no SMA/PCAN options.
- Use the **Sunny Island CAN** add-on for bridging to the SI6048.

## 3.3.4
- Prior release with PCAN Sunny Island transmit (deprecated).
