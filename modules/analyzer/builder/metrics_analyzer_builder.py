from modules.analyzer.analyzer_factory import AnalyzerFactory
from modules.analyzer.builder.analyzer_builder import AnalyzerBuilder
from modules.analyzer.ml_roles import AnalyzerRole
from modules.analyzer.metrics_analyzer import MLMetricsAnalyzer
from modules.scanner.file_filter.extension_filter import ExtensionFilter

@AnalyzerFactory.register(AnalyzerRole.METRICS)
class MetricsAnalyzerBuilder(AnalyzerBuilder):
    """Builder per l’analyzer delle metriche codice."""

    def __init__(self):
        super().__init__()
        self.with_role(AnalyzerRole.METRICS)
        self.with_analyzer_class(MLMetricsAnalyzer)
        self.with_library_dicts([])  # Nessuna libreria ML
        self.with_filters([ExtensionFilter([".py"])])
        self.with_keyword_strategy(DummyKeywordStrategy())


class DummyKeywordStrategy:
    def extract_keywords(self, file, library_dict=None):
        return []
