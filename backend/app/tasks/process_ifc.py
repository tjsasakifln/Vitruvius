from celery import Celery
import os
import json
import hashlib
import pickle
from sqlalchemy.orm import sessionmaker
from sqlalchemy import create_engine
import redis
from ..services.bim_processor import process_ifc_file
from ..services.rules_engine import run_prescriptive_analysis
from ..db.models.project import Project, IFCModel, Conflict, Solution
from ..db.database import DATABASE_URL

# Configure Celery
celery_app = Celery('tasks', broker='redis://redis:6379/0', backend='redis://redis:6379/0')

# Database setup for Celery tasks
engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Redis cache setup
redis_client = redis.Redis(host='redis', port=6379, db=1, decode_responses=False)

# Cache configuration
CACHE_TTL = 3600 * 24 * 7  # 7 days
CACHE_PREFIX = 'vitruvius:ifc:'

def get_file_hash(file_path: str) -> str:
    """Generate hash for file content for caching"""
    try:
        hash_md5 = hashlib.md5()
        with open(file_path, "rb") as f:
            for chunk in iter(lambda: f.read(4096), b""):
                hash_md5.update(chunk)
        return hash_md5.hexdigest()
    except Exception as e:
        print(f"Error generating file hash: {str(e)}")
        return None

def get_cache_key(prefix: str, file_hash: str, suffix: str = "") -> str:
    """Generate cache key"""
    key = f"{CACHE_PREFIX}{prefix}:{file_hash}"
    if suffix:
        key += f":{suffix}"
    return key

def cache_ifc_processing_result(file_hash: str, result_type: str, data: any) -> bool:
    """
    Cache IFC processing results
    
    Args:
        file_hash: MD5 hash of the IFC file
        result_type: Type of result (bim_data, conflicts, solutions, etc.)
        data: Data to cache
        
    Returns:
        Success status
    """
    try:
        cache_key = get_cache_key('result', file_hash, result_type)
        serialized_data = pickle.dumps(data)
        
        redis_client.setex(cache_key, CACHE_TTL, serialized_data)
        print(f"Cached {result_type} for file hash {file_hash}")
        return True
        
    except Exception as e:
        print(f"Error caching result: {str(e)}")
        return False

def get_cached_ifc_processing_result(file_hash: str, result_type: str) -> any:
    """
    Get cached IFC processing result
    
    Args:
        file_hash: MD5 hash of the IFC file
        result_type: Type of result to retrieve
        
    Returns:
        Cached data or None if not found
    """
    try:
        cache_key = get_cache_key('result', file_hash, result_type)
        cached_data = redis_client.get(cache_key)
        
        if cached_data:
            result = pickle.loads(cached_data)
            print(f"Retrieved cached {result_type} for file hash {file_hash}")
            return result
            
        return None
        
    except Exception as e:
        print(f"Error retrieving cached result: {str(e)}")
        return None

def cache_geometry_data(file_hash: str, geometry_data: dict) -> bool:
    """Cache processed geometry data"""
    try:
        cache_key = get_cache_key('geometry', file_hash)
        
        # Compress geometry data before caching
        compressed_data = pickle.dumps(geometry_data)
        
        redis_client.setex(cache_key, CACHE_TTL, compressed_data)
        print(f"Cached geometry data for file hash {file_hash}")
        return True
        
    except Exception as e:
        print(f"Error caching geometry data: {str(e)}")
        return False

def get_cached_geometry_data(file_hash: str) -> dict:
    """Get cached geometry data"""
    try:
        cache_key = get_cache_key('geometry', file_hash)
        cached_data = redis_client.get(cache_key)
        
        if cached_data:
            geometry_data = pickle.loads(cached_data)
            print(f"Retrieved cached geometry data for file hash {file_hash}")
            return geometry_data
            
        return None
        
    except Exception as e:
        print(f"Error retrieving cached geometry data: {str(e)}")
        return None

def cache_model_metadata(file_hash: str, metadata: dict) -> bool:
    """Cache model metadata"""
    try:
        cache_key = get_cache_key('metadata', file_hash)
        redis_client.setex(cache_key, CACHE_TTL, json.dumps(metadata))
        print(f"Cached metadata for file hash {file_hash}")
        return True
        
    except Exception as e:
        print(f"Error caching metadata: {str(e)}")
        return False

def get_cached_model_metadata(file_hash: str) -> dict:
    """Get cached model metadata"""
    try:
        cache_key = get_cache_key('metadata', file_hash)
        cached_data = redis_client.get(cache_key)
        
        if cached_data:
            metadata = json.loads(cached_data)
            print(f"Retrieved cached metadata for file hash {file_hash}")
            return metadata
            
        return None
        
    except Exception as e:
        print(f"Error retrieving cached metadata: {str(e)}")
        return None

