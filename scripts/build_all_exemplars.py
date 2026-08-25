"""Master orchestrator to build all 57 Multi-School Exemplar Case Packages.

Generates:
- 25 IIMA cases in corpus/exemplars/iima/
- 10 IIMB cases in corpus/exemplars/iimb/
- 10 IIMC cases in corpus/exemplars/iimc/
- 12 ISB cases in corpus/exemplars/isb/
Total = 57 cases across 4 top Indian business schools.
"""

from __future__ import annotations
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from scripts.generate_iima_cases import generate_all_iima_cases
from scripts.generate_iimb_cases import generate_all_iimb_cases
from scripts.generate_iimc_cases import generate_all_iimc_cases
from scripts.generate_isb_cases import generate_all_isb_cases


def main():
    print("==========================================================")
    print("Starting Multi-School Exemplar Corpus Generation (57 Cases)...")
    print("==========================================================")
    generate_all_iima_cases()
    generate_all_iimb_cases()
    generate_all_iimc_cases()
    generate_all_isb_cases()
    print("==========================================================")
    print("All 57 Multi-School Exemplar Case Packages Successfully Built!")
    print("==========================================================")


if __name__ == "__main__":
    main()
