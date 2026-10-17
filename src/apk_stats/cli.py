"""Point d'entrée en ligne de commande et composition root.

C'est ici — et seulement ici — que les implémentations concrètes (client Google
Cloud, writer CSV) sont instanciées et câblées ensemble. Le reste du code ne
manipule que des abstractions.
"""

from __future__ import annotations

import argparse
import logging
import sys

from dotenv import load_dotenv

from apk_stats.aggregator import Aggregator
from apk_stats.config import AppConfig
from apk_stats.exceptions import EdmStatsError
from apk_stats.pipeline import StatsPipeline
from apk_stats.sources.gcs import GcsStatsSource
from apk_stats.writers.csv_writer import CsvReportWriter

logger = logging.getLogger("apk_stats")

DEFAULT_ENV_FILE = ".env"


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="apk-stats",
        description=(
            "Extrait et agrège les installations Play Store par pays "
            "(liste configurable) et au total monde."
        ),
    )
    parser.add_argument(
        "--env-file",
        default=DEFAULT_ENV_FILE,
        help="Fichier d'environnement à charger (défaut : .env).",
    )
    parser.add_argument("--credentials", help="Chemin vers la clé de compte de service GCP.")
    parser.add_argument("--bucket", help="Nom du bucket Play Console.")
    parser.add_argument("--packages", help="Packages séparés par des virgules.")
    parser.add_argument(
        "--countries",
        help="Codes pays ISO (deux lettres) séparés par des virgules, ex. 'BF,CI'.",
    )
    parser.add_argument(
        "--start", help="Date de début (AAAA, AAAA-MM ou AAAA-MM-DD, incluse)."
    )
    parser.add_argument(
        "--end", help="Date de fin (AAAA, AAAA-MM ou AAAA-MM-DD, incluse)."
    )
    parser.add_argument(
        "--frequency",
        help="Granularité des résultats : yearly, monthly (défaut) ou daily.",
    )
    parser.add_argument("--output", help="Chemin du fichier CSV de sortie.")
    parser.add_argument(
        "-v",
        "--verbose",
        action="store_true",
        help="Active la journalisation détaillée (DEBUG).",
    )
    return parser


def _build_config(args: argparse.Namespace) -> AppConfig:
    return AppConfig.from_env(
        credentials_path=args.credentials,
        bucket_name=args.bucket,
        packages=args.packages,
        countries=args.countries,
        start=args.start,
        end=args.end,
        output_path=args.output,
        frequency=args.frequency,
    )


def _build_pipeline(config: AppConfig) -> StatsPipeline:
    # Import différé : la dépendance GCP n'est requise que pour un run réel,
    # ce qui garde les tests (et `--help`) exécutables sans le SDK installé.
    from google.cloud import storage

    client = storage.Client.from_service_account_json(config.credentials_path)
    source = GcsStatsSource(client, config.bucket_name)
    writer = CsvReportWriter(config.output_path, config.frequency)
    aggregator = Aggregator(config.countries)
    return StatsPipeline(source, writer, aggregator)


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(levelname)s %(message)s",
    )

    # Charge le .env dans l'environnement avant de lire la configuration.
    # os.environ conserve la priorité (comportement par défaut de python-dotenv).
    load_dotenv(args.env_file)

    try:
        config = _build_config(args)
        pipeline = _build_pipeline(config)
        results = pipeline.run(config.packages, config.date_range, config.frequency)
    except EdmStatsError as exc:
        logger.error("%s", exc)
        return 1
    except ImportError:
        logger.error(
            "La bibliothèque 'google-cloud-storage' est manquante. "
            "Installez-la avec : pip install google-cloud-storage"
        )
        return 1

    return 0 if results else 2


if __name__ == "__main__":
    sys.exit(main())
