import os
from langchain_qdrant import QdrantVectorStore
from langchain_voyageai import VoyageAIEmbeddings
from qdrant_client import QdrantClient
from typing import Optional
from app.core import config
import google.generativeai as genai

def _get_collection_name(project_name: str, branch_name: str) -> str:
    """Generate a valid collection name for Qdrant"""
    safe_name = f"instructor_project_{project_name}_{branch_name}"
    safe_name = "".join(c if c.isalnum() or c == '_' else '_' for c in safe_name)
    return safe_name.lower()

def _get_qdrant_client() -> QdrantClient:
    """Initialize Qdrant client"""
    return QdrantClient(
        host=config.QDRANT_HOST,
        port=config.QDRANT_PORT,
        api_key=config.QDRANT_API_KEY,
    )

def analyze_code(
    student_code_context: str,
    instructor_project_name: str,
    instructor_branch_name: str,
    error_message: Optional[str] = None
):
    # Initialize Qdrant client and get collection name
    client = _get_qdrant_client()
    collection_name = _get_collection_name(instructor_project_name, instructor_branch_name)
    
    try:
        collections = client.get_collections()
        collection_exists = any(col.name == collection_name for col in collections.collections)
        if not collection_exists:
            return {"error": "Instructor project embedding not found"}
    except Exception as e:
        return {"error": f"Failed to connect to Qdrant: {str(e)}"}

    embeddings = VoyageAIEmbeddings(
        model="voyage-code-3",
        voyage_api_key=config.VOYAGE_API_KEY
    )
    
    try:
        vector_store = QdrantVectorStore.from_existing_collection(
            collection_name=collection_name,
            embedding=embeddings,
            url=f"http://{config.QDRANT_HOST}:{config.QDRANT_PORT}"
        )

        # The query for retrieval is the error message if it exists, otherwise the student code.
        # This is the core of the error-driven approach.
        retrieval_query = error_message if error_message else student_code_context
        
        retriever = vector_store.as_retriever()
        relevant_docs = retriever.invoke(retrieval_query)

        prompt = f"""
        You are an expert teaching assistant.
        A student is having trouble with their code.
        
        The student is encountering the following error message:
        ---
        {error_message}
        ---

        Here is the full context of the student's code:
        ---
        {student_code_context}
        ---
        
        Based on the error, here is some relevant code from the instructor's solution:
        --- 
        {[doc.page_content for doc in relevant_docs]}
        ---

        Your task is to identify the error in the student's code and provide a clear, step-by-step instruction for the learner on how to fix it.
        The instruction must include the specific file, line number, and the exact code to be changed.
        Provide the solution in a structured format.
        """

        model = genai.GenerativeModel('gemini-2.5-flash')
        response = model.generate_content(prompt)

        return {"solution": response.text}
    
    except Exception as e:
        return {"error": f"Failed to analyze code: {str(e)}"}