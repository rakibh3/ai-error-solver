import os
from langchain_qdrant import QdrantVectorStore
from langchain_voyageai import VoyageAIEmbeddings
from typing import Optional
from app.core import config
from app.utils.qdrant import get_qdrant_client, get_collection_name
import google.generativeai as genai

def analyze_code(
    student_code_context: str,
    instructor_project_name: str,
    instructor_branch_name: str,
    error_message: Optional[str] = None
):
    # Initialize Qdrant client and get collection name
    client = get_qdrant_client()
    collection_name = get_collection_name(instructor_project_name, instructor_branch_name)
    
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
            embedding=embeddings,
            collection_name=collection_name,
            url=f"http://{config.QDRANT_HOST}:{config.QDRANT_PORT}",
        )
        
        # Perform similarity search to find relevant code
        relevant_docs = vector_store.similarity_search(
            student_code_context, 
            k=5  # Get top 5 similar chunks
        )
        
        # Format the retrieved context
        instructor_context = "\n\n".join([
            f"File: {doc.metadata.get('file_path', 'unknown')}\n{doc.page_content}"
            for doc in relevant_docs
        ])
        
        # Create the analysis prompt
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

       
        
        ### Task
        1. Identify the exact mistake in the student’s code.
        2. Provide a clear step-by-step fix with:
        - File name
        - Line number
        - Exact code replacement

        ### Response Rules
        - Output **only** valid JSON (no extra text).
        - Keep the explanation **concise and to the point** (1–2 short sentences).
        - Remove Markdown, just get JSON
        - Use this schema:

        {{
            "error_explanation": "Briefly state the root cause.",
            "fix_instructions": {{
                "file": "path/to/file.ext",
                "line": 42,
                "change": {{
                "old_code": "incorrect_code_here()",
                "new_code": "correct_code_here()"
                }}
            }}
        }}

        """

        # Generate analysis using Gemini
        model = genai.GenerativeModel('gemini-2.5-flash')
        response = model.generate_content(prompt)
        
        return {
            "analysis": response.text,
        }
        
    except Exception as e:
        return {"error": f"Failed to analyze code: {str(e)}"}