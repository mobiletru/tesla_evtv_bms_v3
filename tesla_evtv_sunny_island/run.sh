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
export CAN_WATCH_SUMMARY_INTERVAL="$(bashio::config can_watch_summary_interval)"
export WEB_ENABLED="$(bashio::config web_enabled)"
export WEB_PORT="$(bashio::config web_port)"
export PUBLISH_MQTT="$(bashio::config publish_mqtt)"
export MODBUS_ENABLED="$(bashio::config modbus_enabled)"
export MODBUS_MODE="$(bashio::config modbus_mode)"
export MODBUS_HOST="$(bashio::config modbus_host)"
export MODBUS_PORT="$(bashio::config modbus_port)"
export MODBUS_UNIT_ID="$(bashio::config modbus_unit_id)"
export MODBUS_SERIAL="$(bashio::config modbus_serial)"
export MODBUS_BAUDRATE="$(bashio::config modbus_baudrate)"
export MODBUS_POLL_INTERVAL="$(bashio::config modbus_poll_interval)"
export PUBLISH_MODBUS="$(bashio::config publish_modbus)"
export DEVICE_NAME="$(bashio::config device_name)"
export SUNNY_ISLAND_DEVICE_NAME="$(bashio::config sunny_island_device_name)"
export PUBLISH_BMS="$(bashio::config publish_bms)"
export PUBLISH_SMA_LIMITS="$(bashio::config publish_sma_limits)"
export PUBLISH_SUNNY_ISLAND="$(bashio::config publish_sunny_island)"
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
