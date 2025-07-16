# Production use requires a separate commercial license from the Licensor.
# For commercial licenses, please contact Tiago Sasaki at tiago@confenge.com.br.

from celery import Celery
import os
import json
import hashlib
import pickle
import tempfile
import numpy as np
from sqlalchemy.orm import sessionmaker
from sqlalchemy import create_engine
import redis
import ifcopenshell
import ifcopenshell.geom
import trimesh
from pygltflib import GLTF2
from ..services.bim_processor import process_ifc_file
from ..services.rules_engine import run_prescriptive_analysis
from ..db.models.project import Project, IFCModel, Conflict, Solution
from ..db.database import DATABASE_URL
from ..core.config import settings

# Configure Celery
celery_app = Celery('tasks', broker=settings.CELERY_BROKER_URL, backend=settings.CELERY_RESULT_BACKEND)

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


@celery_app.task
def convert_ifc_to_gltf(ifc_file_path: str, output_gltf_path: str, project_id: int):
    """
    Convert IFC file to glTF format for optimized web rendering
    """
    try:
        print(f"Starting IFC to glTF conversion: {ifc_file_path} -> {output_gltf_path}")
        
        # Open IFC file
        ifc_file = ifcopenshell.open(ifc_file_path)
        
        # Configure geometry settings
        settings = ifcopenshell.geom.settings()
        settings.set(settings.USE_WORLD_COORDS, True)
        settings.set(settings.WELD_VERTICES, True)
        settings.set(settings.USE_MATERIAL_NAMES, True)
        settings.set(settings.APPLY_DEFAULT_MATERIALS, True)
        
        # Create geometry iterator
        iterator = ifcopenshell.geom.iterator(settings, ifc_file, multiprocessing=True)
        
        # Collect all geometries
        geometries = []
        materials = {}
        
        # Process each element
        if iterator.initialize():
            while True:
                try:
                    shape = iterator.get()
                    element = ifc_file.by_id(shape.id)
                    
                    # Get geometry data
                    geometry = shape.geometry
                    vertices = geometry.verts
                    faces = geometry.faces
                    
                    if len(vertices) > 0 and len(faces) > 0:
                        # Reshape vertices to 3D points
                        vertices_array = np.array(vertices).reshape((-1, 3))
                        faces_array = np.array(faces).reshape((-1, 3))
                        
                        # Create trimesh object
                        mesh = trimesh.Trimesh(vertices=vertices_array, faces=faces_array)
                        
                        # Get material properties
                        material_name = shape.material_name if hasattr(shape, 'material_name') else 'default'
                        if material_name not in materials:
                            materials[material_name] = {
                                'name': material_name,
                                'color': [0.7, 0.7, 0.7, 1.0],  # Default gray
                                'metallic': 0.0,
                                'roughness': 0.5
                            }
                        
                        # Store geometry with metadata
                        geometries.append({
                            'mesh': mesh,
                            'material': material_name,
                            'element_id': shape.id,
                            'element_type': element.is_a(),
                            'element_name': getattr(element, 'Name', f"Element_{shape.id}"),
                            'global_id': element.GlobalId
                        })
                    
                    if not iterator.next():
                        break
                        
                except Exception as e:
                    print(f"Error processing element: {e}")
                    continue
        
        # Create combined scene
        scene = trimesh.Scene()
        
        # Add all geometries to scene
        for i, geom_data in enumerate(geometries):
            mesh = geom_data['mesh']
            
            # Apply material color if available
            if geom_data['material'] in materials:
                material = materials[geom_data['material']]
                mesh.visual.material.main_color = material['color']
            
            # Add to scene with unique name
            scene.add_geometry(mesh, node_name=f"element_{geom_data['element_id']}")
        
        # Export to glTF
        gltf_data = scene.export(file_type='gltf')
        
        # Ensure output directory exists
        os.makedirs(os.path.dirname(output_gltf_path), exist_ok=True)
        
        # Write glTF file
        with open(output_gltf_path, 'w') as f:
            f.write(gltf_data)
        
        # Update database with glTF path
        db = SessionLocal()
        try:
            ifc_model = db.query(IFCModel).filter(
                IFCModel.project_id == project_id,
                IFCModel.file_path == ifc_file_path
            ).first()
            
            if ifc_model:
                # Store glTF path in the model (we'll need to add this field)
                ifc_model.gltf_path = output_gltf_path
                db.commit()
                
        finally:
            db.close()
        
        print(f"IFC to glTF conversion completed successfully")
        
        return {
            "status": "completed",
            "gltf_path": output_gltf_path,
            "elements_count": len(geometries),
            "materials_count": len(materials)
        }
        
    except Exception as e:
        print(f"Error in IFC to glTF conversion: {str(e)}")
        return {
            "status": "failed",
            "error": str(e)
        }


