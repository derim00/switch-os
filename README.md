# Switch-OS: the Switch HOME menu on NumWorks

[Readme en Français](https://github.com/derim00/switch-os/README_fr.md)

**Switch-OS replaces the home screen of the NumWorks calculator (n0110, n0115 or n0120) with a menu inspired by the Nintendo Switch HOME menu**: your `.nwa` games as large tiles in the center, the calculator's apps as round buttons at the bottom, and a "HOME Menu / Ⓐ Continue" screen at startup.

![Switch-OS preview](docs/apercu.png)

<p align="center"><img src="docs/navigation.gif" alt="Navigating Switch-OS" width="480"></p>

> The screenshots come from the simulator, which can't load games, so the tiles are empty there. On the calculator, each tile shows the game's icon, with its name in cyan above it when selected.

## What Switch-OS does

- **"HOME Menu" screen at startup**: dark background, a house, a pulsing "Ⓐ Continue", and your first three games in the left column. Press **OK** to enter.
- **Games in the center**: each `.nwa` app becomes a large tile with its own icon, followed by empty slots like on the console. The selected tile has a pulsing cyan frame and its title above it.
- **Apps at the bottom**: round white buttons with a colored icon (Calculation, Graph, Equations, Statistics… and Settings at the end). The selected button grows, gets the cyan ring, and shows its name.
- **Top bar** (players, battery) and **bottom bar** (console, "Ⓐ OK").
- **Controls**: ◀ ▶ within a row, ▲ to go to the games, ▼ to go to the apps, OK or EXE to launch.
- **Animations**: smooth row scrolling, transitions between rows, pulsing frame and ring, fade-in when the menu opens.
- **Red title bar** in apps, instead of NumWorks yellow.
- **One-click installers for Mac and Windows**: a local web page that detects the calculator, manages your games (drag and drop) and installs everything with one button. On Windows, a simple `.exe`: nothing to install, no Python and no driver.

![The installer](docs/installateur.png)

## Installation

### 1. Get Switch-OS

Since July 2021, Epsilon's code (the NumWorks software) is no longer under a free license. Switch-OS therefore publishes **no NumWorks code or firmware**: only a **patch** (`patches/switch-os-epsilon.patch`) and its own code. The firmware is built from NumWorks' official sources, in your GitHub account or on your Mac.

**Without compiling anything (Mac or Windows)**

1. At the top of this page: **Use this template** > **Create a new repository**, and check **Private** (mandatory: the build refuses to run in a public repository, so the firmware can't be downloaded by everyone).
2. Optional: add your `.nwa` games to the `games/` folder of your private copy (*Add file* > *Upload files*). They will be prepared and included in the installer.
3. In your copy: **Actions** tab > **Build Switch-OS** > **Run workflow**.
4. About 30 minutes later (one firmware per model), at the bottom of the build page, download **Switch-OS-Mac** or **Switch-OS-Windows** and unzip it (twice for the Mac version: GitHub puts the zip inside a zip).

**Building on your Mac**

```bash
brew install make dfu-util libusb
brew install --cask gcc-arm-embedded
git clone https://github.com/derim00/switch-os.git && cd switch-os
./scripts/build-firmware.sh
```

The script downloads Epsilon at the commit given in `EPSILON_COMMIT` (Epsilon 26.1, the latest version published by NumWorks), applies the patch, compiles, prepares the games from `games/` and fills the `installer/` folder.

### 2. Install on the calculator

**On Mac**

1. One time only: `brew install libusb dfu-util` (and `brew install --cask gcc-arm-embedded` if you want to add more games).
2. Double-click **`Installer Switch-OS.command`** (the first time: right-click > **Open**). The installer page opens (http://127.0.0.1:8766).

**On Windows** (nothing to install: no Python, no driver)

1. Unzip **Switch-OS-Windows** (right-click > *Extract all*): don't run the installer from inside the zip.
2. In the `Switch-OS` folder, double-click **`Installer Switch-OS.exe`** (if SmartScreen appears: *More info* > *Run anyway*). A black window opens with the installer page in your browser: leave it open, and close it when you're done to quit. As with NumSocial, the `.exe` contains Python and libusb, and the calculator declares itself as a WinUSB device: Windows recognizes it without a driver.

**Then, on both**

3. Connect the calculator via USB and press **Reset** on the back: it restarts on the official system.
4. When the light turns green, drag your `.nwa` games into the page if you want, then click **Ⓐ Install Switch-OS**.

The installer checks that **slot B** is free before writing: the official system (slot A) is never modified. It prepares the games for their place in slot B (as the NumWorks website does), copies them, reads them back to verify them, then installs Switch-OS and starts it.

## Good to know

- **Calculator**: NumWorks **n0110**, **n0115** or **n0120**, with the official software **26.4.0** in slot A. Switch-OS is built from Epsilon 26.1 (the latest published version) with version number 26.4.0.
- **Three models**: the build produces one firmware per model (n0110, n0115, n0120) and the installer automatically picks the one for the connected calculator. First update your calculator on numworks.com: the system must have the same version as the official software in slot A.
- **Games too large**: a game that doesn't fit in slot B (NumPlay, for example) is skipped with a message, instead of making the build fail. Remove it from the `games/` folder.
- **After a Reset**, the calculator goes back to the official system: Switch-OS stays in slot B, so you just need to run the installation again.
- **Only one system in slot B**: Switch-OS replaces [PSP-OS](https://github.com/derim00/psp-os) if it was installed, and vice versa. Both installers can run at the same time (ports 8765 and 8766).
- **Home and On/Off keys**: on unofficial software, the calculator's system handles these two keys itself. Switch-OS clears the return point left by the official system at startup so that Home takes you back to the menu; if the calculator still goes back to slot A, use **Back** (↩) to return to the menu from an app.
- **Games on Windows**: games already in `games/` at build time are ready; to add more directly from Windows, you need the ARM toolchain ([Arm GNU Toolchain](https://developer.arm.com/downloads/-/arm-gnu-toolchain-downloads), *arm-none-eabi* version).
- **Games**: only `.nwa` apps you have the right to use, and only in your private copy: never in this public repository.

## How it's made

| File | Role |
| --- | --- |
| `patches/switch-os-epsilon.patch` | the HOME menu (`apps/home`), the icons, the animations (`escher`), the red bar |
| `scripts/build-firmware.sh` | downloads Epsilon, applies the patch, compiles, prepares the installer |
| `installer/server.py` | local installer server (127.0.0.1 only), Mac and Windows |
| `installer/dfu_launch.py` | launches NumWorks' DFU tool with libusb (Homebrew or `libusb-package`) and the Windows fixes from NumSocial |
| `scripts/build-windows-installer.py` | builds `Installer Switch-OS.exe` with PyInstaller (on Windows, in the workflow) and tests it |
| `installer/index.html` | the installer page |
| `installer/link_games.py` | places each `.nwa` game at its address in slot B, like the NumWorks website |
| `installer/Installer Switch-OS.command` | double-click launcher for Mac |
| `.github/workflows/build.yml` | build in your private copy, with both installers |

## License

Switch-OS code is under the **CC BY-NC-SA 4.0** license (see `LICENSE`). Epsilon remains the property of NumWorks and is not included in this repository. Switch-OS is a fan project, not affiliated with Nintendo or NumWorks; Nintendo Switch is a trademark of Nintendo.
