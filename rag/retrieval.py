import os
from dotenv import load_dotenv

# Vector Store and Embeddings
from langchain_chroma import Chroma
from langchain_openai import AzureOpenAIEmbeddings

load_dotenv()

# Deterministic paths based on the project root
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# Option A: Always use the project-relative default (No os.getenv needed)
DB_DIR = os.path.join(BASE_DIR, 'rag', 'vector_store')

# Priority 4 Fix: Renamed function to reflect broader operational knowledge
def retrieve_operational_knowledge(query: str, k: int = 3) -> list:
    """
    Queries the Chroma vector database for operational procedures 
    and returns structured document chunks with source metadata.
    """
    print(f"🔎 Searching the knowledge base for: '{query}'")
    
    # Priority 2 Fix: INITIALIZE THE AZURE EMBEDDING MODEL
    # This must perfectly match the model used in ingestion.py to ensure vector alignment
    embeddings = AzureOpenAIEmbeddings(
        azure_endpoint=os.getenv("AZURE_OPENAI_ENDPOINT"),
        api_key=os.getenv("AZURE_OPENAI_API_KEY"),
        openai_api_version=os.getenv("AZURE_OPENAI_API_VERSION", "2023-05-15"),
        azure_deployment=os.getenv("AZURE_OPENAI_DEPLOYMENT_NAME")
    )
    
    # 2. LOAD THE DATABASE
    try:
        vector_store = Chroma(
            persist_directory=DB_DIR, 
            embedding_function=embeddings
        )
    except Exception as e:
        print(f"Error loading database: {e}")
        return []
    
    # 3. PERFORM SIMILARITY SEARCH
    results = vector_store.similarity_search(query, k=k)
    
    if not results:
        print("No relevant company policies found for this query.")
        return []
    
    # Priority 5 Fix: FORMAT THE CONTEXT AS STRUCTURED METADATA
    # Returns a list of dictionaries so the Agent knows which file it is quoting
    structured_results = []
    for doc in results:
        structured_results.append({
            "content": doc.page_content,
            "source": doc.metadata.get("source", "Unknown file")
        })
        
    return structured_results

if __name__ == "__main__":
    # Priority 6 Fix: Updated Test execution for the new function name and data structure
    test_query = "What should we do when a shipment is at high risk of delay?"
    answers = retrieve_operational_knowledge(test_query)
    
    print("\n=== RETRIEVED KNOWLEDGE ===\n")
    for i, ans in enumerate(answers, 1):
        print(f"--- Result {i} ---")
        print(f"Source: {ans['source']}")
        print(f"Content: {ans['content']}\n")