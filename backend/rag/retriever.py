# backend/rag/retriever.py
import os
import logging
from typing import List, Tuple

# Import necessary libraries (install them first!)
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_community.document_loaders import PyPDFLoader # Or use your preferred PDF loader
from langchain_community.vectorstores import FAISS
from langchain_community.embeddings import HuggingFaceEmbeddings # Using Sentence Transformers

from backend.core.config import settings # Import settings

logger = logging.getLogger(__name__)

# --- Helper Functions ---

def _get_vector_store_path(paper_id: str) -> str:
    """Generates the path to save/load the vector store for a paper."""
    base_path = settings.VECTOR_STORE_BASE_PATH
    # Use paper_id (e.g., 'Paper1', 'Paper2') as the filename prefix
    safe_paper_id = "".join(c if c.isalnum() else "_" for c in paper_id) # Sanitize ID for filename
    return os.path.join(base_path, f"{safe_paper_id}_faiss_index")

# --- Core RAG Functions ---

def extract_text_from_pdf(pdf_path: str) -> str:
    """Extracts text content from a given PDF file path."""
    logger.info(f"Extracting text from PDF: {pdf_path}")
    if not os.path.exists(pdf_path):
        logger.error(f"PDF file not found at path: {pdf_path}")
        raise FileNotFoundError(f"PDF file not found: {pdf_path}")
    try:
        # Using PyPDFLoader, requires pypdf installed
        loader = PyPDFLoader(pdf_path)
        # pages = loader.load_and_split() # This also splits, maybe just load?
        documents = loader.load() # Load all pages as documents
        full_text = "\n".join([doc.page_content for doc in documents])
        logger.info(f"Successfully extracted text (length: {len(full_text)}) from {pdf_path}")
        return full_text
    except Exception as e:
        logger.error(f"Failed to extract text from {pdf_path}: {e}", exc_info=True)
        raise RuntimeError(f"Failed to process PDF {pdf_path}") from e


def chunk_text(text: str, chunk_size: int = 1000, chunk_overlap: int = 150) -> List[str]:
    """Splits text into manageable chunks."""
    logger.info(f"Chunking text (length: {len(text)})...")
    try:
        text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
            length_function=len,
        )
        chunks = text_splitter.split_text(text)
        logger.info(f"Split text into {len(chunks)} chunks.")
        return chunks
    except Exception as e:
        logger.error(f"Failed to chunk text: {e}", exc_info=True)
        raise RuntimeError("Text chunking failed") from e


def create_and_save_vector_store(paper_id: str, chunks: List[str]):
    """Creates embeddings, builds a FAISS vector store, and saves it."""
    store_path = _get_vector_store_path(paper_id)
    logger.info(f"Creating vector store for paper '{paper_id}' at {store_path}...")

    if not chunks:
        logger.error(f"Cannot create vector store for '{paper_id}': No text chunks provided.")
        raise ValueError("No text chunks available to create vector store.")

    try:
        # Initialize embeddings model
        logger.info(f"Loading embedding model: {settings.EMBEDDING_MODEL_NAME}")
        # Use CUDA if available and configured, otherwise CPU
        model_kwargs = {'device': 'cuda'} if os.environ.get("USE_CUDA") else {'device': 'cpu'}
        encode_kwargs = {'normalize_embeddings': False}
        embeddings = HuggingFaceEmbeddings(
            model_name=settings.EMBEDDING_MODEL_NAME,
            model_kwargs=model_kwargs,
            encode_kwargs=encode_kwargs
        )
        logger.info("Embedding model loaded.")

        # Create FAISS index from chunks
        logger.info(f"Creating FAISS index from {len(chunks)} chunks...")
        vector_store = FAISS.from_texts(texts=chunks, embedding=embeddings)
        logger.info("FAISS index created.")

        # Ensure the directory exists
        os.makedirs(os.path.dirname(store_path), exist_ok=True)

        # Save the index locally
        vector_store.save_local(store_path)
        logger.info(f"Vector store for paper '{paper_id}' saved successfully to {store_path}.")

    except Exception as e:
        logger.error(f"Failed to create/save vector store for paper '{paper_id}': {e}", exc_info=True)
        raise RuntimeError(f"Vector store creation/saving failed for {paper_id}") from e