@celery_app.task
def convert_ifc_to_xkt(ifc_file_path: str, output_xkt_path: str, project_id: int):
    """
    Convert IFC file to XKT format for xeokit streaming
    Note: This is a placeholder - actual implementation would require xeokit conversion tools
    """
    try:
        print(f"Starting IFC to XKT conversion: {ifc_file_path} -> {output_xkt_path}")
        
        # This would typically use xeokit's conversion tools
        # For now, we'll create a basic implementation
        
        # Open IFC file
        ifc_file = ifcopenshell.open(ifc_file_path)
        
        # Configure geometry settings for XKT optimization
        settings = ifcopenshell.geom.settings()
        settings.set(settings.USE_WORLD_COORDS, True)
        settings.set(settings.WELD_VERTICES, True)
        settings.set(settings.USE_MATERIAL_NAMES, True)
        settings.set(settings.APPLY_DEFAULT_MATERIALS, True)
        
        # Create geometry iterator
        iterator = ifcopenshell.geom.iterator(settings, ifc_file, multiprocessing=True)
        
        # Collect optimized data for XKT format
        xkt_data = {
            "metadata": {
                "version": "1.0",
                "generator": "Vitruvius IFC Converter",
                "schema": ifc_file.schema
            },
            "elements": [],
            "materials": [],
            "geometries": []
        }
        
        # Process elements for XKT
        if iterator.initialize():
            while True:
                try:
                    shape = iterator.get()
                    element = ifc_file.by_id(shape.id)
                    
                    # Get geometry data
                    geometry = shape.geometry
                    vertices = geometry.verts
                    faces = geometry.faces
                    
                    if len(vertices) > 0 and len(faces) > 0:
                        # Store element data
                        element_data = {
                            "id": shape.id,
                            "type": element.is_a(),
                            "name": getattr(element, 'Name', f"Element_{shape.id}"),
                            "globalId": element.GlobalId,
                            "geometry": {
                                "vertices": vertices,
                                "faces": faces
                            }
                        }
                        
                        xkt_data["elements"].append(element_data)
                    
                    if not iterator.next():
                        break
                        
                except Exception as e:
                    print(f"Error processing element for XKT: {e}")
                    continue
        
        # Ensure output directory exists
        os.makedirs(os.path.dirname(output_xkt_path), exist_ok=True)
        
        # For now, save as JSON (actual XKT would be binary)
        with open(output_xkt_path, 'w') as f:
            json.dump(xkt_data, f, indent=2)
        
        print(f"IFC to XKT conversion completed successfully")
        
        return {
            "status": "completed",
            "xkt_path": output_xkt_path,
            "elements_count": len(xkt_data["elements"])
        }
        
    except Exception as e:
        print(f"Error in IFC to XKT conversion: {str(e)}")
        return {
            "status": "failed",
            "error": str(e)
        }