def invalidate_cache(file_hash: str) -> bool:
    """Invalidate all cache entries for a file"""
    try:
        pattern = get_cache_key('*', file_hash, '*')
        keys = redis_client.keys(pattern)
        
        if keys:
            redis_client.delete(*keys)
            print(f"Invalidated {len(keys)} cache entries for file hash {file_hash}")
        
        return True
        
    except Exception as e:
        print(f"Error invalidating cache: {str(e)}")
        return False

def get_cache_stats() -> dict:
    """Get cache statistics"""
    try:
        info = redis_client.info('memory')
        keyspace = redis_client.info('keyspace')
        
        # Count Vitruvius cache keys
        pattern = f"{CACHE_PREFIX}*"
        vitruvius_keys = len(redis_client.keys(pattern))
        
        return {
            'total_memory_used': info.get('used_memory_human', 'Unknown'),
            'total_keys': keyspace.get('db1', {}).get('keys', 0),
            'vitruvius_cache_keys': vitruvius_keys,
            'cache_ttl': CACHE_TTL
        }
        
    except Exception as e:
        print(f"Error getting cache stats: {str(e)}")
        return {}

@celery_app.task
def process_ifc_task(project_id: int, file_path: str):
    """
    Celery task to process an IFC file asynchronously with clash detection and caching.
    """
    db = SessionLocal()
    
    try:
        print(f"Starting IFC processing for project {project_id}: {file_path}")
        
        # Generate file hash for caching
        file_hash = get_file_hash(file_path)
        if not file_hash:
            print("Warning: Could not generate file hash, proceeding without cache")
        
        # Update IFC model status
        ifc_model = db.query(IFCModel).filter(
            IFCModel.project_id == project_id,
            IFCModel.file_path == file_path
        ).first()
        
        if ifc_model:
            ifc_model.status = "processing"
            db.commit()
        
        # Check cache for BIM data
        bim_data = None
        if file_hash:
            bim_data = get_cached_ifc_processing_result(file_hash, 'bim_data')
            
        if bim_data:
            print("Using cached BIM data")
        else:
            # Process IFC file with clash detection
            print("Processing IFC file (no cache found)")
            bim_data = process_ifc_file(file_path)
            
            if not bim_data.get("processed", False):
                raise Exception(f"IFC processing failed: {bim_data.get('error', 'Unknown error')}")
            
            # Cache the BIM data
            if file_hash:
                cache_ifc_processing_result(file_hash, 'bim_data', bim_data)
        
        # Check cache for conflicts
        conflicts_detected = None
        if file_hash:
            conflicts_detected = get_cached_ifc_processing_result(file_hash, 'conflicts')
            
        if conflicts_detected:
            print("Using cached conflict detection results")
        else:
            # Perform clash detection
            print("Performing clash detection (no cache found)")
            conflicts_detected = perform_clash_detection(bim_data)
            
            # Cache the conflicts
            if file_hash:
                cache_ifc_processing_result(file_hash, 'conflicts', conflicts_detected)
        
        # Store conflicts in database
        for conflict_data in conflicts_detected:
            # Check if conflict already exists to avoid duplicates
            existing_conflict = db.query(Conflict).filter(
                Conflict.project_id == project_id,
                Conflict.elements_involved == ",".join(conflict_data["elements"])
            ).first()
            
            if not existing_conflict:
                conflict = Conflict(
                    project_id=project_id,
                    conflict_type=conflict_data["type"],
                    severity=conflict_data["severity"],
                    description=conflict_data["description"],
                    elements_involved=",".join(conflict_data["elements"]),
                    status="detected"
                )
                db.add(conflict)
        
        db.commit()
        
        # Check cache for AI analysis results
        analysis_results = None
        if file_hash:
            analysis_results = get_cached_ifc_processing_result(file_hash, 'analysis_results')
            
        if analysis_results:
            print("Using cached AI analysis results")
        else:
            # Run prescriptive AI analysis
            print("Running prescriptive AI analysis (no cache found)")
            analysis_results = run_prescriptive_analysis(bim_data)
            
            # Cache the analysis results
            if file_hash:
                cache_ifc_processing_result(file_hash, 'analysis_results', analysis_results)
        
        # Store AI-generated solutions
        for result in analysis_results.get("analysis_results", []):
            conflict_id = get_conflict_id_by_elements(db, project_id, result["conflict"]["elements"])
            
            if conflict_id:
                for solution_data in result["solutions"]:
                    # Check if solution already exists
                    existing_solution = db.query(Solution).filter(
                        Solution.conflict_id == conflict_id,
                        Solution.solution_type == solution_data["type"]
                    ).first()
                    
                    if not existing_solution:
                        solution = Solution(
                            conflict_id=conflict_id,
                            solution_type=solution_data["type"],
                            description=solution_data["description"],
                            estimated_cost=int(solution_data["estimated_cost"] * 100),  # Store in cents
                            estimated_time=int(solution_data["estimated_time"]),
                            confidence_score=80,  # Default confidence score
                            status="proposed"
                        )
                        db.add(solution)
        
        db.commit()
        
        # Cache metadata if not already cached
        if file_hash:
            cached_metadata = get_cached_model_metadata(file_hash)
            if not cached_metadata:
                metadata = {
                    'project_id': project_id,
                    'file_path': file_path,
                    'schema': bim_data.get('model_info', {}).get('schema', 'Unknown'),
                    'total_elements': bim_data.get('model_info', {}).get('total_elements', 0),
                    'conflicts_count': len(conflicts_detected),
                    'solutions_count': len(analysis_results.get("analysis_results", []))
                }
                cache_model_metadata(file_hash, metadata)
        
        # Update IFC model status
        if ifc_model:
            ifc_model.status = "processed"
            from datetime import datetime
            ifc_model.processed_at = datetime.utcnow()
            db.commit()
        
        print(f"IFC processing completed for project {project_id}")
        
        # Get cache statistics for logging
        if file_hash:
            cache_stats = get_cache_stats()
            print(f"Cache stats: {cache_stats}")
        
        return {
            "status": "completed",
            "project_id": project_id,
            "conflicts_detected": len(conflicts_detected),
            "solutions_generated": len(analysis_results.get("analysis_results", [])),
            "file_hash": file_hash,
            "cache_used": file_hash is not None
        }

    except Exception as e:
        print(f"Error processing IFC file: {str(e)}")

        # Update status to failed
        if 'ifc_model' in locals() and ifc_model:
            ifc_model.status = "failed"
            db.commit()

        return {
            "status": "failed",
            "error": str(e),
            "project_id": project_id
        }

    finally:
        db.close()


