# Production use requires a separate commercial license from the Licensor.
# For commercial licenses, please contact Tiago Sasaki at tiago@confenge.com.br.

from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, List
from datetime import datetime
from dataclasses import dataclass


@dataclass
class TaskUpdate:
    """Data structure for task updates to external planning tools"""
    task_id: str
    name: Optional[str] = None
    cost: Optional[float] = None
    duration_change_days: Optional[int] = None
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    status: Optional[str] = None
    progress_percentage: Optional[float] = None
    notes: Optional[str] = None


@dataclass
class CostUpdate:
    """Data structure for cost updates to external budget tools"""
    cost_category: str
    amount: float
    currency: str = "USD"
    description: Optional[str] = None
    budget_code: Optional[str] = None
    effective_date: Optional[datetime] = None


@dataclass
class IntegrationResult:
    """Result of an integration operation"""
    success: bool
    message: str
    external_id: Optional[str] = None
    data: Optional[Dict[str, Any]] = None
    error_code: Optional[str] = None


class PlanningIntegrationService(ABC):
    """Abstract base class for planning tool integrations"""
    
    def __init__(self, api_key: str, base_url: str, project_id: str, config: Optional[Dict] = None):
        self.api_key = api_key
        self.base_url = base_url
        self.project_id = project_id
        self.config = config or {}
    
    @abstractmethod
    def test_connection(self) -> IntegrationResult:
        """Test connection to the planning tool"""
        pass
    
    @abstractmethod
    def get_project_info(self) -> IntegrationResult:
        """Get project information from the planning tool"""
        pass
    
    @abstractmethod
    def get_tasks(self) -> IntegrationResult:
        """Get all tasks from the planning tool project"""
        pass
    
    @abstractmethod
    def update_task(self, task_update: TaskUpdate) -> IntegrationResult:
        """Update a specific task in the planning tool"""
        pass
    
    @abstractmethod
    def create_task(self, task_update: TaskUpdate) -> IntegrationResult:
        """Create a new task in the planning tool"""
        pass
    
    @abstractmethod
    def sync_project_schedule(self, schedule_data: Dict[str, Any]) -> IntegrationResult:
        """Sync complete project schedule to planning tool"""
        pass
    
    def get_integration_type(self) -> str:
        """Return the type of integration (e.g., 'primavera', 'msproject')"""
        return self.__class__.__name__.lower().replace('service', '')


class BudgetIntegrationService(ABC):
    """Abstract base class for budget tool integrations"""
    
    def __init__(self, api_key: str, base_url: str, project_id: str, config: Optional[Dict] = None):
        self.api_key = api_key
        self.base_url = base_url
        self.project_id = project_id
        self.config = config or {}
    
    @abstractmethod
    def test_connection(self) -> IntegrationResult:
        """Test connection to the budget tool"""
        pass
    
    @abstractmethod
    def get_project_budget(self) -> IntegrationResult:
        """Get project budget information from the budget tool"""
        pass
    
    @abstractmethod
    def get_cost_categories(self) -> IntegrationResult:
        """Get all cost categories from the budget tool"""
        pass
    
    @abstractmethod
    def update_cost(self, cost_update: CostUpdate) -> IntegrationResult:
        """Update a specific cost in the budget tool"""
        pass
    
    @abstractmethod
    def create_cost_entry(self, cost_update: CostUpdate) -> IntegrationResult:
        """Create a new cost entry in the budget tool"""
        pass
    
    @abstractmethod
    def sync_project_costs(self, cost_data: List[CostUpdate]) -> IntegrationResult:
        """Sync complete project costs to budget tool"""
        pass
    
    def get_integration_type(self) -> str:
        """Return the type of integration (e.g., 'sage', 'quickbooks')"""
        return self.__class__.__name__.lower().replace('service', '')


class BaseIntegrationService:
    """Utility base class with common integration functionality"""
    
    @staticmethod
    def encrypt_api_key(api_key: str) -> str:
        """Encrypt API key for secure storage (simplified implementation)"""
        # In production, use proper encryption like Fernet from cryptography library
        import base64
        return base64.b64encode(api_key.encode()).decode()
    
    @staticmethod
    def decrypt_api_key(encrypted_key: str) -> str:
        """Decrypt API key for use (simplified implementation)"""
        # In production, use proper decryption like Fernet from cryptography library
        import base64
        return base64.b64decode(encrypted_key.encode()).decode()
    
    @staticmethod
    def validate_config(config: Dict[str, Any], required_fields: List[str]) -> bool:
        """Validate that required configuration fields are present"""
        return all(field in config for field in required_fields)
    
    @staticmethod
    def build_headers(api_key: str, content_type: str = "application/json") -> Dict[str, str]:
        """Build common HTTP headers for API requests"""
        return {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": content_type,
            "User-Agent": "Vitruvius-Integration/1.0"
        }
    
    @staticmethod
    def handle_api_error(response, operation: str) -> IntegrationResult:
        """Handle common API error responses"""
        try:
            error_data = response.json() if response.content else {}
        except:
            error_data = {}
        
        error_message = error_data.get('message', f'HTTP {response.status_code} error')
        
        return IntegrationResult(
            success=False,
            message=f"Failed to {operation}: {error_message}",
            error_code=str(response.status_code),
            data=error_data
        )