def load_vector_store(paper_id: str):
    """Loads an existing FAISS vector store from the local path."""
    store_path = _get_vector_store_path(paper_id)
    logger.info(f"Attempting to load vector store for paper '{paper_id}' from {store_path}...")

    if not os.path.exists(store_path):
        logger.error(f"Vector store not found for paper '{paper_id}' at path: {store_path}")
        raise FileNotFoundError(f"Vector store not found for paper {paper_id}. Please process the PDF first.")

    try:
        # Initialize the SAME embeddings model used for creation
        logger.info(f"Loading embedding model: {settings.EMBEDDING_MODEL_NAME}")
        model_kwargs = {'device': 'cuda'} if os.environ.get("USE_CUDA") else {'device': 'cpu'}
        encode_kwargs = {'normalize_embeddings': False}
        embeddings = HuggingFaceEmbeddings(
            model_name=settings.EMBEDDING_MODEL_NAME,
            model_kwargs=model_kwargs,
            encode_kwargs=encode_kwargs
        )
        logger.info("Embedding model loaded.")

        # Load the FAISS index
        vector_store = FAISS.load_local(store_path, embeddings, allow_dangerous_deserialization=True) # Need allow_dangerous_deserialization for FAISS
        logger.info(f"Vector store for paper '{paper_id}' loaded successfully.")
        return vector_store

    except Exception as e:
        logger.error(f"Failed to load vector store for paper '{paper_id}': {e}", exc_info=True)
        raise RuntimeError(f"Vector store loading failed for {paper_id}") from e


def retrieve_relevant_chunks(query: str, vector_store, k: int = 3) -> List[str]:
    """Retrieves the top-k most relevant text chunks for a query."""
    logger.info(f"Retrieving top-{k} relevant chunks for query: '{query[:50]}...'")
    try:
        # Perform similarity search
        results = vector_store.similarity_search(query, k=k)
        # Extract page content from Document objects
        retrieved_chunks = [doc.page_content for doc in results]
        logger.info(f"Retrieved {len(retrieved_chunks)} chunks.")
        return retrieved_chunks
    except Exception as e:
        logger.error(f"Failed to retrieve chunks for query '{query[:50]}...': {e}", exc_info=True)
        raise RuntimeError("Chunk retrieval failed") from e

# --- Main Processing Function (Example Usage) ---
async def process_and_index_paper(paper_id: str, pdf_path: str):
    """Coordinates the extraction, chunking, and indexing for a paper."""
    logger.info(f"Starting processing pipeline for paper ID '{paper_id}' from path '{pdf_path}'")
    try:
        # Check if index already exists to avoid reprocessing
        store_path = _get_vector_store_path(paper_id)
        if os.path.exists(store_path):
             logger.warning(f"Vector store for paper '{paper_id}' already exists at '{store_path}'. Skipping processing.")
             # Optionally add force=True parameter to override
             return

        # 1. Extract Text
        text = extract_text_from_pdf(pdf_path)
        if not text or len(text.strip()) < 50: # Add minimum length check
             logger.error(f"Insufficient text extracted from PDF for paper '{paper_id}'.")
             raise ValueError(f"Could not extract sufficient text from {pdf_path}")

        # 2. Chunk Text
        chunks = chunk_text(text)
        if not chunks:
             logger.error(f"Text chunking resulted in zero chunks for paper '{paper_id}'.")
             raise ValueError(f"Text chunking failed for {pdf_path}")

        # 3. Create and Save Vector Store
        create_and_save_vector_store(paper_id, chunks)

        logger.info(f"Successfully processed and indexed paper ID '{paper_id}'.")

    except (FileNotFoundError, ValueError, RuntimeError) as e:
         logger.error(f"Processing pipeline failed for paper '{paper_id}': {e}", exc_info=True)
         # Re-raise or handle as needed in the calling function
         raise
    except Exception as e:
         logger.error(f"Unexpected error in processing pipeline for paper '{paper_id}': {e}", exc_info=True)
         raise RuntimeError(f"Unexpected error processing {paper_id}") from e

# --- Example how this might be called ---
# async def some_setup_function(assigned_paper_id: str):
#    # Map paper ID to actual PDF file path
#    pdf_file_map = {
#        "Paper1": "./static/pdfs/chapter1.pdf", # Example mapping
#        "Paper2": "./static/pdfs/chapter2.pdf", # Example mapping
#    }
#    pdf_path = pdf_file_map.get(assigned_paper_id)
#    if pdf_path:
#        await process_and_index_paper(assigned_paper_id, pdf_path)
#    else:
#        logger.error(f"No PDF path configured for paper ID: {assigned_paper_id}")