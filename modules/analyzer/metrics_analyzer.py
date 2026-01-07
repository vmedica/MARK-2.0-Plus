# modules/analyzer/ml_metrics_analyzer.py

from modules.analyzer.ml_analyzer import MLAnalyzer
from modules.analyzer.ml_roles import AnalyzerRole

class MLMetricsAnalyzer(MLAnalyzer):
    """Analyzer dedicated to calculating code metrics."""

    def __init__(
        self,
        role: AnalyzerRole,
        library_dicts=None,
        filters=None,
        keyword_strategy=None
    ):
        # calls the base constructor
        super().__init__(
            role=role,
            library_dicts=library_dicts,
            filters=filters,
            keyword_strategy=keyword_strategy
        )

    def check_library(self, file, **kwargs):
        # METRICS does not need to check ML libraries
        return [], [], []
