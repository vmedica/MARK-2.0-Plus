"""Defines the available roles for ML analyzers."""

from enum import Enum


class AnalyzerRole(Enum):
    """Enumeration of ML analyzer roles."""
    PRODUCER = "producer"
    CONSUMER = "consumer"
    METRICS = "metrics"