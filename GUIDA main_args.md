# Guida all'utilizzo di main_args.py

## Prerequisiti

Prima di utilizzare lo script, assicurarsi di avere:

- Python installato (versione consigliata: 3.8+)
- Dipendenze installate: `pip install -r requirements.txt`
- La struttura delle directory `io/` configurata correttamente

## Sintassi di base

```bash
python main_args.py [opzioni]
```

## Opzioni disponibili

### Percorsi

#### `--io-path`

- **Descrizione**: Percorso alla directory IO contenente i dizionari delle librerie e gli output
- **Default**: `./io`
- **Esempio**: `--io-path ./io`

#### `--repository-path`

- **Descrizione**: Percorso alla directory contenente i repository da analizzare
- **Default**: `./io/repos` (se non specificato)
- **Esempio**: `--repository-path ./io/repos`

#### `--project-list`

- **Descrizione**: Percorso al file CSV contenente la lista dei progetti da clonare
- **Default**: `./io/applied_projects.csv` (se non specificato)
- **Esempio**: `--project-list ./io/applied_projects.csv`

#### `--n-repos`

- **Descrizione**: Numero di repository da clonare
- **Default**: `20`
- **Esempio**: `--n-repos 50`

### Flag di controllo delle fasi

#### `--clone`

- **Descrizione**: Abilita la fase di clonazione dei repository
- **Uso**: Aggiungere questa flag per clonare i repository dalla lista specificata

#### `--clone-check`

- **Descrizione**: Abilita la verifica della clonazione
- **Uso**: Controlla che i repository siano stati clonati correttamente

#### `--analysis`

- **Descrizione**: Abilita la fase di analisi ML
- **Uso**: Esegue l'analisi dei repository per identificare producer e consumer

#### `--metrics`

- **Descrizione**: Abilita la fase di calcolo delle metriche del codice
- **Uso**: Calcola Maintainability Index (MI) e Cyclomatic Complexity (CC) per tutti i progetti

#### `--merge`

- **Descrizione**: Abilita la fase di merge dei risultati
- **Uso**: Combina i risultati dell'analisi con l'oracle di riferimento

#### `--result-analysis`

- **Descrizione**: Abilita l'analisi finale dei risultati
- **Uso**: Genera statistiche e metriche finali

#### `--all`

- **Descrizione**: Abilita tutte le fasi del pipeline
- **Uso**: Equivalente a specificare: `--clone --clone-check --analysis --metrics --merge --result-analysis`

### Opzioni di analisi

#### `--no-rules-3`

- **Descrizione**: Disabilita la regola 3 per l'analisi dei consumer
- **Default**: La regola 3 è **abilitata** di default
- **Uso**: Aggiungere questa flag per disabilitare la regola 3
- **Esempio**: `python main_args.py --analysis --no-rules-3`

## Pipeline completa

Il sistema MARK 2.0 esegue le seguenti fasi:

### 1. **Clonazione** (`--clone`)

Clona i repository GitHub specificati nel file CSV della project list.

### 2. **Verifica Clonazione** (`--clone-check`)

Verifica che i repository siano stati clonati correttamente e genera report di log.

### 3. **Analisi ML** (`--analysis`)

Esegue l'analisi sui repository clonati:

- **Analisi Producer**: Identifica i progetti che producono librerie ML
- **Analisi Consumer**: Identifica i progetti che utilizzano librerie ML

### 4. **Calcolo Metriche** (`--metrics`)

Calcola le metriche del codice per tutti i progetti:

- **Maintainability Index (MI)**: Misura la manutenibilità del codice (0-100)
- **Cyclomatic Complexity (CC)**: Misura la complessità ciclomatica delle funzioni

### 4. **Calcolo Metriche** (`--metrics`)

Calcola le metriche del codice per tutti i progetti:

- **Maintainability Index (MI)**: Misura la manutenibilità del codice (0-100)
- **Cyclomatic Complexity (CC)**: Misura la complessità ciclomatica delle funzioni

### 5. **Merge dei Risultati** (`--merge`)

Combina i risultati dell'analisi con l'oracle di riferimento per validazione.

### 6. **Analisi Finale** (`--result-analysis`)

Genera metriche di performance e statistiche sui risultati ottenuti.

## Esempi di utilizzo

### Eseguire l'intero pipeline

```bash
python main_args.py --all
```

Oppure equivalentemente:

```bash
python main_args.py --clone --clone-check --analysis --merge --result-analysis
```

### Clonare solo 10 repository

```bash
python main_args.py --clone --n-repos 10
```

### Eseguire solo l'analisi (repository già clonati)

```bash
python main_args.py --analysis
```

### Calcolare solo le metriche del codice

```bash
python main_args.py --metrics
```

### Eseguire analisi ML e calcolo metriche

```bash
python main_args.py --analysis --metrics
```

### Eseguire analisi e merge

```bash
python main_args.py --analysis --merge
```

### Specificare percorsi personalizzati

```bash
python main_args.py --all --io-path ./custom_io --repository-path ./my_repos --n-repos 30
```

### Clonare, verificare e analizzare

```bash
python main_args.py --clone --clone-check --analysis --n-repos 15
```

### Pipeline completa senza regola 3

```bash
python main_args.py --all --no-rules-3
```

## Struttura delle directory

Il sistema si aspetta la seguente struttura:

```
io/
├── applied_projects.csv           # Lista dei progetti da clonare
├── library_dictionary/            # Dizionari delle librerie
│   ├── library_dict_consumers.csv
│   └── library_dict_producers.csv
├── output/                        # Risultati dell'analisi
│   ├── consumer/
│   ├── producer/
│   └── metrics/
└── repos/                         # Repository clonati
```

## Output

I risultati vengono salvati in:

- **Logs di clonazione**: `modules/cloner/log/`
- **Risultati analisi ML**: `io/output/consumer/` e `io/output/producer/`
- **Risultati metriche**: `io/output/metrics/`
- **Risultati matching**: `modules/oracle/matching/`

## Note

1. **Ordine delle fasi**: Le fasi devono essere eseguite nell'ordine corretto:

   - Prima `--clone` (se necessario clonare)
   - Poi `--clone-check` (opzionale)
   - Poi `--analysis`
   - Infine `--merge` e `--result-analysis`

2. **Dipendenze tra fasi**:

   - `--merge` e `--result-analysis` richiedono che `--analysis` sia stata completata
   - Se si esegue solo `--merge` o `--result-analysis` senza `--analysis`, lo script terminerà con errore

3. **Interruzione**: È possibile interrompere l'esecuzione con `Ctrl+C`

## Risoluzione problemi

### Errore: "IO path does not exist"

- Assicurarsi che la directory `io/` esista e sia specificata correttamente

### Errore: "Library dictionary not found"

- Verificare che esista la cartella `io/library_dictionary/` con i file CSV dei dizionari

### Errore: "Project list file not found"

- Controllare che il file `applied_projects.csv` esista nel percorso specificato

### Errore: "Cannot run merge without analysis results"

- Eseguire prima la fase di analisi con `--analysis`
