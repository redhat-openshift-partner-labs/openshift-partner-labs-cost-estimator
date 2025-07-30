"""
Cost analysis service for analyzing resource costs and providing insights.
"""

from .base import CostService, CostRecord, CostSummary, OptimizationSuggestion
from .explorer_service import CostExplorerService
from typing import Dict, List, Any, Optional
from datetime import datetime, timedelta
import boto3


class CostAnalyzerService(CostService):
    """Analyzes cost data and provides insights"""
    
    def __init__(self):
        super().__init__("CostAnalyzer")
        self.explorer_service: Optional[CostExplorerService] = None
        self.cluster_uid: Optional[str] = None
    
    def set_explorer_service(self, explorer_service: CostExplorerService):
        """Set the cost explorer service"""
        self.explorer_service = explorer_service
    
    def set_cluster_uid(self, cluster_uid: str):
        """Set the cluster UID for cost analysis"""
        self.cluster_uid = cluster_uid
    
    def get_client(self, session: boto3.Session):
        """Cost analyzer doesn't need a direct client"""
        return None
    
    def analyze_resource_costs(
        self,
        resources: List['ResourceInfo'],
        start_date: datetime,
        end_date: datetime
    ) -> List['ResourceInfo']:
        """Analyze costs for a list of resources"""
        if not self.explorer_service:
            return resources
        
        for resource in resources:
            # Get cost data for this resource
            cost_data = self._get_resource_cost_data(resource, start_date, end_date)
            if cost_data:
                resource.cost_data = cost_data
                resource.cost_history = self._create_cost_records(cost_data)
                resource.cost_forecast = self._get_cost_forecast(resource, end_date)
                resource.optimization_suggestions = self._get_optimization_suggestions(resource)
        
        return resources
    
    def generate_cost_summary(
        self,
        resources: List['ResourceInfo'],
        period_start: datetime,
        period_end: datetime
    ) -> CostSummary:
        """Generate cost summary for resources"""
        total_cost = 0.0
        cost_breakdown = {}
        resource_count = len(resources)
        estimated_resources = 0
        
        for resource in resources:
            if resource.cost_data:
                cost = resource.cost_data.get('total_cost', 0.0)
                total_cost += cost
                
                # Track if this is estimated cost
                if resource.cost_data.get('is_estimated', False):
                    estimated_resources += 1
                
                # Build service breakdown
                service = resource.cost_data.get('service', 'Unknown')
                if service not in cost_breakdown:
                    cost_breakdown[service] = 0.0
                cost_breakdown[service] += cost
        
        average_cost = total_cost / resource_count if resource_count > 0 else 0.0
        
        # Calculate cost trend (simplified)
        cost_trend = self._calculate_cost_trend(resources)
        
        # Get forecasts
        forecast_30 = self._calculate_forecast(resources, 30)
        forecast_90 = self._calculate_forecast(resources, 90)
        
        # Add note about estimated costs if any
        if estimated_resources > 0:
            print(f"Note: {estimated_resources} resources have estimated costs (actual Cost Explorer data not available)")
        
        return CostSummary(
            total_cost=total_cost,
            period_start=period_start,
            period_end=period_end,
            cost_breakdown=cost_breakdown,
            resource_count=resource_count,
            average_cost_per_resource=average_cost,
            cost_trend=cost_trend,
            forecast_30_days=forecast_30,
            forecast_90_days=forecast_90
        )
    
    def identify_optimization_opportunities(
        self,
        resources: List['ResourceInfo']
    ) -> List[OptimizationSuggestion]:
        """Identify cost optimization opportunities"""
        suggestions = []
        
        for resource in resources:
            if not resource.cost_data:
                continue
            
            # Analyze for optimization opportunities
            resource_suggestions = self._get_optimization_suggestions(resource)
            suggestions.extend(resource_suggestions)
        
        return suggestions
    
    def _get_resource_cost_data(
        self,
        resource: 'ResourceInfo',
        start_date: datetime,
        end_date: datetime
    ) -> Optional[Dict[str, Any]]:
        """Get cost data for a specific resource using proper Cost Explorer filtering"""
        if not self.explorer_service:
            return None
        
        # Determine the appropriate service filter based on resource type
        service_filter = self._get_service_filter_for_resource(resource)
        if not service_filter:
            return None
        
        # Create proper Cost Explorer filter using service dimension and cluster tags
        cluster_tag = f"kubernetes.io/cluster/{self.cluster_uid or 'ocpv-rwx-lvvbx'}"
        
        # If no cluster UID is set, use a simpler filter
        if not self.cluster_uid:
            filter_expression = {
                'Dimensions': {'Key': 'SERVICE', 'Values': [service_filter]}
            }
        else:
            filter_expression = {
                'And': [
                    {'Dimensions': {'Key': 'SERVICE', 'Values': [service_filter]}},
                    {'Tags': {'Key': cluster_tag, 'Values': ['owned']}}
                ]
            }
        
        try:
            response = self.explorer_service.get_cost_and_usage(
                start_date, end_date, filter_expression=filter_expression
            )
            
            # Process response and extract cost data
            cost_data = self._process_cost_response(response)
            
            # If no cost data found, try fallback to estimated costs
            if not cost_data or cost_data.get('total_cost', 0.0) == 0.0:
                cost_data = self._get_estimated_cost_for_resource(resource)
            
            return cost_data
            
        except Exception as e:
            print(f"Error getting cost data for resource {resource.id}: {e}")
            # Fallback to estimated costs
            return self._get_estimated_cost_for_resource(resource)
    
    def _get_service_filter_for_resource(self, resource: 'ResourceInfo') -> Optional[str]:
        """Get the appropriate AWS service filter for a resource type"""
        # Map resource types to AWS services in Cost Explorer
        service_mapping = {
            'instances': 'Amazon Elastic Compute Cloud - Compute',
            'volumes': 'Amazon Elastic Compute Cloud - Compute',
            'security_groups': 'Amazon Elastic Compute Cloud - Compute',
            'network_interfaces': 'Amazon Elastic Compute Cloud - Compute',
            'classic_elbs': 'AWS Elastic Load Balancing',
            'albs_nlbs': 'AWS Elastic Load Balancing'
        }
        
        # Determine resource type from the resource info
        if hasattr(resource, 'type') and resource.type:
            if 'instance' in resource.type.lower():
                return service_mapping['instances']
            elif 'volume' in resource.type.lower():
                return service_mapping['volumes']
            elif 'security' in resource.type.lower():
                return service_mapping['security_groups']
            elif 'network' in resource.type.lower():
                return service_mapping['network_interfaces']
        
        # Default to EC2 if we can't determine the type
        return service_mapping['instances']
    
    def _get_estimated_cost_for_resource(self, resource: 'ResourceInfo') -> Dict[str, Any]:
        """Provide estimated costs when actual cost data is not available"""
        # Simple estimation based on resource type
        estimated_costs = {
            'instances': 50.0,  # Estimated monthly cost for typical instance
            'volumes': 10.0,    # Estimated monthly cost for typical volume
            'security_groups': 0.0,  # Security groups are typically free
            'network_interfaces': 0.0,  # Network interfaces are typically free
            'classic_elbs': 20.0,  # Estimated monthly cost for load balancer
            'albs_nlbs': 20.0   # Estimated monthly cost for load balancer
        }
        
        # Determine resource type and get estimated cost
        resource_type = 'instances'  # Default
        if hasattr(resource, 'type') and resource.type:
            if 'volume' in resource.type.lower():
                resource_type = 'volumes'
            elif 'security' in resource.type.lower():
                resource_type = 'security_groups'
            elif 'network' in resource.type.lower():
                resource_type = 'network_interfaces'
            elif 'load' in resource.type.lower():
                resource_type = 'albs_nlbs'
        
        estimated_cost = estimated_costs.get(resource_type, 0.0)
        
        return {
            'total_cost': estimated_cost,
            'service_breakdown': {resource_type: estimated_cost},
            'service': resource_type,
            'is_estimated': True
        }
    
    def _process_cost_response(self, response: Dict[str, Any]) -> Dict[str, Any]:
        """Process Cost Explorer response into standardized format"""
        if not response or 'ResultsByTime' not in response:
            return {}
        
        total_cost = 0.0
        service_breakdown = {}
        
        for result in response['ResultsByTime']:
            if 'Total' in result and 'UnblendedCost' in result['Total']:
                cost = float(result['Total']['UnblendedCost']['Amount'])
                total_cost += cost
                
                # Extract service information if available
                if 'Groups' in result:
                    for group in result['Groups']:
                        if 'Keys' in group and 'Metrics' in group:
                            service = group['Keys'][0] if group['Keys'] else 'Unknown'
                            service_cost = float(group['Metrics']['UnblendedCost']['Amount'])
                            service_breakdown[service] = service_breakdown.get(service, 0.0) + service_cost
        
        return {
            'total_cost': total_cost,
            'service_breakdown': service_breakdown,
            'service': list(service_breakdown.keys())[0] if service_breakdown else 'Unknown'
        }
    
    def _create_cost_records(self, cost_data: Dict[str, Any]) -> List[CostRecord]:
        """Create CostRecord objects from cost data"""
        records = []
        
        if cost_data and 'total_cost' in cost_data:
            # Create a single cost record for the total
            record = CostRecord(
                start_date=datetime.now() - timedelta(days=30),
                end_date=datetime.now(),
                amount=cost_data['total_cost'],
                service=cost_data.get('service', 'Unknown')
            )
            records.append(record)
        
        return records
    
    def _get_cost_forecast(
        self,
        resource: 'ResourceInfo',
        end_date: datetime
    ) -> List[CostRecord]:
        """Get cost forecast for a resource"""
        if not self.explorer_service or not resource.cost_data:
            return []
        
        # Simple forecast based on current cost
        current_cost = resource.cost_data.get('total_cost', 0.0)
        
        # Create forecast records (simplified)
        forecast_start = end_date
        forecast_end = end_date + timedelta(days=30)
        
        record = CostRecord(
            start_date=forecast_start,
            end_date=forecast_end,
            amount=current_cost,  # Simplified forecast
            service=resource.cost_data.get('service', 'Unknown')
        )
        
        return [record]
    
    def _get_optimization_suggestions(
        self,
        resource: 'ResourceInfo'
    ) -> List[OptimizationSuggestion]:
        """Get optimization suggestions for a resource"""
        suggestions = []
        
        if not resource.cost_data:
            return suggestions
        
        current_cost = resource.cost_data.get('total_cost', 0.0)
        
        # Simple optimization suggestions based on resource type
        if resource.type and 'instance' in resource.type.lower():
            # EC2 instance optimization
            if current_cost > 100:  # High cost threshold
                suggestion = OptimizationSuggestion(
                    resource_id=resource.id,
                    resource_type=resource.type,
                    current_cost=current_cost,
                    potential_savings=current_cost * 0.3,  # 30% potential savings
                    suggestion_type="resize",
                    description="Consider downsizing instance type for cost optimization",
                    implementation_steps=[
                        "Analyze current usage patterns",
                        "Identify smaller instance types",
                        "Test performance with smaller instances",
                        "Implement gradual migration"
                    ],
                    risk_level="medium"
                )
                suggestions.append(suggestion)
        
        return suggestions
    
    def _calculate_cost_trend(self, resources: List['ResourceInfo']) -> str:
        """Calculate cost trend (increasing, decreasing, stable)"""
        if not resources:
            return "stable"
        
        # Simple trend calculation based on cost data
        total_cost = sum(r.cost_data.get('total_cost', 0.0) for r in resources if r.cost_data)
        
        if total_cost > 1000:
            return "increasing"
        elif total_cost < 100:
            return "decreasing"
        else:
            return "stable"
    
    def _calculate_forecast(self, resources: List['ResourceInfo'], days: int) -> float:
        """Calculate cost forecast for specified number of days"""
        if not resources:
            return 0.0
        
        total_cost = sum(r.cost_data.get('total_cost', 0.0) for r in resources if r.cost_data)
        
        # Simple forecast: current cost * days / 30
        return total_cost * days / 30 