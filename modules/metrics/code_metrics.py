import os
import csv
from radon.complexity import cc_visit
from radon.metrics import mi_visit
from modules.utils.logger import get_logger

logger = get_logger(__name__)


class CodeMetrics:
    """
    Class to calculate code quality metrics (CC and MI) for a set of projects.
    Output will be saved nella cartella 'metrics' dentro output.
    """

    def __init__(self, projects_path: str):
        self.projects_path = projects_path
        self.metrics_list = []

    def _calculate_file_metrics(self, file_path: str):
        """Calcola CC, MI e SLOC di un singolo file Python."""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                code = f.read()
        except Exception as e:
            logger.warning("Non posso leggere %s: %s", file_path, e)
            return 0, 0, 0

        # CC
        try:
            cc_blocks = cc_visit(code)
            cc_values = [b.complexity for b in cc_blocks]
            cc_avg = sum(cc_values) / len(cc_values) if cc_values else 0
        except Exception as e:
            logger.warning("Errore CC %s: %s", file_path, e)
            cc_avg = 0

        # MI
        try:
            mi_score = mi_visit(code, True)
        except Exception as e:
            logger.warning("Errore MI %s: %s", file_path, e)
            mi_score = 0

        # SLOC effettivo
        sloc = sum(1 for line in code.splitlines() if line.strip() and not line.strip().startswith("#"))

        return cc_avg, mi_score, sloc

    def _calculate_project_metrics(self, project_path: str):
        """Calcola CC e MI pesati per SLOC per un progetto."""
        cc_list, mi_list, sloc_list = [], [], []

        for root, _, files in os.walk(project_path):
            for f in files:
                if f.endswith(".py"):
                    cc_val, mi_val, sloc_val = self._calculate_file_metrics(os.path.join(root, f))
                    if sloc_val > 0:
                        cc_list.append((cc_val, sloc_val))
                        mi_list.append((mi_val, sloc_val))
                        sloc_list.append(sloc_val)

        total_sloc = sum(sloc_list) if sloc_list else 1
        cc_avg = sum(cc * sloc for cc, sloc in cc_list) / total_sloc if cc_list else 0
        mi_avg = sum(mi * sloc for mi, sloc in mi_list) / total_sloc if mi_list else 0

        return round(mi_avg, 2), round(cc_avg, 2)

    def analyze_all_projects(self):
        """Calcola le metriche per tutti i progetti nella cartella."""
        if not os.path.isdir(self.projects_path):
            raise FileNotFoundError(f"Folder non trovato: {self.projects_path}")

        for proj in os.listdir(self.projects_path):
            proj_path = os.path.join(self.projects_path, proj)
            if not os.path.isdir(proj_path):
                continue
            mi_avg, cc_avg = self._calculate_project_metrics(proj_path)
            self.metrics_list.append({
                "Nome_progetto": proj,
                "MI_avg": mi_avg,
                "CC_avg": cc_avg
            })
        return self.metrics_list

    def save_csv(self, base_output_folder: str):
        """
        Salva le metriche in un CSV nella cartella 'metrics' dentro output.
        Se la cartella non esiste la crea.
        """
        if not self.metrics_list:
            logger.warning("Nessuna metrica da salvare")
            return

        metrics_folder = os.path.join(base_output_folder, "metrics")
        os.makedirs(metrics_folder, exist_ok=True)

        csv_file = os.path.join(metrics_folder, "metrics.csv")
        with open(csv_file, 'w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=["Nome_progetto", "MI_avg", "CC_avg"])
            writer.writeheader()
            for m in self.metrics_list:
                writer.writerow(m)

        logger.info("CSV metriche salvato in %s", csv_file)
