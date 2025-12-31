"""Main script to orchestrate the ML analysis pipeline."""

import argparse
import sys
from pathlib import Path
from modules.analyzer.ml_analysis_facade import MLAnalysisFacade
from modules.analyzer.ml_roles import AnalyzerRole
from modules.cloner.cloner import RepoCloner
from modules.cloner.cloning_check import RepoInspector
from modules.oracle.matching.results_analysis import ResultAnalysis
from modules.oracle.merge import Merger
from modules.utils.logger import get_logger
from modules.analyzer.analyzer_factory import AnalyzerFactory  # required import
from modules.analyzer.builder.consumer_analyzer_builder import (
    ConsumerAnalyzerBuilder,
)  # required import
from modules.analyzer.builder.producer_analyzer_builder import (
    ProducerAnalyzerBuilder,
)  # required import

logger = get_logger(__name__)


def parse_arguments():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        description="MARK 2.0 - ML Analysis and Recognition Kit",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )

    # Path arguments
    parser.add_argument(
        "--io-path",
        type=Path,
        default=Path("./io"),
        help="Path to IO directory containing library dictionaries and output",
    )

    parser.add_argument(
        "--repository-path",
        type=Path,
        default=None,
        help="Path to directory containing repositories to analyze",
    )

    parser.add_argument(
        "--project-list",
        type=Path,
        default=None,
        help="Path to CSV file with list of projects to clone",
    )

    parser.add_argument(
        "--n-repos", type=int, default=20, help="Number of repositories to clone"
    )

    # Step control flags
    parser.add_argument(
        "--clone",
        action="store_true",
        default=False,
        help="Enable repository cloning step",
    )

    parser.add_argument(
        "--clone-check",
        action="store_true",
        default=False,
        help="Enable cloning verification step",
    )

    parser.add_argument(
        "--analysis", action="store_true", default=False, help="Enable ML analysis step"
    )

    parser.add_argument(
        "--merge", action="store_true", default=False, help="Enable results merge step"
    )

    parser.add_argument(
        "--result-analysis",
        action="store_true",
        default=False,
        help="Enable final result analysis step",
    )

    # Shortcut for running all steps
    parser.add_argument(
        "--all",
        action="store_true",
        default=False,
        help="Enable all steps (clone, clone-check, analysis, merge, result-analysis)",
    )

    # Analysis options
    parser.add_argument(
        "--no-rules-3",
        action="store_true",
        default=False,
        help="Disable rules 3 for consumer analysis (rules 3 are enabled by default)",
    )

    args = parser.parse_args()

    # If --all is specified, enable all steps
    if args.all:
        args.clone = True
        args.clone_check = True
        args.analysis = True
        args.merge = True
        args.result_analysis = True

    # Set default paths if not provided
    if args.repository_path is None:
        args.repository_path = args.io_path / "repos"

    if args.project_list is None:
        args.project_list = args.io_path / "applied_projects.csv"

    # Set rules_3 based on no_rules_3 flag (inverted logic)
    args.rules_3 = not args.no_rules_3

    return args


def validate_paths(args):
    """Validate required paths exist."""
    # IO path must exist and contain library_dictionary
    if not args.io_path.exists():
        logger.error(f"IO path does not exist: {args.io_path}")
        sys.exit(1)

    lib_dict_path = args.io_path / "library_dictionary"
    if not lib_dict_path.exists():
        logger.error(f"Library dictionary not found: {lib_dict_path}")
        sys.exit(1)

    # For cloning, project list must exist
    if args.clone and not args.project_list.exists():
        logger.error(f"Project list file not found: {args.project_list}")
        sys.exit(1)

    # For analysis, repository path must exist
    if args.analysis and not args.repository_path.exists():
        logger.error(f"Repository path does not exist: {args.repository_path}")
        raise FileNotFoundError(f"Input folder not found: {args.repository_path}")


