import os
from langchain_community.vectorstores import Chroma
from langchain_google_genai import GoogleGenerativeAIEmbeddings
import google.generativeai as genai
from app.core import config

from typing import Optional

def analyze_code(student_code: str, instructor_project_name: str, instructor_branch_name: str, error_message: Optional[str] = None):
    # Load the vector store for the instructor's project
    vector_store_path = os.path.join("vectorstore", "chroma_db", instructor_project_name, instructor_branch_name)
    if not os.path.isdir(vector_store_path):
        return {"error": "Instructor project embedding not found"}

    embeddings = GoogleGenerativeAIEmbeddings(model="models/embedding-001", google_api_key=config.GEMINI_API_KEY)
    db = Chroma(persist_directory=vector_store_path, embedding_function=embeddings)

    # Retrieve relevant context from the vector store
    retriever = db.as_retriever()
    relevant_docs = retriever.get_relevant_documents(student_code)

    # Construct a highly specific prompt for the Gemini LLM
    prompt = f"""
    You are an expert teaching assistant.
    A student is having trouble with their code.
    Here is the student's code:
    ---
    {student_code}
    ---
    """
    if error_message:
        prompt += f"""
    The student is encountering the following error message:
    ---
    {error_message}
    ---
    """
    prompt += f"""
    Here is some relevant code from the instructor's solution:
    ---
    {[doc.page_content for doc in relevant_docs]}
    ---
    Your task is to identify the error in the student's code and provide a clear, step-by-step instruction for the learner on how to fix it.
    The instruction must include the specific file, line number, and the exact code to be changed.
    Provide the solution in a structured format.
    """

    # Generate the solution using the Gemini LLM
    model = genai.GenerativeModel('gemini-2.5-flash')
    response = model.generate_content(prompt)

    # Parse the LLM's response to structure the solution data
    # This part will require more sophisticated parsing based on the LLM's output format
    return {"solution": response.text}
