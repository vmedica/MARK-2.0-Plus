"""
CodeMetrics Script

This script calculates code quality metrics for Python projects:
1. CC (Cyclomatic Complexity) - measures the complexity of each function/class
   - CC is calculated for each block (function/method/class)
   - Project-level CC is the average of all block CCs (simple mean, like Radon -a)
2. MI (Maintainability Index) - measures maintainability
   - MI is calculated for each file
   - Project-level MI is a weighted average using the file's SLOC

Formulas:
cc_avg = (CC_blocco_1 + CC_blocco_2 + ... + CC_blocco_n) / n
mi_avg = (MI_file_1 * SLOC_file_1 + MI_file_2 * SLOC_file_2 + ... + MI_file_m * SLOC_file_m) / (SLOC_file_1 + ... + SLOC_file_m)


The output shows:
- CC and MI for each Project
"""

import os
import csv
from radon.complexity import cc_visit
from radon.metrics import mi_visit
from modules.utils.logger import get_logger

# Logger
logger = get_logger(__name__)



class CodeMetrics:
    """Class to calculate CC and MI metrics for a set of projects."""

    def __init__(self, projects_path: str):
        self.projects_path = projects_path
        self.metrics_list = []

    def _calculate_file_metrics(self, file_path: str):
        """Calculate CC, MI, and SLOC for a single Python file."""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                code = f.read()
        except Exception as e:
            logger.info(f"Cannot read file {file_path}: {e}")
            return [], 0, 0  # return empty blocks list

        # --- Calculate CC per block ---
        cc_blocks = []
        try:
            cc_blocks = cc_visit(code)
            logger.info(f"CC details for file: {file_path}")
            for i, b in enumerate(cc_blocks, 1):
                block_sloc = b.endline - b.lineno + 1   # b.lineno -> the line number where the block starts (e.g., a function)
                                                        # b.endline -> the line number where the block ends
                                                        # +1 to also count the starting line
                logger.info(f"  Block {i}: {b.name} | Type: {b.__class__.__name__} | "
                            f"CC: {b.complexity} | SLOC block: {block_sloc}")
        except Exception as e:
            logger.info(f"Error calculating CC for {file_path}: {e}")

        # --- Calculate MI ---
        try:
            mi_score = mi_visit(code, multi=False)
        except Exception as e:
            logger.info(f"Error calculating MI for {file_path}: {e}")
            mi_score = 0

        # --- Calculate SLOC ---
        sloc = sum(1 for line in code.splitlines() if line.strip() and not line.strip().startswith("#"))

        # Total CC for this file
        cc_total_file = sum(b.complexity for b in cc_blocks)
        num_blocks = len(cc_blocks)

        logger.info(f"Total CC file: {cc_total_file}, Number of blocks: {num_blocks}, "
                    f"MI: {mi_score:.2f}, SLOC: {sloc}")

        return cc_blocks, mi_score, sloc

    def _calculate_project_metrics(self, project_path: str):    #_ for private method
        """Calculate project-level metrics: CC (average of blocks) and MI (weighted by SLOC)."""
        all_cc_values = []  # list of all block CCs in the project
        mi_list = []
        sloc_list = []

        logger.info(f"Start analysis for project: {project_path}")

        for root, _, files in os.walk(project_path):
            for f in files:
                if f.endswith(".py"):
                    cc_blocks, mi_val, sloc_val = self._calculate_file_metrics(os.path.join(root, f))
                    if cc_blocks:
                        all_cc_values.extend([b.complexity for b in cc_blocks])
                    if sloc_val > 0:
                        mi_list.append((mi_val, sloc_val))
                        sloc_list.append(sloc_val)

        # --- Calculate weighted MI using SLOC ---
        total_sloc = sum(sloc_list) if sloc_list else 1
        if mi_list:
            mi_avg = sum(mi * sloc for mi, sloc in mi_list) / total_sloc
        else:
            mi_avg = 0

        logger.info(f"[MI] Weighted MI calculation: sum(MI * SLOC) / total SLOC = {mi_avg:.2f}")
        # --- Calculate simple average CC like Radon -a ---
        if all_cc_values:
            cc_avg = sum(all_cc_values) / len(all_cc_values)
        else:
            cc_avg = 0

        logger.info(f"--- Calculating simple average CC (like Radon -a) ---")
        logger.info(f"[CC] Sum of all CC blocks: {sum(all_cc_values)}")
        logger.info(f"[CC] Number of blocks: {len(all_cc_values)}")
        logger.info(f"[CC] Average CC (blocks): {cc_avg:.2f}")

        logger.info(f"[MI and CC]Project {project_path} metrics calculated: MI={mi_avg:.2f}, CC={cc_avg:.2f}")

        return round(mi_avg, 2), round(cc_avg, 2)

    def analyze_all_projects(self):
        """Calculate metrics for all projects in the folder."""
        if not os.path.isdir(self.projects_path):
            raise FileNotFoundError(f"Folder not found: {self.projects_path}")

        for proj in os.listdir(self.projects_path):
            proj_path = os.path.join(self.projects_path, proj)
            if not os.path.isdir(proj_path):
                continue

            mi_avg, cc_avg = self._calculate_project_metrics(proj_path)
            self.metrics_list.append({
                "ProjectName": proj,
                "MI_avg": mi_avg,
                "CC_avg": cc_avg
            })
            logger.info(f"Project {proj} => Weighted MI: {mi_avg}, Average CC: {cc_avg}")

        return self.metrics_list

    def save_csv(self, base_output_folder: str):
        """Save project metrics to a CSV in 'metrics' folder inside output."""
        if not self.metrics_list:
            logger.info("No metrics to save")
            return

        metrics_folder = os.path.join(base_output_folder, "metrics")
        os.makedirs(metrics_folder, exist_ok=True)

        existing_files = [
            f for f in os.listdir(metrics_folder)
            if f.endswith("_metrics.csv") and f.split("_")[0].isdigit()
        ]

        next_index = (
            max(int(f.split("_")[0]) for f in existing_files) + 1
            if existing_files else 1
        )

        csv_file = os.path.join(metrics_folder, f"{next_index}_metrics.csv")

        with open(csv_file, 'w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=["ProjectName", "MI_avg", "CC_avg"])
            writer.writeheader()
            writer.writerows(self.metrics_list)

        logger.info(f"CSV metrics saved in {csv_file}")
