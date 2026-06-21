#!/usr/bin/with-contenv bashio
# ==============================================================================
# Tesla EVTV BMS - Home Assistant OS App
# Installs the custom integration into /config/custom_components
# ==============================================================================

INTEGRATION_SRC="/integration/tesla_evtv_bms_v3"
INTEGRATION_DEST="/config/custom_components/tesla_evtv_bms_v3"
DASHBOARD_SRC="/dashboard/tesla_evtv_bms.yaml"
SYNC_INTERVAL="$(bashio::config 'sync_interval_minutes')"

install_integration() {
    bashio::log.info "Installing Tesla EVTV BMS V3 integration..."

    if [ ! -d "${INTEGRATION_SRC}" ]; then
        bashio::log.fatal "Integration source not found at ${INTEGRATION_SRC}"
        exit 1
    fi

    mkdir -p /config/custom_components
    rsync -a --delete "${INTEGRATION_SRC}/" "${INTEGRATION_DEST}/"
    # Legacy SMA/PCAN modules removed in 3.3.5 — ensure they are gone on upgrade.
    rm -f \
        "${INTEGRATION_DEST}/pcan_transmitter.py" \
        "${INTEGRATION_DEST}/sma_transmitter.py" \
        "${INTEGRATION_DEST}/sma_can.py" \
        "${INTEGRATION_DEST}/charge_control.py"
    bashio::log.info "Integration deployed to ${INTEGRATION_DEST}"
}

install_dashboard() {
    if ! bashio::config.true 'install_dashboard'; then
        bashio::log.info "Dashboard install skipped (disabled in options)"
        return
    fi

    if [ ! -f "${DASHBOARD_SRC}" ]; then
        bashio::log.warning "Dashboard template not found"
        return
    fi

    mkdir -p /config/dashboards
    cp -f "${DASHBOARD_SRC}" /config/dashboards/tesla_evtv_bms.yaml
    bashio::log.info "Dashboard copied to /config/dashboards/tesla_evtv_bms.yaml"
}

write_setup_note() {
    cat > /config/tesla_evtv_bms_setup.txt <<'EOF'
Tesla EVTV BMS - Setup Steps
============================
1. Restart Home Assistant (Settings → System → Restart)
2. Go to Settings → Devices & Services → Add Integration
3. Search for "Tesla EVTV BMS V3"
4. Enter pack name, UDP port (default 6850), and pack settings
5. Optional: add dashboard from Settings → Dashboards → Add Dashboard → Import

Sunny Island 6048-US: use the Sunny Island CAN add-on for PCAN bridging.
This integration listens on UDP only and does not transmit on CAN.
EOF
    bashio::log.info "Setup instructions written to /config/tesla_evtv_bms_setup.txt"
}

install_integration
install_dashboard
write_setup_note

bashio::log.info "----------------------------------------------"
bashio::log.info "Restart Home Assistant to load the integration"
bashio::log.info "Then add 'Tesla EVTV BMS V3' via Settings"
bashio::log.info "----------------------------------------------"

while true; do
    sleep $((SYNC_INTERVAL * 60))
    bashio::log.info "Re-syncing integration files..."
    install_integration
done