#!/usr/bin/env python3
"""with_lock.py — run a command under an exclusive advisory file lock.

Usage:
    python3 scripts/with_lock.py <lockname> [--timeout SECONDS] -- <cmd> [args...]

Takes fcntl.flock on wiki/.locks/<lockname> (created if absent), waiting up to
--timeout seconds (default 120). Runs the command, propagates its exit code.
Exits 75 (EX_TEMPFAIL) if the lock cannot be acquired in time.

The LOCK is the flock on the fd, not the file's existence: leftover lock files
are harmless and must never be "cleaned up" as a way of breaking a lock.
Stdlib only; macOS + Linux.
"""
import fcntl
import os
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(os.environ.get("CLAUDE_PROJECT_DIR")
            or Path(__file__).resolve().parent.parent)
LOCK_DIR = ROOT / "wiki" / ".locks"
USAGE = "usage: with_lock.py <lockname> [--timeout N] -- cmd [args...]"


def main():
    args = sys.argv[1:]
    if "--" not in args:
        sys.exit(USAGE)
    sep = args.index("--")
    head, cmd = args[:sep], args[sep + 1:]
    if not head or not cmd:
        sys.exit(USAGE)
    lockname = head[0]
    timeout = 120.0
    if "--timeout" in head:
        try:
            timeout = float(head[head.index("--timeout") + 1])
        except (IndexError, ValueError):
            sys.exit(USAGE)

    LOCK_DIR.mkdir(parents=True, exist_ok=True)
    fd = os.open(LOCK_DIR / lockname, os.O_CREAT | os.O_RDWR)
    deadline = time.monotonic() + timeout
    while True:
        try:
            fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
            break
        except OSError:
            if time.monotonic() >= deadline:
                print(f"with_lock: timeout after {timeout:g}s waiting for "
                      f"wiki/.locks/{lockname}", file=sys.stderr)
                sys.exit(75)
            time.sleep(0.25)
    try:
        os.ftruncate(fd, 0)
        os.write(fd, f"pid={os.getpid()}\n".encode())
        rc = subprocess.call(cmd)
    finally:
        fcntl.flock(fd, fcntl.LOCK_UN)
        os.close(fd)
    sys.exit(rc)


if __name__ == "__main__":
    main()
