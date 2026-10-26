import csv,json,os
from pathlib import Path
import streamlit as st

st.set_page_config(page_title="Defect Traceability & CAPA",page_icon="🏭",layout="wide")
st.title("🏭 Manufacturing Defect Traceability & CAPA")
st.caption("Synthetic manufacturing quality data • upstream/downstream traceability • exception-aware controls")
DATA=Path(os.environ.get("TRACE_DATA_DIR","data"))
CSV=DATA/"csv"
def load(name):
    p=CSV/f"{name}.csv"
    if not p.exists(): return []
    with p.open(newline="",encoding="utf-8") as f: return list(csv.DictReader(f))
def table(name): return load(name)
products=table("Product"); suppliers=table("Supplier"); lots=table("MaterialLot"); orders=table("ProductionOrder")
steps=table("ProcessStep"); consumptions=table("LotConsumption"); inspections=table("InspectionResult")
defects=table("Defect"); capas=table("CorrectiveAction")
def load_root_csv(name):
    p=DATA/f"{name}.csv"
    if not p.exists(): return []
    with p.open(newline="",encoding="utf-8") as f: return list(csv.DictReader(f))
truth=load_root_csv("ground_truth")
if not products:
    st.warning("No generated data found. Run `python generate_data.py --scale starter --output data` first.")
    st.stop()
defect_units=sum(int(x["defective_qty"]) for x in inspections if x["defective_qty"].lstrip("-").isdigit())
inspected_units=sum(int(x["inspected_qty"]) for x in inspections if x["inspected_qty"].isdigit())
c1,c2,c3,c4=st.columns(4)
c1.metric("Inspection results",f"{len(inspections):,}")
c2.metric("Defect records",f"{len(defects):,}")
c3.metric("Defective-unit rate",f"{(defect_units/max(inspected_units,1))*100:.2f}%")
c4.metric("CAPA cases",f"{len(capas):,}")
st.divider()
tab1,tab2,tab3=st.tabs(["Defect traceability","Quality overview","Exception register"])
with tab1:
    ids=[x["defect_id"] for x in defects]
    selected=st.selectbox("Choose a defect ID",ids)
    d=next((x for x in defects if x["defect_id"]==selected),None)
    if d:
        st.subheader(f"{d['defect_id']} · {d['defect_code']}")
        if d.get("issue_type"): st.error(f"Flagged exception: {d['issue_type']}")
        insp=next((x for x in inspections if x["inspection_result_id"]==d["inspection_result_id"]),{})
        order=next((x for x in orders if x["production_order_id"]==d["production_order_id"]),{})
        prod=next((x for x in products if x["product_id"]==order.get("product_id")),{})
        step=next((x for x in steps if x["process_step_id"]==d["process_step_id"]),{})
        st.write("**Inspection result**",insp or "Missing inspection result")
        st.write("**Production order / product**",{"production_order":order,"product":prod})
        st.write("**Process step / machine**",step or "Broken process-step link")
        cons=[x for x in consumptions if x["production_order_id"]==d["production_order_id"]]
        lotids={x["material_lot_id"] for x in cons}
        trace_lots=[x for x in lots if x["material_lot_id"] in lotids]
        st.write("**Consumed material lots**",trace_lots or "No matching consumed lots")
        supids={x["supplier_id"] for x in trace_lots}
        st.write("**Suppliers**",[x for x in suppliers if x["supplier_id"] in supids])
        st.write("**Corrective actions**",[x for x in capas if x["defect_id"]==d["defect_id"]] or "No CAPA linked")
with tab2:
    a,b,c=st.columns(3)
    a.metric("Products",len(products)); b.metric("Suppliers",len(suppliers)); c.metric("Material lots",len(lots))
    st.subheader("Defects by severity")
    sev={}
    for x in defects: sev[x["severity"]]=sev.get(x["severity"],0)+1
    st.bar_chart(sev)
    st.subheader("CAPA status")
    status={}
    for x in capas: status[x["capa_status"]]=status.get(x["capa_status"],0)+1
    st.bar_chart(status)
    st.subheader("Supplier lot risk")
    risk={}
    for x in lots: risk[x["incoming_status"]]=risk.get(x["incoming_status"],0)+1
    st.bar_chart(risk)
with tab3:
    st.write("Ground-truth labels are stored separately from the input tables and are for evaluation only.")
    st.dataframe(truth,use_container_width=True)
    st.caption("Do not use ground_truth labels as model input features.")
