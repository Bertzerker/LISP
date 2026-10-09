#!/usr/bin/env python3
"""Wait for Mumble's configured local address without requiring netlink access."""

import argparse
import ipaddress
from pathlib import Path
import socket
import sys
import time


def configured_host(path):
    host = ''
    for line in Path(path).read_text().splitlines():
        line = line.strip()
        if not line or line.startswith(('#', ';')):
            continue
        key, separator, value = line.partition('=')
        if separator and key.strip().lower() == 'host':
            host = value.strip().strip('"')
    if host:
        ipaddress.ip_address(host)
    return host


def address_ready(host):
    if not host:
        return True  # Native default: all available addresses.
    family = socket.AF_INET6 if ipaddress.ip_address(host).version == 6 else socket.AF_INET
    try:
        # Port zero checks address availability without taking the voice port.
        with socket.socket(family, socket.SOCK_DGRAM) as probe:
            probe.bind((host, 0))
        return True
    except OSError:
        return False


def wait_for_address(host, timeout=90, interval=1):
    deadline = time.monotonic() + timeout
    while not address_ready(host):
        remaining = deadline - time.monotonic()
        if remaining <= 0:
            return False
        time.sleep(min(interval, remaining))
    return True


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('config')
    args = parser.parse_args()
    try:
        host = configured_host(args.config)
    except (OSError, ValueError):
        print('Cannot read a valid local Mumble host address.', file=sys.stderr)
        return 1
    if not wait_for_address(host):
        print('Mumble LAN address is not ready; systemd will retry startup.', file=sys.stderr)
        return 1
    print('Mumble LAN address is ready.')
    return 0


if __name__ == '__main__':
    sys.exit(main())
