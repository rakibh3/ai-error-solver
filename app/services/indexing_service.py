import os
import shutil
import hashlib
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_qdrant import QdrantVectorStore
from langchain_voyageai import VoyageAIEmbeddings
from qdrant_client import QdrantClient
from qdrant_client.models import Distance, VectorParams, PointStruct
from app.core import config

# Directories and files to ignore during indexing
IGNORE_DIRS = {
    "node_modules", "dist", "build", "out", ".next", ".nuxt", 
    "venv", ".venv", ".env", "__pycache__", ".pytest_cache",
    ".git", ".svn", ".hg", ".vercel", ".netlify", "coverage",
    "public", "static", "assets", ".idea", ".vscode", 
    "logs", "temp", "tmp", ".cache", ".parcel-cache"
}

IGNORE_FILES = {
    "package-lock.json", "yarn.lock", "pnpm-lock.yaml", "composer.lock",
    "Pipfile.lock", "poetry.lock", "components.json", ".DS_Store",
    "Thumbs.db", "desktop.ini", ".gitignore", ".gitattributes",
    "LICENSE", "README.md", "CHANGELOG.md", ".env.example",
    "tsconfig.json", "jsconfig.json", "webpack.config.js",
    "vite.config.js", "next.config.js", "nuxt.config.js"
}

def _should_ignore_path(path: str, base_path: str) -> bool:
    """Check if a path should be ignored during indexing"""
    relative_path = os.path.relpath(path, base_path)
    path_parts = relative_path.split(os.sep)
    
    # Check if any part of the path is in ignore directories
    for part in path_parts:
        if part in IGNORE_DIRS:
            return True
    
    # Check if the file is in ignore files
    filename = os.path.basename(path)
    if filename in IGNORE_FILES:
        return True
    
    # Check for hidden files/directories (starting with .)
    for part in path_parts:
        if part.startswith('.') and part not in {'.', '..'}:
            # Allow specific dotfiles that might contain useful code
            allowed_dotfiles = {'.env.example', '.gitignore', '.dockerignore'}
            if part not in allowed_dotfiles:
                return True
    
    return False

def _get_collection_name(project_name: str, branch_name: str) -> str:
    """Generate a valid collection name for Qdrant"""
    # Replace invalid characters and ensure it starts with a letter
    safe_name = f"instructor_project_{project_name}_{branch_name}"
    safe_name = "".join(c if c.isalnum() or c == '_' else '_' for c in safe_name)
    return safe_name.lower()

def _get_qdrant_client() -> QdrantClient:
    """Initialize Qdrant client"""
    return QdrantClient(
        host=config.QDRANT_HOST,
        port=config.QDRANT_PORT,
        api_key=config.QDRANT_API_KEY
    )