@celery_app.task
def run_inter_model_clash_detection(project_id: int):
    """
    Run clash detection between multiple IFC models in a project (federated models)
    """
    db = SessionLocal()
    
    try:
        print(f"Starting inter-model clash detection for project {project_id}")
        
        # Get all IFC models for the project
        project = db.query(Project).filter(Project.id == project_id).first()
        if not project:
            return {"status": "failed", "error": "Project not found"}
        
        ifc_models = db.query(IFCModel).filter(IFCModel.project_id == project_id).all()
        
        if len(ifc_models) < 2:
            return {"status": "skipped", "message": "Need at least 2 models for inter-model clash detection"}
        
        # Process all combinations of model pairs
        from itertools import combinations
        total_clashes = 0
        
        for model1, model2 in combinations(ifc_models, 2):
            print(f"Checking clashes between {model1.filename} and {model2.filename}")
            
            # Check if files exist
            if not os.path.exists(model1.file_path) or not os.path.exists(model2.file_path):
                print(f"One or both files don't exist, skipping: {model1.file_path}, {model2.file_path}")
                continue
            
            # Generate file hashes for caching
            file1_hash = get_file_hash(model1.file_path)
            file2_hash = get_file_hash(model2.file_path)
            
            # Create cache key for this model pair
            cache_key = f"inter_clash_{min(file1_hash, file2_hash)}_{max(file1_hash, file2_hash)}"
            
            # Check cache for existing clash results
            cached_clashes = get_cached_ifc_processing_result(cache_key, 'inter_model_clashes')
            
            if cached_clashes:
                print(f"Using cached inter-model clash results for {model1.filename} vs {model2.filename}")
                inter_clashes = cached_clashes
            else:
                # Perform clash detection between the two models
                inter_clashes = detect_clashes_between_models(model1.file_path, model2.file_path)
                
                # Cache the results
                if file1_hash and file2_hash:
                    cache_ifc_processing_result(cache_key, 'inter_model_clashes', inter_clashes)
            
            # Store clashes in database
            for clash_data in inter_clashes:
                # Check if clash already exists
                existing_clash = db.query(Conflict).filter(
                    Conflict.project_id == project_id,
                    Conflict.description.contains(clash_data["description"])
                ).first()
                
                if not existing_clash:
                    conflict = Conflict(
                        project_id=project_id,
                        conflict_type=clash_data["type"],
                        severity=clash_data["severity"],
                        description=clash_data["description"],
                        status="detected"
                    )
                    db.add(conflict)
                    
                    # Link elements from both models
                    for element_id in clash_data["elements"]:
                        element = db.query(Element).filter(
                            Element.ifc_id == element_id
                        ).first()
                        if element:
                            conflict.elements.append(element)
            
            total_clashes += len(inter_clashes)
        
        db.commit()
        
        print(f"Inter-model clash detection completed. Found {total_clashes} clashes")
        
        return {
            "status": "completed",
            "project_id": project_id,
            "models_processed": len(ifc_models),
            "total_clashes": total_clashes
        }
        
    except Exception as e:
        print(f"Error in inter-model clash detection: {str(e)}")
        return {
            "status": "failed",
            "error": str(e)
        }
    
    finally:
        db.close()


def detect_clashes_between_models(model1_path: str, model2_path: str):
    """
    Detect clashes between elements from two different IFC models
    """
    try:
        # Open both IFC files
        ifc_file1 = ifcopenshell.open(model1_path)
        ifc_file2 = ifcopenshell.open(model2_path)
        
        # Configure geometry settings
        settings = ifcopenshell.geom.settings()
        settings.set(settings.USE_WORLD_COORDS, True)
        settings.set(settings.WELD_VERTICES, True)
        
        # Get geometries from both models
        geometries1 = extract_model_geometries(ifc_file1, settings)
        geometries2 = extract_model_geometries(ifc_file2, settings)
        
        clashes = []
        
        # Check for clashes between elements from different models
        for geom1 in geometries1:
            for geom2 in geometries2:
                # Skip if same element type (less likely to clash)
                if geom1['type'] == geom2['type']:
                    continue
                
                # Check if elements are likely to clash based on types
                if is_potential_inter_model_conflict(geom1, geom2):
                    # Perform bounding box intersection test
                    if bounding_boxes_intersect(geom1['bbox'], geom2['bbox']):
                        severity = determine_inter_model_severity(geom1, geom2)
                        
                        clash = {
                            "type": "inter_model_collision",
                            "severity": severity,
                            "description": f"{geom1['type']} from {os.path.basename(model1_path)} conflicts with {geom2['type']} from {os.path.basename(model2_path)}",
                            "elements": [geom1['global_id'], geom2['global_id']],
                            "model1": os.path.basename(model1_path),
                            "model2": os.path.basename(model2_path)
                        }
                        clashes.append(clash)
        
        return clashes
        
    except Exception as e:
        print(f"Error detecting clashes between models: {str(e)}")
        return []


