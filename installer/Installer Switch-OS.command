#!/bin/bash
# Double-clic : lance l'installateur Switch-OS et ouvre la page dans le navigateur.
cd "$(dirname "$0")" || exit 1
export PATH="/opt/homebrew/bin:/usr/local/bin:$PATH"
export DYLD_FALLBACK_LIBRARY_PATH="/opt/homebrew/lib:/usr/local/lib:${DYLD_FALLBACK_LIBRARY_PATH:-}"
if ! command -v dfu-util >/dev/null; then
  echo "Il manque dfu-util. Installe-le avec :  brew install dfu-util libusb"
  read -r -p "Appuie sur Entrée pour fermer." _
  exit 1
fi
exec python3 server.py "$@"
