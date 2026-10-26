import csv, json, os, tempfile, unittest
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from generate_data import generate
from validate_data import validate

class ProjectTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory()
        self.path=Path(self.tmp.name)/"data"
        generate(20261022,"starter",str(self.path))
    def tearDown(self): self.tmp.cleanup()
    def read(self,name):
        with (self.path/"csv"/f"{name}.csv").open(newline="",encoding="utf-8") as f: return list(csv.DictReader(f))
    def test_starter_volume(self):
        self.assertEqual(len(self.read("Product")),20)
        self.assertEqual(len(self.read("Supplier")),8)
        self.assertEqual(len(self.read("MaterialLot")),100)
        self.assertEqual(len(self.read("ProductionOrder")),150)
        self.assertEqual(len(self.read("InspectionResult")),600)
    def test_required_edge_cases_labelled(self):
        truth=self.read_ground_truth()
        kinds={x["issue_type"] for x in truth}
        self.assertTrue({"DEFECT_NONEXISTENT_LOT","BOM_MATERIAL_NOT_CONSUMED","CAPA_CLOSED_BEFORE_VERIFICATION","DEFECT_COUNT_EXCEEDS_INSPECTED","TRACEABILITY_CHAIN_BREAK"}.issubset(kinds))
    def read_ground_truth(self):
        with (self.path/"ground_truth.csv").open(newline="",encoding="utf-8") as f: return list(csv.DictReader(f))
    def test_validation_report_created(self):
        report=validate(self.path)
        self.assertTrue((self.path/"validation_summary.json").exists())
        self.assertGreaterEqual(report["ground_truth_cases"],5)
    def test_fixed_seed_reproducibility(self):
        p2=Path(self.tmp.name)/"data2"
        generate(20261022,"starter",str(p2))
        import hashlib
        for f in (self.path/"csv").glob("*.csv"):
            h=lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
            self.assertEqual(h(f),h(p2/"csv"/f.name))
if __name__=="__main__": unittest.main()
