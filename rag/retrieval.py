import os
from dotenv import load_dotenv

# Vector Store and Embeddings
from langchain_chroma import Chroma
from langchain_openai import OpenAIEmbeddings

load_dotenv()

# Point to the existing database directory created by ingestion.py
DB_DIR = os.getenv("VECTOR_STORE_PATH", "./rag/vector_store")

def get_company_policy(query: str) -> str:
    """
    Queries the Chroma vector database for internal company policies and 
    returns the most relevant document chunks formatted as a single string.
    """
    print(f"🔎 Searching the knowledge base for: '{query}'")
    
    # 1. INITIALIZE THE EMBEDDING MODEL
    # This must perfectly match the model used in ingestion.py to ensure vector alignment
    embeddings = OpenAIEmbeddings()
    
    # 2. LOAD THE DATABASE
    # Connect to the persisted Chroma vector store on the local disk
    try:
        vector_store = Chroma(
            persist_directory=DB_DIR, 
            embedding_function=embeddings
        )
    except Exception as e:
        return f"Error loading database. Ensure ingestion.py has been executed. Details: {e}"
    
    # 3. PERFORM SIMILARITY SEARCH
    # Retrieve the top 3 document chunks that are mathematically closest to the user's query
    results = vector_store.similarity_search(query, k=3)
    
    if not results:
        return "No relevant company policies found for this query."
    
    # 4. FORMAT THE CONTEXT
    # Join the retrieved chunks with a visual separator so the downstream Agent can easily parse them
    formatted_context = "\n\n---\n\n".join([doc.page_content for doc in results])
    
    return formatted_context

if __name__ == "__main__":
    # Test execution for direct terminal runs
    test_query = "What happens if a refrigerated truck gets too warm?"
    answer = get_company_policy(test_query)
    print("\n=== RETRIEVED POLICY ===\n")
    print(answer)