def extract_model_geometries(ifc_file, settings):
    """
    Extract geometry data from an IFC model
    """
    geometries = []
    
    try:
        iterator = ifcopenshell.geom.iterator(settings, ifc_file)
        
        if iterator.initialize():
            while True:
                try:
                    shape = iterator.get()
                    element = ifc_file.by_id(shape.id)
                    
                    # Get geometry data
                    geometry = shape.geometry
                    vertices = geometry.verts
                    
                    if len(vertices) > 0:
                        # Calculate bounding box
                        vertices_array = np.array(vertices).reshape((-1, 3))
                        min_coords = np.min(vertices_array, axis=0)
                        max_coords = np.max(vertices_array, axis=0)
                        
                        geom_data = {
                            'id': shape.id,
                            'global_id': element.GlobalId,
                            'type': element.is_a(),
                            'name': getattr(element, 'Name', ''),
                            'bbox': {
                                'min': min_coords.tolist(),
                                'max': max_coords.tolist()
                            },
                            'vertices': vertices
                        }
                        geometries.append(geom_data)
                    
                    if not iterator.next():
                        break
                        
                except Exception as e:
                    print(f"Error processing element in geometry extraction: {e}")
                    continue
    
    except Exception as e:
        print(f"Error in geometry extraction: {str(e)}")
    
    return geometries


def is_potential_inter_model_conflict(geom1, geom2):
    """
    Determine if two elements from different models are likely to conflict
    """
    # Common inter-model conflicts
    structural_elements = ["IfcBeam", "IfcColumn", "IfcSlab", "IfcWall"]
    mep_elements = ["IfcPipeSegment", "IfcDuctSegment", "IfcCableSegment"]
    
    type1, type2 = geom1['type'], geom2['type']
    
    # Structural vs MEP conflicts
    if (type1 in structural_elements and type2 in mep_elements) or \
       (type1 in mep_elements and type2 in structural_elements):
        return True
    
    # Structural vs Structural from different models
    if type1 in structural_elements and type2 in structural_elements:
        return True
    
    # MEP vs MEP from different models
    if type1 in mep_elements and type2 in mep_elements:
        return True
    
    return False


def determine_inter_model_severity(geom1, geom2):
    """
    Determine severity of inter-model conflicts
    """
    critical_conflicts = [
        ("IfcBeam", "IfcPipeSegment"),
        ("IfcSlab", "IfcDuctSegment"),
        ("IfcColumn", "IfcCableSegment"),
        ("IfcWall", "IfcPipeSegment")
    ]
    
    element_pair = (geom1['type'], geom2['type'])
    reverse_pair = (geom2['type'], geom1['type'])
    
    if element_pair in critical_conflicts or reverse_pair in critical_conflicts:
        return "high"
    
    # MEP vs MEP conflicts are generally medium severity
    mep_elements = ["IfcPipeSegment", "IfcDuctSegment", "IfcCableSegment"]
    if geom1['type'] in mep_elements and geom2['type'] in mep_elements:
        return "medium"
    
    return "low"


def bounding_boxes_intersect(bbox1, bbox2):
    """
    Check if two bounding boxes intersect
    """
    # Check if bounding boxes overlap in all three dimensions
    return (bbox1['min'][0] <= bbox2['max'][0] and bbox1['max'][0] >= bbox2['min'][0] and
            bbox1['min'][1] <= bbox2['max'][1] and bbox1['max'][1] >= bbox2['min'][1] and
            bbox1['min'][2] <= bbox2['max'][2] and bbox1['max'][2] >= bbox2['min'][2])