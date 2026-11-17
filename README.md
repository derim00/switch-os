# Switch-OS : le menu HOME de la Switch sur NumWorks

**Switch-OS remplace l'écran d'accueil de la calculatrice NumWorks (n0120) par
un menu inspiré du menu HOME de la Nintendo Switch** : tes jeux `.nwa` en
grandes vignettes au centre, les applis de la calculatrice en boutons ronds en
bas, et l'écran « Menu HOME / Ⓐ Continuer » au démarrage.

![Aperçu de Switch-OS](docs/apercu.png)

<p align="center"><img src="docs/navigation.gif" alt="Navigation dans Switch-OS" width="480"></p>

> Les captures viennent du simulateur, qui ne sait pas charger de jeux : les
> vignettes y sont vides. Sur la calculatrice, chaque vignette affiche
> l'icône du jeu, avec son nom en cyan au-dessus quand il est sélectionné.

## Ce que fait Switch-OS

- **Écran « Menu HOME » au démarrage** : fond sombre, maison, « Ⓐ Continuer »
  qui pulse, et tes trois premiers jeux dans la colonne de gauche. **OK** pour
  entrer.
- **Les jeux au centre** : chaque appli `.nwa` devient une grande vignette avec
  sa propre icône, suivie d'emplacements vides comme sur la console. La vignette
  choisie a un cadre cyan qui pulse et son titre au-dessus.
- **Les applis en bas** : boutons ronds blancs avec une icône de couleur
  (Calculs, Grapheur, Équations, Statistiques… et Paramètres à la fin) ; le
  bouton choisi grossit, prend l'anneau cyan et affiche son nom.
- **Barre du haut** (joueurs, batterie) et **barre du bas** (console, « Ⓐ OK »).
- **Commandes** : ◀ ▶ dans une rangée, ▲ vers les jeux, ▼ vers les applis,
  OK ou EXE pour lancer.
- **Animations** : défilement fluide des rangées, passage d'une rangée à
  l'autre, cadre et anneau qui pulsent, fondu à l'ouverture du menu.
- **Barre de titre rouge** dans les applis, au lieu du jaune NumWorks.
- **Installateur en un clic pour Mac** : une page web locale qui détecte la
  calculatrice, gère tes jeux (glisser-déposer) et installe tout avec un bouton.

![L'installateur](docs/installateur.png)

## Installation

### 1. Obtenir Switch-OS

Depuis juillet 2021, le code d'Epsilon (le logiciel de la NumWorks) n'est plus
sous licence libre. Switch-OS ne publie donc **aucun code ni aucun firmware de
NumWorks** : seulement un **patch** (`patches/switch-os-epsilon.patch`) et son
propre code. Le firmware se compile à partir des sources officielles de
NumWorks, dans ton compte GitHub ou sur ton Mac.

**Sans rien compiler**

1. En haut de cette page : **Use this template** > **Create a new repository**,
   coche **Private** (obligatoire : la compilation refuse de tourner dans un
   dépôt public, pour que le firmware ne soit pas téléchargeable par tous).
2. Dans ta copie : onglet **Actions** > **Build Switch-OS** > **Run workflow**.
3. Environ 10 minutes plus tard, en bas de la page de la compilation,
   télécharge **Switch-OS** et décompresse-le (deux fois : GitHub met le zip
   dans un zip).

**En compilant sur ton Mac**

```bash
brew install make dfu-util libusb
brew install --cask gcc-arm-embedded
git clone https://github.com/derim00/switch-os.git && cd switch-os
./scripts/build-firmware.sh
```

Le script télécharge Epsilon au commit indiqué dans `EPSILON_COMMIT`
(Epsilon 26.1, la dernière version publiée par NumWorks), applique le patch,
compile, et prépare le dossier `installer/`.

### 2. Installer sur la calculatrice

1. Une seule fois : `brew install dfu-util libusb` (et
   `brew install --cask gcc-arm-embedded` pour ajouter des jeux).
2. Double-clique sur **`Installer Switch-OS.command`** (la première fois :
   clic droit > **Ouvrir**). La page de l'installateur s'ouvre
   (http://127.0.0.1:8766).
3. Branche la calculatrice en USB et appuie sur **Reset** au dos : elle
   redémarre sur le système officiel.
4. Quand le voyant passe au vert, glisse tes jeux `.nwa` dans la page si tu
   veux, puis clique sur **Ⓐ Installer Switch-OS**.

L'installateur vérifie que le **slot B** est libre avant d'écrire : le système
officiel (slot A) n'est jamais modifié. Il prépare les jeux pour leur place
dans le slot B (comme le fait le site de NumWorks), les copie, les relit pour
les vérifier, puis installe Switch-OS et le démarre.

## À savoir

- **Calculatrice** : NumWorks **n0120**, avec le logiciel officiel
  **26.4.0** dans le slot A. Switch-OS est compilé à partir d'Epsilon 26.1 (la
  dernière version publiée) avec le numéro de version 26.4.0.
- **Après un Reset**, la calculatrice revient sur le système officiel :
  Switch-OS reste dans le slot B, il suffit de relancer l'installation.
- **Un seul système dans le slot B** : Switch-OS remplace
  [PSP-OS](https://github.com/derim00/psp-os) s'il était installé, et
  inversement. Les deux installateurs peuvent tourner en même temps (ports
  8765 et 8766).
- **Touches Home et On/Off** : sur un logiciel non officiel, le système de la
  calculatrice gère lui-même ces deux touches. Switch-OS efface au démarrage le
  point de retour laissé par le système officiel pour que Home ramène au menu ;
  si la calculatrice revient quand même sur le slot A, utilise **Retour** (↩)
  pour revenir au menu depuis une appli.
- **Jeux** : seules les applis `.nwa` dont tu as le droit de te servir ;
  elles ne sont jamais publiées dans ce dépôt.

## Comment c'est fait

| Fichier | Rôle |
| --- | --- |
| `patches/switch-os-epsilon.patch` | le menu HOME (`apps/home`), les icônes, les animations (`escher`), la barre rouge |
| `scripts/build-firmware.sh` | télécharge Epsilon, applique le patch, compile, prépare l'installateur |
| `installer/server.py` | serveur local (127.0.0.1 uniquement) de l'installateur |
| `installer/index.html` | la page de l'installateur |
| `installer/link_games.py` | place chaque jeu `.nwa` à son adresse dans le slot B, comme le site de NumWorks |
| `.github/workflows/build.yml` | compilation dans ta copie privée |

## Licence

Le code de Switch-OS est sous licence **CC BY-NC-SA 4.0** (voir `LICENSE`).
Epsilon reste la propriété de NumWorks et n'est pas inclus dans ce dépôt.
Switch-OS est un projet de fan, sans lien avec Nintendo ni avec NumWorks ;
Nintendo Switch est une marque de Nintendo.
