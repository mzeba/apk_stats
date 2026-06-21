"""Hiérarchie d'exceptions du domaine.

Permet d'attraper les erreurs métier de façon ciblée plutôt que par un
`except Exception` global, et de distinguer la couche d'origine du problème.
"""


class EdmStatsError(Exception):
    """Classe de base de toutes les erreurs applicatives."""


class ConfigError(EdmStatsError):
    """Configuration absente ou invalide."""


class SourceError(EdmStatsError):
    """Échec d'accès à la source de données (réseau, droits, bucket...)."""


class ParsingError(EdmStatsError):
    """Contenu de rapport illisible ou mal formé."""
