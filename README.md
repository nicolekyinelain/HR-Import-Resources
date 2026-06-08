# HR Import Resources

Interactive CLI utility for normalizing and splitting HR export CSV files (Users and Job Assignments) before they are imported into downstream systems (the Lift LMS). Tenant-specific records are extracted into separate output files with an auto-enrollment column added.

## Requirements

- [Python 3.11+](https://www.python.org/downloads/)
- [pandas](https://pandas.pydata.org/) (the only third-party dependency; everything else is part of the Python standard library)

## Setup

1. Clone or download this repository.

3. Install the required packages from [requirements.txt](requirements.txt):

   ```powershell
   pip install -r requirements.txt
   ```

   This installs `pandas`, which is all the program needs to run.

## Usage

Run the interactive CLI from the project directory:

```powershell
# Run with no tenant splitting
python Main.py

# Run with one or more tenant IDs (case-insensitive, must exist in tenants.json)
python Main.py jbg
python Main.py jbg jaa
```

After launch, paste a CSV path at the prompt (surrounding quotes are stripped automatically). Enter `q` to quit.

> **Note:** The filename **must** contain either `Users` or `Job Assignments` (case-insensitive). That substring is what routes processing

## What it does

- **`Job Assignments` files** — drops rows with a missing `useridnumber`, fills missing `Manager email` values with `#N/A`, and lowercases `Manager email` and `useridnumber`.
- **`Users` files** — drops rows with a missing `idnumber`, splits out tenant-specific rows (see below), then lowercases `idnumber` and `email`.
- Both paths drop the hardcoded accounts (`joeben@joby.aero`, `patryck.chipman@joby.aero`).

### Tenant splitting

For each tenant ID passed on the command line, rows whose `business unit description` matches the tenant's configured value are written to a sibling file `<original>_<tenant_id>.csv` with an added `tenantmember` column (set to the tenant ID) used downstream for auto-enrollment. Those rows are then removed from the main output.

> **Warning:** The original CSV is overwritten in place when processing completes. Backups of the original files are made

## Project layout

| File | Purpose |
|---|---|
| [Main.py](Main.py) | Entry point — validates tenant arguments and runs the read → process loop. |
| [HrImport.py](HrImport.py) | `HRImport.run()` — dispatches processing based on the filename. |
| [Tenants.py](Tenants.py) | `load_tenants()` — reads tenant definitions from `tenants.json`. |
| [tenants.json](tenants.json) | Tenant ID → business-unit configuration. |
| [not_in_both.py](not_in_both.py) | Standalone helper (not wired into `Main.py`). **LEGACY** |
| [requirements.txt](requirements.txt) | Python dependencies. |
