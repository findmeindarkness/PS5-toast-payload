#!/usr/bin/env python3
"""make_notify.py — generate a custom PS5 toast payload

This patches a prebuilt "shell" ELF. You don't need the PS5 SDK


Files:
    make_notify.py        (this script)
    notify_shell.elf      (prebuilt template, ships alongside)

Usage:
    python3 make_notify.py


The message is patched into the ELF at offset 0x10060 (the .toast_msg
section). The shell ELF reads it at runtime and sends it as a toast.

Message can be up to 480 characters (512 minus the @@MSG@@ delimiters).
"""
import os
import sys
import time

# Path to the bundled shell ELF — same dir as this script.
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
SHELL_ELF = os.path.join(SCRIPT_DIR, "notify_shell.elf")

# Offset of the .toast_msg section in the shell ELF.
# Verified via: readelf -S notify_shell.elf | grep toast_msg
# If you rebuild the shell ELF, re-check this offset.
MSG_OFFSET = 0x10060
MSG_TOTAL_SIZE = 512  # padded to 512 bytes in the source
MSG_PREFIX = b"@@MSG@@"
MSG_SUFFIX = b"@@MSG@@"
MSG_MAX_LEN = MSG_TOTAL_SIZE - len(MSG_PREFIX) - len(MSG_SUFFIX) - 2  # null + safety


def patch_message(elf_data: bytes, message: str) -> bytes:
    """Patch the message into the .toast_msg section."""
    msg_bytes = message.encode("utf-8")
    if len(msg_bytes) > MSG_MAX_LEN:
        raise ValueError(
            f"Message too long ({len(msg_bytes)} bytes, max {MSG_MAX_LEN})"
        )

    # Format: @@MSG@@ <message> @@MSG@@ <null padding>
    payload = MSG_PREFIX + b" " + msg_bytes + b" " + MSG_SUFFIX
    payload = payload.ljust(MSG_TOTAL_SIZE, b"\x00")

    if len(payload) != MSG_TOTAL_SIZE:
        raise ValueError(f"Internal error: payload is {len(payload)} bytes, expected {MSG_TOTAL_SIZE}")

    # Patch the bytes at MSG_OFFSET
    out = bytearray(elf_data)
    out[MSG_OFFSET:MSG_OFFSET + MSG_TOTAL_SIZE] = payload
    return bytes(out)


def verify_shell():
    """Verify notify_shell.elf exists and is the right one."""
    if not os.path.isfile(SHELL_ELF):
        print(f"ERROR: {SHELL_ELF} not found.")
        print("This script needs notify_shell.elf in the same directory.")
        print("Download it from the same place you got this script.")
        sys.exit(1)

    with open(SHELL_ELF, "rb") as f:
        data = f.read()

    if len(data) < MSG_OFFSET + MSG_TOTAL_SIZE:
        print(f"ERROR: {SHELL_ELF} is too small ({len(data)} bytes).")
        print("Expected at least", MSG_OFFSET + MSG_TOTAL_SIZE, "bytes.")
        sys.exit(1)

    # Check the @@MSG@@ signature is at the expected offset
    section = data[MSG_OFFSET:MSG_OFFSET + MSG_TOTAL_SIZE]
    if not section.startswith(MSG_PREFIX):
        print(f"ERROR: {SHELL_ELF} does not have the expected signature at offset 0x{MSG_OFFSET:x}.")
        print("This means the shell ELF was built differently than expected.")
        print("Re-download notify_shell.elf from the original source.")
        sys.exit(1)


def main():
    if len(sys.argv) > 1:
        message = " ".join(sys.argv[1:])
    else:
        print("=" * 60)
        print("PS5 Toast Payload Generator (no SDK needed)")
        print("=" * 60)
        print()
        message = input("Enter the message to display on the PS5: ").strip()
        if not message:
            print("Empty message, exiting.")
            sys.exit(1)

    verify_shell()

    # Read the shell ELF
    with open(SHELL_ELF, "rb") as f:
        shell_data = f.read()

    # Patch in the message
    try:
        out_data = patch_message(shell_data, message)
    except ValueError as e:
        print(f"ERROR: {e}")
        sys.exit(1)

    # Write the output ELF
    timestamp = time.strftime("%Y%m%d_%H%M%S")
    out_name = f"notify_{timestamp}.elf"
    out_path = os.path.abspath(out_name)

    with open(out_path, "wb") as f:
        f.write(out_data)

    size = os.path.getsize(out_path)
    print()
    print("=" * 60)
    print(f"  Built: {out_path}")
    print(f"  Size:  {size:,} bytes")
    print(f"  Message:")
    print(f'    "{message}"')
    print("=" * 60)
    print()
    print("Push to PS5 via elfldr:")
    print(f"  curl -s --data-binary @{out_name} http://PS5_IP:9021")
    print()
    print("Or use your Payload Manager to push the ELF.")


if __name__ == "__main__":
    main()
