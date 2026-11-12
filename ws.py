"""Workshop driver: find ESP32 boards, build a sketch for each chip, flash, monitor.

Run through ./ws (it enters the `.#esp` Nix shell). Commands:
  ws boards                     list connected boards with their number and chip
  ws new <team> [example]       start teams/<team>.cpp from an example (default 01_blink)
  ws flash <sketch> [board]     build + flash; <sketch> = team name, example name or a .cpp path
  ws run <sketch> [board]       flash, then open the serial monitor (Ctrl+] to quit)
  ws monitor [board]            serial monitor only
  ws flash-all <sketch>         flash every connected board (e.g. 00_hello self-test)
  ws prewarm                    build every example for every chip type, so class-time builds are seconds
  ws doctor                     check permissions, services and boards
  ws capture [board] [seconds]  reset the board and print its serial output for a while (no keyboard)
  ws ci <before-sha> <sha>      GitHub Actions: flash every teams/*.cpp the push changed
  ws ci-pr <base-sha> <head-sha> GitHub Actions: same for a pull request, using ONLY its teams/*.cpp
                                files (never its tooling), built in a sandbox
[board] = the number from `ws boards` (or a /dev path). It can be left out when the sketch has a
`// board: 3` line, or when only one board is plugged in.

Board numbers stick to the USB port (hub socket) a board is plugged into. They are stored with the
flash lock in ~/.cache/esp32-workshop, so your terminal and the Actions runner agree on them.
"""

import fcntl
import glob
import grp
import json
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
STATE = Path(os.environ.get("WS_STATE", Path.home() / ".cache" / "esp32-workshop"))
STATE.mkdir(parents=True, exist_ok=True)
REGISTRY = STATE / "boards.json"
LOCK = STATE / "lock"
IN_CI = os.environ.get("GITHUB_ACTIONS") == "true"
# Untrusted code (PRs from anyone) compiles inside bubblewrap: no network, and only the Nix store
# and this checkout visible, so #include "/home/..." or .incbin can't read the laptop's files.
SANDBOX = os.environ.get("WS_SANDBOX") == "1"
SKETCH = HERE / "main" / "sketch.cpp"
TARGETS = ["esp32", "esp32s3", "esp32c6", "esp32c3", "esp32s2"]
CHIP_TO_TARGET = {"ESP32": "esp32", "ESP32-S3": "esp32s3", "ESP32-C6": "esp32c6",
                  "ESP32-C3": "esp32c3", "ESP32-S2": "esp32s2"}
BAUD = "460800"  # CH340 bridges get flaky at 921600

BOLD, RED, GREEN, YELLOW, OFF = "\033[1m", "\033[31m", "\033[32m", "\033[33m", "\033[0m"


def say(msg, color=""):
    print(f"{color}{msg}{OFF if color else ''}", flush=True)


# CI: student-facing failures are also collected here, one section per sketch, for the
# build-hint job that explains them on the pull request.
ERRORS_FILE = os.environ.get("WS_ERRORS_FILE")
CURRENT = {"name": None, "written": set()}


def record(text):
    if not ERRORS_FILE or not CURRENT["name"]:
        return
    with open(ERRORS_FILE, "a") as f:
        if CURRENT["name"] not in CURRENT["written"]:
            f.write(f"### {CURRENT['name']}\n")
            CURRENT["written"].add(CURRENT["name"])
        f.write(text.rstrip() + "\n")


def die(msg):
    say(f"✗ {msg}", RED)
    record(msg)
    sys.exit(1)


# ---------------------------------------------------------------- boards

def udev_props(dev):
    r = subprocess.run(["udevadm", "info", "-q", "property", "-n", dev], capture_output=True, text=True)
    return dict(l.split("=", 1) for l in r.stdout.splitlines() if "=" in l)


def norm_mac(mac):
    """6-byte MAC; chips with 802.15.4 (C6) report an EUI-64 with ff:fe in the middle."""
    parts = mac.lower().split(":")
    if len(parts) == 8 and parts[3:5] == ["ff", "fe"]:
        parts = parts[:3] + parts[5:]
    return ":".join(parts)