def run_pipeline(args):
    """Run the ML analysis pipeline based on provided arguments."""

    # Validate paths
    validate_paths(args)

    # Derived paths
    output_path = args.io_path / "output"
    oracle_path = Path("./modules/oracle")

    # Variables to store result directories
    dir_producer = None
    dir_consumer = None

    # === CLONAZIONE DEI REPOSITORY ===
    if args.clone:
        logger.info("*** CLONER ***")
        cloner = RepoCloner(
            input_path=args.project_list,
            output_path=args.repository_path,
            n_repos=args.n_repos,
        )
        cloner.clone_all()

    # === VERIFICA CLONAZIONE ===
    if args.clone_check:
        logger.info("*** CLONER_CHECK ***")
        inspector = RepoInspector(
            csv_input_path=args.project_list, output_path=args.repository_path
        )
        inspector.run_analysis()

    # === ANALISI ML ===
    if args.analysis:
        logger.info("*** INIZIO L'ANALISI ***")

        # Producer analysis
        logger.info("Analyzing producers...")
        producer_facade = MLAnalysisFacade(
            input_path=args.repository_path,
            io_path=args.io_path,
            role=AnalyzerRole.PRODUCER,
        )
        dir_producer = producer_facade.run_analysis()
        logger.info(f"Producer analysis completed. Results in: {dir_producer}")

        # Consumer analysis
        logger.info("Analyzing consumers...")
        consumer_facade = MLAnalysisFacade(
            input_path=args.repository_path,
            io_path=args.io_path,
            role=AnalyzerRole.CONSUMER,
        )
        dir_consumer = consumer_facade.run_analysis(rules_3=args.rules_3)
        logger.info(f"Consumer analysis completed. Results in: {dir_consumer}")

    # === MERGE DEI RISULTATI ===
    if args.merge:
        if dir_producer is None or dir_consumer is None:
            logger.error(
                "Cannot run merge without analysis results. Run with --analysis first."
            )
            sys.exit(1)

        logger.info("*** INIZIO IL MERGE ***")

        producer_merger = Merger(column_name="producer", oracle_path=oracle_path)
        producer_merger.reporting(
            base_output_path=output_path,
            dir_result=dir_producer,
            file_name="results.csv",
        )

        consumer_merger = Merger(column_name="consumer", oracle_path=oracle_path)
        consumer_merger.reporting(
            base_output_path=output_path,
            dir_result=dir_consumer,
            file_name="results.csv",
        )

    # === ANALISI FINALE DEI RISULTATI ===
    if args.result_analysis:
        if dir_producer is None or dir_consumer is None:
            logger.error(
                "Cannot run result analysis without analysis results. Run with --analysis first."
            )
            sys.exit(1)

        logger.info("*** INIZIO LA RESULT ANALYSIS ***")

        producer_analysis = ResultAnalysis(
            role=AnalyzerRole.PRODUCER,
            oracle_path=oracle_path,
            base_folder_path=output_path,
            results_subdir=dir_producer,
        )
        consumer_analysis = ResultAnalysis(
            role=AnalyzerRole.CONSUMER,
            oracle_path=oracle_path,
            base_folder_path=output_path,
            results_subdir=dir_consumer,
        )

        producer_analysis.start_analysis()
        consumer_analysis.start_analysis()

    logger.info("*** PIPELINE COMPLETED ***")
    return 0


def main():
    """Main entry point."""
    try:
        args = parse_arguments()

        # Show configuration
        logger.info("=" * 80)
        logger.info("MARK 2.0 - ML Automated Rule-based Classification Kit")
        logger.info("=" * 80)
        logger.info(f"IO Path: {args.io_path}")
        logger.info(f"Repository Path: {args.repository_path}")
        logger.info(f"Steps enabled:")
        logger.info(f"  - Clone: {args.clone}")
        logger.info(f"  - Clone Check: {args.clone_check}")
        logger.info(f"  - Analysis: {args.analysis}")
        logger.info(f"  - Merge: {args.merge}")
        logger.info(f"  - Result Analysis: {args.result_analysis}")
        logger.info("=" * 80)

        return run_pipeline(args)

    except KeyboardInterrupt:
        logger.info("\nExecution interrupted by user")
        return 130
    except Exception as e:
        logger.error(f"Fatal error: {e}", exc_info=True)
        return 1


if __name__ == "__main__":
    sys.exit(main())
