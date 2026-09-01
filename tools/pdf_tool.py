from pathlib import Path
import sys

# Allow this file to work both when imported by LifeLens and when run/debugged directly.
PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

# Re-export the user-scoped RAG tool defined in rag/retrieve.py.
from rag.retrieve import search_documents

' __all__ = ["search_documents"] '

