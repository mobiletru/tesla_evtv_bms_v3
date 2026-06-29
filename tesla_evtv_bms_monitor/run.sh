#!/usr/bin/with-contenv bashio
# shellcheck shell=bash
set -e

export LOG_LEVEL="$(bashio::config log_level)"
export UDP_PORT="$(bashio::config udp_port)"
export WEB_PORT="$(bashio::config web_port)"
export PACK_NAME="$(bashio::config pack_name)"
export PACK_SIZE_KWH="$(bashio::config pack_size_kwh)"

bashio::log.info "Starting EVTV BMS Monitor (UDP ${UDP_PORT}, web ${WEB_PORT})"
exec python3 -m app.main
