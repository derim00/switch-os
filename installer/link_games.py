#!/usr/bin/env python3
"""Pre-install NWA games into the PSP-OS external apps area (slot B).

Does what NumWorks' nwlink does when installing an app from the website: link
each relocatable .nwa together with the EADK runtime at its final flash
address inside the slot's external apps area, and concatenate the results
(each app aligned on the external apps sector unit) into one binary image to
flash at the start of the area.

The EADK runtime (eadk.o) and its linker script template are produced by
scripts/build-firmware.sh from NumWorks' sources, in numworks/eadk/.

Usage: link_games.py <userland.elf> <games_dir> <out.bin> [--eadk DIR]
Needs arm-none-eabi-gcc only when there is at least one game.
"""

import argparse
import os
import shutil
import subprocess
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
SECTOR = 0x10000  # Config::ExternalAppsSectorUnit on n0120
TRAMPOLINE = 0x0807FC00  # TrampolineOrigin (bootloader, internal flash)
CPU = ["-mcpu=cortex-m7", "-mthumb", "-mfloat-abi=hard", "-mfpu=fpv5-d16"]


def tool(name):
    path = shutil.which(name)
    if path is None:
        for prefix in ("/opt/homebrew/bin", "/usr/local/bin",
                       "/Applications/ArmGNUToolchain/bin"):
            candidate = os.path.join(prefix, name)
            if os.path.exists(candidate):
                return candidate
        raise SystemExit(f"{name} introuvable : installe la chaîne ARM "
                         "(brew install --cask gcc-arm-embedded).")
    return path


def symbols(elf):
    out = subprocess.run([tool("arm-none-eabi-nm"), elf], check=True,
                         capture_output=True, text=True).stdout
    table = {}
    for line in out.splitlines():
        parts = line.split()
        if len(parts) == 3:
            table[parts[2]] = int(parts[0], 16)
    return table


def linker_script(template, flash_start, flash_length, ram_start, ram_length):
    ld = (template.replace("{{ flashStart }}", hex(flash_start))
                  .replace("{{ flashLength }}", hex(flash_length))
                  .replace("{{ ramStart }}", hex(ram_start))
                  .replace("{{ ramLength }}", hex(ram_length))
                  .replace("{{ trampolineStart }}", hex(TRAMPOLINE)))
    # The app size in the header must cover the .data initial values stored
    # in flash after .rodata, otherwise the next app could overlap them.
    ld = ld.replace("    _eadk_app_end = .;\n", "")
    ld += ("\n_eadk_app_end = LOADADDR(.data) + SIZEOF(.data);\n"
           "_eadk_external_data_start = _eadk_app_end;\n"
           "_eadk_external_data_size = 0;\n")
    return ld


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("userland_elf")
    parser.add_argument("games_dir")
    parser.add_argument("out_bin")
    parser.add_argument("--eadk", default=str(HERE / "numworks" / "eadk"))
    args = parser.parse_args()

    games = sorted(Path(args.games_dir).glob("*.nwa"), key=lambda p: p.name.lower())
    image = bytearray()
    if games:
        sym = symbols(args.userland_elf)
        area_start = sym["_external_apps_flash_start"]
        area_end = sym["_external_apps_flash_end"]
        ram_start = (sym["_external_apps_RAM_start"] + 7) & ~7
        ram_end = sym["_external_apps_RAM_end"]
        eadk_obj = os.path.join(args.eadk, "eadk.o")
        template = Path(args.eadk, "linker.ld").read_text()
        with tempfile.TemporaryDirectory() as tmp:
            for game in games:
                address = area_start + len(image)
                ld_path = os.path.join(tmp, "app.ld")
                Path(ld_path).write_text(linker_script(
                    template, address, area_end - address, ram_start,
                    ram_end - ram_start))
                elf = os.path.join(tmp, "app.elf")
                binary = os.path.join(tmp, "app.bin")
                subprocess.run([tool("arm-none-eabi-gcc"), *CPU, "-nostartfiles",
                                "-nostdlib", "-T", ld_path, "-Wl,--gc-sections",
                                "-Wl,-e,_start", "-Wl,--no-warn-rwx-segments",
                                str(game), eadk_obj, "-lgcc", "-o", elf],
                               check=True)
                subprocess.run([tool("arm-none-eabi-objcopy"), "-O", "binary",
                                elf, binary], check=True)
                data = Path(binary).read_bytes()
                assert int.from_bytes(data[0:4], "little") == 0xDEC0BEBA
                size_field = int.from_bytes(data[24:28], "little")
                assert size_field >= len(data), (game, size_field, len(data))
                padded = (len(data) + SECTOR - 1) // SECTOR * SECTOR
                image += data + b"\xff" * (padded - len(data))
                print(f"{game.name:28s} @ {address:#x}  {len(data):7d} octets")
        assert area_start + len(image) + SECTOR <= area_end, "Trop de jeux"
    # One erased sector after the last app ends the app list
    image += b"\xff" * SECTOR
    Path(args.out_bin).write_bytes(image)
    print(f"Image des jeux : {len(image)} octets, {len(games)} jeu(x)")


if __name__ == "__main__":
    main()
