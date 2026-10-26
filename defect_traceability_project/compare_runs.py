import hashlib,sys,csv,json
from pathlib import Path
def sha(p): return hashlib.sha256(p.read_bytes()).hexdigest()
def main(a,b):
    a,b=Path(a),Path(b); failures=[]
    for p in sorted((a/"csv").glob("*.csv")):
        q=b/"csv"/p.name
        if not q.exists(): failures.append(f"Missing {q}"); continue
        if sha(p)!=sha(q): failures.append(f"Checksum mismatch: {p.name}")
        with p.open(encoding="utf-8",newline="") as f: n1=sum(1 for _ in csv.DictReader(f))
        with q.open(encoding="utf-8",newline="") as f: n2=sum(1 for _ in csv.DictReader(f))
        if n1!=n2: failures.append(f"Row count mismatch: {p.name} {n1}!={n2}")
    print(json.dumps({"reproducible":not failures,"failures":failures},indent=2))
    return 0 if not failures else 1
if __name__=="__main__":
    if len(sys.argv)!=3: print("Usage: python compare_runs.py run_a run_b"); raise SystemExit(2)
    raise SystemExit(main(sys.argv[1],sys.argv[2]))
