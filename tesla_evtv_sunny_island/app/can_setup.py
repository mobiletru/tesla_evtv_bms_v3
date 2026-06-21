"""SocketCAN interface setup using iproute2 (/sbin/ip)."""

from __future__ import annotations

import logging
import subprocess

log = logging.getLogger(__name__)

IP_BIN = "/sbin/ip"


def setup_can_interface(iface: str, bitrate: int, restart_ms: int = 100) -> None:
    """Bring up a SocketCAN interface (HA OS needs iproute2, not BusyBox ip)."""
    cmds = [
        [IP_BIN, "link", "set", "dev", iface, "down"],
        [IP_BIN, "link", "set", "dev", iface, "type", "can", "bitrate", str(bitrate), "restart-ms", str(restart_ms)],
        [IP_BIN, "link", "set", "dev", iface, "up"],
    ]
    for cmd in cmds:
        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode != 0:
            log.warning("CAN setup failed: %s -> %s", " ".join(cmd), result.stderr.strip() or result.stdout.strip())
    log.info("CAN interface %s configured at %s bps (restart-ms %s)", iface, bitrate, restart_ms)


def read_can_stats(iface: str) -> str:
    """Return link state / error counter snippet for logging."""
    result = subprocess.run(
        [IP_BIN, "-details", "-statistics", "link", "show", "dev", iface],
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        return f"{iface}: stats unavailable"
    lines = []
    for line in result.stdout.splitlines():
        stripped = line.strip()
        if any(k in stripped for k in ("state", "can state", "berr-counter", "bitrate", "bus-off")):
            lines.append(stripped)
    return " | ".join(lines) if lines else result.stdout.strip()
