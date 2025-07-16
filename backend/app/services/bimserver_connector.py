import requests
import json
import base64
from typing import Dict, List, Any, Optional
import logging
from datetime import datetime

logger = logging.getLogger(__name__)

class BIMServerConnector:
    """Connector for BIMserver.org integration"""
    
    def __init__(self, base_url: str = "http://bimserver:8080", 
                 username: str = "admin@bimserver.org", 
                 password: str = "admin"):
        self.base_url = base_url
        self.username = username
        self.password = password
        self.token = None
        self.session = requests.Session()
        self._authenticate()
    
    def _authenticate(self) -> bool:
        """Authenticate with BIMserver"""
        try:
            auth_data = {
                "request": {
                    "interface": "AuthInterface",
                    "method": "login",
                    "parameters": {
                        "username": self.username,
                        "password": self.password
                    }
                }
            }
            
            response = self.session.post(
                f"{self.base_url}/json",
                json=auth_data,
                headers={"Content-Type": "application/json"}
            )
            
            if response.status_code == 200:
                result = response.json()
                if "response" in result and "result" in result["response"]:
                    self.token = result["response"]["result"]
                    logger.info("Successfully authenticated with BIMserver")
                    return True
            
            logger.error(f"Authentication failed: {response.text}")
            return False
            
        except Exception as e:
            logger.error(f"Error authenticating with BIMserver: {str(e)}")
            return False
    
    def _make_request(self, interface: str, method: str, parameters: Dict[str, Any]) -> Optional[Dict]:
        """Make authenticated request to BIMserver"""
        if not self.token:
            if not self._authenticate():
                return None
        
        request_data = {
            "token": self.token,
            "request": {
                "interface": interface,
                "method": method,
                "parameters": parameters
            }
        }
        
        try:
            response = self.session.post(
                f"{self.base_url}/json",
                json=request_data,
                headers={"Content-Type": "application/json"}
            )
            
            if response.status_code == 200:
                result = response.json()
                if "response" in result:
                    return result["response"]
            
            logger.error(f"Request failed: {response.text}")
            return None
            
        except Exception as e:
            logger.error(f"Error making request to BIMserver: {str(e)}")
            return None
    
    def create_project(self, name: str, description: str = "") -> Optional[int]:
        """Create a new project in BIMserver"""
        parameters = {
            "name": name,
            "description": description,
            "schema": "ifc4"
        }
        
        response = self._make_request("ServiceInterface", "addProject", parameters)
        
        if response and "result" in response:
            project_id = response["result"]
            logger.info(f"Created BIMserver project: {name} (ID: {project_id})")
            return project_id
        
        return None
    
    def upload_ifc_file(self, project_id: int, file_path: str, 
                       filename: str = None) -> Optional[int]:
        """Upload IFC file to BIMserver project"""
        if not filename:
            filename = file_path.split("/")[-1]
        
        try:
            # Read and encode file
            with open(file_path, 'rb') as f:
                file_content = f.read()
            
            file_base64 = base64.b64encode(file_content).decode('utf-8')
            
            parameters = {
                "poid": project_id,
                "filename": filename,
                "data": file_base64,
                "merge": False,
                "comment": f"Uploaded via Vitruvius - {datetime.now().isoformat()}",
                "deserializerOid": self._get_deserializer_oid()
            }
            
            response = self._make_request("ServiceInterface", "checkin", parameters)
            
            if response and "result" in response:
                revision_id = response["result"]
                logger.info(f"Uploaded IFC file to project {project_id}, revision: {revision_id}")
                return revision_id
            
            return None
            
        except Exception as e:
            logger.error(f"Error uploading IFC file: {str(e)}")
            return None
    
    def _get_deserializer_oid(self) -> int:
        """Get IFC deserializer OID"""
        response = self._make_request("ServiceInterface", "getAllDeserializers", {})
        
        if response and "result" in response:
            for deserializer in response["result"]:
                if "ifc" in deserializer.get("name", "").lower():
                    return deserializer["oid"]
        
        # Default IFC deserializer OID
        return 1
    
    def get_project_revisions(self, project_id: int) -> List[Dict[str, Any]]:
        """Get all revisions for a project"""
        parameters = {"poid": project_id}
        
        response = self._make_request("ServiceInterface", "getAllRevisionsOfProject", parameters)
        
        if response and "result" in response:
            return response["result"]
        
        return []
    
    def download_ifc_file(self, revision_id: int, output_path: str) -> bool:
        """Download IFC file from BIMserver"""
        try:
            # Get download data
            parameters = {
                "roid": revision_id,
                "serializerOid": self._get_serializer_oid(),
                "showOwn": True
            }
            
            response = self._make_request("ServiceInterface", "download", parameters)
            
            if response and "result" in response:
                download_id = response["result"]
                
                # Get download data
                download_response = self._make_request(
                    "ServiceInterface", 
                    "getDownloadData", 
                    {"actionId": download_id}
                )
                
                if download_response and "result" in download_response:
                    file_data = base64.b64decode(download_response["result"]["data"])
                    
                    with open(output_path, 'wb') as f:
                        f.write(file_data)
                    
                    logger.info(f"Downloaded IFC file to {output_path}")
                    return True
            
            return False
            
        except Exception as e:
            logger.error(f"Error downloading IFC file: {str(e)}")
            return False
    
    def _get_serializer_oid(self) -> int:
        """Get IFC serializer OID"""
        response = self._make_request("ServiceInterface", "getAllSerializers", {})
        
        if response and "result" in response:
            for serializer in response["result"]:
                if "ifc" in serializer.get("name", "").lower():
                    return serializer["oid"]
        
        # Default IFC serializer OID
        return 1
    
    def query_model_data(self, revision_id: int, query: str) -> Optional[Dict]:
        """Execute query on model data"""
        parameters = {
            "roid": revision_id,
            "code": query,
            "type": "JavaScript"
        }
        
        response = self._make_request("ServiceInterface", "query", parameters)
        
        if response and "result" in response:
            return response["result"]
        
        return None
    
    def get_model_geometry(self, revision_id: int) -> Optional[Dict]:
        """Get geometry data for model"""
        parameters = {
            "roid": revision_id,
            "geometryType": "TRIANGLES"
        }
        
        response = self._make_request("ServiceInterface", "getGeometry", parameters)
        
        if response and "result" in response:
            return response["result"]
        
        return None
    
    def get_model_elements(self, revision_id: int, 
                          ifc_type: str = None) -> List[Dict[str, Any]]:
        """Get model elements, optionally filtered by IFC type"""
        query = "var elements = model.getAll();"
        
        if ifc_type:
            query = f"var elements = model.getAllOfType('{ifc_type}');"
        
        query += """
        var result = [];
        for (var i = 0; i < elements.length; i++) {
            var element = elements[i];
            result.push({
                oid: element.getOid(),
                type: element.getType(),
                globalId: element.getGlobalId(),
                name: element.getName(),
                description: element.getDescription()
            });
        }
        result;
        """
        
        response = self.query_model_data(revision_id, query)
        
        if response:
            return response
        
        return []
    
    def get_clash_detection_results(self, revision_id: int) -> List[Dict[str, Any]]:
        """Get clash detection results from BIMserver"""
        # This would integrate with BIMserver's clash detection plugins
        # For now, return empty list as placeholder
        logger.info(f"Clash detection requested for revision {revision_id}")
        return []
    
    def get_project_info(self, project_id: int) -> Optional[Dict[str, Any]]:
        """Get detailed project information"""
        parameters = {"poid": project_id}
        
        response = self._make_request("ServiceInterface", "getProjectByPoid", parameters)
        
        if response and "result" in response:
            return response["result"]
        
        return None
    
    def delete_project(self, project_id: int) -> bool:
        """Delete a project from BIMserver"""
        parameters = {"poid": project_id}
        
        response = self._make_request("ServiceInterface", "deleteProject", parameters)
        
        if response:
            logger.info(f"Deleted BIMserver project {project_id}")
            return True
        
        return False
    
    def get_server_info(self) -> Optional[Dict[str, Any]]:
        """Get BIMserver information"""
        response = self._make_request("AdminInterface", "getServerInfo", {})
        
        if response and "result" in response:
            return response["result"]
        
        return None