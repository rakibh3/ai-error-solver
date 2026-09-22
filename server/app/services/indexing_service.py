import os
import hashlib
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_qdrant import QdrantVectorStore
from langchain_voyageai import VoyageAIEmbeddings
from qdrant_client.models import Distance
from app.core import config
from app.utils.qdrant import get_qdrant_client

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
    """
    Check if a path should be ignored during indexing
    """
    # Get relative path from base
    rel_path = os.path.relpath(path, base_path)
    
    # Check if any part of the path contains ignored directories
    path_parts = rel_path.split(os.sep)
    
    for part in path_parts:
        if part in IGNORE_DIRS:
            return True
    
    # Check if it's an ignored file
    if os.path.isfile(path):
        filename = os.path.basename(path)
        if filename in IGNORE_FILES:
            return True
        
        # Check file extensions
        if filename.startswith('.') and filename not in {'.env.example'}:
            return True
    
    return False

def index_reference_branch(project_name: str, branch_name: str, project_path: str,
                           collection_name: str):
    """Embed one checked-out branch into `collection_name`.

    The collection name is supplied by the caller and stored on
    `reference_branches`, rather than being re-derived from the project and
    branch names.
    """
    if not os.path.isdir(project_path):
        return {"error": f"Reference project path not found: {project_path}"}

    # Initialize Qdrant client
    client = get_qdrant_client()
    
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
    if not config.EMBEDDING_MODEL:
        return {"error": "EMBEDDING_MODEL is not set"}

    embeddings = VoyageAIEmbeddings(
        model=config.EMBEDDING_MODEL,
        voyage_api_key=config.VOYAGE_API_KEY
    )
    
    try:
        # Create Qdrant vector store from unique documents
        QdrantVectorStore.from_documents(
            unique_texts,
            embeddings,
            collection_name=collection_name,
            url=config.QDRANT_URL,
            api_key=config.QDRANT_API_KEY,
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
