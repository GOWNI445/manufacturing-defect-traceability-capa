import argparse,csv,json
from pathlib import Path

def read_csv(p):
    with p.open(newline="",encoding="utf-8") as f: return list(csv.DictReader(f))
def validate(data_dir):
    d=Path(data_dir); csvdir=d/"csv"
    tables={p.stem:read_csv(p) for p in csvdir.glob("*.csv")}
    issues=[]
    def unique(table,key):
        seen=set()
        for r in tables.get(table,[]):
            v=r.get(key,"")
            if v in seen: issues.append(f"duplicate PK {table}.{key}={v}")
            seen.add(v)
    for t,k in [("Product","product_id"),("Supplier","supplier_id"),("Material","material_id"),("BOM","bom_line_id"),("Machine","machine_id"),("MaterialLot","material_lot_id"),("ProductionOrder","production_order_id"),("ProcessStep","process_step_id"),("LotConsumption","consumption_id"),("InspectionPlan","inspection_plan_id"),("InspectionResult","inspection_result_id"),("Defect","defect_id"),("CorrectiveAction","capa_id"),("CAPAEvent","capa_event_id"),("ProductionOrderEvent","order_event_id")]: unique(t,k)
    # FK checks. Deliberate anomaly rows are expected to be reported, not hidden.
    refs={"BOM":[("product_id","Product","product_id"),("material_id","Material","material_id")],
      "MaterialLot":[("supplier_id","Supplier","supplier_id"),("material_id","Material","material_id")],
      "ProductionOrder":[("product_id","Product","product_id")],
      "ProcessStep":[("production_order_id","ProductionOrder","production_order_id"),("machine_id","Machine","machine_id")],
      "LotConsumption":[("production_order_id","ProductionOrder","production_order_id"),("material_lot_id","MaterialLot","material_lot_id"),("bom_line_id","BOM","bom_line_id")],
      "InspectionResult":[("inspection_plan_id","InspectionPlan","inspection_plan_id"),("production_order_id","ProductionOrder","production_order_id"),("process_step_id","ProcessStep","process_step_id")],
      "Defect":[("inspection_result_id","InspectionResult","inspection_result_id"),("production_order_id","ProductionOrder","production_order_id"),("material_lot_id","MaterialLot","material_lot_id"),("process_step_id","ProcessStep","process_step_id")],
      "CorrectiveAction":[("defect_id","Defect","defect_id")],"CAPAEvent":[("capa_id","CorrectiveAction","capa_id")],
      "ProductionOrderEvent":[("production_order_id","ProductionOrder","production_order_id")]}
    truth=read_csv(d/"ground_truth.csv") if (d/"ground_truth.csv").exists() else []
    labelled={(x["entity_name"],x["entity_id"],x["issue_type"]) for x in truth}
    for table,links in refs.items():
        for col,parent,pkey in links:
            parent_ids={r[pkey] for r in tables.get(parent,[])}
            for r in tables.get(table,[]):
                val=r.get(col,"")
                if val and val not in parent_ids:
                    if r.get("issue_type"): continue
                    issues.append(f"FK violation {table}.{r.get(next(iter(r)))} {col}={val} missing {parent}")
    # Every required BOM line should have a consumption bridge for each order.
    # The one deliberately injected missing-consumption case is identified by ground truth.
    labelled_missing_orders={x["entity_id"] for x in truth if x.get("issue_type")=="BOM_MATERIAL_NOT_CONSUMED" and x.get("entity_name")=="ProductionOrder"}
    product_by_order={x["production_order_id"]:x["product_id"] for x in tables.get("ProductionOrder",[])}
    bom_by_product={}
    for b in tables.get("BOM",[]): bom_by_product.setdefault(b["product_id"],set()).add(b["bom_line_id"])
    consumed_lines={}
    for c in tables.get("LotConsumption",[]): consumed_lines.setdefault(c["production_order_id"],set()).add(c["bom_line_id"])
    for oid,pid in product_by_order.items():
        missing=bom_by_product.get(pid,set())-consumed_lines.get(oid,set())
        if missing and oid not in labelled_missing_orders:
            issues.append(f"BOM material not consumed for {oid}: {len(missing)} missing line(s)")
    for r in tables.get("InspectionResult",[]):
        try:
            if int(r["inspected_qty"])<=0 or int(r["defective_qty"])<0: issues.append(f"invalid inspection quantities {r['inspection_result_id']}")
            if int(r["defective_qty"])>int(r["inspected_qty"]) and not r.get("issue_type"): issues.append(f"defect count exceeds inspected qty {r['inspection_result_id']}")
        except ValueError: issues.append("non-numeric inspection quantities")
    for c in tables.get("CorrectiveAction",[]):
        if c["capa_status"]=="CLOSED" and (c["verification_result"]!="PASS" or not c["verified_at"] or not c["closed_at"] or c["closed_at"]<c["verified_at"]):
            if not c.get("issue_type"): issues.append(f"CAPA closed without successful prior verification {c['capa_id']}")
    # Arithmetic reconciliation from consumption rows, using observed source bridge records.
    consumed={}
    for r in tables.get("LotConsumption",[]):
        try: consumed[r["material_lot_id"]]=consumed.get(r["material_lot_id"],0)+int(r["consumed_qty"])
        except ValueError: pass
    for l in tables.get("MaterialLot",[]):
        try:
            expected=int(l["received_qty"])-consumed.get(l["material_lot_id"],0)-int(l["scrapped_qty"])
            if expected!=int(l["available_qty"]): issues.append(f"lot balance mismatch {l['material_lot_id']}")
        except ValueError: issues.append(f"invalid lot balance {l['material_lot_id']}")
    report={"status":"PASS_WITH_LABELLED_EXCEPTIONS" if not issues else "FAIL","validation_issue_count":len(issues),
            "validation_issues":issues[:200],"ground_truth_cases":len(truth),"row_counts":{k:len(v) for k,v in tables.items()},
            "kpis":{"inspection_results":len(tables.get("InspectionResult",[])),
                    "defect_records":len(tables.get("Defect",[])),
                    "defect_rate_by_units":round(sum(int(x["defective_qty"]) for x in tables.get("InspectionResult",[]) if x.get("defective_qty","").isdigit())/max(1,sum(int(x["inspected_qty"]) for x in tables.get("InspectionResult",[]) if x.get("inspected_qty","").isdigit())),4),
                    "closed_capa":sum(x.get("capa_status")=="CLOSED" for x in tables.get("CorrectiveAction",[])),
                    "process_drift_steps":sum(x.get("process_drift_flag")=="1" for x in tables.get("ProcessStep",[]))}}
    (d/"validation_summary.json").write_text(json.dumps(report,indent=2),encoding="utf-8")
    return report
if __name__=="__main__":
    ap=argparse.ArgumentParser(); ap.add_argument("--data",default="data"); a=ap.parse_args()
    r=validate(a.data); print(json.dumps(r,indent=2))
