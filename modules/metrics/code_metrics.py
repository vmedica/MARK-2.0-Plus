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
            return [], 0, 0  # ritorna lista vuota di blocchi

        # CC — dettagli per blocco
        cc_blocks = []
        try:
            cc_blocks = cc_visit(code)
            print(f"\n  Dettaglio CC per file: {file_path}")
            for b in cc_blocks:
                print(
                    f"    Blocco: {b.name} | "
                    f"Tipo: {b.__class__.__name__} | "
                    f"CC_blocco: {b.complexity}"
                )
        except Exception as e:
            logger.warning("Errore CC %s: %s", file_path, e)

        # MI
        try:
            mi_score = mi_visit(code, False)
        except Exception as e:
            logger.warning("Errore MI %s: %s", file_path, e)
            mi_score = 0

        # SLOC effettivo
        sloc = sum(
            1 for line in code.splitlines()
            if line.strip() and not line.strip().startswith("#")
        )

        return cc_blocks, mi_score, sloc

    def _calculate_project_metrics(self, project_path: str):
        """Calcola CC media (come Radon -a) e MI pesato per progetto."""
        all_cc_values = []  # lista di tutte le complessità dei blocchi
        mi_list, sloc_list = [], []

        print("\n==============================")
        print(f"Progetto: {project_path}")
        print("==============================")

        for root, _, files in os.walk(project_path):
            for f in files:
                if f.endswith(".py"):
                    cc_blocks, mi_val, sloc_val = self._calculate_file_metrics(
                        os.path.join(root, f)
                    )
                    if cc_blocks:
                        all_cc_values.extend([b.complexity for b in cc_blocks])
                        print(
                            f"File: {os.path.join(root, f)} | "
                            f"{len(cc_blocks)} blocchi"
                        )
                    if sloc_val > 0:
                        mi_list.append((mi_val, sloc_val))
                        sloc_list.append(sloc_val)

        # Media semplice dei blocchi (Radon -a)
        if all_cc_values:
            cc_avg = sum(all_cc_values) / len(all_cc_values)
        else:
            cc_avg = 0

        print(f"\n--- Calcolo media CC semplice (come Radon -a) ---")
        print(f"Somma(CC blocchi) = {sum(all_cc_values)}")
        print(f"Numero blocchi    = {len(all_cc_values)}")
        print(f"CC_media_blocchi  = {cc_avg}")

        # MI media pesata per SLOC
        total_sloc = sum(sloc_list) if sloc_list else 1
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
                "ProjectName": proj,
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
            writer = csv.DictWriter(
                f, fieldnames=["ProjectName", "MI_avg", "CC_avg"]
            )
            writer.writeheader()
            writer.writerows(self.metrics_list)

        logger.info("CSV metriche salvato in %s", csv_file)
