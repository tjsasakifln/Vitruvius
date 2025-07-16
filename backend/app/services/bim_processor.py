# Production use requires a separate commercial license from the Licensor.
# For commercial licenses, please contact Tiago Sasaki at tiago@confenge.com.br.

import ifcopenshell
import ifcopenshell.geom
from typing import Dict, List, Any
import json

class BIMProcessor:
    """Process IFC files and extract BIM data"""
    
    def __init__(self):
        self.settings = ifcopenshell.geom.settings()
        self.settings.set(self.settings.USE_WORLD_COORDS, True)
        
    def process_ifc_file(self, file_path: str) -> Dict[str, Any]:
        """Process IFC file and extract relevant data"""
        try:
            ifc_file = ifcopenshell.open(file_path)
            
            # Extract basic model information
            model_info = self._extract_model_info(ifc_file)
            
            # Extract elements
            elements = self._extract_elements(ifc_file)
            
            # Extract spatial structure
            spatial_structure = self._extract_spatial_structure(ifc_file)
            
            return {
                "model_info": model_info,
                "elements": elements,
                "spatial_structure": spatial_structure,
                "processed": True
            }
            
        except Exception as e:
            return {
                "error": str(e),
                "processed": False
            }
    
    def _extract_model_info(self, ifc_file) -> Dict[str, Any]:
        """Extract basic model information"""
        project = ifc_file.by_type('IfcProject')[0] if ifc_file.by_type('IfcProject') else None
        
        return {
            "schema": ifc_file.schema,
            "project_name": project.Name if project else "Unknown",
            "project_description": project.Description if project else "",
            "total_elements": len(ifc_file.by_type('IfcElement'))
        }
    
    def _extract_elements(self, ifc_file) -> List[Dict[str, Any]]:
        """Extract building elements"""
        elements = []
        
        # Get common building elements
        element_types = [
            'IfcWall', 'IfcBeam', 'IfcColumn', 'IfcSlab', 
            'IfcDoor', 'IfcWindow', 'IfcStair', 'IfcRoof'
        ]
        
        for element_type in element_types:
            for element in ifc_file.by_type(element_type):
                try:
                    element_data = {
                        "id": element.id(),
                        "type": element.is_a(),
                        "name": getattr(element, 'Name', ''),
                        "description": getattr(element, 'Description', ''),
                        "global_id": getattr(element, 'GlobalId', ''),
                        "properties": self._extract_properties(element)
                    }
                    
                    # Try to get geometry
                    try:
                        shape = ifcopenshell.geom.create_shape(self.settings, element)
                        element_data["has_geometry"] = True
                        element_data["geometry_info"] = {
                            "vertices": len(shape.geometry.verts) // 3,
                            "faces": len(shape.geometry.faces) // 3
                        }
                    except Exception:
                        element_data["has_geometry"] = False
                    
                    elements.append(element_data)
                except Exception:
                    continue
        
        return elements
    
    def _extract_properties(self, element) -> Dict[str, Any]:
        """Extract properties from an element"""
        properties = {}
        
        # Get property sets
        for definition in getattr(element, 'IsDefinedBy', []):
            if definition.is_a('IfcRelDefinesByProperties'):
                property_set = definition.RelatingPropertyDefinition
                if property_set.is_a('IfcPropertySet'):
                    properties[property_set.Name] = {}
                    for prop in property_set.HasProperties:
                        if prop.is_a('IfcPropertySingleValue'):
                            properties[property_set.Name][prop.Name] = prop.NominalValue.wrappedValue if prop.NominalValue else None
        
        return properties
    
    def _extract_spatial_structure(self, ifc_file) -> Dict[str, Any]:
        """Extract spatial structure (buildings, floors, etc.)"""
        structure = {}
        
        # Get buildings
        buildings = ifc_file.by_type('IfcBuilding')
        structure["buildings"] = []
        
        for building in buildings:
            building_data = {
                "id": building.id(),
                "name": getattr(building, 'Name', ''),
                "description": getattr(building, 'Description', ''),
                "floors": []
            }
            
            # Get floors in this building
            for rel in building.IsDecomposedBy:
                for floor in rel.RelatedObjects:
                    if floor.is_a('IfcBuildingStorey'):
                        floor_data = {
                            "id": floor.id(),
                            "name": getattr(floor, 'Name', ''),
                            "description": getattr(floor, 'Description', ''),
                            "elevation": getattr(floor, 'Elevation', 0)
                        }
                        building_data["floors"].append(floor_data)
            
            structure["buildings"].append(building_data)
        
        return structure


def process_ifc_file(file_path: str) -> Dict[str, Any]:
    """Main function to process IFC file"""
    processor = BIMProcessor()
    return processor.process_ifc_file(file_path)