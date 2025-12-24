"""Abstract base class for ML analyzers handling project scans and keyword detection.

This module defines the `MLAnalyzer` abstract base class, which encapsulates the
common workflow for scanning projects, applying file filters, extracting ML-related
libraries/keywords, and exporting results to CSV. Concrete analyzers (e.g., producer
vs consumer) specialize only the `check_library` method to express role-specific rules.
"""
"""
Abstract base class for ML analyzers handling project scans and keyword detection.
"""
import os
from abc import ABC, abstractmethod
from typing import Optional, List, Tuple

import pandas as pd
from radon.complexity import cc_visit
from radon.metrics import mi_visit

from modules.keyword_extractor.keyword_extractor_base import KeywordExtractionStrategy
from modules.keyword_extractor.keyword_extractor_default import DefaultKeywordMatcher
from modules.analyzer.ml_roles import AnalyzerRole
from modules.scanner.file_filter.file_filter_base import FileFilter
from modules.scanner.project_scanner import ProjectScanner
from modules.utils.logger import get_logger

logger = get_logger(__name__)


class MLAnalyzer(ABC):
    """Base class for all machine learning analyzers."""

    def __init__(
        self,
        role: AnalyzerRole,
        library_dicts: Optional[List[FileFilter]] = None,
        filters: Optional[List[FileFilter]] = None,
        keyword_strategy: KeywordExtractionStrategy = None,
    ):
        self.role = role
        self.role_str = str(self.role.value)
        self.filters = filters or []
        self.library_dicts = library_dicts or []
        self.keyword_strategy = keyword_strategy or DefaultKeywordMatcher()

        # === METRICHE SOLO PER PRODUCER ===
        self.project_metrics = []

    # ============================================================
    # SALVATAGGIO METRICHE CSV (SOLO PRODUCER)
    # ============================================================

    def _save_metrics_csv(self, output_base_path: str):
        if self.role != AnalyzerRole.METRICS:
            return

        if not self.project_metrics:
            logger.info("No metrics to save")
            return

        metrics_dir = os.path.join(output_base_path, "metrics")
        os.makedirs(metrics_dir, exist_ok=True)

        existing = [
            f for f in os.listdir(metrics_dir)
            if f.endswith("_metrics.csv") and f.split("_")[0].isdigit()
        ]

        next_index = (
            max(int(f.split("_")[0]) for f in existing) + 1
            if existing else 1
        )

        csv_path = os.path.join(metrics_dir, f"{next_index}_metrics.csv")

        pd.DataFrame(self.project_metrics).to_csv(csv_path, index=False)

        logger.info("Metrics saved to %s", csv_path)

    # ============================================================
    # ANALISI FILE
    # ============================================================

    def analyze_single_file(self, file, repo, **kwargs):
        """
        Restituisce:
        - librerie ML trovate
        - keywords
        - eventuali load keywords
        - CC (lista complessità dei blocchi)
        - MI (singolo valore)
        - SLOC
        """
        if not os.path.isfile(file):
            return [], [], [], [], 0, 0

        libraries, keywords, list_load_keywords = self.check_library(file, **kwargs)

        try:
            with open(file, "r", encoding="utf-8") as f:
                code = f.read()
        except Exception as e:
            logger.info(f"Cannot read file {file}: {e}")
            return libraries, keywords, list_load_keywords, [], 0, 0

        # --- CC ---
        try:
            cc_blocks = cc_visit(code)
        except Exception as e:
            logger.info(f"Error calculating CC for {file}: {e}")
            cc_blocks = []

        # --- MI ---
        try:
            mi_val = mi_visit(code, multi=False)
        except Exception:
            mi_val = 0

        # --- SLOC ---
        sloc_val = sum(
            1 for line in code.splitlines()
            if line.strip() and not line.strip().startswith("#")
        )

        if keywords:
            logger.info(
                "Found %s with ML libraries %s and training instruction %s in %s",
                file, libraries, keywords, repo
            )

        return libraries, keywords, list_load_keywords, cc_blocks, mi_val, sloc_val


    # ============================================================
    # ANALISI DIRECTORY
    # ============================================================

    def analyze_project(
        self, repo, project, directory, output_folder, **kwargs
    ) -> Tuple[pd.DataFrame, list, list, list]:

        rows = []
        all_cc_values, mi_weighted, sloc_list = [], [], []

        for root, _, files in os.walk(repo):
            for filename in files:

                if not ProjectScanner.is_valid_file(filename, self.filters):
                    continue

                file_path = os.path.join(root, filename)

                # === ANALISI ML E METRICHE ===
                _, keywords, _, cc_blocks, mi_val, sloc_val = self.analyze_single_file(file_path, repo, **kwargs)

                # --- aggiorna metriche solo se PRODUCER e file Python ---
                if self.role in [AnalyzerRole.METRICS]:
                    all_cc_values.extend(b.complexity for b in cc_blocks)

                    if sloc_val > 0:
                        mi_weighted.append((mi_val, sloc_val))
                        sloc_list.append(sloc_val)

                # --- aggiorna righe ML ---
                if keywords:
                    for keyword in keywords:
                        rows.append({
                            "ProjectName": f"{project}/{directory}",
                            f"Is ML {self.role_str}": "Yes",
                            "libraries": keyword["library"],
                            "where": file_path,
                            "keyword": keyword["keyword"],
                            "line_number": keyword["line_number"],
                        })

        df = pd.DataFrame(rows)

        if not df.empty:
            output_file = os.path.join(
                output_folder,
                f"{project}_{directory}_ml_{self.role_str}.csv"
            )
            df.to_csv(output_file, index=False)

        return df, all_cc_values, mi_weighted, sloc_list

    # ============================================================
    # ANALISI SET DI PROGETTI
    # ============================================================

    def analyze_projects_set(self, input_folder, output_folder, **kwargs):
        all_rows = []

        for project in os.listdir(input_folder):
            project_path = os.path.join(input_folder, project)
            if not os.path.isdir(project_path):
                continue

            project_cc, project_mi, project_sloc = [], [], []

            for dir_path in os.listdir(project_path):
                full_dir_path = os.path.join(project_path, dir_path)
                if not os.path.isdir(full_dir_path):
                    continue

                logger.info("Project: %s", project)

                df, cc_vals, mi_vals, sloc_vals = self.analyze_project(
                    full_dir_path,
                    project,
                    dir_path,
                    output_folder,
                    **kwargs
                )

                if self.role == AnalyzerRole.METRICS:
                    project_cc.extend(cc_vals)
                    project_mi.extend(mi_vals)
                    project_sloc.extend(sloc_vals)

                if not df.empty:
                    all_rows.extend(df.to_dict(orient="records"))

            # === METRICHE FINALI SOLO METRICS ===
            if self.role == AnalyzerRole.METRICS:
                cc_avg = sum(project_cc) / len(project_cc) if project_cc else 0
                total_sloc = sum(project_sloc)
                mi_avg = (
                    sum(mi * sloc for mi, sloc in project_mi) / total_sloc
                    if total_sloc > 0 else 0
                )

                self.project_metrics.append({
                    "ProjectName": project,
                    "CC_avg": round(cc_avg, 2),
                    "MI_avg": round(mi_avg, 2),
                })

        final_df = pd.DataFrame(all_rows)
        if not final_df.empty:
            final_df.to_csv(os.path.join(output_folder, "results.csv"), index=False)

        self._save_metrics_csv(output_folder)

        return final_df

    # ============================================================
    # METODO ASTRATTO
    # ============================================================

    @abstractmethod
    def check_library(self, file, **kwargs):
        raise NotImplementedError
