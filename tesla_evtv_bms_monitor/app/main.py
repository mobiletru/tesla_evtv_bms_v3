#!/usr/bin/env python3
"""Home Assistant OS add-on: EVTV BMS UDP monitor and web dashboard."""

from __future__ import annotations

import logging
import os
import socket
import sys
import threading
import time

from app.parser import parse_udp_packet
from app.state import BMSMonitorState
from app.web_dashboard import start_web_dashboard

logging.basicConfig(
    level=getattr(logging, os.environ.get("LOG_LEVEL", "INFO").upper(), logging.INFO),
    format="%(asctime)s %(levelname)s %(message)s",
)
log = logging.getLogger("tesla_evtv_bms_monitor")


def udp_listener(state: BMSMonitorState, port: int) -> None:
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    sock.bind(("", port))
    log.info("Listening for UDP on port %s", port)

    while True:
        try:
            data, _addr = sock.recvfrom(1024)
        except OSError as exc:
            log.error("UDP recv failed: %s", exc)
            time.sleep(1)
            continue

        parsed = parse_udp_packet(data)
        if parsed:
            state.merge(parsed)


def main() -> None:
    udp_port = int(os.environ.get("UDP_PORT", "6850"))
    web_port = int(os.environ.get("WEB_PORT", "8100"))

    state = BMSMonitorState()
    start_web_dashboard(state, "0.0.0.0", web_port, udp_port)

    thread = threading.Thread(target=udp_listener, args=(state, udp_port), daemon=True)
    thread.start()

    log.info("EVTV BMS Monitor running (UDP %s, web %s)", udp_port, web_port)
    try:
        while True:
            time.sleep(3600)
    except KeyboardInterrupt:
        log.info("Shutting down")


if __name__ == "__main__":
    try:
        main()
    except Exception:
        log.exception("Fatal error")
        sys.exit(1)
