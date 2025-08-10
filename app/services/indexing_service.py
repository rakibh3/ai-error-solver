import os
import shutil
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_community.vectorstores import Chroma
from langchain_google_genai import GoogleGenerativeAIEmbeddings
from app.core import config

def index_instructor_project(project_name: str, branch_name: str):
    # Construct the path to the instructor's project directory
    project_path = os.path.join("instructor_projects", project_name, branch_name)
    print(project_path)

    if not os.path.isdir(project_path):
        return {"error": "Instructor project not found"}

    # For simplicity, we'll store the vector database in a directory named after the project and branch
    vector_store_path = os.path.join("vectorstore", "chroma_db", project_name, branch_name)
    
    # Clean up old vector store if it exists
    if os.path.exists(vector_store_path):
        shutil.rmtree(vector_store_path)

    # Scan the directory for files
    filepaths = []
    for root, _, files in os.walk(project_path):
        for file in files:
            print(file)
            # Simple check to avoid non-code files, can be improved
            if file.endswith(('.py', '.js', '.ts', '.tsx', '.html', '.css', '.md', 'json')):
                filepaths.append(os.path.join(root, file))

    if not filepaths:
        return {"error": "No code files found in the project"}

    # Read the content of each file
    documents = []
    for filepath in filepaths:
        with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
            documents.append(f.read())

    # Chunk the code
    text_splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=200)
    texts = text_splitter.create_documents(documents)

    # Embed the chunks using Google's text embedding model
    embeddings = GoogleGenerativeAIEmbeddings(model="models/embedding-001", google_api_key=config.GEMINI_API_KEY)
    
    # Store the embeddings in ChromaDB
    db = Chroma.from_documents(texts, embeddings, persist_directory=vector_store_path)
    db.persist()

    return {"status": "success", "message": f"Project {project_name}/{branch_name} indexed successfully."}
