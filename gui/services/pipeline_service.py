"""Pipeline Service - Orchestrates the ML analysis pipeline."""

from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

from modules.analyzer.ml_analysis_facade import MLAnalysisFacade
from modules.analyzer.ml_roles import AnalyzerRole
from modules.cloner.cloner import RepoCloner
from modules.cloner.cloning_check import RepoInspector
from modules.utils.logger import get_logger

from modules.analyzer.analyzer_factory import AnalyzerFactory
from modules.analyzer.builder.consumer_analyzer_builder import ConsumerAnalyzerBuilder
from modules.analyzer.builder.producer_analyzer_builder import ProducerAnalyzerBuilder
from modules.analyzer.builder.metrics_analyzer_builder import MetricsAnalyzerBuilder

logger = get_logger(__name__)


@dataclass
class PipelineConfig:
    """Configuration for the pipeline execution."""

    io_path: Path = field(default_factory=lambda: Path("./io"))
    repository_path: Optional[Path] = None
    project_list_path: Optional[Path] = None
    n_repos: int = 10

    # Step flags
    run_cloner: bool = True
    run_cloner_check: bool = True
    run_producer_analysis: bool = True
    run_consumer_analysis: bool = True
    run_metrics_analysis: bool = True

    # Analysis options
    rules_3: bool = True


@dataclass
class PipelineResult:
    """Result of the pipeline execution."""

    success: bool
    producer_output_dir: Optional[str] = None
    consumer_output_dir: Optional[str] = None
    metrics_output_dir: Optional[str] = None
    error_message: Optional[str] = None


class PipelineService:
    """Service that orchestrates the ML analysis pipeline."""

    def __init__(self, config: PipelineConfig):
        self.config = config

    def run_pipeline(self) -> PipelineResult:
        """Execute the pipeline with the configured steps."""
        result = PipelineResult(success=True)

        try:
            if self.config.run_cloner:
                self._run_cloner()

            if self.config.run_cloner_check:
                self._run_cloner_check()

            if self.config.run_producer_analysis:
                result.producer_output_dir = self._run_producer_analysis()

            if self.config.run_consumer_analysis:
                result.consumer_output_dir = self._run_consumer_analysis()

            if self.config.run_metrics_analysis:
                result.metrics_output_dir = self._run_metrics_analysis()

        except Exception as e:
            logger.exception("Pipeline execution failed")
            result.success = False
            result.error_message = str(e)

        return result

    def _run_cloner(self) -> None:
        """Execute the repository cloning step."""
        logger.info("*** CLONER ***")
        cloner = RepoCloner(
            input_path=self.config.project_list_path,
            output_path=self.config.repository_path,
            n_repos=self.config.n_repos,
        )
        cloner.clone_all()

    def _run_cloner_check(self) -> None:
        """Execute the cloning verification step."""
        logger.info("*** CLONER_CHECK ***")
        inspector = RepoInspector(
            csv_input_path=self.config.project_list_path,
            output_path=self.config.repository_path,
        )
        inspector.run_analysis()

    def _run_producer_analysis(self) -> str:
        """Execute the ML producer analysis step."""
        logger.info("*** PRODUCER ANALYSIS ***")
        facade = MLAnalysisFacade(
            input_path=self.config.repository_path,
            io_path=self.config.io_path,
            role=AnalyzerRole.PRODUCER,
        )
        return facade.run_analysis()

    def _run_consumer_analysis(self) -> str:
        """Execute the ML consumer analysis step."""
        logger.info("*** CONSUMER ANALYSIS ***")
        facade = MLAnalysisFacade(
            input_path=self.config.repository_path,
            io_path=self.config.io_path,
            role=AnalyzerRole.CONSUMER,
        )
        return facade.run_analysis(rules_3=self.config.rules_3)

    def _run_metrics_analysis(self) -> str:
        """Execute the code metrics analysis step."""
        logger.info("*** METRICS ANALYSIS ***")
        facade = MLAnalysisFacade(
            input_path=self.config.repository_path,
            io_path=self.config.io_path,
            role=AnalyzerRole.METRICS,
        )
        return facade.run_analysis()
