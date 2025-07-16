# Production use requires a separate commercial license from the Licensor.
# For commercial licenses, please contact Tiago Sasaki at tiago@confenge.com.br.

import os
import json
import gzip
import base64
import subprocess
import tempfile
from typing import Dict, List, Any, Optional, Tuple
import logging
from pathlib import Path
import ifcopenshell
import ifcopenshell.geom
import numpy as np
from dataclasses import dataclass

logger = logging.getLogger(__name__)

@dataclass
class XKTGeometry:
    """XKT geometry data structure"""
    positions: List[float]
    normals: List[float]
    indices: List[int]
    colors: List[float]
    pickColors: List[float]

@dataclass
class XKTEntity:
    """XKT entity data structure"""
    entityId: str
    meshIds: List[str]
    matrix: List[float]
    aabb: List[float]
    layer: str

@dataclass
class XKTMesh:
    """XKT mesh data structure"""
    meshId: str
    geometryId: str
    matrix: List[float]
    aabb: List[float]
    color: List[float]
    opacity: float

class IFCToXKTConverter:
    """Converter from IFC to XKT format for optimized xeokit visualization"""
    
    def __init__(self):
        self.settings = ifcopenshell.geom.settings()
        self.settings.set(self.settings.USE_WORLD_COORDS, True)
        self.settings.set(self.settings.WELD_VERTICES, True)
        self.settings.set(self.settings.USE_BREP_DATA, False)
        self.settings.set(self.settings.SEW_SHELLS, True)
        self.settings.set(self.settings.FASTER_BOOLEANS, True)
        
        # Color mapping for different IFC types
        self.type_colors = {
            'IfcWall': [0.8, 0.8, 0.8, 1.0],
            'IfcSlab': [0.7, 0.7, 0.7, 1.0],
            'IfcBeam': [0.8, 0.4, 0.2, 1.0],
            'IfcColumn': [0.6, 0.6, 0.8, 1.0],
            'IfcDoor': [0.8, 0.6, 0.4, 1.0],
            'IfcWindow': [0.4, 0.6, 0.8, 1.0],
            'IfcRoof': [0.6, 0.3, 0.2, 1.0],
            'IfcStair': [0.7, 0.7, 0.5, 1.0],
            'IfcSpace': [0.9, 0.9, 0.9, 0.3],
            'IfcFurnishingElement': [0.8, 0.5, 0.3, 1.0],
            'default': [0.5, 0.5, 0.5, 1.0]
        }
    
    def convert_ifc_to_xkt(self, ifc_file_path: str, output_path: str, 
                          options: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        Convert IFC file to XKT format
        
        Args:
            ifc_file_path: Path to input IFC file
            output_path: Path for output XKT file
            options: Conversion options
            
        Returns:
            Conversion result with metadata
        """
        try:
            logger.info(f"Starting IFC to XKT conversion: {ifc_file_path}")
            
            # Default options
            if options is None:
                options = {}
            
            options = {
                'includeTypes': options.get('includeTypes', []),
                'excludeTypes': options.get('excludeTypes', []),
                'splitGeometry': options.get('splitGeometry', True),
                'quantizePositions': options.get('quantizePositions', True),
                'quantizeNormals': options.get('quantizeNormals', True),
                'compressGeometry': options.get('compressGeometry', True),
                'maxGeometryBucketSize': options.get('maxGeometryBucketSize', 50000),
                **options
            }
            
            # Load IFC file
            ifc_file = ifcopenshell.open(ifc_file_path)
            logger.info(f"Loaded IFC file with schema: {ifc_file.schema}")
            
            # Extract model data
            model_data = self._extract_model_data(ifc_file, options)
            
            # Convert to XKT format
            xkt_data = self._create_xkt_data(model_data, options)
            
            # Write XKT file
            self._write_xkt_file(xkt_data, output_path, options)
            
            # Generate metadata
            metadata = self._generate_metadata(ifc_file, model_data, xkt_data)
            
            logger.info(f"XKT conversion completed: {output_path}")
            
            return {
                'success': True,
                'output_path': output_path,
                'metadata': metadata,
                'stats': {
                    'entities_processed': len(model_data['entities']),
                    'meshes_created': len(xkt_data['meshes']),
                    'geometries_created': len(xkt_data['geometries']),
                    'file_size': os.path.getsize(output_path) if os.path.exists(output_path) else 0
                }
            }
            
        except Exception as e:
            logger.error(f"Error converting IFC to XKT: {str(e)}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def _extract_model_data(self, ifc_file, options: Dict[str, Any]) -> Dict[str, Any]:
        """Extract model data from IFC file"""
        entities = []
        geometries = {}
        materials = {}
        
        # Get all building elements
        all_elements = ifc_file.by_type('IfcProduct')
        
        include_types = options.get('includeTypes', [])
        exclude_types = options.get('excludeTypes', [])
        
        for element in all_elements:
            element_type = element.is_a()
            
            # Filter by type if specified
            if include_types and element_type not in include_types:
                continue
            if exclude_types and element_type in exclude_types:
                continue
            
            # Skip elements without geometry
            if not hasattr(element, 'Representation') or not element.Representation:
                continue
            
            try:
                # Get geometry
                shape = ifcopenshell.geom.create_shape(self.settings, element)
                
                if shape:
                    geometry_data = self._extract_geometry_data(shape, element)
                    
                    if geometry_data:
                        geometry_id = f"geometry_{element.id()}"
                        geometries[geometry_id] = geometry_data
                        
                        # Create entity
                        entity = {
                            'entityId': str(element.GlobalId),
                            'elementId': element.id(),
                            'type': element_type,
                            'name': getattr(element, 'Name', None),
                            'description': getattr(element, 'Description', None),
                            'geometryId': geometry_id,
                            'color': self._get_element_color(element),
                            'matrix': list(shape.transformation.matrix.data),
                            'aabb': geometry_data['aabb'],
                            'properties': self._extract_properties(element)
                        }
                        
                        entities.append(entity)
                        
            except Exception as e:
                logger.warning(f"Failed to process element {element.id()}: {str(e)}")
                continue
        
        return {
            'entities': entities,
            'geometries': geometries,
            'materials': materials,
            'project_info': self._extract_project_info(ifc_file)
        }
    
    def _extract_geometry_data(self, shape, element) -> Optional[Dict[str, Any]]:
        """Extract geometry data from IFC shape"""
        try:
            geometry = shape.geometry
            
            # Get vertices
            vertices = geometry.verts
            if len(vertices) == 0:
                return None
            
            # Convert to numpy arrays for easier manipulation
            positions = np.array(vertices, dtype=np.float32).reshape(-1, 3)
            
            # Get faces
            faces = geometry.faces
            if len(faces) == 0:
                return None
            
            indices = np.array(faces, dtype=np.uint32)
            
            # Calculate normals
            normals = self._calculate_normals(positions, indices)
            
            # Calculate AABB
            aabb = [
                float(np.min(positions[:, 0])), float(np.min(positions[:, 1])), float(np.min(positions[:, 2])),
                float(np.max(positions[:, 0])), float(np.max(positions[:, 1])), float(np.max(positions[:, 2]))
            ]
            
            return {
                'positions': positions.flatten().tolist(),
                'normals': normals.flatten().tolist(),
                'indices': indices.tolist(),
                'aabb': aabb,
                'primitive': 'triangles'
            }
            
        except Exception as e:
            logger.warning(f"Failed to extract geometry: {str(e)}")
            return None
    
    def _calculate_normals(self, positions: np.ndarray, indices: np.ndarray) -> np.ndarray:
        """Calculate vertex normals from positions and indices"""
        normals = np.zeros_like(positions)
        
        # Calculate face normals
        for i in range(0, len(indices), 3):
            if i + 2 >= len(indices):
                break
                
            i0, i1, i2 = indices[i], indices[i + 1], indices[i + 2]
            
            if i0 >= len(positions) or i1 >= len(positions) or i2 >= len(positions):
                continue
            
            v0, v1, v2 = positions[i0], positions[i1], positions[i2]
            
            # Calculate face normal
            edge1 = v1 - v0
            edge2 = v2 - v0
            face_normal = np.cross(edge1, edge2)
            
            # Normalize
            length = np.linalg.norm(face_normal)
            if length > 0:
                face_normal = face_normal / length
            
            # Add to vertex normals
            normals[i0] += face_normal
            normals[i1] += face_normal
            normals[i2] += face_normal
        
        # Normalize vertex normals
        lengths = np.linalg.norm(normals, axis=1, keepdims=True)
        lengths[lengths == 0] = 1  # Avoid division by zero
        normals = normals / lengths
        
        return normals
    
    def _get_element_color(self, element) -> List[float]:
        """Get color for element based on type"""
        element_type = element.is_a()
        return self.type_colors.get(element_type, self.type_colors['default'])
    
    def _extract_properties(self, element) -> Dict[str, Any]:
        """Extract properties from IFC element"""
        properties = {}
        
        # Basic properties
        properties['GlobalId'] = str(element.GlobalId)
        properties['Type'] = element.is_a()
        if hasattr(element, 'Name') and element.Name:
            properties['Name'] = str(element.Name)
        if hasattr(element, 'Description') and element.Description:
            properties['Description'] = str(element.Description)
        
        # Property sets
        if hasattr(element, 'IsDefinedBy'):
            for definition in element.IsDefinedBy:
                if definition.is_a('IfcRelDefinesByProperties'):
                    property_set = definition.RelatingPropertyDefinition
                    if property_set.is_a('IfcPropertySet'):
                        pset_name = str(property_set.Name)
                        properties[pset_name] = {}
                        
                        for prop in property_set.HasProperties:
                            if prop.is_a('IfcPropertySingleValue'):
                                prop_name = str(prop.Name)
                                if prop.NominalValue:
                                    properties[pset_name][prop_name] = str(prop.NominalValue.wrappedValue)
        
        return properties
    
    def _extract_project_info(self, ifc_file) -> Dict[str, Any]:
        """Extract project information"""
        project_info = {}
        
        # Get project
        projects = ifc_file.by_type('IfcProject')
        if projects:
            project = projects[0]
            project_info['name'] = str(getattr(project, 'Name', 'Unnamed Project'))
            project_info['description'] = str(getattr(project, 'Description', ''))
            project_info['globalId'] = str(project.GlobalId)
        
        # Get units
        try:
            unit_assignments = ifc_file.by_type('IfcUnitAssignment')
            if unit_assignments:
                units = unit_assignments[0].Units
                project_info['units'] = [str(unit.Name) for unit in units if hasattr(unit, 'Name']
        except:
            project_info['units'] = ['METRE']
        
        # Get schema
        project_info['schema'] = ifc_file.schema
        
        return project_info
    
    def _create_xkt_data(self, model_data: Dict[str, Any], options: Dict[str, Any]) -> Dict[str, Any]:
        """Create XKT data structure from model data"""
        xkt_data = {
            'xktVersion': '10',
            'gltfUpAxis': 'Y',
            'aabb': self._calculate_model_aabb(model_data),
            'geometries': [],
            'meshes': [],
            'entities': [],
            'propertysets': []
        }
        
        # Process geometries
        geometry_buckets = self._bucket_geometries(model_data['geometries'], options)
        
        for bucket_id, bucket_geometries in geometry_buckets.items():
            geometry_data = self._merge_geometries(bucket_geometries, options)
            
            if geometry_data:
                xkt_data['geometries'].append({
                    'geometryId': bucket_id,
                    'primitiveType': 'triangles',
                    'positions': geometry_data['positions'],
                    'normals': geometry_data['normals'],
                    'indices': geometry_data['indices'],
                    'positionsCompressed': geometry_data.get('positionsCompressed', False),
                    'normalsCompressed': geometry_data.get('normalsCompressed', False)
                })
        
        # Process entities and meshes
        for entity in model_data['entities']:
            mesh_id = f"mesh_{entity['elementId']}"
            
            xkt_data['meshes'].append({
                'meshId': mesh_id,
                'geometryId': self._get_geometry_bucket_id(entity['geometryId'], geometry_buckets),
                'color': entity['color'][:3],  # RGB only
                'opacity': entity['color'][3],
                'matrix': entity['matrix']
            })
            
            xkt_data['entities'].append({
                'entityId': entity['entityId'],
                'meshIds': [mesh_id],
                'layer': entity['type']
            })
            
            # Add property set
            if entity['properties']:
                xkt_data['propertysets'].append({
                    'propertySetId': f"pset_{entity['elementId']}",
                    'propertySetType': 'IfcPropertySet',
                    'propertySetName': 'Properties',
                    'properties': entity['properties']
                })
        
        return xkt_data
    
    def _calculate_model_aabb(self, model_data: Dict[str, Any]) -> List[float]:
        """Calculate axis-aligned bounding box for entire model"""
        if not model_data['entities']:
            return [0, 0, 0, 0, 0, 0]
        
        min_x = min_y = min_z = float('inf')
        max_x = max_y = max_z = float('-inf')
        
        for entity in model_data['entities']:
            aabb = entity['aabb']
            min_x = min(min_x, aabb[0])
            min_y = min(min_y, aabb[1])
            min_z = min(min_z, aabb[2])
            max_x = max(max_x, aabb[3])
            max_y = max(max_y, aabb[4])
            max_z = max(max_z, aabb[5])
        
        return [min_x, min_y, min_z, max_x, max_y, max_z]
    
    def _bucket_geometries(self, geometries: Dict[str, Any], options: Dict[str, Any]) -> Dict[str, List[str]]:
        """Group geometries into buckets for optimization"""
        max_bucket_size = options.get('maxGeometryBucketSize', 50000)
        
        if not options.get('splitGeometry', True):
            # Single bucket
            return {'bucket_0': list(geometries.keys())}
        
        buckets = {}
        current_bucket = 0
        current_bucket_size = 0
        
        for geom_id, geom_data in geometries.items():
            vertex_count = len(geom_data['positions']) // 3
            
            if current_bucket_size + vertex_count > max_bucket_size and current_bucket_size > 0:
                current_bucket += 1
                current_bucket_size = 0
            
            bucket_id = f'bucket_{current_bucket}'
            if bucket_id not in buckets:
                buckets[bucket_id] = []
            
            buckets[bucket_id].append(geom_id)
            current_bucket_size += vertex_count
        
        return buckets
    
    def _merge_geometries(self, geometry_ids: List[str], options: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Merge multiple geometries into a single geometry"""
        # For now, return the first geometry
        # In a full implementation, you would merge all geometries
        if not geometry_ids:
            return None
        
        # This is a simplified implementation
        # In reality, you would merge all geometries in the bucket
        return None  # Placeholder
    
    def _get_geometry_bucket_id(self, geometry_id: str, buckets: Dict[str, List[str]]) -> str:
        """Get bucket ID for a geometry"""
        for bucket_id, geom_ids in buckets.items():
            if geometry_id in geom_ids:
                return bucket_id
        return 'bucket_0'
    
    def _write_xkt_file(self, xkt_data: Dict[str, Any], output_path: str, options: Dict[str, Any]):
        """Write XKT data to file"""
        try:
            # Convert to JSON
            json_data = json.dumps(xkt_data, separators=(',', ':'))
            
            # Compress if requested
            if options.get('compressGeometry', True):
                compressed_data = gzip.compress(json_data.encode('utf-8'))
                
                with open(output_path, 'wb') as f:
                    f.write(compressed_data)
            else:
                with open(output_path, 'w') as f:
                    f.write(json_data)
                    
        except Exception as e:
            logger.error(f"Error writing XKT file: {str(e)}")
            raise
    
    def _generate_metadata(self, ifc_file, model_data: Dict[str, Any], xkt_data: Dict[str, Any]) -> Dict[str, Any]:
        """Generate conversion metadata"""
        return {
            'source_format': 'IFC',
            'target_format': 'XKT',
            'schema': ifc_file.schema,
            'project_info': model_data['project_info'],
            'statistics': {
                'entities_count': len(model_data['entities']),
                'geometries_count': len(model_data['geometries']),
                'meshes_count': len(xkt_data['meshes']),
                'model_aabb': xkt_data['aabb']
            }
        }

# Utility functions
def convert_ifc_to_xkt(ifc_file_path: str, output_path: str = None, 
                      options: Dict[str, Any] = None) -> Dict[str, Any]:
    """
    Utility function to convert IFC to XKT format
    
    Args:
        ifc_file_path: Path to input IFC file
        output_path: Path for output XKT file (optional, will generate if not provided)
        options: Conversion options
        
    Returns:
        Conversion result
    """
    if output_path is None:
        output_path = os.path.splitext(ifc_file_path)[0] + '.xkt'
    
    converter = IFCToXKTConverter()
    return converter.convert_ifc_to_xkt(ifc_file_path, output_path, options)

def get_xkt_viewer_config(xkt_file_path: str) -> Dict[str, Any]:
    """
    Generate viewer configuration for XKT file
    
    Args:
        xkt_file_path: Path to XKT file
        
    Returns:
        Viewer configuration
    """
    return {
        'type': 'xkt',
        'src': xkt_file_path,
        'edges': True,
        'saoEnabled': True,
        'pbrEnabled': False,
        'colorTextureEnabled': True,
        'backfaces': False
    }