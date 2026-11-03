import sys
from pathlib import Path

# The prototype dashboard is not a workspace package; its modules import each other
# as `dashboard.src.prototype...`, so the repo root has to be importable.
REPO_ROOT = Path(__file__).resolve().parents[3]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))
