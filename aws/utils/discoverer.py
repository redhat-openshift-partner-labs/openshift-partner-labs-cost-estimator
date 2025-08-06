"""
Enhanced AWS resource discovery orchestrator with optional cost integration.
"""

from services import SERVICE_REGISTRY, SERVICE_CONFIG, should_use_unified_discovery, should_fallback_to_individual
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
        """Discover resources using unified or modular approach with optional cost integration"""
        
        # Check if unified discovery should be used
        if should_use_unified_discovery():
            print("Using unified resource discovery via ResourceGroups API...")
            try:
                self.results = self._unified_discovery()
            except Exception as e:
                print(f"Unified discovery failed: {e}")
                if should_fallback_to_individual():
                    print("Falling back to individual service discovery...")
                    self.results = self._modular_discovery()
                else:
                    raise e
        else:
            print("Using modular service discovery...")
            self.results = self._modular_discovery()
        
        # Optional cost enrichment
        if include_costs:
            self.results = self._enrich_with_costs(self.results)
        
        return self.results
    
    def _unified_discovery(self) -> Dict[str, Dict[str, List[ResourceInfo]]]:
        """Discover resources using ResourceGroups API (unified approach)"""
        resource_groups_service = SERVICE_REGISTRY.get('ResourceGroups')
        if not resource_groups_service:
            raise Exception("ResourceGroups service not found in registry")
        
        client = resource_groups_service.get_client(self.session)
        unified_results = resource_groups_service.search_resources(
            client, self.tag_key, self.tag_value
        )
        
        # If resource enrichment is enabled, fetch additional details
        rg_config = SERVICE_CONFIG.get('ResourceGroups', {})
        if rg_config.get('enrich_resources', False):
            unified_results = self._enrich_unified_results(unified_results, resource_groups_service)
        
        # Return results in the expected format (single service with all resource types)
        return {'ResourceGroups': unified_results}
    
    def _modular_discovery(self) -> Dict[str, Dict[str, List[ResourceInfo]]]:
        """Discover resources using individual service modules (original approach)"""
        results = {}
        
        for service_name, service in SERVICE_REGISTRY.items():
            # Skip ResourceGroups service in modular mode
            if service_name == 'ResourceGroups':
                continue
                
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
                    
                    results[service_name] = service_resources
                    
                except Exception as e:
                    print(f"Error discovering {service_name} resources: {e}")
                    results[service_name] = {rt: [] for rt in service.resource_types}
        
        return results
    
    def _enrich_unified_results(
        self, 
        unified_results: Dict[str, List[ResourceInfo]], 
        resource_groups_service
    ) -> Dict[str, List[ResourceInfo]]:
        """Enrich unified results with additional resource details"""
        enriched_results = {}
        
        for resource_type, resources in unified_results.items():
            enriched_resources = []
            for resource in resources:
                try:
                    enriched_resource = resource_groups_service.get_resource_details(
                        resource, self.session
                    )
                    enriched_resources.append(enriched_resource)
                except Exception as e:
                    print(f"Warning: Could not enrich resource {resource.id}: {e}")
                    enriched_resources.append(resource)
            
            enriched_results[resource_type] = enriched_resources
        
        return enriched_results
    
    def _enrich_with_costs(
        self,
        all_resources: Dict[str, Dict[str, List[ResourceInfo]]]
    ) -> Dict[str, Dict[str, List[ResourceInfo]]]:
        """Enrich resources with cost information using AWS Pricing API"""
        # Initialize cost services
        explorer_service = COST_SERVICE_REGISTRY['explorer']
        analyzer_service = COST_SERVICE_REGISTRY['analyzer']
        pricing_service = COST_SERVICE_REGISTRY['pricing']
        
        # Store cost services for later use
        self.cost_services = {
            'explorer': explorer_service,
            'analyzer': analyzer_service,
            'pricing': pricing_service
        }
        
        # Set up cost analyzer with pricing service
        try:
            pricing_service.client = pricing_service.get_client(self.session)
            analyzer_service.set_pricing_service(pricing_service)
            analyzer_service.set_region(self.session.region_name or 'us-east-1')
            
            # Extract cluster UID from tag key for analyzer
            if 'kubernetes.io/cluster/' in self.tag_key:
                cluster_uid = self.tag_key.replace('kubernetes.io/cluster/', '')
                analyzer_service.set_cluster_uid(cluster_uid)
            
            print("Using AWS Pricing API for accurate cost calculation")
            
        except Exception as e:
            print(f"Warning: Could not initialize Pricing API: {e}")
            print("Falling back to Cost Explorer and estimated costs")
            
            # Fallback to Cost Explorer
            explorer_service.client = explorer_service.get_client(self.session)
            analyzer_service.set_explorer_service(explorer_service)
            
            if not self._validate_cost_explorer_availability(explorer_service):
                print("Warning: Cost Explorer also not available. Using estimated costs only.")
        
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