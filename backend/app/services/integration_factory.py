# Production use requires a separate commercial license from the Licensor.
# For commercial licenses, please contact Tiago Sasaki at tiago@confenge.com.br.

import json
from typing import Optional, Dict, Any, Union
from .integrations.base import PlanningIntegrationService, BudgetIntegrationService, BaseIntegrationService
from .integrations.primavera import PrimaveraService
from .integrations.msproject import MSProjectService


class IntegrationFactory:
    """Factory class to create and manage integration services"""
    
    # Registry of available planning tool integrations
    PLANNING_INTEGRATIONS = {
        'primavera': PrimaveraService,
        'msproject': MSProjectService,
        'p6': PrimaveraService,  # Alias for Primavera P6
        'project': MSProjectService,  # Alias for MS Project
        'msp': MSProjectService,  # Alias for MS Project
    }
    
    # Registry of available budget tool integrations (placeholder for future implementations)
    BUDGET_INTEGRATIONS = {
        'sage': None,  # To be implemented
        'quickbooks': None,  # To be implemented
        'oracle_cost': None,  # To be implemented
        'sap': None,  # To be implemented
    }
    
    @classmethod
    def get_planning_service(
        cls, 
        integration_type: str, 
        api_key: str, 
        base_url: str, 
        project_id: str, 
        config: Optional[Dict] = None
    ) -> Optional[PlanningIntegrationService]:
        """
        Create a planning integration service instance
        
        Args:
            integration_type: Type of planning tool ('primavera', 'msproject', etc.)
            api_key: API key or access token for the planning tool
            base_url: Base URL for the planning tool API
            project_id: Project ID in the external planning tool
            config: Additional configuration parameters
            
        Returns:
            Planning integration service instance or None if not supported
        """
        if not integration_type or integration_type.lower() not in cls.PLANNING_INTEGRATIONS:
            return None
        
        service_class = cls.PLANNING_INTEGRATIONS[integration_type.lower()]
        if service_class is None:
            return None
        
        try:
            # Decrypt API key if it's encrypted
            decrypted_key = BaseIntegrationService.decrypt_api_key(api_key)
            
            # Parse config if it's a JSON string
            parsed_config = config
            if isinstance(config, str):
                try:
                    parsed_config = json.loads(config)
                except json.JSONDecodeError:
                    parsed_config = {}
            
            return service_class(
                api_key=decrypted_key,
                base_url=base_url,
                project_id=project_id,
                config=parsed_config or {}
            )
        except Exception as e:
            print(f"Error creating {integration_type} service: {str(e)}")
            return None
    
    @classmethod
    def get_budget_service(
        cls, 
        integration_type: str, 
        api_key: str, 
        base_url: str, 
        project_id: str, 
        config: Optional[Dict] = None
    ) -> Optional[BudgetIntegrationService]:
        """
        Create a budget integration service instance
        
        Args:
            integration_type: Type of budget tool ('sage', 'quickbooks', etc.)
            api_key: API key or access token for the budget tool
            base_url: Base URL for the budget tool API
            project_id: Project ID in the external budget tool
            config: Additional configuration parameters
            
        Returns:
            Budget integration service instance or None if not supported
        """
        if not integration_type or integration_type.lower() not in cls.BUDGET_INTEGRATIONS:
            return None
        
        service_class = cls.BUDGET_INTEGRATIONS[integration_type.lower()]
        if service_class is None:
            return None
        
        try:
            # Decrypt API key if it's encrypted
            decrypted_key = BaseIntegrationService.decrypt_api_key(api_key)
            
            # Parse config if it's a JSON string
            parsed_config = config
            if isinstance(config, str):
                try:
                    parsed_config = json.loads(config)
                except json.JSONDecodeError:
                    parsed_config = {}
            
            return service_class(
                api_key=decrypted_key,
                base_url=base_url,
                project_id=project_id,
                config=parsed_config or {}
            )
        except Exception as e:
            print(f"Error creating {integration_type} service: {str(e)}")
            return None
    
    @classmethod
    def get_available_planning_integrations(cls) -> Dict[str, Dict[str, Any]]:
        """Get list of available planning tool integrations with their metadata"""
        return {
            'primavera': {
                'name': 'Oracle Primavera P6',
                'description': 'Enterprise project portfolio management',
                'aliases': ['p6'],
                'supported_features': [
                    'project_info', 'tasks', 'update_task', 'create_task', 
                    'sync_schedule', 'cost_accounts'
                ],
                'required_config': ['database_instance', 'user_name'],
                'optional_config': ['timeout', 'api_version']
            },
            'msproject': {
                'name': 'Microsoft Project',
                'description': 'Microsoft Project Online and Project for the Web',
                'aliases': ['project', 'msp'],
                'supported_features': [
                    'project_info', 'tasks', 'update_task', 'create_task', 
                    'sync_schedule', 'buckets'
                ],
                'required_config': ['tenant_id'],
                'optional_config': ['site_url']
            }
        }
    
    @classmethod
    def get_available_budget_integrations(cls) -> Dict[str, Dict[str, Any]]:
        """Get list of available budget tool integrations with their metadata"""
        return {
            'sage': {
                'name': 'Sage Construction Management',
                'description': 'Construction project accounting and management',
                'status': 'planned',
                'supported_features': [],
                'required_config': [],
                'optional_config': []
            },
            'quickbooks': {
                'name': 'QuickBooks Enterprise',
                'description': 'Small to medium business accounting software',
                'status': 'planned',
                'supported_features': [],
                'required_config': [],
                'optional_config': []
            },
            'oracle_cost': {
                'name': 'Oracle Cost Management',
                'description': 'Enterprise cost management and accounting',
                'status': 'planned',
                'supported_features': [],
                'required_config': [],
                'optional_config': []
            },
            'sap': {
                'name': 'SAP Project System',
                'description': 'Enterprise resource planning for project management',
                'status': 'planned',
                'supported_features': [],
                'required_config': [],
                'optional_config': []
            }
        }
    
    @classmethod
    def validate_integration_config(cls, integration_type: str, config: Dict[str, Any]) -> tuple[bool, str]:
        """
        Validate integration configuration
        
        Args:
            integration_type: Type of integration
            config: Configuration to validate
            
        Returns:
            Tuple of (is_valid, error_message)
        """
        planning_integrations = cls.get_available_planning_integrations()
        budget_integrations = cls.get_available_budget_integrations()
        
        integration_info = (
            planning_integrations.get(integration_type.lower()) or 
            budget_integrations.get(integration_type.lower())
        )
        
        if not integration_info:
            return False, f"Unknown integration type: {integration_type}"
        
        # Check required configuration fields
        required_fields = integration_info.get('required_config', [])
        missing_fields = [field for field in required_fields if field not in config]
        
        if missing_fields:
            return False, f"Missing required configuration fields: {', '.join(missing_fields)}"
        
        return True, "Configuration is valid"
    
    @classmethod
    def create_integration_from_project(cls, project_data: Dict[str, Any]) -> Dict[str, Optional[Union[PlanningIntegrationService, BudgetIntegrationService]]]:
        """
        Create all configured integration services for a project
        
        Args:
            project_data: Project data dictionary with integration fields
            
        Returns:
            Dictionary with 'planning' and 'budget' service instances
        """
        services = {
            'planning': None,
            'budget': None
        }
        
        # Create planning service if configured
        if (project_data.get('planning_tool_connected') and 
            project_data.get('planning_tool_api_key') and 
            project_data.get('planning_tool_project_id')):
            
            services['planning'] = cls.get_planning_service(
                integration_type=project_data['planning_tool_connected'],
                api_key=project_data['planning_tool_api_key'],
                base_url=project_data.get('planning_tool_base_url', ''),
                project_id=project_data['planning_tool_project_id'],
                config=project_data.get('planning_tool_config')
            )
        
        # Create budget service if configured
        if (project_data.get('budget_tool_connected') and 
            project_data.get('budget_tool_api_key') and 
            project_data.get('budget_tool_project_id')):
            
            services['budget'] = cls.get_budget_service(
                integration_type=project_data['budget_tool_connected'],
                api_key=project_data['budget_tool_api_key'],
                base_url=project_data.get('budget_tool_base_url', ''),
                project_id=project_data['budget_tool_project_id'],
                config=project_data.get('budget_tool_config')
            )
        
        return services