"""Deny non-loopback sockets during opt-in release verification."""

from __future__ import annotations

import ipaddress
import os
import socket


class OfflineAccessDenied(OSError):
    pass


def _is_loopback_host(host: object) -> bool:
    if not isinstance(host, str):
        return False
    if host.casefold() == "localhost":
        return True
    try:
        return ipaddress.ip_address(host).is_loopback
    except ValueError:
        return False


if os.environ.get("FS_FILTERLAB_ENFORCE_OFFLINE") == "1":
    _original_connect = socket.socket.connect
    _original_connect_ex = socket.socket.connect_ex
    _original_getaddrinfo = socket.getaddrinfo

    def _guard_address(address: object) -> None:
        if isinstance(address, str):  # AF_UNIX local socket path
            return
        if not isinstance(address, tuple) or not address or not _is_loopback_host(address[0]):
            raise OfflineAccessDenied(f"Non-loopback socket denied during release verification: {address!r}")

    def _connect(sock: socket.socket, address: object):
        _guard_address(address)
        return _original_connect(sock, address)

    def _connect_ex(sock: socket.socket, address: object):
        _guard_address(address)
        return _original_connect_ex(sock, address)

    def _getaddrinfo(host, *args, **kwargs):
        if host is not None and not _is_loopback_host(host):
            raise OfflineAccessDenied(f"Non-loopback name resolution denied: {host!r}")
        return _original_getaddrinfo(host, *args, **kwargs)

    socket.socket.connect = _connect
    socket.socket.connect_ex = _connect_ex
    socket.getaddrinfo = _getaddrinfo
