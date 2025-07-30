"""
Base classes and shared types for AWS services.
"""

from dataclasses import dataclass
from typing import Dict, List, Any, Optional
from abc import ABC, abstractmethod
import boto3
from botocore.exceptions import ClientError


@dataclass
class ResourceInfo:
    """Enhanced resource information with optional cost data"""
    id: str
    name: Optional[str] = None
    type: Optional[str] = None
    state: Optional[str] = None
    region: Optional[str] = None
    additional_info: Optional[Dict[str, Any]] = None
    # Optional cost-related fields (None by default for backward compatibility)
    cost_data: Optional[Dict[str, Any]] = None
    cost_history: Optional[List['CostRecord']] = None
    cost_forecast: Optional[List['CostRecord']] = None
    optimization_suggestions: Optional[List['OptimizationSuggestion']] = None


class AWSService(ABC):
    """Enhanced abstract base class with optional cost estimation support"""
    
    def __init__(self, service_name: str, resource_types: List[str]):
        self.service_name = service_name
        self.resource_types = resource_types
        self.cost_analyzer: Optional['CostAnalyzerService'] = None
    
    @abstractmethod
    def get_client(self, session: boto3.Session):
        """Return the appropriate AWS client for this service"""
        pass
    
    @abstractmethod
    def search_resources(self, client, tag_key: str, tag_value: str) -> Dict[str, List[ResourceInfo]]:
        """Search for resources with the specified tag"""
        pass
    
    def handle_error(self, error: ClientError, resource_type: str):
        """Standardized error handling"""
        print(f"Error searching {self.service_name} {resource_type}: {error}")
    
    # Optional cost integration methods
    def set_cost_analyzer(self, cost_analyzer: 'CostAnalyzerService'):
        """Set the cost analyzer for this service (optional)"""
        self.cost_analyzer = cost_analyzer
    
    def enrich_resources_with_costs(
        self,
        resources: Dict[str, List[ResourceInfo]],
        start_date: 'datetime',
        end_date: 'datetime'
    ) -> Dict[str, List[ResourceInfo]]:
        """Enrich discovered resources with cost information (optional)"""
        if not self.cost_analyzer:
            return resources
        
        for resource_type, resource_list in resources.items():
            enriched_resources = self.cost_analyzer.analyze_resource_costs(
                resource_list, start_date, end_date
            )
            resources[resource_type] = enriched_resources
        
        return resources 