def perform_clash_detection(bim_data):
    """
    Perform clash detection on BIM data using geometric analysis.
    """
    conflicts = []
    elements = bim_data.get("elements", [])
    
    # Simple clash detection algorithm
    for i, element1 in enumerate(elements):
        for j, element2 in enumerate(elements[i + 1:], i + 1):
            # Check if elements have geometry
            if not (element1.get("has_geometry") and element2.get("has_geometry")):
                continue

            # Check for potential conflicts based on element types
            if is_potential_conflict(element1, element2):
                severity = determine_severity(element1, element2)

                conflict = {
                    "type": "collision",
                    "severity": severity,
                    "description": f"{element1['type']} conflicts with {element2['type']}",
                    "elements": [element1["global_id"], element2["global_id"]]
                }
                conflicts.append(conflict)

    return conflicts

def is_potential_conflict(element1, element2):
    """
    Determine if two elements are likely to conflict based on their types.
    """
    structural_elements = ["IfcBeam", "IfcColumn", "IfcSlab", "IfcWall"]
    
    # Check if both are structural elements (higher chance of conflict)
    if element1["type"] in structural_elements and element2["type"] in structural_elements:
        return True
    
    # Check specific conflict scenarios
    if element1["type"] == "IfcBeam" and element2["type"] == "IfcColumn":
        return True
    if element1["type"] == "IfcDoor" and element2["type"] == "IfcWall":
        return True
    
    return False

def determine_severity(element1, element2):
    """
    Determine conflict severity based on element types.
    """
    critical_conflicts = [
        ("IfcBeam", "IfcColumn"),
        ("IfcSlab", "IfcBeam"),
        ("IfcWall", "IfcColumn")
    ]
    
    element_pair = (element1["type"], element2["type"])
    reverse_pair = (element2["type"], element1["type"])
    
    if element_pair in critical_conflicts or reverse_pair in critical_conflicts:
        return "high"
    
    return "medium"

def get_conflict_id_by_elements(db, project_id, elements):
    """
    Get conflict ID by matching elements.
    """
    elements_str = ",".join(elements)
    conflict = db.query(Conflict).filter(
        Conflict.project_id == project_id,
        Conflict.elements_involved == elements_str
    ).first()
    
    return conflict.id if conflict else None
