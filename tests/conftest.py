import os
import sys

# Ensure contracts package is importable (it's a workspace member)
# The contracts package is at packages/contracts/src
contracts_src = os.path.join(os.path.dirname(__file__), "..", "packages", "contracts", "src")
sys.path.insert(0, os.path.abspath(contracts_src))

# Import real contracts package
import contracts

# Make it available as 'contracts' module for the backend
sys.modules["contracts"] = contracts

os.environ.setdefault("DATABASE_URL", "postgresql://test:test@localhost:5433/telemetry_test")