#!/usr/bin/env python3
"""Switch-OS installer: a small local web server to install Switch-OS and its games
on a NumWorks n0120 with one click.

Only listens on 127.0.0.1. Never writes anything outside of slot B: before
flashing, it checks that slot B is the inactive slot (i.e. that the
calculator is running its official software from slot A).

Usage: server.py [--port 8765] [--no-browser]

Needs: python3, dfu-util and libusb (brew install dfu-util libusb), plus the
ARM toolchain to add games (brew install --cask gcc-arm-embedded).
"""

import argparse
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import threading
import time
import webbrowser
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import unquote

HERE = Path(__file__).resolve().parent
# NumWorks' DFU tool (with its bundled pyusb), copied here by the build
DFU_PY = HERE / "numworks" / "dfu.py"
LINK_GAMES = HERE / "link_games.py"
FIRMWARE_DFU = HERE / "firmware" / "switch-os.B.dfu"
FIRMWARE_ELF = HERE / "firmware" / "switch-os.B.elf"
GAMES_DIR = HERE / "games"
PAGE = HERE / "index.html"

PYTHON = sys.executable
DFU_UTIL = shutil.which("dfu-util") or "/opt/homebrew/bin/dfu-util"
if shutil.which("dfu-util") is None and not os.path.exists(DFU_UTIL):
    DFU_UTIL = "/usr/local/bin/dfu-util"
OBJCOPY = shutil.which("arm-none-eabi-objcopy") or "/opt/homebrew/bin/arm-none-eabi-objcopy"

USERLAND_B = 0x90410000
APPS_START = 0x90580000
APPS_SIZE = 0x907F0000 - APPS_START  # external apps area of slot B
MAX_UPLOAD = 4 * 1024 * 1024

# ------------------------------------------------------------------ helpers


def run(cmd, timeout=600):
    p = subprocess.run(cmd, cwd=HERE, capture_output=True, text=True,
                       timeout=timeout)
    return p.returncode, (p.stdout or "") + (p.stderr or "")


def dfu_query(flag):
    code, out = run([PYTHON, str(DFU_PY), flag], timeout=20)
    lines = [l.strip() for l in out.strip().splitlines() if l.strip()]
    if code != 0 or not lines or "Error" in out:
        return None
    return lines[-1]


def calculator_status():
    model = dfu_query("--model")
    if model is None:
        return {"connected": False}
    slot = dfu_query("--inactive_slot")
    return {"connected": True, "model": model, "inactiveSlot": slot}


def game_name(path):
    with tempfile.TemporaryDirectory() as tmp:
        out = os.path.join(tmp, "name.bin")
        code, _ = run([OBJCOPY, "-O", "binary",
                       "--only-section=.rodata.eadk_app_name", str(path), out],
                      timeout=20)
        if code != 0 or not os.path.exists(out):
            return None
        raw = Path(out).read_bytes().split(b"\0")[0]
        return raw.decode("utf-8", "replace") or None


def list_games():
    games = []
    for p in sorted(GAMES_DIR.glob("*.nwa"), key=lambda p: p.name.lower()):
        games.append({"file": p.name, "name": game_name(p) or p.stem,
                      "size": p.stat().st_size})
    return games


def safe_game_path(filename):
    name = os.path.basename(unquote(filename))
    if not name.lower().endswith(".nwa") or name.startswith("."):
        return None
    return GAMES_DIR / name


# ---------------------------------------------------------------- install job


class Job:
    def __init__(self):
        self.lock = threading.Lock()
        self.running = False
        self.steps = []
        self.log = []
        self.result = None  # "ok" | "error" | None

    def snapshot(self):
        with self.lock:
            return {"running": self.running, "steps": list(self.steps),
                    "log": "\n".join(self.log[-200:]), "result": self.result}

    def step(self, label, state="running"):
        with self.lock:
            if self.steps and self.steps[-1]["state"] == "running":
                self.steps[-1]["state"] = "done"
            self.steps.append({"label": label, "state": state})

    def fail(self, message):
        with self.lock:
            if self.steps:
                self.steps[-1]["state"] = "error"
            self.log.append("ERREUR: " + message)
            self.result = "error"
            self.running = False

    def write(self, text):
        with self.lock:
            for line in text.replace("\r", "\n").splitlines():
                # Drop progress-bar noise
                if line.strip() and "%" not in line:
                    self.log.append(line.rstrip())


JOB = Job()


