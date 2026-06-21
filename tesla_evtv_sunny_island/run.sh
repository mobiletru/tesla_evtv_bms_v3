#!/usr/bin/with-contenv bashio
# shellcheck shell=bash
set -e

export LOG_LEVEL="$(bashio::config log_level)"
export UDP_PORT="$(bashio::config udp_port)"
export CAN_INTERFACE="$(bashio::config can_interface)"
export CAN_BITRATE="$(bashio::config can_bitrate)"
export SETUP_CAN="$(bashio::config setup_can)"
export SMA_ENABLED="$(bashio::config sma_enabled)"
export CAN_WATCH_ENABLED="$(bashio::config can_watch_enabled)"
export CAN_WATCH_FILTER="$(bashio::config can_watch_filter)"
export CAN_WATCH_MQTT="$(bashio::config can_watch_mqtt)"
export CAN_WATCH_SUMMARY_INTERVAL="$(bashio::config can_watch_summary_interval)"
export CAN_WATCH_DEVICE_NAME="$(bashio::config can_watch_device_name)"
export DEVICE_NAME="$(bashio::config device_name)"
export MODULE_COUNT="$(bashio::config module_count)"
export MODULES_IN_SERIES="$(bashio::config modules_in_series)"
export MIN_CELL_VOLTS="$(bashio::config min_cell_volts)"
export MAX_CELL_VOLTS="$(bashio::config max_cell_volts)"
export CHARGE_CURRENT="$(bashio::config charge_current_limit)"
export DISCHARGE_CURRENT="$(bashio::config discharge_current_limit)"
export INVERT_CURRENT="$(bashio::config invert_current)"

if bashio::services.available mqtt; then
  export MQTT_HOST="$(bashio::services mqtt "host")"
  export MQTT_PORT="$(bashio::services mqtt "port")"
  export MQTT_USER="$(bashio::services mqtt "username")"
  export MQTT_PASSWORD="$(bashio::services mqtt "password")"
else
  bashio::log.warning "MQTT add-on not found — install Mosquitto broker"
  export MQTT_HOST="core-mosquitto"
  export MQTT_PORT="1883"
fi

bashio::log.info "Starting Tesla EVTV BMS + Sunny Island on ${CAN_INTERFACE} (UDP ${UDP_PORT})"
exec python3 -m app.main
