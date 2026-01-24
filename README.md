# 🔍 MARK 2.0 Plus

> **Fork of MARK 2.0** — Extended with GUI, Code Metrics, and Dashboard features.

This project is a fork of the original **MARK 2.0** tool, developed as part of the *Master's Degree in Computer Science* at the **University of Salerno**, for the course **Ingegneria del Software Tecniche Avanzate  (Advanced Software Engineering Techniques)**.

🔍 **MARK 2.0** is a static analysis tool that automatically classifies Machine Learning (ML) projects based on whether they:

- **Produce models** (PRODUCER)  
- **Use models** (CONSUMER)  

using heuristic rules and source code inspection.

---

## ✨ What's New in MARK 2.0 Plus

This fork extends the original MARK 2.0 with **three main features**:

### 📊 1. Code Quality Metrics (Radon)
Integration of:
- **Cyclomatic Complexity (CC)**
- **Maintainability Index (MI)**

using **Radon**.

Metrics are calculated on analyzed source files and then **aggregated at project level**, enabling:
- comparison between repositories
- quality monitoring across datasets

---

### 🖥️ 2. GUI for Configuration and Execution
A **Tkinter-based GUI** (`mark_gui.py`) that allows users to:

- 📁 Select input sources (local folder or CSV for repository cloning)  
- ⚙️ Configure analysis parameters (step, rules, metrics toggle)  
- ▶️ Run analysis via a simple **Run** button  
- 👀 View results directly in the interface  

---

### 📈 3. Integrated Reporting Dashboard
A **Dashboard** section in the GUI with interactive charts (matplotlib):

- **Analysis Overview:**  count and percentage of Producer/Consumer classifications  
- **Code Quality Overview:** average CC and MI metrics  
- **Top ML Keywords:** most detected ML keywords across analyzed projects  

---

## 📚 Documentation

Additional documentation is available in the **`ISTA_DOCS/`** folder.

---

## 📂Main structure of the project 

### `/modules` — Core of the tool
- **analyzer** → classification logic (Facade + Factory + Builder)
- **cloner** → Git repository cloning
- **keyword_extractor** → keyword extraction (Strategy Pattern)
- **library_manager** → library management scripts
- **scanner** → filters the files to be analyzed
- **utils** → logging utilities
- **oracle** → result comparison with oracle files

### `/gui`
- GUI components (views, services, controller)

---

## 🛠️ Installation

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
## ▶️ Usage

MARK 2.0 Plus can be used in **two ways**:

- 🧾 **Command-Line** → `main.py`  
- 🖥️ **GUI** → `mark_gui.py`

---

### 🧾 Command-Line Mode

The main configurations are defined in `main.py`.

#### 🔄 Workflow

1. **Repository Cloning**  
   The *RepoCloner* receives an integer **N** and clones the first **N** repositories  
   from the configured source.

2. **Analysis (Classification)**  
   The *Facade* instantiates the correct analyzer based on:
   - **AnalyzerRole**
   - **LibraryDictType**  
   using **Factory → Builder**.

3. **Aggregation and Reporting**  
   Final phase using **Merger** and **ResultAnalysis**.

---

#### 🎭 Supported Roles
- `PRODUCER`
- `CONSUMER`
- `METRICS`

---

#### ▶️ Run from terminal

```sh
python main.py
```
> ⚠️ **Note**  
> In MARK 2.0, phases are modular and parameterizable.  
> Partially starting a single phase may require a minor modification to `main.py`  
> (e.g., enabling/disabling steps).

📄 For advanced CLI options, see:  
**`GUIDA main_args.md`** (with `main_args.py`)

---

### 🖥️ GUI Mode

Run the graphical interface for an intuitive, guided workflow:

```sh
python mark_gui.py
```

---
## ⚙️ Configuration

Available configuration options:

- **AnalyzerRole** → select the analysis role (**Producer / Consumer**)
- **LibraryDictType** → select the library dictionary for the selected role
- **FileFilters** → include / exclude files (e.g. tests, examples)
- **KeywordExtractionStrategy** → keyword extraction logic (default: `regex`)
- **Enable Metrics** → toggle code quality metrics calculation (**CC & MI**)

👉 The GUI provides an intuitive way to set all these options  
**without editing any code**.

---

## 📤 Output

MARK 2.0 Plus generates:

- CSV with projects classified by role  
- CSV with code quality metrics (**CC**, **MI**)  
- Dashboard visualizations for aggregated analysis  
- Persistent logs in `logs/` for each execution
