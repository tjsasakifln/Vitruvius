# Production use requires a separate commercial license from the Licensor.
# For commercial licenses, please contact Tiago Sasaki at tiago@confenge.com.br.

import os
import requests
import json
import base64
import logging
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
from urllib.parse import urlencode, quote
from authlib.integrations.requests_client import OAuth2Session
from sqlalchemy.orm import Session
from ..db.models.project import User
from ..db.database import get_db

logger = logging.getLogger(__name__)

class APSIntegration:
    """
    Integration with Autodesk Platform Services (APS, formerly Forge)
    """
    
    def __init__(self, client_id: str, client_secret: str, callback_url: str = None):
        self.client_id = client_id
        self.client_secret = client_secret
        self.callback_url = callback_url
        self.base_url = "https://developer.api.autodesk.com"
        self.auth_url = "https://developer.api.autodesk.com/authentication/v1"
        
        # OAuth2 scopes needed for APS
        self.scopes = [
            "data:read",
            "data:write", 
            "data:create",
            "data:search",
            "account:read",
            "user-profile:read"
        ]
        
        self._access_token = None
        self._refresh_token = None
        self._token_expires_at = None
        self._user_id = None
    
    def get_authorization_url(self, state: str = None) -> str:
        """
        Generate the authorization URL for OAuth2 flow
        """
        params = {
            "response_type": "code",
            "client_id": self.client_id,
            "redirect_uri": self.callback_url,
            "scope": " ".join(self.scopes)
        }
        
        if state:
            params["state"] = state
        
        return f"{self.auth_url}/authorize?" + urlencode(params)
    
    def exchange_code_for_token(self, code: str) -> Dict[str, Any]:
        """
        Exchange authorization code for access token
        """
        try:
            token_url = f"{self.auth_url}/gettoken"
            
            headers = {
                "Content-Type": "application/x-www-form-urlencoded",
                "Accept": "application/json"
            }
            
            data = {
                "grant_type": "authorization_code",
                "code": code,
                "client_id": self.client_id,
                "client_secret": self.client_secret,
                "redirect_uri": self.callback_url
            }
            
            response = requests.post(token_url, headers=headers, data=data)
            response.raise_for_status()
            
            token_data = response.json()
            
            # Store token information
            self._access_token = token_data.get("access_token")
            self._refresh_token = token_data.get("refresh_token")
            expires_in = token_data.get("expires_in", 3600)
            self._token_expires_at = datetime.now() + timedelta(seconds=expires_in)
            
            return token_data
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Error exchanging code for token: {e}")
            raise Exception(f"Failed to exchange code for token: {e}")
    
    def refresh_access_token(self) -> Dict[str, Any]:
        """
        Refresh the access token using refresh token
        """
        if not self._refresh_token:
            raise Exception("No refresh token available")
        
        try:
            token_url = f"{self.auth_url}/refreshtoken"
            
            headers = {
                "Content-Type": "application/x-www-form-urlencoded",
                "Accept": "application/json"
            }
            
            data = {
                "grant_type": "refresh_token",
                "refresh_token": self._refresh_token,
                "client_id": self.client_id,
                "client_secret": self.client_secret
            }
            
            response = requests.post(token_url, headers=headers, data=data)
            response.raise_for_status()
            
            token_data = response.json()
            
            # Update token information
            self._access_token = token_data.get("access_token")
            if "refresh_token" in token_data:
                self._refresh_token = token_data.get("refresh_token")
            expires_in = token_data.get("expires_in", 3600)
            self._token_expires_at = datetime.now() + timedelta(seconds=expires_in)
            
            return token_data
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Error refreshing token: {e}")
            raise Exception(f"Failed to refresh token: {e}")
    
    def get_access_token(self) -> str:
        """
        Get valid access token, refreshing if necessary
        """
        if not self._access_token:
            raise Exception("No access token available. Please authenticate first.")
        
        # Check if token is expired
        if self._token_expires_at and datetime.now() >= self._token_expires_at:
            logger.info("Access token expired, refreshing...")
            self.refresh_access_token()
        
        return self._access_token
    
    def set_token(self, access_token: str, refresh_token: str = None, expires_in: int = 3600, user_id: int = None):
        """
        Set token information directly (for when tokens are stored/retrieved from database)
        """
        self._access_token = access_token
        self._refresh_token = refresh_token
        self._token_expires_at = datetime.now() + timedelta(seconds=expires_in)
        self._user_id = user_id
    
    def get_user_profile(self) -> Dict[str, Any]:
        """
        Get user profile information
        """
        try:
            headers = {
                "Authorization": f"Bearer {self.get_access_token()}",
                "Content-Type": "application/json"
            }
            
            response = requests.get(f"{self.base_url}/userprofile/v1/users/@me", headers=headers)
            response.raise_for_status()
            
            return response.json()
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Error getting user profile: {e}")
            raise Exception(f"Failed to get user profile: {e}")
    
    def get_hubs(self) -> List[Dict[str, Any]]:
        """
        Get list of hubs (teams/companies) user has access to
        """
        try:
            headers = {
                "Authorization": f"Bearer {self.get_access_token()}",
                "Content-Type": "application/json"
            }
            
            response = requests.get(f"{self.base_url}/project/v1/hubs", headers=headers)
            response.raise_for_status()
            
            data = response.json()
            return data.get("data", [])
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Error getting hubs: {e}")
            raise Exception(f"Failed to get hubs: {e}")
    
    def get_projects(self, hub_id: str) -> List[Dict[str, Any]]:
        """
        Get list of projects in a hub
        """
        try:
            headers = {
                "Authorization": f"Bearer {self.get_access_token()}",
                "Content-Type": "application/json"
            }
            
            response = requests.get(f"{self.base_url}/project/v1/hubs/{hub_id}/projects", headers=headers)
            response.raise_for_status()
            
            data = response.json()
            return data.get("data", [])
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Error getting projects for hub {hub_id}: {e}")
            raise Exception(f"Failed to get projects: {e}")
    
    def get_project_contents(self, hub_id: str, project_id: str, folder_id: str = None) -> List[Dict[str, Any]]:
        """
        Get contents of a project folder
        """
        try:
            headers = {
                "Authorization": f"Bearer {self.get_access_token()}",
                "Content-Type": "application/json"
            }
            
            if folder_id:
                url = f"{self.base_url}/data/v1/projects/{project_id}/folders/{folder_id}/contents"
            else:
                # Get top-level folders
                url = f"{self.base_url}/data/v1/projects/{project_id}/topFolders"
            
            response = requests.get(url, headers=headers)
            response.raise_for_status()
            
            data = response.json()
            return data.get("data", [])
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Error getting project contents: {e}")
            raise Exception(f"Failed to get project contents: {e}")
    
    def get_item_versions(self, project_id: str, item_id: str) -> List[Dict[str, Any]]:
        """
        Get versions of a specific item
        """
        try:
            headers = {
                "Authorization": f"Bearer {self.get_access_token()}",
                "Content-Type": "application/json"
            }
            
            response = requests.get(f"{self.base_url}/data/v1/projects/{project_id}/items/{item_id}/versions", headers=headers)
            response.raise_for_status()
            
            data = response.json()
            return data.get("data", [])
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Error getting item versions: {e}")
            raise Exception(f"Failed to get item versions: {e}")
    
    def translate_to_svf(self, urn: str, force_translate: bool = False) -> Dict[str, Any]:
        """
        Translate a model to SVF format for viewing
        """
        try:
            headers = {
                "Authorization": f"Bearer {self.get_access_token()}",
                "Content-Type": "application/json"
            }
            
            # Base64 encode the URN
            encoded_urn = base64.b64encode(urn.encode()).decode()
            
            # Check if already translated
            if not force_translate:
                manifest_response = requests.get(
                    f"{self.base_url}/modelderivative/v2/designdata/{encoded_urn}/manifest",
                    headers=headers
                )
                
                if manifest_response.status_code == 200:
                    manifest = manifest_response.json()
                    if manifest.get("status") == "success":
                        return manifest
            
            # Start translation job
            payload = {
                "input": {
                    "urn": encoded_urn
                },
                "output": {
                    "formats": [
                        {
                            "type": "svf",
                            "views": ["2d", "3d"]
                        }
                    ]
                }
            }
            
            response = requests.post(
                f"{self.base_url}/modelderivative/v2/designdata/job",
                headers=headers,
                json=payload
            )
            
            response.raise_for_status()
            return response.json()
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Error translating model: {e}")
            raise Exception(f"Failed to translate model: {e}")
    
    def translate_to_ifc(self, urn: str, force_translate: bool = False) -> Dict[str, Any]:
        """
        Translate a model to IFC format for Vitruvius processing
        """
        try:
            headers = {
                "Authorization": f"Bearer {self.get_access_token()}",
                "Content-Type": "application/json"
            }
            
            # Base64 encode the URN
            encoded_urn = base64.b64encode(urn.encode()).decode()
            
            # Start translation job
            payload = {
                "input": {
                    "urn": encoded_urn
                },
                "output": {
                    "formats": [
                        {
                            "type": "ifc",
                            "advanced": {
                                "exportFileStructure": "multiple",
                                "exportSettingsName": "standard"
                            }
                        }
                    ]
                }
            }
            
            response = requests.post(
                f"{self.base_url}/modelderivative/v2/designdata/job",
                headers=headers,
                json=payload
            )
            
            response.raise_for_status()
            return response.json()
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Error translating model to IFC: {e}")
            raise Exception(f"Failed to translate model to IFC: {e}")
    
    def get_derivative_manifest(self, urn: str) -> Dict[str, Any]:
        """
        Get the derivative manifest for a model
        """
        try:
            headers = {
                "Authorization": f"Bearer {self.get_access_token()}",
                "Content-Type": "application/json"
            }
            
            # Base64 encode the URN
            encoded_urn = base64.b64encode(urn.encode()).decode()
            
            response = requests.get(
                f"{self.base_url}/modelderivative/v2/designdata/{encoded_urn}/manifest",
                headers=headers
            )
            
            response.raise_for_status()
            return response.json()
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Error getting derivative manifest: {e}")
            raise Exception(f"Failed to get derivative manifest: {e}")
    
    def download_derivative(self, urn: str, derivative_urn: str) -> bytes:
        """
        Download a derivative file
        """
        try:
            headers = {
                "Authorization": f"Bearer {self.get_access_token()}",
                "Accept": "application/octet-stream"
            }
            
            # Base64 encode the URNs
            encoded_urn = base64.b64encode(urn.encode()).decode()
            encoded_derivative_urn = base64.b64encode(derivative_urn.encode()).decode()
            
            response = requests.get(
                f"{self.base_url}/modelderivative/v2/designdata/{encoded_urn}/manifest/{encoded_derivative_urn}",
                headers=headers
            )
            
            response.raise_for_status()
            return response.content
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Error downloading derivative: {e}")
            raise Exception(f"Failed to download derivative: {e}")
    
    def create_issue(self, container_id: str, issue_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Create an issue in ACC/BIM 360
        """
        try:
            headers = {
                "Authorization": f"Bearer {self.get_access_token()}",
                "Content-Type": "application/vnd.api+json"
            }
            
            # Format issue data for APS Issues API
            payload = {
                "data": {
                    "type": "issues",
                    "attributes": {
                        "title": issue_data.get("title", "Clash detected by Vitruvius"),
                        "description": issue_data.get("description", ""),
                        "status": "open",
                        "issueTypeId": issue_data.get("issue_type_id", ""),
                        "issueSubtypeId": issue_data.get("issue_subtype_id", ""),
                        "rootCauseId": issue_data.get("root_cause_id", ""),
                        "locationId": issue_data.get("location_id", ""),
                        "locationDetails": issue_data.get("location_details", ""),
                        "dueDate": issue_data.get("due_date", ""),
                        "assignedTo": issue_data.get("assigned_to", ""),
                        "assignedToType": issue_data.get("assigned_to_type", "user"),
                        "priority": issue_data.get("priority", "normal"),
                        "createdBy": issue_data.get("created_by", ""),
                        "createdAt": datetime.now().isoformat(),
                        "customAttributes": issue_data.get("custom_attributes", [])
                    }
                }
            }
            
            # Add pushpin (3D location) if provided
            if "pushpin" in issue_data:
                payload["data"]["attributes"]["pushpin"] = issue_data["pushpin"]
            
            response = requests.post(
                f"{self.base_url}/issues/v1/containers/{container_id}/issues",
                headers=headers,
                json=payload
            )
            
            response.raise_for_status()
            return response.json()
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Error creating issue: {e}")
            raise Exception(f"Failed to create issue: {e}")
    
    def get_issues(self, container_id: str, filters: Dict[str, Any] = None) -> List[Dict[str, Any]]:
        """
        Get issues from ACC/BIM 360
        """
        try:
            headers = {
                "Authorization": f"Bearer {self.get_access_token()}",
                "Content-Type": "application/json"
            }
            
            url = f"{self.base_url}/issues/v1/containers/{container_id}/issues"
            
            if filters:
                query_params = []
                for key, value in filters.items():
                    query_params.append(f"{key}={quote(str(value))}")
                if query_params:
                    url += "?" + "&".join(query_params)
            
            response = requests.get(url, headers=headers)
            response.raise_for_status()
            
            data = response.json()
            return data.get("data", [])
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Error getting issues: {e}")
            raise Exception(f"Failed to get issues: {e}")
    
    def save_tokens_to_db(self, db: Session, user_id: int):
        """
        Save APS tokens to database for persistence
        """
        try:
            user = db.query(User).filter(User.id == user_id).first()
            if not user:
                raise Exception("User not found")
            
            # Store tokens in user profile (you might want to create a separate table for this)
            user.aps_access_token = self._access_token
            user.aps_refresh_token = self._refresh_token
            user.aps_token_expires_at = self._token_expires_at
            
            db.commit()
            logger.info(f"Saved APS tokens for user {user_id}")
            
        except Exception as e:
            logger.error(f"Error saving tokens to database: {e}")
            raise Exception(f"Failed to save tokens: {e}")
    
    def load_tokens_from_db(self, db: Session, user_id: int) -> bool:
        """
        Load APS tokens from database
        """
        try:
            user = db.query(User).filter(User.id == user_id).first()
            if not user:
                return False
            
            if user.aps_access_token:
                self._access_token = user.aps_access_token
                self._refresh_token = user.aps_refresh_token
                self._token_expires_at = user.aps_token_expires_at
                self._user_id = user_id
                
                logger.info(f"Loaded APS tokens for user {user_id}")
                return True
            
            return False
            
        except Exception as e:
            logger.error(f"Error loading tokens from database: {e}")
            return False
    
    def is_token_valid(self) -> bool:
        """
        Check if the current token is valid and not expired
        """
        if not self._access_token:
            return False
        
        if self._token_expires_at and datetime.now() >= self._token_expires_at:
            return False
        
        return True
    
    def revoke_tokens(self, db: Session = None):
        """
        Revoke and clear tokens
        """
        try:
            # Try to revoke the token on APS side
            if self._access_token:
                headers = {
                    "Content-Type": "application/x-www-form-urlencoded",
                    "Accept": "application/json"
                }
                
                data = {
                    "token": self._access_token,
                    "client_id": self.client_id,
                    "client_secret": self.client_secret
                }
                
                # Note: APS doesn't have a standard revoke endpoint, so we'll just clear locally
                # In a real implementation, you might want to check if APS provides token revocation
                
            # Clear local tokens
            self._access_token = None
            self._refresh_token = None
            self._token_expires_at = None
            
            # Clear from database if db session provided
            if db and self._user_id:
                user = db.query(User).filter(User.id == self._user_id).first()
                if user:
                    user.aps_access_token = None
                    user.aps_refresh_token = None
                    user.aps_token_expires_at = None
                    db.commit()
                    
            self._user_id = None
            logger.info("Revoked APS tokens")
            
        except Exception as e:
            logger.error(f"Error revoking tokens: {e}")
            # Still clear local tokens even if revocation fails
            self._access_token = None
            self._refresh_token = None
            self._token_expires_at = None
            self._user_id = None
