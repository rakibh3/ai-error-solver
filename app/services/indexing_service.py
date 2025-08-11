import os
import shutil
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_community.vectorstores import Chroma
from langchain_voyageai import VoyageAIEmbeddings
from app.core import config

def index_instructor_project(project_name: str, branch_name: str):
    # Construct the path to the instructor's project directory
    project_path = os.path.join("instructor_projects", project_name, branch_name)

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
            # Simple check to avoid non-code files, can be improved
            if file.endswith(('.py', '.js', 'jsx' ,'.ts', '.tsx', '.html', '.css', '.md', 'json')):
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

    # Embed the chunks using Voyage AI's text embedding model
    embeddings = VoyageAIEmbeddings(
        model="voyage-code-3",
        voyage_api_key=config.VOYAGE_API_KEY
    )
    
    # Store the embeddings in ChromaDB
    db = Chroma.from_documents(texts, embeddings, persist_directory=vector_store_path)
    db.persist()

    return {"status": "success", "message": f"Project {project_name}/{branch_name} indexed successfully."}

def index_project_branches(project_name: str):
    project_dir = os.path.join("instructor_projects", project_name)
    if not os.path.isdir(project_dir):
        return {"error": "Project not found"}

    branches = [d for d in os.listdir(project_dir) if os.path.isdir(os.path.join(project_dir, d))]
    if not branches:
        return {"error": "No branches found for the project"}

    indexed_branches = []
    errors = []

    for branch_name in branches:
        result = index_instructor_project(project_name, branch_name)
        if "error" in result:
            errors.append(f"Branch {branch_name}: {result['error']}")
        else:
            indexed_branches.append(branch_name)

    if errors:
        return {"status": "partial_success", "indexed_branches": indexed_branches, "errors": errors}

    return {"status": "success", "message": f"All branches of project {project_name} indexed successfully."}
