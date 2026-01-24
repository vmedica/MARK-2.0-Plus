# MARK 2.0 Plus

> **Fork of MARK 2.0** — Extended with GUI, Code Metrics, and Dashboard features.

This project is a fork of the original **MARK 2.0** tool, developed as part of the *Master's Degree in Computer Science* at the **University of Salerno**, for the course **Ingegneria del Software Tecniche Avanzate (Advanced Software Engineering Techniques)**.

**MARK 2.0** is a tool that automatically classifies Machine Learning (ML) projects based on their behavior with respect to model production and/or use, using heuristic rules and static analysis of source code.

---

## What's New in MARK 2.0 Plus

This fork extends the original MARK 2.0 with three main features:

### 1. Code Quality Metrics (Radon)
Integration of **Cyclomatic Complexity (CC)** and **Maintainability Index (MI)** metrics using Radon. Metrics are calculated on analyzed source files and aggregated at project level, enabling comparison between repositories.

### 2. GUI for Configuration and Execution
A **Tkinter-based GUI** (`mark_gui.py`) that allows users to:
- Select input sources (local folder or CSV for repository cloning)
- Configure analysis parameters (step, rules, metrics toggle)
- Run analysis via a simple "Run" button
- View results directly in the interface

### 3. Integrated Reporting Dashboard
A **Dashboard** section in the GUI with charts (matplotlib) and aggregated statistics:
- **Analysis Overview**: count and percentage of Producer/Consumer classifications
- **Code Quality Overview**: average CC and MI metrics
- **Top ML Keywords**: most detected ML keywords across analyzed projects

---

## Documentation

Additional documentation is available in the **ISTA_DOCS/** folder.

---

## Content

**/modules** — All the modules that make up the tool:
- **analyzer**: classification logic, from classifier selection to its construction and use
- **cloner**: for cloning projects from Git
- **keyword_extractor**: keyword extraction logic (Strategy Pattern)
- **library_manager**: scripts for managing libraries
- **scanner**: filters the files to be analyzed
- **utils**: logger utilities
- **oracle**: tools for comparing results with oracle files

**/gui** — GUI components (views, services, controller)

---

## Installation

Install the required dependencies:
```sh
pip install -r requirements.txt
```
> Includes runtime dependencies: pandas, GitPython, ttkbootstrap, matplotlib.

Optional development tools:
```sh
pip install -r dev-requirements.txt
```
> Includes linting (pylint, flake8), metrics (radon), and testing (pytest, pytest-cov).

---

## Usage

MARK 2.0 Plus can be used in two ways: via **Command-Line** (`main.py`) or via **GUI** (`mark_gui.py`).

---

### Command-Line Mode

The configurations are in `main.py`.

1. **Repository Cloning**: The RepoCloner receives an integer N and clones the first N repositories from the configured source.
2. **Analysis (Classification)**: The Facade instantiates the correct analyzer based on the role (AnalyzerRole) and configuration (LibraryDictType), via Factory → Builder.
3. **Aggregation and Reporting**: Concludes with Merger and ResultAnalysis.

**Supported roles**: PRODUCER, CONSUMER, METRICS

```sh
python main.py
```

**Note**: In MARK 2.0, phases are modular and parameterizable; partially starting a single phase may require a minor modification to `main.py` (e.g., enabling/disabling steps).

See `GUIDA main_args.md` for advanced CLI options with `main_args.py`.

---

### GUI Mode

Run the graphical interface for an intuitive, guided workflow:
```sh
python mark_gui.py
```

---

## Configuration

- **AnalyzerRole**: Select the analysis role (Producer/Consumer)
- **LibraryDictType**: Select the library dictionary for the role
- **FileFilters**: Include/exclude files (e.g., exclude tests/examples)
- **KeywordExtractionStrategy**: Keyword extraction strategy (default: regex)
- **Enable Metrics**: Toggle code quality metrics calculation

The GUI provides an intuitive way to set these options without editing code.

---

## Output

- CSV with projects classified by role
- CSV with metrics (CC, MI) calculated for each project
- Dashboard visualizations for aggregated analysis
- Persistent logs in `logs/` for each execution