def index_instructor_project(project_name: str, branch_name: str):
    # Construct the path to the instructor's project directory
    project_path = os.path.join("instructor_projects", project_name, branch_name)

    if not os.path.isdir(project_path):
        return {"error": "Instructor project not found"}

    # Initialize Qdrant client
    client = _get_qdrant_client()
    collection_name = _get_collection_name(project_name, branch_name)
    
    # Clean up old collection if it exists
    try:
        client.delete_collection(collection_name)
    except Exception:
        pass  # Collection might not exist

    # Scan the directory for files, filtering out ignored paths
    filepaths = []
    ignored_count = 0
    
    for root, dirs, files in os.walk(project_path):
        # Filter out ignored directories in-place to prevent os.walk from entering them
        dirs[:] = [d for d in dirs if not _should_ignore_path(os.path.join(root, d), project_path)]
        
        for file in files:
            filepath = os.path.join(root, file)
            
            # Skip ignored files
            if _should_ignore_path(filepath, project_path):
                ignored_count += 1
                continue
            
            # Check for code files (expanded list)
            if file.endswith(('.py', '.js', '.jsx', '.ts', '.tsx', '.html', '.css', '.scss', '.sass', 
                             '.less', '.vue', '.svelte', '.php', '.rb', '.go', '.rs', '.java', '.kt', 
                             '.swift', '.cpp', '.c', '.h', '.hpp', '.cs', '.dart', '.scala', '.clj', 
                             '.md', '.json', '.yaml', '.yml', '.xml', '.toml', '.ini', '.cfg', '.conf',
                             '.sh', '.bash', '.zsh', '.fish', '.ps1', '.bat', '.cmd', '.dockerfile', 
                             '.sql', '.graphql', '.proto', '.thrift')):
                filepaths.append(filepath)

    if not filepaths:
        return {"error": f"No code files found in the project. {ignored_count} files/folders were ignored."}

    print(f"Indexing {len(filepaths)} files, ignored {ignored_count} files/folders")

    # Read the content of each file and prepare documents
    documents = []
    metadatas = []
    for filepath in filepaths:
        try:
            with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read()
                # Skip empty files
                if not content.strip():
                    continue
                    
                documents.append(content)
                # Store file metadata to preserve folder structure
                relative_path = os.path.relpath(filepath, project_path)
                metadatas.append({
                    "file_path": relative_path,
                    "full_path": filepath,
                    "project_name": project_name,
                    "branch_name": branch_name,
                    "file_type": os.path.splitext(filepath)[1],
                    "file_size": len(content)
                })
        except Exception as e:
            print(f"Warning: Could not read file {filepath}: {str(e)}")
            continue

    if not documents:
        return {"error": f"No readable code files found in the project. {ignored_count} files/folders were ignored."}

    # Chunk the code
    text_splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=200)
    texts = text_splitter.create_documents(documents, metadatas=metadatas)

    # Deduplicate chunks using hashing to avoid embedding identical content
    unique_texts = []
    unique_chunk_hashes = set()
    for doc in texts:
        chunk_hash = hashlib.sha256(doc.page_content.encode('utf-8')).hexdigest()
        if chunk_hash not in unique_chunk_hashes:
            unique_chunk_hashes.add(chunk_hash)
            unique_texts.append(doc)

    print(f"Total chunks created: {len(texts)}, Unique chunks to be indexed: {len(unique_texts)}")

    # Initialize embeddings
    embeddings = VoyageAIEmbeddings(
        model="voyage-code-3",
        voyage_api_key=config.VOYAGE_API_KEY
    )
    
    try:
        # Create Qdrant vector store from unique documents
        vector_store = QdrantVectorStore.from_documents(
            unique_texts,
            embeddings,
            collection_name=collection_name,
            url=f"http://{config.QDRANT_HOST}:{config.QDRANT_PORT}",
            distance=Distance.COSINE
        )
        
        return {
            "status": "success", 
            "message": f"Project {project_name}/{branch_name} indexed successfully in collection: {collection_name}",
            "files_indexed": len(documents),
            "files_ignored": ignored_count,
            "total_chunks": len(texts),
            "unique_chunks_indexed": len(unique_texts)
        }
    
    except Exception as e:
        return {"error": f"Failed to index project: {str(e)}"}

def index_project_branches(project_name: str):
    project_dir = os.path.join("instructor_projects", project_name)
    if not os.path.isdir(project_dir):
        return {"error": "Project not found"}

    branches = [d for d in os.listdir(project_dir) if os.path.isdir(os.path.join(project_dir, d))]
    if not branches:
        return {"error": "No branches found for the project"}

    indexed_branches = []
    errors = []
    total_files_indexed = 0
    total_files_ignored = 0

    for branch_name in branches:
        result = index_instructor_project(project_name, branch_name)
        if "error" in result:
            errors.append(f"Branch {branch_name}: {result['error']}")
        else:
            indexed_branches.append(branch_name)
            total_files_indexed += result.get('files_indexed', 0)
            total_files_ignored += result.get('files_ignored', 0)

    if errors:
        return {
            "status": "partial_success", 
            "indexed_branches": indexed_branches, 
            "errors": errors,
            "total_files_indexed": total_files_indexed,
            "total_files_ignored": total_files_ignored
        }

    return {
        "status": "success", 
        "message": f"All branches of project {project_name} indexed successfully.",
        "total_files_indexed": total_files_indexed,
        "total_files_ignored": total_files_ignored
    }
