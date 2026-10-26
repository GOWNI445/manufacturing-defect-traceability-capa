# Manufacturing Defect Traceability & CAPA

A reproducible synthetic-data project for tracing manufacturing defects from inspection results to production orders, process steps, machines, supplier batches, containment, and corrective actions.

## Features
- Generates the requested baseline volume: 200 products/SKUs, 50 suppliers, 2,000 material lots, 5,000 production orders, and 20,000 inspection results.
- Fixed seed (`20261022`) and configurable scale.
- Creates master, bridge, transaction, and event-history tables as CSV and JSON.
- Generates deliberate labelled exceptions and a separate `ground_truth.csv` that must not be used as model input.
- Validates primary keys, foreign keys, enums, dates, arithmetic, CAPA verification-before-closure, BOM consumption, inspected quantities, and traceability.
- Exports a SQLite database and SQL seed dump.
- Includes a Streamlit dashboard for KPIs, traceability lookup, and exception review.

## Quick start (Windows / VS Code)
1. Install Python 3.10+.
2. Open a terminal in this project folder.
3. Create a virtual environment (optional but recommended):
   ```powershell
   py -m venv .venv
   .venv\Scripts\activate
   ```
4. Install dependencies:
   ```powershell
   pip install -r requirements.txt
   ```
5. Generate the full dataset:
   ```powershell
   python generate_data.py --seed 20261022 --scale full --output data
   ```
6. Run validation:
   ```powershell
   python validate_data.py --data data
   ```
7. Launch dashboard:
   ```powershell
   streamlit run app.py
   ```

For a smaller smoke test:
```powershell
python generate_data.py --seed 20261022 --scale starter --output data
python validate_data.py --data data
```

`starter` uses 20 SKUs, 8 suppliers, 100 material lots, 150 production orders, and 600 inspections. Both scales use the same deterministic generation logic.

## Main outputs
- `data/csv/`: one CSV per entity/table.
- `data/json/`: one JSON array per entity/table.
- `data/defect_traceability.sqlite`: queryable SQLite database.
- `data/seed.sql`: SQL schema and inserts.
- `data/ground_truth.csv` and `data/ground_truth.json`: labelled injected anomalies and expected decisions; keep these separate from input features.
- `data/validation_summary.json`: validation result and counts.
- `data/manifest.json`: seed, parameters, row counts, SHA-256 checksums, generator version.

## Business rules
- A production order can consume multiple material lots; a material lot can be consumed by multiple orders (many-to-many bridge: `LotConsumption`).
- Products have BOM lines. The generator records material consumption for each order and checks BOM coverage.
- An inspection result belongs to an inspection plan and production order; a result may create zero or more defects.
- Defects connect to the order, material lot (when traceable), process step, machine, and inspection result.
- CAPA is tracked with append-only `CAPAEvent` history. A CAPA cannot validly close until verification passes.
- `issue_type` and `ground_truth` label deliberately injected exceptions. They are not silently mixed into unrelated rows.
- Defect rate = defective inspected units / inspected units; do not divide defect count by order count.
- Lot balance = received quantity - consumed quantity - scrapped quantity.

## Trace a defect
In the dashboard, enter a defect ID such as `DEF-2026-000001`. The trace output shows the inspection, production order, product, process step, machine, consumed supplier lot(s), supplier, and CAPA.

## Reproducibility
Run twice into separate folders:
```powershell
python generate_data.py --seed 20261022 --scale starter --output run_a
python generate_data.py --seed 20261022 --scale starter --output run_b
python compare_runs.py run_a run_b
```
The comparison checks CSV row counts and file SHA-256 checksums. For full scale, use the same commands with `--scale full`.

## Repository submission checklist
- Push the project to a **public** GitHub repository.
- Include this README and generated validation summary.
- Include tests (`python -m unittest discover -s tests -v`).
- Do not upload secrets or real confidential/production data. All generated records are synthetic.

## Limitations
This is a local demo/reference implementation, not a validated MES/QMS production system. Before production use, add authentication/authorization, audit controls, migrations, backups, observability, and review of plant-specific rules.
