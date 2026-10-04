import os
from dotenv import load_dotenv

# Import specific loaders for narrative file types (No CSV or Excel)
from langchain_community.document_loaders import (
    TextLoader, 
    PyPDFLoader, 
    Docx2txtLoader
)
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_openai import AzureOpenAIEmbeddings
from langchain_chroma import Chroma

load_dotenv()
# Deterministic paths based on the project root
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DOCS_DIR = os.path.join(BASE_DIR, 'rag', 'documents')

# Option A: Always use the project-relative default (No os.getenv needed)
DB_DIR = os.path.join(BASE_DIR, 'rag', 'vector_store')

# The Router: Strictly narrative formats for optimal RAG chunking
LOADER_MAPPING = {
    ".md": TextLoader,
    ".txt": TextLoader,
    ".pdf": PyPDFLoader,
    ".docx": Docx2txtLoader,
}

def ingest_documents():
    """
    Scans the documents directory, automatically detects narrative file types,
    extracts the text, chunks it, and saves the embeddings to ChromaDB.
    """
    print(f"Scanning directory for documents: {DOCS_DIR}")
    documents = []
    
    # Manually loop through all files in the directory
    for root, _, files in os.walk(DOCS_DIR):
        for file in files:
            # Ignore hidden files like .gitkeep
            if file.startswith("."):
                continue
                
            file_ext = os.path.splitext(file)[1].lower()
            file_path = os.path.join(root, file)
            
            # If the file type is in our mapping, load it
            if file_ext in LOADER_MAPPING:
                print(f"Loading {file}...")
                loader_class = LOADER_MAPPING[file_ext]
                loader = loader_class(file_path)
                documents.extend(loader.load())
            else:
                print(f"Skipping {file}: Unsupported format for narrative RAG.")
                
    if not documents:
        print("No valid documents found! Add .pdf, .docx, .txt, or .md files.")
        return

    # Chunk the compiled text from all supported files
    text_splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=200)
    chunks = text_splitter.split_documents(documents)
    
    print(f"Successfully extracted and split text into {len(chunks)} chunks.")

    # Priority 2 Fix: Generate Azure OpenAI embeddings and save to database
    print("Generating Azure OpenAI embeddings and saving to ChromaDB...")
    embeddings = AzureOpenAIEmbeddings(
        azure_endpoint=os.getenv("AZURE_OPENAI_ENDPOINT"),
        api_key=os.getenv("AZURE_OPENAI_API_KEY"),
        openai_api_version=os.getenv("AZURE_OPENAI_API_VERSION", "2023-05-15"),
        azure_deployment=os.getenv("AZURE_OPENAI_DEPLOYMENT_NAME")
    )
    
    Chroma.from_documents(documents=chunks, embedding=embeddings, persist_directory=DB_DIR)
    
    print(f"Success! Vector database saved at: {DB_DIR}")

if __name__ == "__main__":
    ingest_documents()