def install():
    try:
        JOB.step("Recherche de la calculatrice")
        status = calculator_status()
        if not status["connected"]:
            return JOB.fail("Calculatrice introuvable. Branche-la en USB, "
                            "appuie sur Reset (au dos) et attends le menu officiel.")
        JOB.write(f"Modèle: {status['model']}, slot inactif: {status['inactiveSlot']}")
        if status["model"] != "n0120":
            return JOB.fail(f"Modèle {status['model']} non supporté (Switch-OS est fait pour la n0120).")
        if status["inactiveSlot"] != "B":
            return JOB.fail("La calculatrice tourne sur le slot B. Appuie sur Reset au dos "
                            "pour revenir sur le système officiel (slot A), puis réessaie.")
        if not FIRMWARE_DFU.exists() or not FIRMWARE_ELF.exists():
            return JOB.fail("Firmware Switch-OS introuvable dans installer/firmware : "
                            "compile-le d'abord (voir le README).")

        JOB.step("Préparation des jeux")
        with tempfile.TemporaryDirectory() as tmp:
            image = os.path.join(tmp, "games.bin")
            code, out = run([PYTHON, str(LINK_GAMES), str(FIRMWARE_ELF),
                             str(GAMES_DIR), image])
            JOB.write("\n".join(l for l in out.splitlines() if "RWX" not in l))
            if code != 0:
                return JOB.fail("Impossible de préparer les jeux (voir le journal).")
            size = os.path.getsize(image)
            if size > APPS_SIZE:
                return JOB.fail("Trop de jeux: ils ne tiennent pas dans le slot B.")

            JOB.step("Copie des jeux sur la calculatrice")
            code, out = run([DFU_UTIL, "-a", "0", "-s", hex(APPS_START), "-D", image])
            JOB.write(out)
            if code != 0:
                return JOB.fail("Échec de l'écriture des jeux.")

            JOB.step("Vérification des jeux")
            back = os.path.join(tmp, "readback.bin")
            code, out = run([DFU_UTIL, "-a", "0", "-s", f"{hex(APPS_START)}:{size}",
                             "-U", back])
            if code != 0 or Path(back).read_bytes() != Path(image).read_bytes():
                JOB.write(out)
                return JOB.fail("Les jeux relus ne correspondent pas à ce qui a été écrit.")
            JOB.write("Jeux vérifiés: identiques.")

        JOB.step("Installation de Switch-OS (slot B)")
        if dfu_query("--inactive_slot") != "B":
            return JOB.fail("Le slot B n'est plus le slot inactif, installation annulée.")
        code, out = run([PYTHON, str(DFU_PY), "-s", f"{hex(USERLAND_B)}:leave",
                         "-D", str(FIRMWARE_DFU)])
        JOB.write(out)
        if code != 0:
            return JOB.fail("Échec de l’écriture de Switch-OS.")

        JOB.step("Switch-OS démarre sur la calculatrice", "done")
        with JOB.lock:
            JOB.result = "ok"
            JOB.running = False
    except Exception as e:  # pragma: no cover - surfaced to the page
        JOB.fail(f"{type(e).__name__}: {e}")


def start_install():
    with JOB.lock:
        if JOB.running:
            return False
        JOB.running = True
        JOB.steps = []
        JOB.log = []
        JOB.result = None
    threading.Thread(target=install, daemon=True).start()
    return True


# --------------------------------------------------------------------- http


class Handler(BaseHTTPRequestHandler):
    def log_message(self, *args):
        pass

    def send_json(self, data, code=200):
        body = json.dumps(data).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def same_origin(self):
        # Basic protection against other websites driving the installer
        origin = self.headers.get("Origin")
        host = self.headers.get("Host", "")
        return origin is None or origin == f"http://{host}"

    def do_GET(self):
        if self.path in ("/", "/index.html"):
            body = PAGE.read_bytes()
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.send_header("Cache-Control", "no-store")
            self.end_headers()
            self.wfile.write(body)
        elif self.path == "/api/status":
            busy = JOB.snapshot()["running"]
            calc = {"connected": None} if busy else calculator_status()
            self.send_json({"calculator": calc, "games": list_games(),
                            "firmware": FIRMWARE_DFU.exists(),
                            "appsCapacity": APPS_SIZE})
        elif self.path == "/api/job":
            self.send_json(JOB.snapshot())
        else:
            self.send_json({"error": "not found"}, 404)

    def do_POST(self):
        if not self.same_origin():
            return self.send_json({"error": "forbidden"}, 403)
        if self.path == "/api/install":
            ok = start_install()
            return self.send_json({"started": ok}, 200 if ok else 409)
        if self.path == "/api/games":
            target = safe_game_path(self.headers.get("X-Filename", ""))
            length = int(self.headers.get("Content-Length", "0"))
            if target is None:
                return self.send_json({"error": "Seuls les fichiers .nwa sont acceptés."}, 400)
            if length <= 0 or length > MAX_UPLOAD:
                return self.send_json({"error": "Fichier vide ou trop gros."}, 400)
            data = self.rfile.read(length)
            if not data.startswith(b"\x7fELF"):
                return self.send_json({"error": "Ce n'est pas un fichier .nwa valide."}, 400)
            target.write_bytes(data)
            if game_name(target) is None:
                target.unlink()
                return self.send_json({"error": "Fichier .nwa invalide (pas de nom d'app)."}, 400)
            return self.send_json({"ok": True})
        self.send_json({"error": "not found"}, 404)

    def do_DELETE(self):
        if not self.same_origin():
            return self.send_json({"error": "forbidden"}, 403)
        if self.path.startswith("/api/games/"):
            target = safe_game_path(self.path[len("/api/games/"):])
            if target is None or not target.exists():
                return self.send_json({"error": "Jeu introuvable."}, 404)
            target.unlink()
            return self.send_json({"ok": True})
        self.send_json({"error": "not found"}, 404)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--port", type=int, default=8766)
    parser.add_argument("--no-browser", action="store_true")
    args = parser.parse_args()
    GAMES_DIR.mkdir(exist_ok=True)
    # 8765 is the PSP-OS installer: use another port, and the next free one
    # if this one is already taken.
    server = None
    for port in range(args.port, args.port + 20):
        try:
            server = ThreadingHTTPServer(("127.0.0.1", port), Handler)
            break
        except OSError:
            continue
    if server is None:
        raise SystemExit("Aucun port libre pour l'installateur.")
    url = f"http://127.0.0.1:{port}/"
    print(f"Switch-OS Installer: {url}  (Ctrl+C pour quitter)")
    if not args.no_browser:
        threading.Timer(0.5, lambda: webbrowser.open(url)).start()
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()
