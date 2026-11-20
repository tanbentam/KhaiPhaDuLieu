"""QA nhat quan so lieu: python scripts/run_qa.py  (exit 1 neu co FAIL)."""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.qa.consistency import claim_register, run_all  # noqa: E402
from src.visualization.build_m4 import SOURCES  # noqa: E402

if __name__ == "__main__":
    res = run_all(ROOT, required_artifacts=list(SOURCES) + ["outputs/m4_artifact_manifest.csv"])
    cl = claim_register(ROOT)
    res.to_csv(ROOT / "outputs" / "metrics" / "qa_checks_m4.csv", index=False)
    cl.to_csv(ROOT / "outputs" / "metrics" / "qa_claim_register.csv", index=False)
    print(res[["check_id", "scope", "status", "detail"]].to_string(index=False, max_colwidth=110))
    print("\n== Claim register (van ban M3 vs CSV) ==")
    print(cl[["claim_id", "verdict", "claim", "observed"]].to_string(index=False, max_colwidth=100))
    print("\nTong:", res.status.value_counts().to_dict(), "| claims:", cl.verdict.value_counts().to_dict())
    sys.exit(1 if (res.status == "FAIL").any() else 0)
