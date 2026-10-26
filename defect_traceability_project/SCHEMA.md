# Schema and Relationship Guide

All IDs are immutable string primary keys. `effective_from` / `effective_to` describe master-data validity; an empty `effective_to` means currently effective. Date/time values are ISO-8601 strings. All records are synthetic.

## Entities, keys and cardinality

| Entity/table | Primary key | Important foreign keys | Cardinality / optionality |
|---|---|---|---|
| Product | `product_id` (`SKU-######`) | — | One Product has many BOM lines, production orders, and inspection plans. |
| BOM | `bom_line_id` | `product_id` → Product; `material_id` → Material | Product 1:N BOM; Material 1:N BOM. Effective-dated BOM lines. |
| Material | `material_id` | — | One Material can appear in many BOM lines and material lots. |
| Supplier | `supplier_id` (`SUP-####`) | — | One Supplier has many incoming MaterialLots. |
| MaterialLot | `material_lot_id` (`LOT-SUP-2026-######`) | `supplier_id` → Supplier; `material_id` → Material | Supplier 1:N lots; Material 1:N lots. A defect's lot reference is optional in business reality, but the generated defect table includes a labelled broken-lot case. |
| ProductionOrder | `production_order_id` (`WO-2026-######`) | `product_id` → Product | Product 1:N orders. Orders have append-only ProductionOrderEvent records. |
| Machine | `machine_id` (`MCH-####`) | — | One Machine can execute many ProcessSteps. |
| ProcessStep | `process_step_id` | `production_order_id` → ProductionOrder; `machine_id` → Machine | Order 1:N steps; Machine 1:N steps. `(production_order_id, step_sequence)` is unique. |
| LotConsumption | `consumption_id` | `production_order_id` → ProductionOrder; `material_lot_id` → MaterialLot; `bom_line_id` → BOM | Bridge table: ProductionOrder N:M MaterialLot. One order and one lot can have many consumption rows. |
| InspectionPlan | `inspection_plan_id` | `product_id` → Product | Product 1:N plans; plan revision and effective dates are retained. |
| InspectionResult | `inspection_result_id` (`INSP-WO-...-###`) | `inspection_plan_id` → InspectionPlan; `production_order_id` → ProductionOrder; `process_step_id` → ProcessStep | Plan/order/step each 1:N inspection results. |
| Defect | `defect_id` (`DEF-2026-######`) | `inspection_result_id` → InspectionResult; `production_order_id` → ProductionOrder; `material_lot_id` → MaterialLot (nullable in business rules); `process_step_id` → ProcessStep; `machine_id` → Machine | InspectionResult 1:N defects. Trace links are mandatory in baseline data; deliberately broken links are labelled. |
| CorrectiveAction | `capa_id` (`CAPA-2026-######`) | `defect_id` → Defect | Defect 1:N CAPAs is supported; this generator creates zero or one CAPA per defect. |
| CAPAEvent | `capa_event_id` | `capa_id` → CorrectiveAction | CAPA 1:N append-only events; do not overwrite event history. |
| ProductionOrderEvent | `order_event_id` | `production_order_id` → ProductionOrder | Order 1:N append-only status history. |

## Lifecycle rules

- Production order states: `PLANNED`, `RELEASED`, `IN_PROCESS`, `COMPLETED`, `ON_HOLD`, `CLOSED`.
- Inspection results: `PASS` or `FAIL`; `defective_qty` must be between zero and `inspected_qty`.
- CAPA can be `CLOSED` only after `verification_result=PASS`, with a verification timestamp no later than closure.
- Material lot balance: `available_qty = received_qty - consumed_qty - scrapped_qty`.
- Material consumption must cover every effective BOM line for the product/order. The intentionally omitted consumption is identified in `ground_truth.csv`.
- A defect trace should join defect → inspection result → production order → process step → machine, and order → LotConsumption → MaterialLot → Supplier.
- `ground_truth.csv/json` is a separate evaluation artifact. Do not include its labels as input features when building a model.

## Known labelled negative cases

The generator adds five cases after producing the valid baseline:
1. Defect references a nonexistent material lot → `REJECT_AND_QUARANTINE`.
2. A BOM line is missing a consumption bridge row → `BLOCK_RELEASE`.
3. CAPA is closed before verification → `REOPEN_CAPA`.
4. Defective quantity exceeds inspected quantity → `INVALID_INSPECTION`.
5. Defect references a nonexistent process step → `HOLD_FOR_INVESTIGATION`.

The validator suppresses only the specific expected violation documented in ground truth. Other integrity violations are reported.
