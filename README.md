# Sesame - Taiga Crawler

Le Sesame - Taiga Crawler est un projet Python qui interagit avec l'API Taiga pour effectuer des tâches spécifiques.

## Table des matières

- [Sesame - Taiga Crawler](#sesame---taiga-crawler)
  - [Table des matières](#table-des-matières)
  - [Aperçu](#aperçu)
  - [Installation](#installation)
  - [Configuration](#configuration)
  - [Utilisation](#utilisation)
  - [Développement](#développement)

## Aperçu

Le Sesame - Taiga Crawler est conçu pour effectuer des tâches liées à l'API Taiga. Il comprend des fonctionnalités telles que la vérification AmoinsB et l'exportation de données individuelles. Le projet est structuré avec des composants modulaires et utilise la programmation asynchrone pour l'efficacité.

## Installation

1. Requis :
   - Python 3
   - PIP

2. Clonez le dépôt :

    ```bash
    git clone https://github.com/libertech-fr/sesame-taiga_crawler.git
    cd taiga-crawler
    ```

3. Installez les dépendances :

    ```bash
    make install-deps
    ```

## Configuration

1. Créez un fichier `.env` à la racine du projet et ajoutez la configuration suivante :

    ```dotenv
    STC_API_BASEURL=https://[URL_DU_SERVEUR_AUTHORISE]:1337
    STC_API_USERNAME=[IDENTIFIANT_DE_L_API]
    STC_API_PASSWORD=[PASSWORD_DE_L_API]
    STC_API_FORWARD_PORT=1337
    STC_API_PASSENSA=[PASSWORD_ENSA]

    SESAME_API_BASEURL=http://[URL_DU_SERVEUR_AUTHORISE]:4002
    ```

    Assurez-vous de remplacer les valeurs fictives par vos informations réelles.

    - **STC_API_BASEURL** : Peut être vide si vous lancez le logiciel depuis le serveur autorisé
    - **STC_API_FORWARD_PORT** : Non requis si `make taiga-forward` n'est pas utilisé
## Utilisation

1. Mise en route
   
   !!! ATTENTION !!!
   Vous êtes sur la machine authorisée par L'API Taiga : Alors ignorez cette étape !!!
   
   ```bash
   make taiga-forward
   ```
   
2. Exécution du script

   Exécutez le script principal :
   
   ```bash
   make run-crawler
   ```

## Développement

Vous pouvez utiliser Pycharm avec la Makefile extension, le débuggeur est automatiquement configuré !

- Mise à jour des requirements :
   ```bash
   make update-reqs
   ```
