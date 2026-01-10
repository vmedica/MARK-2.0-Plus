"""Output Reader - Reads and parses pipeline output files."""

import csv
from dataclasses import dataclass, field
from pathlib import Path
from typing import List


@dataclass
class OutputFile:
    """Represents an output file in the results directory."""

    name: str
    path: Path
    category: str
    run_id: str

    @property
    def is_summary(self) -> bool:
        """Check if this is a summary results file."""
        return self.name in ("results.csv", "metrics.csv")


@dataclass
class OutputDirectory:
    """Represents a run output directory."""

    name: str
    path: Path
    category: str
    files: List[OutputFile] = field(default_factory=list)


@dataclass
class OutputTree:
    """Tree structure of output directories and files."""

    producer_dirs: List[OutputDirectory] = field(default_factory=list)
    consumer_dirs: List[OutputDirectory] = field(default_factory=list)
    metrics_dirs: List[OutputDirectory] = field(default_factory=list)


@dataclass
class CSVData:
    """Represents loaded CSV data."""

    headers: List[str]
    rows: List[List[str]]
    file_path: Path

    @property
    def row_count(self) -> int:
        return len(self.rows)


class OutputReader:
    """Service for reading and parsing pipeline output files."""

    CATEGORIES = ("producer", "consumer", "metrics")

    def __init__(self, output_path: Path):
        self.output_path = Path(output_path)

    def scan_output_tree(self) -> OutputTree:
        """Scan the output directory and build a tree structure."""
        tree = OutputTree()

        for category in self.CATEGORIES:
            category_path = self.output_path / category
            if not category_path.exists():
                continue

            dirs_list = getattr(tree, f"{category}_dirs")

            for run_dir in sorted(category_path.iterdir()):
                if not run_dir.is_dir():
                    continue

                output_dir = OutputDirectory(
                    name=run_dir.name, path=run_dir, category=category
                )

                for csv_file in run_dir.glob("*.csv"):
                    output_dir.files.append(
                        OutputFile(
                            name=csv_file.name,
                            path=csv_file,
                            category=category,
                            run_id=run_dir.name,
                        )
                    )

                output_dir.files.sort(key=lambda f: (not f.is_summary, f.name))
                dirs_list.append(output_dir)

        return tree

    def load_csv(self, file_path: Path) -> CSVData:
        """Load a CSV file into a structured data object."""
        file_path = Path(file_path)

        if not file_path.exists():
            raise FileNotFoundError(f"CSV file not found: {file_path}")

        with open(file_path, "r", encoding="utf-8", newline="") as f:
            reader = csv.reader(f)
            rows = list(reader)

        if not rows:
            return CSVData(headers=[], rows=[], file_path=file_path)

        return CSVData(headers=rows[0], rows=rows[1:], file_path=file_path)

    def find_complete_analyses(self) -> list[str]:
        producer = {d.name.split("_")[-1] for d in (self.output_path / "producer").iterdir()}
        consumer = {d.name.split("_")[-1] for d in (self.output_path / "consumer").iterdir()}

        return sorted(producer & consumer)
