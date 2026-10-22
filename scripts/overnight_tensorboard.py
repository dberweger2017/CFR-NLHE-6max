"""Dependency-free TensorBoard scalar TFRecords (Event/Summary protobuf wire format)."""
import os
from pathlib import Path
import socket
import struct
import time


def crc32c(data):
    crc = 0xffffffff
    for byte in data:
        crc ^= byte
        for _ in range(8):
            crc = (crc >> 1) ^ (0x82f63b78 if crc & 1 else 0)
    return crc ^ 0xffffffff


def masked_crc(data):
    value = crc32c(data)
    return ((value >> 15 | value << 17) + 0xa282ead8) & 0xffffffff


def varint(value):
    out = bytearray()
    while value > 127:
        out.append((value & 127) | 128)
        value >>= 7
    return bytes(out + bytes([value]))


def string_field(number, value):
    value = value.encode() if isinstance(value, str) else value
    return varint(number * 8 + 2) + varint(len(value)) + value


class Scalars:
    def __init__(self, folder):
        folder = Path(folder)
        folder.mkdir(parents=True, exist_ok=False)
        self.path = folder / f'events.out.tfevents.{int(time.time())}.{socket.gethostname()}.{os.getpid()}'
        self.file = self.path.open('xb')
        self.record(b'\x09' + struct.pack('<d', time.time()) + string_field(3, 'brain.Event:2'))

    def record(self, value):
        size = struct.pack('<Q', len(value))
        self.file.write(size + struct.pack('<I', masked_crc(size)) + value + struct.pack('<I', masked_crc(value)))
        self.file.flush()

    def add(self, tag, value, step):
        scalar = string_field(1, tag) + b'\x15' + struct.pack('<f', float(value))
        event = b'\x09' + struct.pack('<d', time.time()) + b'\x10' + varint(int(step))
        self.record(event + string_field(5, string_field(1, scalar)))

    def close(self):
        self.file.close()
