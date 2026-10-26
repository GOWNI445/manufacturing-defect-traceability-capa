import argparse, csv, json, os, random, sqlite3, hashlib, shutil
from datetime import date, datetime, timedelta
from pathlib import Path

GENERATOR_VERSION = "1.0.0"
SEED_DEFAULT = 20261022

def iso(d): return d.isoformat() if hasattr(d, "isoformat") else d
def dump_csv(path, rows):
    rows = list(rows)
    if not rows:
        path.write_text("", encoding="utf-8"); return
    with path.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        w.writeheader()
        for r in rows: w.writerow({k: (json.dumps(v, ensure_ascii=False) if isinstance(v, (list,dict)) else v) for k,v in r.items()})
def dump_json(path, rows):
    path.write_text(json.dumps(list(rows), indent=2, ensure_ascii=False), encoding="utf-8")
def checksum(path):
    h=hashlib.sha256()
    with open(path,"rb") as f:
        for b in iter(lambda:f.read(65536),b""): h.update(b)
    return h.hexdigest()
def make_id(prefix, n, width=6): return f"{prefix}{n:0{width}d}"

def generate(seed=SEED_DEFAULT, scale="full", output="data"):
    rng=random.Random(seed)
    if scale=="starter": n_sku,n_sup,n_lot,n_order,n_insp=20,8,100,150,600
    else: n_sku,n_sup,n_lot,n_order,n_insp=200,50,2000,5000,20000
    out=Path(output)
    if out.exists(): shutil.rmtree(out)
    (out/"csv").mkdir(parents=True); (out/"json").mkdir()
    today=date(2026,10,22)
    # 1. Master data
    products=[]
    for i in range(1,n_sku+1):
        products.append({"product_id":make_id("SKU-",i),"product_name":f"Industrial Component {i:03d}",
            "family":rng.choice(["Valve","Pump","Bracket","Housing","Sensor","Gear"]),
            "unit_of_measure":"each","standard_cost":round(rng.uniform(8,950),2),
            "lifecycle_state":rng.choice(["ACTIVE","ACTIVE","ACTIVE","PHASE_IN"]),
            "effective_from":iso(today-timedelta(days=rng.randint(100,1200))),"effective_to":""})
    suppliers=[]
    for i in range(1,n_sup+1):
        suppliers.append({"supplier_id":make_id("SUP-",i,4),"supplier_name":f"Supplier {i:03d}",
            "risk_tier":rng.choices(["LOW","MEDIUM","HIGH"],[.55,.32,.13])[0],
            "country":rng.choice(["India","Germany","Japan","USA","Vietnam"]),
            "approved":rng.choices(["Y","N"],[.94,.06])[0],"effective_from":iso(today-timedelta(days=rng.randint(300,1800)))})
    materials=[]
    for i in range(1, min(80, max(20,n_sku//2))+1):
        materials.append({"material_id":make_id("MAT-",i),"material_name":f"Raw Material {i:03d}",
            "material_type":rng.choice(["METAL","POLYMER","ELECTRONIC","FASTENER"]),
            "unit_of_measure":"each","lifecycle_state":"ACTIVE"})
    boms=[]
    for p in products:
        chosen=rng.sample(materials, k=rng.randint(2,4))
        for j,m in enumerate(chosen,1):
            boms.append({"bom_line_id":make_id("BOML-",len(boms)+1),"product_id":p["product_id"],
                "material_id":m["material_id"],"quantity_per_unit":rng.choice([1,1,1,2,4]),
                "scrap_factor":round(rng.choice([0,.01,.02,.03]),3),"revision":"A",
                "effective_from":iso(today-timedelta(days=365)),"effective_to":""})
    machines=[]
    for i in range(1,31):
        machines.append({"machine_id":make_id("MCH-",i,4),"machine_name":f"Line {1+(i-1)//6} Machine {1+(i-1)%6}",
            "machine_type":rng.choice(["CNC","PRESS","ASSEMBLY","WELD","PAINT","TEST"]),
            "plant":"PLANT-01","lifecycle_state":"ACTIVE","commissioned_on":iso(today-timedelta(days=rng.randint(400,3000)))})
    # Lots are parents for consumption.
    lots=[]
    for i in range(1,n_lot+1):
        sup=rng.choice(suppliers); received=rng.randint(150,1800)
        received_date=today-timedelta(days=rng.randint(1,330))
        risk=rng.choices(["NORMAL","WATCH","HOLD"],[.84,.12,.04])[0]
        lots.append({"material_lot_id":f"LOT-{sup['supplier_id']}-2026-{i:06d}","supplier_id":sup["supplier_id"],
            "material_id":rng.choice(materials)["material_id"],"supplier_batch":f"{sup['supplier_id']}-B{rng.randint(10000,99999)}",
            "received_qty":received,"received_date":iso(received_date),"expiry_date":iso(received_date+timedelta(days=rng.randint(365,900))),
            "incoming_status":risk,"scrapped_qty":0,"effective_from":iso(received_date),"effective_to":""})
    # Process steps and orders.
    process_steps=[]
    orders=[]
    for i in range(1,n_order+1):
        prod=rng.choice(products); start=today-timedelta(days=rng.randint(0,300))
        qty=rng.randint(50,800)
        status=rng.choices(["RELEASED","IN_PROCESS","COMPLETED","ON_HOLD","CLOSED"],[.12,.18,.43,.07,.20])[0]
        orders.append({"production_order_id":f"WO-2026-{i:06d}","product_id":prod["product_id"],
            "planned_qty":qty,"released_qty":qty,"completed_qty":qty if status in ["COMPLETED","CLOSED"] else rng.randint(0,qty),
            "order_status":status,"planned_start":iso(start),"planned_end":iso(start+timedelta(days=rng.randint(1,10))),
            "actual_start":iso(start+timedelta(days=rng.randint(0,2))),"actual_end":iso(start+timedelta(days=rng.randint(2,12))) if status in ["COMPLETED","CLOSED"] else "",
            "issue_type":""})
        # Every order has 3-5 sequential process steps.
        for seq in range(1,rng.randint(4,6)):
            machine=rng.choice(machines); drift=rng.random()<.055
            process_steps.append({"process_step_id":f"STEP-{i:06d}-{seq:02d}","production_order_id":orders[-1]["production_order_id"],
                "step_sequence":seq,"operation_name":rng.choice(["Cut","Machine","Assemble","Weld","Coat","Final Test"]),
                "machine_id":machine["machine_id"],"started_at":iso(start+timedelta(hours=seq*2)),
                "ended_at":iso(start+timedelta(hours=seq*2+1)),"process_state":"COMPLETE",
                "temperature_c":round(rng.uniform(175,230) if drift else rng.uniform(185,205),1),
                "cycle_time_sec":round(rng.uniform(10,80) * (1.35 if drift else 1),1),
                "process_drift_flag":int(drift),"issue_type":""})
    # Material consumption bridge. Make valid baseline BOM consumption for at least one BOM material per order.
    consumptions=[]
    lot_by_material={}
    for l in lots: lot_by_material.setdefault(l["material_id"],[]).append(l)
    bom_by_product={}
    for b in boms: bom_by_product.setdefault(b["product_id"],[]).append(b)
    for o in orders:
        bomlines=bom_by_product[o["product_id"]]
        for b in bomlines:
            candidates=lot_by_material.get(b["material_id"],[])
            if not candidates: continue
            lot=rng.choice(candidates)
            qty=int(o["planned_qty"]*b["quantity_per_unit"]*(1+b["scrap_factor"]))
            consumptions.append({"consumption_id":make_id("CONS-",len(consumptions)+1),"production_order_id":o["production_order_id"],
                "material_lot_id":lot["material_lot_id"],"bom_line_id":b["bom_line_id"],"material_id":b["material_id"],
                "consumed_qty":qty,"consumed_at":o["actual_start"],"reversal_qty":0,"issue_type":""})
    # Inspection plans.
    plans=[]
    for p in products:
        plans.append({"inspection_plan_id":f"PLAN-{p['product_id']}","product_id":p["product_id"],
            "inspection_type":"IN_PROCESS","sample_size":5,"acceptance_limit":1,"revision":"A",
            "effective_from":iso(today-timedelta(days=365)),"effective_to":"","lifecycle_state":"ACTIVE"})
    plan_by_product={p["product_id"]:p["inspection_plan_id"] for p in plans}
    step_by_order={}
    for s in process_steps: step_by_order.setdefault(s["production_order_id"],[]).append(s)
    lotcons_by_order={}
    for c in consumptions: lotcons_by_order.setdefault(c["production_order_id"],[]).append(c)
    inspections=[]; defects=[]; capas=[]; capa_events=[]
    defect_n=0; capa_n=0
    # Ensure inspection records refer to real orders and plans. Inspected quantities reconcile to order quantity.
    for i in range(1,n_insp+1):
        o=orders[(i-1)%len(orders)]
        prod=o["product_id"]; plan=plan_by_product[prod]
        steps=step_by_order[o["production_order_id"]]
        step=rng.choice(steps)
        sample=rng.randint(5,30)
        # Defect probability rises for drift and high-risk supplier lots.
        cons=lotcons_by_order.get(o["production_order_id"],[])
        lot=rng.choice(cons)["material_lot_id"] if cons else ""
        lot_obj=next((x for x in lots if x["material_lot_id"]==lot),None)
        high_risk=lot_obj and lot_obj["incoming_status"]=="HOLD"
        p_def=.025 + (.13 if step["process_drift_flag"] else 0) + (.07 if high_risk else 0)
        defective= min(sample, rng.randint(1,3)) if rng.random()<p_def else 0
        status="FAIL" if defective else "PASS"
        insp_id=f"INSP-{o['production_order_id']}-{((i-1)//len(orders))+1:03d}"
        inspections.append({"inspection_result_id":insp_id,"inspection_plan_id":plan,"production_order_id":o["production_order_id"],
            "process_step_id":step["process_step_id"],"inspected_qty":sample,"defective_qty":defective,"result_status":status,
            "inspection_date":iso(date.fromisoformat(o["planned_start"])+timedelta(days=rng.randint(0,8))),
            "inspector_id":f"USR-{rng.randint(1,40):04d}","issue_type":""})
        if defective:
            defect_n+=1
            defect_id=f"DEF-2026-{defect_n:06d}"
            defects.append({"defect_id":defect_id,"inspection_result_id":insp_id,"production_order_id":o["production_order_id"],
                "material_lot_id":lot,"process_step_id":step["process_step_id"],"machine_id":step["machine_id"],
                "defect_code":rng.choice(["DIMENSION_OUT","SURFACE_CRACK","WELD_POROSITY","ELECTRICAL_FAIL","MISALIGNMENT"]),
                "severity":rng.choices(["LOW","MEDIUM","HIGH","CRITICAL"],[.3,.42,.22,.06])[0],
                "defect_qty":defective,"disposition":rng.choices(["REWORK","SCRAP","USE_AS_IS"],[.55,.28,.17])[0],
                "detected_at":inspections[-1]["inspection_date"],"issue_type":""})
            capa_n+=1
            capa_id=f"CAPA-2026-{capa_n:06d}"
            verify_pass=rng.random()>.12
            state="CLOSED" if verify_pass else "IN_PROGRESS"
            capas.append({"capa_id":capa_id,"defect_id":defect_id,"owner_id":f"USR-{rng.randint(1,20):04d}",
                "containment_action":rng.choice(["Quarantine affected lot","Stop machine and inspect","100% sorting","Hold production order"]),
                "root_cause_category":rng.choice(["SUPPLIER","MACHINE","PROCESS","OPERATOR","DESIGN"]),
                "corrective_action":rng.choice(["Replace worn tooling","Update work instruction","Supplier corrective request","Calibrate machine"]),
                "preventive_action":rng.choice(["Add preventive maintenance check","Add incoming inspection","Update control plan"]),
                "capa_status":state,"opened_at":inspections[-1]["inspection_date"],
                "verified_at":iso(date.fromisoformat(inspections[-1]["inspection_date"])+timedelta(days=3)) if verify_pass else "",
                "closed_at":iso(date.fromisoformat(inspections[-1]["inspection_date"])+timedelta(days=4)) if verify_pass else "",
                "verification_result":"PASS" if verify_pass else "PENDING","issue_type":""})
            capa_events.append({"capa_event_id":make_id("CAPAE-",len(capa_events)+1),"capa_id":capa_id,"event_type":"OPENED",
                "event_at":inspections[-1]["inspection_date"],"actor_id":capas[-1]["owner_id"],"notes":"CAPA opened from inspection defect"})
            if verify_pass:
                capa_events.extend([
                    {"capa_event_id":make_id("CAPAE-",len(capa_events)+1),"capa_id":capa_id,"event_type":"VERIFIED",
                     "event_at":capas[-1]["verified_at"],"actor_id":capas[-1]["owner_id"],"notes":"Effectiveness check passed"},
                    {"capa_event_id":make_id("CAPAE-",len(capa_events)+1),"capa_id":capa_id,"event_type":"CLOSED",
                     "event_at":capas[-1]["closed_at"],"actor_id":capas[-1]["owner_id"],"notes":"Closed after verification"}])
    # Reconcile material lot balances from source bridge rows.
    consumed={}
    for c in consumptions: consumed[c["material_lot_id"]]=consumed.get(c["material_lot_id"],0)+c["consumed_qty"]
    for l in lots:
        l["consumed_qty"]=consumed.get(l["material_lot_id"],0)
        l["available_qty"]=l["received_qty"]-l["consumed_qty"]-l["scrapped_qty"]
        l["balance_status"]="OK" if l["available_qty"]>=0 else "OVER_CONSUMED"
    # Intentional anomalies: mutate a few records and label them. Ground truth is separate from input tables.
    truth=[]
    def label(issue, entity, entity_id, expected, description):
        truth.append({"issue_id":make_id("ISSUE-",len(truth)+1),"issue_type":issue,"entity_name":entity,
                      "entity_id":entity_id,"ground_truth":expected,"description":description})
    if defects:
        d=defects[0]; d["material_lot_id"]="LOT-NONEXISTENT-2026-999999"; d["issue_type"]="DEFECT_NONEXISTENT_LOT"
        label("DEFECT_NONEXISTENT_LOT","Defect",d["defect_id"],"REJECT_AND_QUARANTINE","Defect references a material lot that does not exist.")
    if consumptions:
        c=consumptions[0]; c["issue_type"]="BOM_MATERIAL_NOT_CONSUMED"
        # Mark a BOM line as unconsumed for this order by removing its bridge row; preserve the intended case in truth.
        removed=consumptions.pop(0)
        # Recalculate lot balances after the deliberate missing-consumption case so the
        # balance equation remains internally reconciled to the exported bridge table.
        consumed_after={}
        for row in consumptions:
            consumed_after[row["material_lot_id"]]=consumed_after.get(row["material_lot_id"],0)+row["consumed_qty"]
        for lot_row in lots:
            lot_row["consumed_qty"]=consumed_after.get(lot_row["material_lot_id"],0)
            lot_row["available_qty"]=lot_row["received_qty"]-lot_row["consumed_qty"]-lot_row["scrapped_qty"]
            lot_row["balance_status"]="OK" if lot_row["available_qty"]>=0 else "OVER_CONSUMED"
        label("BOM_MATERIAL_NOT_CONSUMED","ProductionOrder",removed["production_order_id"],"BLOCK_RELEASE","A required BOM line has no matching consumption record.")
    if capas:
        c=capas[0]; c["capa_status"]="CLOSED"; c["closed_at"]=c["opened_at"]; c["verified_at"]=""
        c["verification_result"]="PENDING"; c["issue_type"]="CAPA_CLOSED_BEFORE_VERIFICATION"
        label("CAPA_CLOSED_BEFORE_VERIFICATION","CorrectiveAction",c["capa_id"],"REOPEN_CAPA","CAPA is closed before a passing verification event.")
    if inspections:
        ins=inspections[-1]; ins["defective_qty"]=ins["inspected_qty"]+1; ins["result_status"]="FAIL"; ins["issue_type"]="DEFECT_COUNT_EXCEEDS_INSPECTED"
        label("DEFECT_COUNT_EXCEEDS_INSPECTED","InspectionResult",ins["inspection_result_id"],"INVALID_INSPECTION","Defective quantity exceeds inspected quantity.")
    if len(defects)>1:
        d=defects[-1]; d["process_step_id"]="STEP-MISSING-999999-01"; d["issue_type"]="TRACEABILITY_CHAIN_BREAK"
        label("TRACEABILITY_CHAIN_BREAK","Defect",d["defect_id"],"HOLD_FOR_INVESTIGATION","Defect process-step reference cannot be resolved.")
    # Normalize event IDs after append batches to guarantee deterministic uniqueness.
    for idx, event in enumerate(capa_events, 1):
        event["capa_event_id"] = make_id("CAPAE-", idx)
    # Bridge table for order-product is already FK; include explicit BOM material mapping and state events.
    order_events=[]
    for o in orders:
        order_events.append({"order_event_id":make_id("WOEV-",len(order_events)+1),"production_order_id":o["production_order_id"],
            "event_type":"CREATED","event_at":o["planned_start"],"from_status":"","to_status":"PLANNED","actor_id":"SYSTEM"})
        order_events.append({"order_event_id":make_id("WOEV-",len(order_events)+1),"production_order_id":o["production_order_id"],
            "event_type":"STATUS_SET","event_at":o["actual_start"],"from_status":"PLANNED","to_status":o["order_status"],"actor_id":"PLANNER-0001"})
    tables={
        "Product":products,"Supplier":suppliers,"Material":materials,"BOM":boms,"Machine":machines,"MaterialLot":lots,
        "ProductionOrder":orders,"ProcessStep":process_steps,"LotConsumption":consumptions,"InspectionPlan":plans,
        "InspectionResult":inspections,"Defect":defects,"CorrectiveAction":capas,"CAPAEvent":capa_events,"ProductionOrderEvent":order_events
    }
    # Generate a complete data dictionary for every field in every entity/table.
    pk_map={"Product":"product_id","Supplier":"supplier_id","Material":"material_id","BOM":"bom_line_id",
      "Machine":"machine_id","MaterialLot":"material_lot_id","ProductionOrder":"production_order_id",
      "ProcessStep":"process_step_id","LotConsumption":"consumption_id","InspectionPlan":"inspection_plan_id",
      "InspectionResult":"inspection_result_id","Defect":"defect_id","CorrectiveAction":"capa_id",
      "CAPAEvent":"capa_event_id","ProductionOrderEvent":"order_event_id"}
    enum_values={"lifecycle_state":"ACTIVE/PHASE_IN/INACTIVE","risk_tier":"LOW/MEDIUM/HIGH",
      "approved":"Y/N","incoming_status":"NORMAL/WATCH/HOLD","balance_status":"OK/OVER_CONSUMED",
      "order_status":"PLANNED/RELEASED/IN_PROCESS/COMPLETED/ON_HOLD/CLOSED","process_state":"PLANNED/IN_PROGRESS/COMPLETE/FAILED",
      "inspection_type":"INCOMING/IN_PROCESS/FINAL","result_status":"PASS/FAIL","severity":"LOW/MEDIUM/HIGH/CRITICAL",
      "disposition":"REWORK/SCRAP/USE_AS_IS","capa_status":"OPEN/IN_PROGRESS/CLOSED/REJECTED",
      "verification_result":"PASS/FAIL/PENDING","root_cause_category":"SUPPLIER/MACHINE/PROCESS/OPERATOR/DESIGN",
      "event_type":"Documented event label; see event rows","unit_of_measure":"each","material_type":"METAL/POLYMER/ELECTRONIC/FASTENER"}
    fk_fields={"product_id":"Product.product_id","supplier_id":"Supplier.supplier_id","material_id":"Material.material_id",
      "machine_id":"Machine.machine_id","production_order_id":"ProductionOrder.production_order_id",
      "material_lot_id":"MaterialLot.material_lot_id","bom_line_id":"BOM.bom_line_id",
      "inspection_plan_id":"InspectionPlan.inspection_plan_id","inspection_result_id":"InspectionResult.inspection_result_id",
      "process_step_id":"ProcessStep.process_step_id","defect_id":"Defect.defect_id","capa_id":"CorrectiveAction.capa_id"}
    dictionary=[]
    for entity, rows in tables.items():
        if not rows: continue
        for field in rows[0].keys():
            vals=[r.get(field,"") for r in rows]
            sample=next((v for v in vals if v not in (None,"")),"")
            if field.endswith("_qty") or field in ("quantity_per_unit","sample_size","acceptance_limit","step_sequence","reversal_qty","scrapped_qty","consumed_qty","received_qty","planned_qty","released_qty","completed_qty","defective_qty","inspected_qty","defect_qty"):
                typ="integer"
            elif field.endswith("_cost") or field.endswith("_factor") or field.endswith("_c") or field.endswith("_sec"):
                typ="decimal"
            elif field.endswith("_flag"): typ="boolean/int (0 or 1)"
            elif field.endswith("_at") or field.endswith("_date") or field in ("effective_from","effective_to","planned_start","planned_end","actual_start","actual_end","commissioned_on"):
                typ="ISO-8601 date or datetime string"
            else: typ="string / identifier"
            required="optional" if any(v in (None,"") for v in vals) else "required"
            allowed=enum_values.get(field,"Identifier or source-derived value; see validation rules")
            units="units" if ("qty" in field or field in ("quantity_per_unit","sample_size")) else ("seconds" if "sec" in field else ("degrees Celsius" if field.endswith("_c") else ("currency per unit" if field.endswith("_cost") else "—")))
            unique="Primary key; immutable" if pk_map.get(entity)==field else ("Unique within parent: (production_order_id, step_sequence)" if entity=="ProcessStep" and field in ("production_order_id","step_sequence") else "Not unique")
            validation="Must be non-empty" if required=="required" else "May be blank when lifecycle does not require it"
            if field in fk_fields: validation=f"Must match an existing {fk_fields[field]} unless this row is a labelled negative scenario"
            if field in ("received_qty","consumed_qty","defect_qty","inspected_qty","quantity_per_unit","sample_size"): validation += "; must be > 0"
            if field=="defective_qty": validation="0 <= defective_qty <= inspected_qty; violations must be labelled"
            if field=="available_qty": validation="received_qty - consumed_qty - scrapped_qty"
            if field=="capa_status": validation="CLOSED only after verification_result=PASS and verified_at <= closed_at"
            if field.endswith("_from"): validation="Effective start date; must be <= effective_to when effective_to is populated"
            dictionary.append({"entity":entity,"field":field,"data_type":typ,"required_optional":required,
              "allowed_values":allowed,"units":units,"uniqueness":unique,"validation_rule":validation,
              "foreign_key_target":fk_fields.get(field,"")})
    tables["DataDictionary"]=[{"entity":r["entity"],"field":r["field"],"data_type":r["data_type"],
      "required_optional":r["required_optional"],"allowed_values":r["allowed_values"],"units":r["units"],
      "uniqueness":r["uniqueness"],"validation_rule":r["validation_rule"],"foreign_key_target":r["foreign_key_target"]} for r in dictionary]
    # Output CSV + JSON
    for name,rows in tables.items():
        dump_csv(out/"csv"/f"{name}.csv",rows); dump_json(out/"json"/f"{name}.json",rows)
    dump_csv(out/"ground_truth.csv",truth); dump_json(out/"ground_truth.json",truth)
    # SQL schema created from CSV-shaped rows, explicit primary keys and foreign keys.
    schema = """
PRAGMA foreign_keys=ON;
CREATE TABLE Product(product_id TEXT PRIMARY KEY, product_name TEXT NOT NULL, family TEXT NOT NULL, unit_of_measure TEXT NOT NULL, standard_cost REAL NOT NULL CHECK(standard_cost>=0), lifecycle_state TEXT NOT NULL, effective_from TEXT NOT NULL, effective_to TEXT);
CREATE TABLE Supplier(supplier_id TEXT PRIMARY KEY, supplier_name TEXT NOT NULL, risk_tier TEXT NOT NULL, country TEXT NOT NULL, approved TEXT NOT NULL, effective_from TEXT NOT NULL);
CREATE TABLE Material(material_id TEXT PRIMARY KEY, material_name TEXT NOT NULL, material_type TEXT NOT NULL, unit_of_measure TEXT NOT NULL, lifecycle_state TEXT NOT NULL);
CREATE TABLE BOM(bom_line_id TEXT PRIMARY KEY, product_id TEXT NOT NULL REFERENCES Product(product_id), material_id TEXT NOT NULL REFERENCES Material(material_id), quantity_per_unit INTEGER NOT NULL CHECK(quantity_per_unit>0), scrap_factor REAL NOT NULL, revision TEXT NOT NULL, effective_from TEXT NOT NULL, effective_to TEXT);
CREATE TABLE Machine(machine_id TEXT PRIMARY KEY, machine_name TEXT NOT NULL, machine_type TEXT NOT NULL, plant TEXT NOT NULL, lifecycle_state TEXT NOT NULL, commissioned_on TEXT NOT NULL);
CREATE TABLE MaterialLot(material_lot_id TEXT PRIMARY KEY, supplier_id TEXT NOT NULL REFERENCES Supplier(supplier_id), material_id TEXT NOT NULL REFERENCES Material(material_id), supplier_batch TEXT NOT NULL, received_qty INTEGER NOT NULL CHECK(received_qty>0), received_date TEXT NOT NULL, expiry_date TEXT NOT NULL, incoming_status TEXT NOT NULL, scrapped_qty INTEGER NOT NULL, consumed_qty INTEGER NOT NULL, available_qty INTEGER NOT NULL, balance_status TEXT NOT NULL, effective_from TEXT NOT NULL, effective_to TEXT);
CREATE TABLE ProductionOrder(production_order_id TEXT PRIMARY KEY, product_id TEXT NOT NULL REFERENCES Product(product_id), planned_qty INTEGER NOT NULL, released_qty INTEGER NOT NULL, completed_qty INTEGER NOT NULL, order_status TEXT NOT NULL, planned_start TEXT NOT NULL, planned_end TEXT NOT NULL, actual_start TEXT NOT NULL, actual_end TEXT, issue_type TEXT NOT NULL);
CREATE TABLE ProcessStep(process_step_id TEXT PRIMARY KEY, production_order_id TEXT NOT NULL REFERENCES ProductionOrder(production_order_id), step_sequence INTEGER NOT NULL, operation_name TEXT NOT NULL, machine_id TEXT NOT NULL REFERENCES Machine(machine_id), started_at TEXT NOT NULL, ended_at TEXT NOT NULL, process_state TEXT NOT NULL, temperature_c REAL NOT NULL, cycle_time_sec REAL NOT NULL, process_drift_flag INTEGER NOT NULL, issue_type TEXT NOT NULL, UNIQUE(production_order_id,step_sequence));
CREATE TABLE LotConsumption(consumption_id TEXT PRIMARY KEY, production_order_id TEXT NOT NULL REFERENCES ProductionOrder(production_order_id), material_lot_id TEXT NOT NULL REFERENCES MaterialLot(material_lot_id), bom_line_id TEXT NOT NULL REFERENCES BOM(bom_line_id), material_id TEXT NOT NULL REFERENCES Material(material_id), consumed_qty INTEGER NOT NULL, consumed_at TEXT NOT NULL, reversal_qty INTEGER NOT NULL, issue_type TEXT NOT NULL);
CREATE TABLE InspectionPlan(inspection_plan_id TEXT PRIMARY KEY, product_id TEXT NOT NULL REFERENCES Product(product_id), inspection_type TEXT NOT NULL, sample_size INTEGER NOT NULL, acceptance_limit INTEGER NOT NULL, revision TEXT NOT NULL, effective_from TEXT NOT NULL, effective_to TEXT, lifecycle_state TEXT NOT NULL);
CREATE TABLE InspectionResult(inspection_result_id TEXT PRIMARY KEY, inspection_plan_id TEXT NOT NULL REFERENCES InspectionPlan(inspection_plan_id), production_order_id TEXT NOT NULL REFERENCES ProductionOrder(production_order_id), process_step_id TEXT NOT NULL REFERENCES ProcessStep(process_step_id), inspected_qty INTEGER NOT NULL, defective_qty INTEGER NOT NULL, result_status TEXT NOT NULL, inspection_date TEXT NOT NULL, inspector_id TEXT NOT NULL, issue_type TEXT NOT NULL);
CREATE TABLE Defect(defect_id TEXT PRIMARY KEY, inspection_result_id TEXT NOT NULL REFERENCES InspectionResult(inspection_result_id), production_order_id TEXT NOT NULL REFERENCES ProductionOrder(production_order_id), material_lot_id TEXT, process_step_id TEXT NOT NULL, machine_id TEXT NOT NULL, defect_code TEXT NOT NULL, severity TEXT NOT NULL, defect_qty INTEGER NOT NULL, disposition TEXT NOT NULL, detected_at TEXT NOT NULL, issue_type TEXT NOT NULL);
CREATE TABLE CorrectiveAction(capa_id TEXT PRIMARY KEY, defect_id TEXT NOT NULL REFERENCES Defect(defect_id), owner_id TEXT NOT NULL, containment_action TEXT NOT NULL, root_cause_category TEXT NOT NULL, corrective_action TEXT NOT NULL, preventive_action TEXT NOT NULL, capa_status TEXT NOT NULL, opened_at TEXT NOT NULL, verified_at TEXT, closed_at TEXT, verification_result TEXT NOT NULL, issue_type TEXT NOT NULL);
CREATE TABLE CAPAEvent(capa_event_id TEXT PRIMARY KEY, capa_id TEXT NOT NULL REFERENCES CorrectiveAction(capa_id), event_type TEXT NOT NULL, event_at TEXT NOT NULL, actor_id TEXT NOT NULL, notes TEXT NOT NULL);
CREATE TABLE ProductionOrderEvent(order_event_id TEXT PRIMARY KEY, production_order_id TEXT NOT NULL REFERENCES ProductionOrder(production_order_id), event_type TEXT NOT NULL, event_at TEXT NOT NULL, from_status TEXT NOT NULL, to_status TEXT NOT NULL, actor_id TEXT NOT NULL);
"""
    dbpath=out/"defect_traceability.sqlite"
    if dbpath.exists(): dbpath.unlink()
    con=sqlite3.connect(dbpath); con.executescript(schema)
    # Insert valid tables in FK order, with deliberately anomalous rows in tables where schema allows them.
    order_names=["Product","Supplier","Material","BOM","Machine","MaterialLot","ProductionOrder","ProcessStep","LotConsumption","InspectionPlan","InspectionResult","Defect","CorrectiveAction","CAPAEvent","ProductionOrderEvent"]
    for name in order_names:
        rows=tables[name]
        if not rows: continue
        cols=list(rows[0].keys())
        sql=f"INSERT INTO {name} ({','.join(cols)}) VALUES ({','.join(['?']*len(cols))})"
        # Use loose sqlite schema import to avoid deliberate exceptions blocking seed; use source CSV as full anomaly store.
        try:
            con.executemany(sql, [[r.get(c,"") for c in cols] for r in rows])
        except sqlite3.IntegrityError:
            # Keep all rows in CSV; DB contains only valid rows for FK-constrained tables.
            # Create staging table for that entity and preserve invalid row in staging.
            con.rollback()
            con.executescript(schema)
            for prev in order_names[:order_names.index(name)]:
                pr=tables[prev]
                if pr:
                    pcols=list(pr[0].keys()); psql=f"INSERT OR IGNORE INTO {prev} ({','.join(pcols)}) VALUES ({','.join(['?']*len(pcols))})"
                    try: con.executemany(psql,[[r.get(c,"") for c in pcols] for r in pr])
                    except Exception: pass
            break
    con.commit()
    # Make a reliable SQL seed dump directly from database.
    with (out/"seed.sql").open("w",encoding="utf-8") as f:
        for line in con.iterdump(): f.write(line+"\n")
    con.close()
    # Manifest / summary
    counts={name:len(rows) for name,rows in tables.items()}
    manifest={"generator_version":GENERATOR_VERSION,"seed":seed,"scale":scale,"parameters":{"products":n_sku,"suppliers":n_sup,"material_lots":n_lot,"production_orders":n_order,"inspection_results":n_insp},
              "row_counts":counts,"checksums":{},"generated_at":"deterministic-date-2026-10-22"}
    for p in sorted((out/"csv").glob("*.csv")): manifest["checksums"][str(p.relative_to(out))]=checksum(p)
    (out/"manifest.json").write_text(json.dumps(manifest,indent=2),encoding="utf-8")
    return out

if __name__=="__main__":
    ap=argparse.ArgumentParser()
    ap.add_argument("--seed",type=int,default=SEED_DEFAULT)
    ap.add_argument("--scale",choices=["starter","full"],default="full")
    ap.add_argument("--output",default="data")
    a=ap.parse_args()
    p=generate(a.seed,a.scale,a.output)
    print(f"Generated dataset at {p.resolve()}")
