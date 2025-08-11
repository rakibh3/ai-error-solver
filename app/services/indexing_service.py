import os
import shutil
import hashlib
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
    
    # Initialize or load the ChromaDB vector store
    embeddings = GoogleGenerativeAIEmbeddings(model="models/embedding-001", google_api_key=config.GEMINI_API_KEY)
    if os.path.exists(vector_store_path):
        db = Chroma(persist_directory=vector_store_path, embedding_function=embeddings)
    else:
        db = None # Will be initialized later if no existing DB

    current_files_data = {}
    for root, _, files in os.walk(project_path):
        for file in files:
            if file.endswith(('.py', '.js', '.ts', '.tsx', '.html', '.css', '.md', 'json')):
                filepath = os.path.join(root, file)
                try:
                    with open(filepath, 'rb') as f: # Read as binary for hashing
                        file_content = f.read()
                        file_hash = hashlib.md5(file_content).hexdigest()
                    current_files_data[filepath] = {'content': file_content.decode('utf-8', errors='ignore'), 'hash': file_hash}
                except Exception as e:
                    print(f"Error reading file {filepath}: {e}")
                    continue

    if not current_files_data:
        return {"error": "No code files found in the project"}

    # Initialize text splitter and embeddings
    text_splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=200)
    embeddings = GoogleGenerativeAIEmbeddings(model="models/embedding-001", google_api_key=config.GEMINI_API_KEY)

    # Get existing files from ChromaDB
    existing_files_in_db = {}
    if db:
        # Fetch all documents from the existing ChromaDB to get their metadata
        # This might be inefficient for very large dbs, but necessary for incremental updates
        # ChromaDB's get() method with no parameters retrieves all documents
        all_docs_in_db = db.get(include=['metadatas'])
        for i, metadata in enumerate(all_docs_in_db['metadatas']):
            filepath = metadata.get('filepath')
            file_hash = metadata.get('file_hash')
            if filepath and file_hash:
                existing_files_in_db[filepath] = file_hash

    files_to_add_or_update = []
    files_to_delete_from_db = []
    
    # Identify new, modified, and deleted files
    for filepath, data in current_files_data.items():
        if filepath not in existing_files_in_db or existing_files_in_db[filepath] != data['hash']:
            # File is new or modified
            files_to_add_or_update.append(filepath)
    
    for filepath in existing_files_in_db:
        if filepath not in current_files_data:
            # File has been deleted
            files_to_delete_from_db.append(filepath)

    # Process files to delete
    if files_to_delete_from_db and db:
        # ChromaDB doesn't have a direct delete by filepath.
        # We need to get the IDs of documents associated with these filepaths and delete them.
        # This is a placeholder for actual deletion logic.
        # For now, we'll just print a message.
        print(f"Files to delete from DB (not yet implemented): {files_to_delete_from_db}")
        # A more robust solution would involve querying ChromaDB for documents with these filepaths
        # and then deleting by ID. This might require a custom filter or iterating through all documents.
        # For now, we'll skip actual deletion to avoid breaking the current setup.

    # Process files to add or update
    if files_to_add_or_update:
        documents_to_add = []
        for filepath in files_to_add_or_update:
            content = current_files_data[filepath]['content']
            file_hash = current_files_data[filepath]['hash']
            
            # Create documents with metadata for chunking
            doc = text_splitter.create_documents([content])
            for d in doc:
                d.metadata['filepath'] = filepath
                d.metadata['file_hash'] = file_hash
            documents_to_add.extend(doc)

        if documents_to_add:
            if db is None:
                # First time indexing, create the DB
                db = Chroma.from_documents(documents_to_add, embeddings, persist_directory=vector_store_path)
            else:
                # Add new/updated documents to existing DB
                db.add_documents(documents_to_add)
            db.persist()
            print(f"Added/Updated {len(documents_to_add)} chunks for {len(files_to_add_or_update)} files.")
    else:
        print("No files to add or update.")

    if db is None:
        return {"error": "No code files found in the project to index."}

    return {"status": "success", "message": f"Project {project_name}/{branch_name} indexed successfully."}
