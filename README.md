<p align="center">
  <a href="https://libertech-fr.github.io/sesame-taiga_crawler" target="blank"><img src="./static/sesame-logo.svg" width="200" alt="Sesame Logo" /></a>
</p>
<p align="center">Sésame Taiga Crawler - Importation de données</p>
<p align="center">
  <img alt="GitHub all releases" src="https://img.shields.io/github/downloads/libertech-fr/sesame-taiga_crawler/total">
  <img alt="GitHub" src="https://img.shields.io/github/license/libertech-fr/sesame-taiga_crawler">
  <img alt="GitHub contributors" src="https://img.shields.io/github/contributors/libertech-fr/sesame-taiga_crawler">
  <a href="https://github.com/Libertech-Fr/sesame-taiga_crawler/actions/workflows/release.yml?event=workflow_dispatch"><img alt="GitHub contributors" src="https://github.com/Libertech-Fr/sesame-taiga_crawler/actions/workflows/release.yml/badge.svg"></a>
</p>
<br>

Le Sesame - Taiga Crawler est un projet Python qui interagit avec l'API Taiga (ou OASYS) pour extraire des données individus et photos, les transformer via un moteur de mapping configurable, puis les importer dans l'API Sésame.

## Table des matières

- [Aperçu](#aperçu)
- [Installation](#installation)
- [Configuration (`.env`)](#configuration-env)
- [Utilisation](#utilisation)
  - [Arguments CLI de `main.py`](#arguments-cli-de-mainpy)
  - [Cibles Makefile](#cibles-makefile)
- [Le fichier `config.yml`](#le-fichier-configyml)
  - [Structure générale](#structure-générale)
  - [`exclude` — filtrer des enregistrements](#exclude--filtrer-des-enregistrements)
  - [`mapping` — mettre en correspondance les champs](#mapping--mettre-en-correspondance-les-champs)
  - [`additionalFields` — ajouter des valeurs statiques](#additionalfields--ajouter-des-valeurs-statiques)
  - [`transforms` — transformer les valeurs](#transforms--transformer-les-valeurs)
  - [Fonctions de transformation disponibles](#fonctions-de-transformation-disponibles)
- [Tests](#tests)
- [Développement](#développement)
  - [Structure du projet](#structure-du-projet)
  - [Workflow de contribution](#workflow-de-contribution)
- [Release](#release)

## Aperçu

Le flux d'exécution est le suivant :

1. **Extraction** — Le crawler interroge l'API Taiga (JSON‑RPC) ou OASYS (REST) et écrit les réponses brutes dans `./cache/` (`taiga_adm.json`, `taiga_etd.json`, `taiga_esn.json`, `taiga_pri.json`, `oasys_etd.json`, plus les photos base64 dans `./cache/pictures/`).
2. **Transformation** — Le moteur [`lib/data_weaver3`](lib/data_weaver3/) lit [`config.yml`](config.yml) et convertit chaque fichier de cache en données normalisées écrites dans `./data/` (mapping, exclusions, valeurs statiques, transformations).
3. **Import** — Les données transformées sont poussées vers l'API Sésame (`/management/identities/upsert` pour les individus, `/management/identities/upsert/photo` pour les photos).

## Installation

1. Prérequis :
   - Python 3.11+
   - pip
   - Docker (uniquement pour `make test` et `make build`)

2. Clonez le dépôt :

   ```bash
   git clone https://github.com/libertech-fr/sesame-taiga_crawler.git
   cd sesame-taiga_crawler
   ```

3. Installez les dépendances :

   ```bash
   make install-deps
   ```

## Configuration (`.env`)

Créez un fichier `.env` à la racine du projet. Toutes les variables lues par le code sont listées ci‑dessous.

| Variable | Obligatoire | Défaut | Rôle |
|---|---|---|---|
| `SOURCE` | non | `TAIGA` | `TAIGA` = extraction Taiga JSON‑RPC ; toute autre valeur (ex. `OASYS`) bascule sur l'export OASYS REST. |
| `STC_API_BASEURL` | oui | `https://taiga.archi.fr` | URL de base de l'API source (Taiga ou OASYS). Peut être vide si le script tourne directement sur le serveur autorisé. |
| `STC_API_USERNAME` | oui | — | Identifiant Basic Auth côté Taiga. |
| `STC_API_PASSWORD` | oui | — | Mot de passe Basic Auth côté Taiga. |
| `STC_API_PASSENSA` | oui (Taiga) | — | Secret ENSA concaténé à la date `YYYYMMDD` puis hashé SHA‑1 avant envoi. |
| `STC_API_CODEENSA` | non | `lyon` | Code établissement ENSA transmis à l'API Taiga. |
| `STC_API_FORWARD_PORT` | non | `1337` | Port local utilisé par `make taiga-forward`. Inutile sinon. |
| `SESAME_API_BASEURL` | oui | — | URL de l'API Sésame cible pour l'import. |
| `SESAME_API_TOKEN` | oui | — | Token Bearer Sésame. |
| `SESAME_IMPORT_PARALLELS_FILES` | non | `1` | Nombre de fichiers traités en parallèle lors de l'import. |
| `SESAME_IMPORT_PARALLELS_ENTRIES` | non | `1` (individus) / `5` (photos) | Nombre d'entrées traitées en parallèle par fichier. |
| `CONFIG_FILE_TRANSFORM` | non | `./config.yml` | Chemin vers le fichier de mapping. |

Exemple minimal :

```dotenv
SOURCE=TAIGA
STC_API_BASEURL=https://taiga.archi.fr
STC_API_USERNAME=mon_user
STC_API_PASSWORD=mon_password
STC_API_PASSENSA=secret_ensa
STC_API_CODEENSA=lyon

SESAME_API_BASEURL=https://sesame.example.org
SESAME_API_TOKEN=ey...
```

## Utilisation

> **⚠️ Tunnel SSH Taiga** — Si vous exécutez le crawler depuis une machine **non autorisée** par l'API Taiga, démarrez d'abord le forwarding :
>
> ```bash
> make taiga-forward
> ```
>
> Sur la machine autorisée, ignorez cette étape.

Lancer le crawler localement :

```bash
make run-crawler
```

Ou via Docker (image `ghcr.io/libertech-fr/sesame-taiga_crawler`) :

```bash
make pull-crawler-docker
make run-crawler-docker
```

### Arguments CLI de `main.py`

`make run-crawler` appelle `python3 main.py` sans argument (tout par défaut). Pour les cas avancés, lancez directement :

```bash
python3 main.py --run=<scope> --imports=<type> --an=<year> --force=<0|1>
```

| Argument | Valeurs | Défaut | Effet |
|---|---|---|---|
| `--run` | `all`, `taiga`, `sesame` | `all` | `taiga` : extraction uniquement (écrit dans `./cache/`). `sesame` : transformation + import uniquement (lit `./cache/`, envoie à Sésame). `all` : chaîne les deux. |
| `--imports` | `all`, `ind`, `pictures` | `all` | `ind` : individus seulement. `pictures` : photos seulement. `all` : les deux. |
| `--an` | `0` ou année ≥ 2000 | `0` | `0` = année en cours. Une année explicite remplace la valeur `au` envoyée à l'API. Validation : entre 2000 et l'année courante + 1. |
| `--force` | `0`, `1` | `0` | `1` bypasse la vérification du fingerprint et réimporte tous les individus même inchangés. |

> L'extraction OASYS est pilotée par la variable d'env `SOURCE` (≠ `TAIGA`), pas par `--run`. Dans ce mode, seul le dataset `oasys_etd` est produit.

### Cibles Makefile

| Cible | Description |
|---|---|
| `make help` | Affiche l'aide (cible par défaut). |
| `make install-deps` | `pip install -r requirements.txt`. |
| `make run-crawler` | Lance `python3 main.py`. |
| `make run-crawler-docker` | Lance le crawler via Docker, monte le cwd sur `/data`. |
| `make pull-crawler-docker` | Récupère la dernière image publiée sur GHCR. |
| `make build` | Build local de l'image Docker. |
| `make test` | Exécute les tests unitaires + intégration dans Docker. |
| `make taiga-forward` | Ouvre un tunnel SSH pour atteindre l'API Taiga depuis une machine non autorisée. |
| `make update-reqs` | Regénère `requirements.txt` via `pipreqs`. |

## Le fichier `config.yml`

Le fichier [`config.yml`](config.yml) pilote entièrement la **transformation** des données brutes (`cache/*.json`) vers les données importables (`data/*.json`). Il est lu par [`src/cache_to_data.py`](src/cache_to_data.py) et appliqué entrée par entrée par le moteur [`lib/data_weaver3`](lib/data_weaver3/).

### Structure générale

Chaque **clé de premier niveau** est un **nom de fichier** de cache attendu. Un fichier de cache non référencé est ignoré silencieusement. Les clés usuelles sont :

- `oasys_etd.json` — étudiants OASYS
- `taiga_etd.json` — étudiants Taiga
- `taiga_adm.json` — personnels administratifs
- `taiga_esn.json` — personnels enseignants
- `taiga_pri.json` — profils « privés » (selon l'export Taiga)

Chaque valeur est un objet avec quatre sous‑sections optionnelles :

```yaml
taiga_adm.json:
  exclude:           # filtres regex → enregistrement ignoré si match
    - sn: "^#"
  mapping:           # champ source  →  chemin de destination
    inetOrgPerson.sn: "nom"
  additionalFields:  # valeurs statiques injectées dans la sortie
    state: 1
  transforms:        # fonctions appliquées APRÈS mapping, sur la valeur produite
    inetOrgPerson.cn: "join(delimiter=' ')"
```

Les chemins de destination utilisent la **notation pointée** (`inetOrgPerson.cn`, `additionalFields.attributes.supannPerson.supannEtuId`, etc.). Le préfixe spécial `$setOnInsert.` indique un champ à n'écrire qu'à la création (sémantique MongoDB upsert).

### `exclude` — filtrer des enregistrements

Liste de paires `{ champ_source: regex }`. Dès qu'une regex matche la valeur du champ source pour un enregistrement, celui‑ci est **exclu** du traitement.

```yaml
exclude:
  - sn: "^#"          # exclut les enregistrements dont 'sn' commence par #
  - givenName: "^#"
```

### `mapping` — mettre en correspondance les champs

Chaque entrée `destination: source` copie une valeur du cache vers la sortie.

- **Valeur simple (string)** — copie 1:1 :

  ```yaml
  inetOrgPerson.sn: "nom"
  ```

- **Valeur liste** — compose plusieurs champs sources en une liste (à réduire ensuite via un transform `join` ou `concat`) :

  ```yaml
  inetOrgPerson.cn:
    - "nom"
    - "prenom"
  ```

- **Préfixe `$setOnInsert`** — la clé n'est écrite qu'à l'insertion initiale, pas lors d'une mise à jour :

  ```yaml
  $setOnInsert.inetOrgPerson.uid: "CODE"
  ```

### `additionalFields` — ajouter des valeurs statiques

Valeurs constantes mergées dans la sortie, indépendamment du source. Idéal pour des libellés, des listes d'`objectClasses`, un état par défaut, etc.

```yaml
additionalFields:
  state: 1
  inetOrgPerson.employeeType: "TAIGA"
  additionalFields.objectClasses:
    - "supannPerson"
    - "eduPerson"
```

### `transforms` — transformer les valeurs

Chaîne de fonctions appliquées **après** le mapping, sur la valeur produite. Peut être une string (un seul transform) ou une liste (pipeline appliqué dans l'ordre).

```yaml
transforms:
  inetOrgPerson.cn: "join(delimiter=' ')"     # joint ["Dupont", "Jean"] → "Dupont Jean"

  $setOnInsert.inetOrgPerson.mail:
    - "join(delimiter='.')"                    # ["Jean", "Dupont"] → "Jean.Dupont"
    - "remove_accents"                         # "Jéan.Dupônt" → "Jean.Dupont"
    - "lower"                                  # → "jean.dupont"
    - "regex(pattern='\\s+', replace='-')"     # remplace espaces par -
    - "suffix(string='@lyon.archi.fr')"        # → "jean.dupont@lyon.archi.fr"
```

Les arguments utilisent la syntaxe `nom=valeur`. Les strings peuvent être quotées en `'` ou `"`.

### Fonctions de transformation disponibles

Source de vérité : [`lib/data_weaver3/transforms.py`](lib/data_weaver3/transforms.py).

| Fonction | Signature | Exemple |
|---|---|---|
| `join` | `join(delimiter=' ')` | `["a","b"] → "a b"` |
| `concat` | `concat(delimiter='')` | identique à `join` mais exige des strings |
| `split` | `split(delimiter=' ')` | `"a b" → ["a","b"]` |
| `lower` | `lower` | `"Abc" → "abc"` |
| `upper` | `upper` | `"Abc" → "ABC"` |
| `title` | `title` | `"jean dupont" → "Jean Dupont"` |
| `capitalize` | `capitalize` | `"jean dupont" → "Jean dupont"` |
| `remove_accents` | `remove_accents` | `"éà" → "ea"` |
| `prefix` | `prefix(string='x')` | `"foo" → "xfoo"` |
| `suffix` | `suffix(string='x')` | `"foo" → "foox"` |
| `replace` | `replace(old='a', new='b')` | `"aaa" → "bbb"` |
| `regex` | `regex(pattern='\\s+', replace='-')` | `"a b" → "a-b"` |
| `substr` | `substr(start=0, end=3)` | `"abcdef" → "abc"` |
| `parse_type` | `parse_type(typename='int\|float\|str\|bool')` | `"42" → 42` |

Les transformations sont **appliquées récursivement** dans les dicts et listes : transformer une liste applique le transform à chaque élément (sauf pour `join`/`concat`/`split` qui opèrent sur la structure).

## Tests

La suite de tests s'exécute entièrement dans Docker pour garantir la reproductibilité :

```bash
make test
```

Détail du pipeline (voir [`Makefile`](Makefile)) :

1. Build de l'image `sesame-taiga-crawler-test:local` (basée sur `Dockerfile`).
2. Génération d'un cache mocké **déterministe** (`--seed 42`, 8 entrées) par [`src/mock_cache_data.py`](src/mock_cache_data.py) → `./tests_artifacts/cache_mocks/`.
3. Exécution des tests unitaires :

   ```bash
   python -m unittest discover -s tests -p "test_*.py"
   ```

   avec les variables :
   - `TEST_MOCK_CACHE_DIR=./tests_artifacts/cache_mocks`
   - `TEST_DATA_OUTPUT_DIR=./tests_artifacts/data`
   - `TEST_CONFIG_PATH=./config.yml`

4. Exécution des tests d'intégration sur fixtures réelles (non mockées) présents dans [`tests_integration/`](tests_integration/) :

   ```bash
   python -m unittest tests.test_integration_fixtures
   ```

### Lancer les tests sans Docker

Si vos dépendances sont installées localement (`make install-deps`), vous pouvez lancer la suite en direct :

```bash
TEST_MOCK_CACHE_DIR=./tests_artifacts/cache_mocks \
TEST_DATA_OUTPUT_DIR=./tests_artifacts/data \
TEST_CONFIG_PATH=./config.yml \
python -m unittest discover -s tests -p "test_*.py"
```

Les tests d'intégration tournent également sur `main` à chaque push via [`.github/workflows/tests-main.yml`](.github/workflows/tests-main.yml).

## Développement

**Tout le cycle de développement passe par `make`.** N'invoquez pas `python3 main.py` directement : passez par les cibles Makefile — elles chargent le `.env`, fixent les bons ports et restent cohérentes entre dev local, Docker et CI.

### Boucle de développement typique

Depuis une machine **non autorisée** par l'API Taiga (cas le plus fréquent en dev) :

```bash
# Terminal 1 — ouvre le tunnel SSH vers Taiga (à laisser tourner)
make taiga-forward

# Terminal 2 — lance le crawler
make run-crawler
```

Depuis la machine autorisée, seul `make run-crawler` est nécessaire.

Pour des runs ciblés pendant le debug (ex. ne rejouer que l'import sans refaire l'extraction) :

```bash
python3 main.py --run=sesame --imports=ind
```

Voir [Arguments CLI de `main.py`](#arguments-cli-de-mainpy) pour la liste complète.

### PyCharm

Vous pouvez utiliser PyCharm avec l'extension **Makefile** ; le debugger est automatiquement configuré pour les cibles `run-crawler` et `test`.

### Mettre à jour les dépendances

Après ajout d'un `import` dans le code :

```bash
make update-reqs
```

### Structure du projet

```
.
├── main.py                 # point d'entrée CLI
├── config.yml              # mapping Taiga/OASYS → Sésame (voir section dédiée)
├── Makefile                # toutes les cibles de dev / test / run
├── Dockerfile              # image runtime + test
├── requirements.txt
├── src/
│   ├── a_moins_b.py                  # check de cohérence API Taiga (AmoinsB)
│   ├── export_ind.py                 # extrait les individus Taiga → cache/taiga_*.json
│   ├── export_oasis.py               # extrait les étudiants OASYS → cache/oasys_etd.json
│   ├── export_pictures.py            # extrait les photos Taiga (base64 → jpg)
│   ├── cache_to_data.py              # lit config.yml et transforme cache/ → data/
│   ├── data_utils.py                 # utilitaires de filtrage + fingerprint
│   ├── import_ind.py                 # POST data/*.json vers l'API Sésame
│   ├── import_pictures.py            # POST data/pictures/* vers l'API Sésame
│   ├── mock_cache_data.py            # générateur de cache synthétique pour les tests
│   └── anonymize_integration_data.py # anonymisation des fixtures d'intégration
├── lib/data_weaver3/
│   ├── main.py       # weave_entry : orchestration mapping + transforms
│   ├── transforms.py # les 14 fonctions de transformation (source de vérité)
│   └── utils.py      # crush/construct (dot-notation ↔ nested dict)
├── tests/            # tests unitaires (unittest)
└── tests_integration/ # fixtures réelles anonymisées pour tests d'intégration
```

### Workflow de contribution

1. Branche depuis `main` : `git checkout -b feat/ma-feature`.
2. Développez. Les modifications de mapping se font dans `config.yml` et sont idéalement couvertes par un test dans `tests/`.
3. Lancez `make test` en local — le CI exécutera exactement la même commande.
4. Mettez à jour `requirements.txt` (`make update-reqs`) si vous avez ajouté une dépendance.
5. Ouvrez une Pull Request vers `main`. Le workflow [`tests-main.yml`](.github/workflows/tests-main.yml) rejoue les tests à chaque push sur `main`.

## Release

La release se déclenche **manuellement** depuis GitHub Actions (le workflow est en `workflow_dispatch`). Deux façons :

- **Via le badge du README** — cliquez sur le badge **Release** en haut de cette page : il pointe vers la page du workflow, sur laquelle le bouton **Run workflow** (en haut à droite) ouvre le formulaire de release.
- **Depuis l'interface GitHub** — onglet **Actions** → workflow **Release** → bouton **Run workflow**.

Le formulaire demande trois paramètres (voir [`.github/workflows/release.yml`](.github/workflows/release.yml)) :

| Input | Valeurs | Défaut | Rôle |
|---|---|---|---|
| `version_increment` | `major`, `minor`, `patch` | `patch` | Incrément appliqué au tag de version (SemVer). |
| `build_docker_image` | `true` / `false` | `true` | Construit et pousse l'image sur `ghcr.io/libertech-fr/sesame-taiga_crawler`. |
| `latest` | `true` / `false` | `false` | Applique aussi le tag `latest` à l'image Docker publiée. |

Le workflow exécute automatiquement, dans l'ordre :

1. **Job `tests`** — `make test` (la release est annulée si les tests échouent).
2. **Job `build`** — délègue à l'action [`Libertech-FR/lt-actions/release@main`](https://github.com/Libertech-FR/lt-actions) : bump de version, tag Git, build + push Docker, création de la GitHub Release.