def serial_ports():
    """Stable physical path (by-path = which USB socket) -> (dev, native_usb_mac or None).
    udev makes both usb- and usbv2- links for one port: keep one per device."""
    ports, seen = {}, set()
    links = sorted(glob.glob("/dev/serial/by-path/*"), key=lambda p: ("usbv2-" in p, p))
    for p in links:
        dev = os.path.realpath(p)
        if dev in seen or not re.search(r"tty(USB|ACM)\d+$", dev):
            continue
        seen.add(dev)
        props = udev_props(dev)
        native = None
        if props.get("ID_VENDOR_ID") == "303a":  # Espressif's own USB-Serial-JTAG
            m = re.search(r"([0-9A-Fa-f]{2}(?::[0-9A-Fa-f]{2}){5})$", props.get("ID_SERIAL_SHORT", ""))
            native = norm_mac(m.group(1)) if m else "?"
        ports[p] = (dev, native)
    if not ports:  # rare: no udev symlinks
        for dev in sorted(glob.glob("/dev/ttyUSB*") + glob.glob("/dev/ttyACM*")):
            ports[dev] = (dev, None)
    return ports


def load_registry():
    try:
        return json.loads(REGISTRY.read_text())
    except (OSError, ValueError):
        return {"numbers": {}, "chips": {}}


def save_registry(reg):
    REGISTRY.write_text(json.dumps(reg, indent=1))


def detect_chip(dev):
    """Ask the ROM bootloader which chip this is (resets the board)."""
    r = subprocess.run([sys.executable, "-m", "esptool", "--port", dev, "--baud", "115200",
                        "--connect-attempts", "3", "chip_id"],
                       capture_output=True, text=True, timeout=60)
    out = r.stdout + r.stderr
    m = re.search(r"Detecting chip type\.\.\.\s*(ESP32(?:-[A-Z0-9]+)?)", out)
    mac = re.search(r"MAC:\s*([0-9a-f:]{17,23})", out)
    if not m:
        return None, out
    chip = m.group(1)
    return {"chip": chip, "target": CHIP_TO_TARGET.get(chip), "mac": norm_mac(mac.group(1)) if mac else "?"}, out


def boards(probe=True):
    """[(number, path, dev, info)] for connected boards, numbering new sockets.
    A board plugged in by both its UART-bridge and its native USB port is listed once,
    on the bridge port (its auto-reset into the bootloader is the dependable one)."""
    reg = load_registry()
    ports = serial_ports()
    found = []
    # Bridge ports first, so native ports can be matched against their MACs.
    for path, (dev, native) in sorted(ports.items(), key=lambda kv: kv[1][1] is not None):
        if native is not None and any(i and i.get("mac") == native for *_, i in found):
            continue
        if path not in reg["numbers"]:
            reg["numbers"][path] = max(reg["numbers"].values(), default=0) + 1
        info = reg["chips"].get(path)
        if probe or info is None:
            new, _ = detect_chip(dev)
            if new:
                reg["chips"][path] = info = new
        found.append((reg["numbers"][path], path, dev, info))
    save_registry(reg)
    return sorted(found)


def pick_board(arg):
    found = boards(probe=False)
    if not found:
        die("No boards found. Plug one in (use a DATA cable, not a charge-only one) and run: ws doctor")
    if arg is None:
        if len(found) == 1:
            return found[0]
        cmd_boards(None)
        die("Several boards are connected: add the board number, e.g.  ws flash blue 3")
    for b in found:
        if arg in (str(b[0]), b[1], b[2]):
            return b
    cmd_boards(None)
    die(f"No board '{arg}'.")


def board_target(board, fresh=False):
    """Chip target for a board. fresh=True asks the chip again instead of trusting the cache:
    the cache is per USB socket, and a different board may have been plugged in since."""
    n, path, dev, info = board
    if fresh or not info or not info.get("target"):
        info, out = detect_chip(dev)
        if not info:
            say(out[-1500:])
            die(f"Board {n} ({dev}) did not answer. Hold its BOOT button, tap EN/RST, "
                "release BOOT, and try again.")
        reg = load_registry()
        reg["chips"][path] = info
        save_registry(reg)
    if not info.get("target"):
        die(f"Board {n} is a {info['chip']}, which this workshop has no build for.")
    return info["target"]


