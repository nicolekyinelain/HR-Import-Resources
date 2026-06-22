# HR Import Resources

Interactive CLI utility for normalizing and splitting HR export CSV files (Users and Job Assignments) before they are imported into downstream systems (the Lift LMS). Files are normalized (validated, lowercased, suspended accounts filtered) and tenant-specific records are extracted into separate output files with an auto-enrollment column added.

## Requirements

- [Python 3.11+](https://www.python.org/downloads/)
- [pandas](https://pandas.pydata.org/) (the only third-party dependency; everything else is part of the Python standard library)

## Setup

1. Clone or download this repository.

2. Install the required packages from [requirements.txt](requirements.txt):

   ```powershell
   pip install -r requirements.txt
   ```

   This installs `pandas`, which is all the program needs to run.

3. Create a `dont_suspend.csv` file in the project directory (it is git-ignored). It must contain an `email` column listing the IDs (matched against `idnumber` / `useridnumber`) that should always be filtered out:

   ```csv
   email
   first.last1@email.com
   first.last2@email.com
   ```

## Usage

Run the interactive CLI from the project directory:

```powershell
# Run with no tenant splitting
python Main.py

# Run with one or more tenant IDs (case-insensitive, must exist in tenants.json)
python Main.py jbg
python Main.py jbg jaa
```

After launch, paste a CSV path at the prompt (surrounding quotes and backslashes are stripped automatically). The CLI keeps prompting for files until you enter `q`, `quit`, or `exit`.

Other arguments:

- `-h` / `--help` — print usage and exit.

> **Note:** The filename **must** contain either `Users` or `Job Assignments` (case-insensitive). That substring is what routes processing.

## What it does

Every processed file is backed up first, then transformed in place.

- **`Job Assignments` files** — drops rows with a missing `useridnumber`, fills missing `Manager email` values with `#N/A`, drops suspended users (`suspended == 1`), and lowercases `Manager email` and `useridnumber`.
- **`Users` files** — drops rows with a missing `idnumber`, splits out tenant-specific rows (see below), filters by suspension state (see *Terminated files* below), lowercases `idnumber` and `email`, and clears the `tenantmember` column on the remaining (non-tenant) rows.
- Both paths drop any account whose ID appears in `dont_suspend.csv` (matched against `idnumber` / `useridnumber`).

### Terminated files

For `Users` files whose name contains `terminated` (case-insensitive), the suspension handling is inverted: only suspended rows (`suspended == 1`) are kept, the existing `deleted` column is dropped, and `suspended` is renamed to `deleted`. Non-terminated `Users` files instead keep only active rows (`suspended == 0`).

### Tenant splitting

Tenant definitions live in [tenants.json](tenants.json) (currently `jbg` — Joby Aviation Germany, and `jaa` — Joby Aviation Academy). For each tenant ID passed on the command line, rows whose `business unit description` matches the tenant's configured value (case-insensitive, whitespace-trimmed) are written to a sibling file `<original> <tenant_id>.csv` with an added `tenantmember` column (set to the tenant ID) used downstream for auto-enrollment. Those rows are removed from the main output, and the new tenant file is then run through the same normalization (with no further tenant splitting).

> **Warning:** The original CSV is overwritten in place when processing completes. Before each file is processed, a backup of the original is copied to an `original_files/` subfolder (alongside the input file) prefixed with `Original `.

## Project layout

| File | Purpose |
|---|---|
| [Main.py](Main.py) | Entry point — validates tenant arguments, backs up originals, and runs the read → process loop. |
| [HRImport.py](HRImport.py) | `HRImport.run()` — dispatches and performs processing based on the filename. |
| [Tenants.py](Tenants.py) | `load_tenants()` — reads tenant definitions from `tenants.json`. |
| [tenants.json](tenants.json) | Tenant ID → business-unit configuration. |
| `dont_suspend.csv` | Local (git-ignored) list of IDs to always retain. Required at runtime. |
| [not_in_both.py](not_in_both.py) | Standalone helper (not wired into `Main.py`). **LEGACY** |
| [requirements.txt](requirements.txt) | Python dependencies. |
