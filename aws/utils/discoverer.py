"""
Enhanced AWS resource discovery orchestrator with optional cost integration.
"""

from services import SERVICE_REGISTRY, SERVICE_CONFIG
from services.base import ResourceInfo
from cost import CostExplorerService, CostAnalyzerService, CostReporterService, CostSummary
from cost.registry import COST_SERVICE_REGISTRY
from typing import Dict, List, Any, Optional
from datetime import datetime, timedelta
import boto3


class AWSResourceDiscoverer:
    """Enhanced resource discoverer with optional cost integration"""
    
    def __init__(self, session: boto3.Session, tag_key: str, tag_value: str):
        self.session = session
        self.tag_key = tag_key
        self.tag_value = tag_value
        self.results = {}
        self.cost_services: Optional[Dict[str, Any]] = None
    
    def discover_all_resources(self, include_costs: bool = False) -> Dict[str, Dict[str, List[ResourceInfo]]]:
        """Discover resources across all registered services with optional cost integration"""
        for service_name, service in SERVICE_REGISTRY.items():
            if SERVICE_CONFIG.get(service_name, {}).get('enabled', True):
                try:
                    if service_name == 'ELB':
                        # ELB service needs special handling
                        service_resources = service.search_resources(
                            self.session, self.tag_key, self.tag_value
                        )
                    else:
                        client = service.get_client(self.session)
                        service_resources = service.search_resources(
                            client, self.tag_key, self.tag_value
                        )
                    
                    self.results[service_name] = service_resources
                    
                except Exception as e:
                    print(f"Error discovering {service_name} resources: {e}")
                    self.results[service_name] = {rt: [] for rt in service.resource_types}
        
        # Optional cost enrichment
        if include_costs:
            self.results = self._enrich_with_costs(self.results)
        
        return self.results
    
    def _enrich_with_costs(
        self,
        all_resources: Dict[str, Dict[str, List[ResourceInfo]]]
    ) -> Dict[str, Dict[str, List[ResourceInfo]]]:
        """Enrich resources with cost information"""
        # Initialize cost services
        explorer_service = COST_SERVICE_REGISTRY['explorer']
        analyzer_service = COST_SERVICE_REGISTRY['analyzer']
        
        # Store cost services for later use
        self.cost_services = {
            'explorer': explorer_service,
            'analyzer': analyzer_service
        }
        
        # Set up cost analyzer
        explorer_service.client = explorer_service.get_client(self.session)
        analyzer_service.set_explorer_service(explorer_service)
        
        # Validate Cost Explorer availability
        if not self._validate_cost_explorer_availability(explorer_service):
            print("Warning: Cost Explorer not available or not properly configured. Using estimated costs.")
        
        # Calculate date range for cost analysis
        end_date = datetime.now()
        start_date = end_date - timedelta(days=30)  # Default 30 days
        
        # Enrich each service's resources with costs
        for service_name, service in SERVICE_REGISTRY.items():
            if service_name in all_resources:
                service.set_cost_analyzer(analyzer_service)
                all_resources[service_name] = service.enrich_resources_with_costs(
                    all_resources[service_name], start_date, end_date
                )
        
        return all_resources
    
    def _validate_cost_explorer_availability(self, explorer_service) -> bool:
        """Validate that Cost Explorer is available and working"""
        try:
            # Try a simple cost query to test availability
            end_date = datetime.now()
            start_date = end_date - timedelta(days=1)
            
            # Use a simple filter to test Cost Explorer availability
            test_filter = {
                'Dimensions': {
                    'Key': 'SERVICE',
                    'Values': ['Amazon Elastic Compute Cloud - Compute']
                }
            }
            
            test_response = explorer_service.get_cost_and_usage(
                start_date, end_date,
                granularity='DAILY',
                metrics=['UnblendedCost'],
                filter_expression=test_filter
            )
            
            # If we get a response, Cost Explorer is working
            return 'ResultsByTime' in test_response
            
        except Exception as e:
            print(f"Cost Explorer validation failed: {e}")
            return False
    
    def generate_cost_summary(
        self,
        all_resources: Dict[str, Dict[str, List[ResourceInfo]]]
    ) -> Optional['CostSummary']:
        """Generate cost summary for all resources"""
        if not self.cost_services:
            return None
        
        analyzer_service = self.cost_services['analyzer']
        
        # Flatten all resources into a single list
        all_resource_list = []
        for service_resources in all_resources.values():
            for resource_list in service_resources.values():
                all_resource_list.extend(resource_list)
        
        # Calculate date range
        end_date = datetime.now()
        start_date = end_date - timedelta(days=30)
        
        return analyzer_service.generate_cost_summary(
            all_resource_list, start_date, end_date
        ) 