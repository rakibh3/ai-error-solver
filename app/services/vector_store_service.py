from typing import List, Dict, Any
from datetime import datetime
from app.utils.qdrant import get_qdrant_client, get_collection_name, parse_collection_name


def get_all_indexed_projects() -> Dict[str, Any]:
    """
    Get all indexed projects from the vector database
    Returns a list of indexed projects with their metadata
    """
    try:
        client = get_qdrant_client()
        
        # Get all collections from Qdrant
        collections_response = client.get_collections()
        collections = collections_response.collections
        
        indexed_projects = []
        
        for collection in collections:
            collection_name = collection.name
            
            # Only process instructor project collections
            if collection_name.startswith("instructor_project_"):
                project_info = parse_collection_name(collection_name)
                
                if project_info:
                    try:
                        # Get collection info for additional metadata
                        collection_info = client.get_collection(collection_name)
                        
                        # Safely get vector size
                        vector_size = None
                        distance_metric = None
                        
                        try:
                            if hasattr(collection_info.config, 'params') and collection_info.config.params:
                                if hasattr(collection_info.config.params, 'vectors'):
                                    vectors_config = collection_info.config.params.vectors
                                    if hasattr(vectors_config, 'size'):
                                        vector_size = vectors_config.size
                                    elif isinstance(vectors_config, dict) and 'size' in vectors_config:
                                        vector_size = vectors_config['size']
                                    
                                    if hasattr(vectors_config, 'distance'):
                                        distance_metric = vectors_config.distance.name if hasattr(vectors_config.distance, 'name') else str(vectors_config.distance)
                                    elif isinstance(vectors_config, dict) and 'distance' in vectors_config:
                                        distance_metric = str(vectors_config['distance'])
                        except Exception as e:
                            print(f"Warning: Could not get vector config for {collection_name}: {str(e)}")
                        
                        project_data = {
                            "collection_name": collection_name,
                            "project_name": project_info["project_name"],
                            "branch_name": project_info["branch_name"],
                            "vectors_count": collection_info.vectors_count or 0,
                            "indexed_at": collection_info.status.name if collection_info.status else "unknown",
                            "vector_size": vector_size,
                            "distance_metric": distance_metric
                        }
                        
                        indexed_projects.append(project_data)
                        
                    except Exception as e:
                        print(f"Warning: Could not get info for collection {collection_name}: {str(e)}")
                        # Add basic info even if detailed info fails
                        project_data = {
                            "collection_name": collection_name,
                            "project_name": project_info["project_name"],
                            "branch_name": project_info["branch_name"],
                            "vectors_count": 0,
                            "indexed_at": "unknown",
                            "vector_size": None,
                            "distance_metric": None,
                            "status": "error_retrieving_info"
                        }
                        indexed_projects.append(project_data)
        
        return {
            "status": "success",
            "total_indexed_projects": len(indexed_projects),
            "indexed_projects": indexed_projects
        }
        
    except Exception as e:
        return {
            "status": "error",
            "message": f"Failed to retrieve indexed projects: {str(e)}"
        }


def delete_indexed_project(project_name: str, branch_name: str) -> Dict[str, Any]:
    
    try:
        client = get_qdrant_client()
        collection_name = get_collection_name(project_name, branch_name)
        
        # Check if collection exists
        try:
            collections_response = client.get_collections()
            collection_exists = any(
                col.name == collection_name for col in collections_response.collections
            )
            
            if not collection_exists:
                return {
                    "status": "error",
                    "message": f"Indexed project not found: {project_name}/{branch_name}",
                    "collection_name": collection_name
                }
            
        except Exception as e:
            return {
                "status": "error",
                "message": f"Failed to check if collection exists: {str(e)}"
            }
        
        # Get collection info before deletion for logging
        try:
            collection_info = client.get_collection(collection_name)
            vectors_count = collection_info.vectors_count or 0
        except Exception:
            vectors_count = "unknown"
        
        # Delete the collection
        delete_result = client.delete_collection(collection_name)
        
        return {
            "status": "success",
            "message": f"Successfully deleted indexed project: {project_name}/{branch_name}",
            "collection_name": collection_name,
            "vectors_deleted": vectors_count,
            "deleted_at": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        return {
            "status": "error",
            "message": f"Failed to delete indexed project {project_name}/{branch_name}: {str(e)}"
        } 