# ---------------------------------------------------------------- build

def resolve_sketch(name):
    cands = [Path(name), HERE / "teams" / f"{name}.cpp", HERE / "teams" / name,
             HERE / "examples" / f"{name}.cpp", HERE / "examples" / name]
    cands += sorted((HERE / "examples").glob(f"*{name}*.cpp"))
    for c in cands:
        if c.is_file() and c.suffix == ".cpp":
            return c.resolve()
    die(f"No sketch '{name}'. Teams: {', '.join(p.stem for p in (HERE / 'teams').glob('*.cpp')) or 'none yet'}."
        f"  Examples: {', '.join(p.stem for p in sorted((HERE / 'examples').glob('*.cpp')))}")


def stage_sketch(src, display=None):
    """Copy the sketch into main/sketch.cpp, only rewriting it if it changed (keeps builds incremental).
    #line makes compiler errors point at the student's own file and line numbers, named as the
    student knows it (teams/rockets.cpp), not where it sits on the laptop."""
    if display is None:
        try:
            display = src.resolve().relative_to(HERE)
        except ValueError:
            display = src
    text = (f'#line 1 "{display}"\n' + src.read_text() +
            f'\n// ---- added by ws ----\nconst char* sketch_name() {{ return "{src.stem}"; }}\n')
    if not SKETCH.exists() or SKETCH.read_text() != text:
        SKETCH.write_text(text)


def build(target):
    bdir = HERE / "build" / target
    cmd = ["idf.py", "-C", str(HERE), "-B", str(bdir), f"-DIDF_TARGET={target}",
           f"-DSDKCONFIG={bdir / 'sdkconfig'}", "build"]
    if SANDBOX:
        cmd = ["bwrap", "--unshare-all", "--die-with-parent", "--new-session",
               "--ro-bind", "/nix", "/nix", "--ro-bind", "/bin", "/bin", "--ro-bind", "/usr", "/usr",
               "--bind", str(HERE), str(HERE), "--dev", "/dev", "--proc", "/proc",
               "--tmpfs", "/tmp", "--setenv", "HOME", "/tmp", "--chdir", str(HERE), "--"] + cmd
    first = not (bdir / "build.ninja").exists()
    if first:
        say(f"First build for {target}: about 1-3 minutes (later builds take seconds)…", YELLOW)
    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode != 0:
        out = r.stdout + r.stderr
        # Show the compiler's error lines first, then the tail, so students see their mistake.
        # Keep GCC's diagnostics plus its source excerpt ("   12 |   code" and the ^ line under it).
        errs = [l for l in out.splitlines()
                if (re.search(r"(error|warning|note):", l) and "ninja" not in l)
                or re.match(r"^\s*\d*\s+\|", l)]
        excerpt = ("\n".join(errs[:60]) or out[-3000:]).replace(str(HERE) + "/", "")
        say(excerpt)
        record(excerpt)
        die("Build failed: fix the first error above (file:line:column), then flash again.")
    return bdir


def flash(board, bdir, target):
    n, _, dev, _ = board
    for attempt in (1, 2):
        r = subprocess.run([sys.executable, "-m", "esptool", "--chip", target, "--port", dev,
                            "--baud", BAUD, "--before", "default_reset", "--after", "hard_reset",
                            "write_flash", "@flash_args"], cwd=bdir, capture_output=True, text=True)
        if r.returncode == 0:
            say(f"✓ Flashed board {n} ({dev})", GREEN)
            return
        out = r.stdout + r.stderr
        if "Permission denied" in out:
            die(f"No permission on {dev}: you must be in the 'dialout' group (then log out and in).")
        if "Device or resource busy" in out or "could not open port" in out.lower():
            die(f"{dev} is busy: close any serial monitor that has board {n} open.")
        if attempt == 1:
            say(out[-800:])
            if IN_CI:
                say(f"Board {n} didn't respond, retrying once…", YELLOW)
                continue
            say(f"Board {n} didn't respond. Hold BOOT, tap EN/RST, release BOOT, then press Enter…", YELLOW)
            try:
                input()
            except EOFError:
                pass
    die(f"Flashing board {n} failed twice. Try another USB cable or socket.")


