1. Move the retrieval pipeline from rag/query.py into rag/retrieve.py.
2. Delete query.py after updating imports.
3. Import search_documents from tools/pdf_tool.py in agent.py.
4. Replace the placeholder Gmail/Timeline tools with real implementations.
