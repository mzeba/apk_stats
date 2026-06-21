# APK Stats — Extraction des statistiques d'installation Play Store

Outil d'extraction et d'agrégation mensuelle des installations d'applications Android
depuis le bucket Google Play Console (Google Cloud Storage). Les téléchargements sont
ventilés **par pays** (liste configurable, codes ISO) et au **total monde**.

## Architecture

Pipeline ETL en couches, chaque responsabilité isolée dans son module :

```
src/apk_stats/
├── config.py        # Chargement & validation de la configuration (env)
├── models.py        # Objets-valeur immutables : Period, CountryInstall, MonthlyResult
├── exceptions.py    # Hiérarchie d'exceptions métier
├── parsing.py       # Décodage UTF-16 + détection de colonnes (FR/EN)
├── aggregator.py    # Logique métier : totaux par pays ciblé + total monde
├── sources/         # Abstraction de la source (pattern Repository/Strategy)
│   ├── base.py      #   StatsSource (interface)
│   └── gcs.py       #   GcsStatsSource (Google Cloud Storage)
├── writers/         # Abstraction de la sortie (pattern Strategy)
│   ├── base.py      #   ReportWriter (interface)
│   └── csv_writer.py
├── pipeline.py      # Orchestrateur (pattern Facade)
└── cli.py           # Point d'entrée + câblage des dépendances (composition root)
```

**Patterns** : Repository/Strategy (source), Strategy (writer), Facade (pipeline),
Injection de dépendances (câblage dans `cli.py`), Objets-valeur immutables.

## Installation

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
```

## Configuration

La configuration passe **exclusivement par l'environnement** (aucun secret dans le code).
Copiez le gabarit et renseignez vos valeurs :

```bash
cp .env.example .env
# puis éditez .env
```

Le fichier `.env` est **chargé automatiquement** au lancement (via python-dotenv) ; les
variables déjà présentes dans l'environnement du shell gardent la priorité. Vous pouvez
pointer un autre fichier avec `--env-file`.

| Variable | Rôle |
|---|---|
| `GOOGLE_APPLICATION_CREDENTIALS` | Chemin vers la clé du compte de service GCP |
| `EDM_BUCKET_NAME` | Bucket Play Console (`pubsite_prod_...`) |
| `EDM_PACKAGES` | Packages séparés par des virgules (ex. `com.incubuo.mbem`) |
| `EDM_COUNTRIES` | Codes pays ISO 3166-1 alpha-2 séparés par des virgules (ex. `BF,CI,ML`) |
| `EDM_START_PERIOD` / `EDM_END_PERIOD` | Bornes de période `AAAA-MM` |
| `EDM_OUTPUT` | Fichier CSV de sortie |

## Configuration côté Google Play Console

Les rapports statistiques de Play Console sont déposés chaque mois dans un bucket Google
Cloud Storage **géré par Google** et propre à votre compte développeur. L'outil lit ce
bucket en lecture seule. Mise en place, une fois :

### 1. Récupérer l'URI du bucket de rapports

1. Ouvrez la [Play Console](https://play.google.com/console) avec un compte **propriétaire**
   du compte développeur.
2. Menu **Téléchargement groupé de rapports** → **Statistiques**
   (*Download reports → Statistics*).
3. Cliquez sur **Copier l'URI Cloud Storage**. Vous obtenez quelque chose comme :
   ```
   gs://pubsite_prod_1234567890123456789
   ```
   Le nom du bucket (sans le préfixe `gs://`) est votre **`EDM_BUCKET_NAME`**.

### 2. Créer un compte de service avec accès en lecture

1. Dans la [console Google Cloud](https://console.cloud.google.com), sélectionnez (ou créez)
   un projet GCP vous appartenant.
2. **IAM et administration → Comptes de service → Créer un compte de service**.
   Donnez-lui un nom (ex. `play-store-extractor`).
3. Une fois créé, ouvrez l'onglet **Clés → Ajouter une clé → Créer une clé → JSON**.
   Téléchargez le fichier `.json` : c'est votre **`GOOGLE_APPLICATION_CREDENTIALS`**.
   Stockez-le **hors du dépôt** (voir [Sécurité](#sécurité)).

### 3. Autoriser ce compte de service sur le bucket

Le bucket `pubsite_prod_*` n'est pas dans votre projet ; vous y donnez accès via l'adresse
e-mail du compte de service. Avec le SDK `gcloud`/`gsutil`, authentifié en tant que
propriétaire du compte développeur :

```bash
gsutil iam ch \
  serviceAccount:play-store-extractor@VOTRE_PROJET.iam.gserviceaccount.com:objectViewer \
  gs://pubsite_prod_1234567890123456789
```

Le rôle **`objectViewer`** (lecture seule) suffit — n'accordez rien de plus
(principe de moindre privilège).

### 4. Identifier les packages et les périodes

- **`EDM_PACKAGES`** : l'`applicationId` de chaque app (Play Console → l'app →
  *Tableau de bord* ; ex. `com.incubuo.mbem`). Plusieurs séparés par des virgules.
- **`EDM_START_PERIOD` / `EDM_END_PERIOD`** : les rapports sont **mensuels** et publiés
  après la clôture du mois. Un mois en cours n'est donc pas encore disponible.

### Structure attendue des rapports

L'outil lit les rapports de granularité « pays », au chemin et au format générés par
Play Console :

```
stats/installs/installs_<package>_<AAAAMM>_country.csv
```

Ce sont des CSV **encodés en UTF-16**, dont les en-têtes varient selon la langue du compte
(anglais ou français) — les deux sont gérés automatiquement.

## Utilisation

```bash
# Avec la configuration issue de .env (chargé automatiquement)
apk-stats

# En surchargeant ponctuellement via la CLI
apk-stats --start 2026-01 --end 2026-05 \
          --packages com.incubuo.mbem,com.incubuo.meg \
          --countries BF,CI,ML \
          --output rapport.csv -v

# Fichier d'environnement personnalisé
apk-stats --env-file prod.env

# Équivalent sans console-script
python -m apk_stats --help
```

Pour chaque package et chaque mois, le CSV de sortie contient une ligne par pays ciblé
(code ISO) puis une ligne **« Tous les pays »** (total monde) :

```csv
Application,Mois,Zone Géographique,Nombre de Téléchargements
com.incubuo.mbem,2026-01,BF,563
com.incubuo.mbem,2026-01,CI,30
com.incubuo.mbem,2026-01,Tous les pays,611
```

## Tests

```bash
pytest
```

Les tests s'exécutent **hors réseau** grâce à une source factice (`FakeStatsSource`).

## Sécurité

- **Aucun secret n'est versionné** : `.gitignore` exclut `*.json` et `.env`. La clé de
  compte de service est référencée par `GOOGLE_APPLICATION_CREDENTIALS`, jamais codée en dur.
- **Moindre privilège** : le compte de service ne doit disposer que du rôle
  `roles/storage.objectViewer` (lecture seule) sur le bucket concerné.
- **Validation des entrées** : les noms de package, codes pays et périodes sont validés
  avant d'être insérés dans le chemin de l'objet GCS (protection contre l'injection de chemin).

> ⚠️ **Rotation de clé requise** : si une clé de compte de service a déjà été déposée en
> clair dans ce répertoire (par ex. `edm-apps-*.json`), considérez-la comme compromise.
> Révoquez-la dans la console GCP (IAM > Comptes de service > Clés) et générez-en une
> nouvelle, stockée hors du dépôt.