def board_from_header(src):
    """A sketch can name its board in a comment:  // board: 3"""
    m = re.search(r"^\s*//\s*board\s*:\s*(\S+)", src.read_text(), re.M | re.I)
    return m.group(1) if m else None


def build_and_flash(sketch_name, board, display=None):
    src = resolve_sketch(sketch_name)
    target = board_target(board, fresh=True)
    say(f"{BOLD}▶ {src.stem} → board {board[0]} ({target}){OFF}")
    # One build tree per chip is shared by everyone, so build+flash happen under one lock:
    # nobody else's sketch can land in main/sketch.cpp between our build and our flash.
    with open(LOCK, "w") as lk:
        try:
            fcntl.flock(lk, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            say("Another team is flashing, waiting for them…", YELLOW)
            fcntl.flock(lk, fcntl.LOCK_EX)
        stage_sketch(src, display)
        bdir = build(target)
        flash(board, bdir, target)
    return bdir


def monitor(board, bdir=None):
    n, _, dev, _ = board
    target = board_target(board)
    bdir = bdir or HERE / "build" / target
    elf = bdir / "workshop.elf"
    say(f"Serial monitor on board {n} — press Ctrl+] to quit", YELLOW)
    cmd = [sys.executable, "-m", "esp_idf_monitor", "--port", dev, "--baud", "115200",
           "--target", target]
    if elf.exists():
        cmd.append(str(elf))
    os.execvp(cmd[0], cmd)


# ---------------------------------------------------------------- commands

def cmd_boards(_):
    found = boards(probe=True)
    if not found:
        say("No boards connected.", YELLOW)
        return
    say(f"{BOLD}{'#':>3}  {'device':14} {'chip':10} {'MAC':18} USB socket{OFF}")
    for n, path, dev, info in found:
        chip = info["chip"] if info else f"{RED}no answer{OFF}"
        mac = info["mac"] if info else ""
        say(f"{n:>3}  {dev:14} {chip:10} {mac:18} {Path(path).name}")


def cmd_new(args):
    if not args:
        die("Usage: ws new <team> [example] [board]")
    team = args[0]
    if not re.fullmatch(r"[A-Za-z][A-Za-z0-9_-]{0,30}", team):
        die("Team names: letters, digits, - and _ (start with a letter).")
    dst = HERE / "teams" / f"{team}.cpp"
    if dst.exists():
        die(f"{dst.relative_to(HERE)} already exists: edit it, or pick another name.")
    src = resolve_sketch(args[1] if len(args) > 1 else "01_blink")
    board = args[2] if len(args) > 2 else "?"
    dst.write_text(f"// board: {board}\n" + src.read_text())
    say(f"✓ Created {dst.relative_to(HERE)} from {src.stem}. Edit it, then:  ws run {team} <board>", GREEN)


def cmd_flash(args, then_monitor=False):
    if not args:
        die("Usage: ws flash <sketch> [board]")
    board = pick_board(args[1] if len(args) > 1 else board_from_header(resolve_sketch(args[0])))
    bdir = build_and_flash(args[0], board)
    if then_monitor:
        monitor(board, bdir)


def cmd_flash_all(args):
    if not args:
        die("Usage: ws flash-all <sketch>")
    found = boards(probe=True)
    if not found:
        die("No boards connected.")
    failed = []
    for b in found:
        try:
            build_and_flash(args[0], b)
        except SystemExit:
            failed.append(str(b[0]))
    if failed:
        die(f"Failed boards: {', '.join(failed)}")
    say(f"✓ All {len(found)} boards flashed.", GREEN)


def cmd_monitor(args):
    monitor(pick_board(args[0] if args else None))


def capture(board, seconds=8.0):
    """Reset the board and print what it says (for the Actions log)."""
    import time
    import serial  # pyserial ships with esptool
    n, _, dev, _ = board
    say(f"── serial output from board {n}, first {seconds:g} s ──", YELLOW)
    with serial.Serial(dev, 115200, timeout=0.2) as s:
        s.dtr = False
        s.rts = True   # hold EN low = reset…
        time.sleep(0.1)
        s.rts = False  # …and run the app
        end, line = time.time() + seconds, b""
        while time.time() < end:
            line += s.read(256)
            *done, line = line.split(b"\n")
            for l in done:
                text = l.decode(errors="replace").rstrip("\r")
                # Skip the ROM boot banner; show the sketch's own output.
                if not re.match(r"^(ESP-ROM|Build:|rst:|SPIWP|mode:|load:|entry |configsip|clk_drv)", text):
                    print(text, flush=True)
        if line:
            print(line.decode(errors="replace"), flush=True)
    say("── end of output ──", YELLOW)


def cmd_capture(args):
    board = pick_board(args[0] if args else None)
    capture(board, float(args[1]) if len(args) > 1 else 8.0)


def cmd_ci(args):
    """Flash each team file changed between two commits; one failure doesn't stop the others."""
    before, sha = (args + ["", ""])[:2]
    if not sha:
        die("Usage: ws ci <before-sha> <sha>")
    if re.fullmatch(r"0+", before or "0") or subprocess.run(
            ["git", "-C", str(HERE), "cat-file", "-e", f"{before}^{{commit}}"],
            capture_output=True).returncode != 0:
        # New branch (or history we don't have): use what this commit touched.
        diff = ["git", "-C", str(HERE), "diff-tree", "--no-commit-id", "--name-only", "-r", "--root", sha]
    else:
        diff = ["git", "-C", str(HERE), "diff", "--name-only", before, sha]
    changed = subprocess.run(diff, capture_output=True, text=True, check=True).stdout.split()
    sketches = [HERE / f for f in changed
                if re.fullmatch(r"teams/[^/]+\.cpp", f) and (HERE / f).is_file()]
    if not sketches:
        say("No team sketches changed in this push: nothing to flash.")
        return
    failed = []
    for src in sketches:
        say(f"\n{BOLD}════ {src.relative_to(HERE)} ════{OFF}")
        CURRENT["name"] = str(src.relative_to(HERE))
        try:
            num = board_from_header(src)
            if num is None:
                die(f"{src.name} has no board line. Add  // board: 3  (your board number) at the top.")
            board = pick_board(num)
            build_and_flash(str(src), board)
            capture(board)
        except SystemExit:
            failed.append(src.name)
    if failed:
        die(f"Failed: {', '.join(failed)}")


ALLOWED_INCLUDES = {"workshop.h", "cstdio", "cstdlib", "cstdint", "cstring", "cmath", "cctype",
                    "climits", "array", "algorithm", "stdio.h", "stdlib.h", "stdint.h", "string.h",
                    "math.h", "ctype.h", "limits.h"}


def check_untrusted(src):
    """Readable refusals for things a workshop sketch never needs (the sandbox is the real fence)."""
    text = src.read_text()
    for inc in re.findall(r'^\s*#\s*include\s*[<"]([^>"]+)[>"]', text, re.M):
        if inc not in ALLOWED_INCLUDES:
            die(f"{src.name}: #include <{inc}> isn't allowed here. Use workshop.h (plus <cmath> etc.).")
    if re.search(r"\b(asm|__asm__|__asm|incbin|_Pragma|#\s*pragma|#\s*embed)\b", text):
        die(f"{src.name}: asm / pragma / embed aren't allowed in workshop sketches.")


def cmd_ci_pr(args):
    """Pull request: take only teams/*.cpp from the PR head; build with main's tooling, sandboxed."""
    base, head = (args + ["", ""])[:2]
    if not head:
        die("Usage: ws ci-pr <base-sha> <head-sha>")
    git = ["git", "-C", str(HERE)]
    changed = subprocess.run(git + ["diff", "--name-only", f"{base}...{head}"],
                             capture_output=True, text=True, check=True).stdout.split()
    others = [f for f in changed if not re.fullmatch(r"teams/[A-Za-z0-9_-]+\.cpp", f)]
    if others:
        say(f"Note: only teams/*.cpp files are used from a pull request; ignoring {', '.join(others)}",
            YELLOW)
    stage = HERE / "build" / "pr"
    stage.mkdir(parents=True, exist_ok=True)
    sketches = []
    for f in changed:
        if not re.fullmatch(r"teams/[A-Za-z0-9_-]+\.cpp", f):
            continue
        r = subprocess.run(git + ["show", f"{head}:{f}"], capture_output=True)
        if r.returncode != 0:
            continue  # deleted in the PR
        dst = stage / Path(f).name
        dst.write_bytes(r.stdout[:100_000])
        sketches.append(dst)
    if not sketches:
        say("No team sketches changed in this pull request: nothing to flash.")
        return
    failed = []
    for src in sketches:
        say(f"\n{BOLD}════ teams/{src.name} ════{OFF}")
        CURRENT["name"] = f"teams/{src.name}"
        try:
            check_untrusted(src)
            num = board_from_header(src)
            if num is None:
                die(f"{src.name} has no board line. Add  // board: 3  (your board number) at the top.")
            board = pick_board(num)
            build_and_flash(str(src), board, f"teams/{src.name}")
            capture(board)
        except SystemExit:
            failed.append(src.name)
    if failed:
        die(f"Failed: {', '.join(failed)}")


def cmd_prewarm(args):
    targets = args or TARGETS
    examples = sorted((HERE / "examples").glob("*.cpp"))
    with open(LOCK, "w") as lk:
        fcntl.flock(lk, fcntl.LOCK_EX)
        for t in targets:
            for ex in examples:
                say(f"build {t} / {ex.stem}")
                stage_sketch(ex)
                build(t)
    say(f"✓ All {len(examples)} examples build for {', '.join(targets)}.", GREEN)


def cmd_doctor(_):
    ok = True
    user_groups = {grp.getgrgid(g).gr_name for g in os.getgroups()}
    if "dialout" in user_groups:
        say("✓ in the dialout group", GREEN)
    else:
        ok = False
        say("✗ not in 'dialout': add it (NixOS: users.users.<you>.extraGroups) and log in again", RED)
    for svc in ("brltty", "ModemManager"):
        r = subprocess.run(["systemctl", "is-active", svc], capture_output=True, text=True)
        if r.stdout.strip() == "active":
            ok = False
            say(f"✗ {svc} is running and can grab USB-serial boards: sudo systemctl stop {svc}", RED)
    if shutil.which("idf.py"):
        say("✓ ESP-IDF toolchain on PATH", GREEN)
    else:
        ok = False
        say("✗ idf.py missing: run through ./ws (it enters nix develop .#esp)", RED)
    built = [t for t in TARGETS if (HERE / "build" / t / "build.ninja").exists()]
    say(f"{'✓' if built else '!'} prewarmed builds: {', '.join(built) or 'none (run ws prewarm)'}",
        GREEN if built else YELLOW)
    cmd_boards(None)
    if not serial_ports():
        say("  No serial ports. Check: data cable (not charge-only), `dmesg | tail` shows ch341/cp210x/cdc_acm.",
            YELLOW)
    sys.exit(0 if ok else 1)


COMMANDS = {
    "boards": cmd_boards, "new": cmd_new, "flash": cmd_flash,
    "run": lambda a: cmd_flash(a, then_monitor=True), "monitor": cmd_monitor,
    "flash-all": cmd_flash_all, "prewarm": cmd_prewarm, "doctor": cmd_doctor,
    "capture": cmd_capture, "ci": cmd_ci, "ci-pr": cmd_ci_pr,
}

if __name__ == "__main__":
    if len(sys.argv) < 2 or sys.argv[1] not in COMMANDS:
        print(__doc__)
        sys.exit(0 if len(sys.argv) < 2 else 1)
    COMMANDS[sys.argv[1]](sys.argv[2:])
