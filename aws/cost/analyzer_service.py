"""
Cost analysis service for analyzing resource costs and providing insights.
"""

from .base import CostService, CostRecord, CostSummary, OptimizationSuggestion
from .explorer_service import CostExplorerService
from .pricing_service import PricingService
from typing import Dict, List, Any, Optional
from datetime import datetime, timedelta
import boto3


class CostAnalyzerService(CostService):
    """Analyzes cost data and provides insights"""
    
    def __init__(self):
        super().__init__("CostAnalyzer")
        self.explorer_service: Optional[CostExplorerService] = None
        self.pricing_service: Optional[PricingService] = None
        self.cluster_uid: Optional[str] = None
        self.region: Optional[str] = None
    
    def set_explorer_service(self, explorer_service: CostExplorerService):
        """Set the cost explorer service"""
        self.explorer_service = explorer_service
    
    def set_pricing_service(self, pricing_service: PricingService):
        """Set the pricing service"""
        self.pricing_service = pricing_service
    
    def set_cluster_uid(self, cluster_uid: str):
        """Set the cluster UID for cost analysis"""
        self.cluster_uid = cluster_uid
    
    def set_region(self, region: str):
        """Set the AWS region for pricing calculations"""
        self.region = region
    
    def get_client(self, session: boto3.Session):
        """Cost analyzer doesn't need a direct client"""
        return None
    
    def analyze_resource_costs(
        self,
        resources: List['ResourceInfo'],
        start_date: datetime,
        end_date: datetime
    ) -> List['ResourceInfo']:
        """Analyze costs for a list of resources using AWS Pricing API"""
        if not self.pricing_service or not self.region:
            # Fallback to estimated costs if pricing service not available
            for resource in resources:
                self._apply_estimated_cost(resource, start_date, end_date)
            return resources
        
        # Calculate number of days for the cost period
        days = (end_date - start_date).days
        if days <= 0:
            days = 30  # Default to 30 days
        
        # Calculate accurate cost for each resource using Pricing API
        for resource in resources:
            try:
                cost_data = self.pricing_service.calculate_resource_cost(
                    resource, self.region, days
                )
                
                if cost_data:
                    resource.cost_data = cost_data
                    resource.cost_history = self._create_cost_records(cost_data)
                    resource.cost_forecast = self._get_cost_forecast(resource, end_date)
                    resource.optimization_suggestions = self._get_optimization_suggestions(resource)
                else:
                    self._apply_estimated_cost(resource, start_date, end_date)
                    
            except Exception as e:
                print(f"Error calculating cost for resource {resource.id}: {e}")
                self._apply_estimated_cost(resource, start_date, end_date)
        
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
    
    def _get_service_cost_data(
        self,
        service_filter: str,
        start_date: datetime,
        end_date: datetime
    ) -> Optional[Dict[str, Any]]:
        """Get cost data for a specific service type using Cost Explorer"""
        if not self.explorer_service:
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
            return self._process_cost_response(response)
            
        except Exception as e:
            print(f"Error getting cost data for service {service_filter}: {e}")
            return None
    
    def _distribute_cost_among_resources(
        self,
        resources: List['ResourceInfo'],
        total_cost_data: Dict[str, Any],
        start_date: datetime,
        end_date: datetime
    ):
        """Distribute total service cost among individual resources"""
        if not resources or not total_cost_data:
            return
        
        total_cost = total_cost_data.get('total_cost', 0.0)
        service_name = total_cost_data.get('service', 'Unknown')
        
        # Calculate weights for cost distribution based on resource characteristics
        resource_weights = []
        total_weight = 0.0
        
        for resource in resources:
            weight = self._calculate_resource_cost_weight(resource)
            resource_weights.append(weight)
            total_weight += weight
        
        # Distribute cost based on weights
        for i, resource in enumerate(resources):
            if total_weight > 0:
                resource_cost = total_cost * (resource_weights[i] / total_weight)
            else:
                # Equal distribution if no weights can be calculated
                resource_cost = total_cost / len(resources)
            
            # Apply cost data to resource
            resource.cost_data = {
                'total_cost': resource_cost,
                'service_breakdown': {service_name: resource_cost},
                'service': service_name,
                'is_estimated': False
            }
            resource.cost_history = self._create_cost_records(resource.cost_data)
            resource.cost_forecast = self._get_cost_forecast(resource, end_date)
            resource.optimization_suggestions = self._get_optimization_suggestions(resource)
    
    def _apply_estimated_cost(
        self,
        resource: 'ResourceInfo',
        start_date: datetime,
        end_date: datetime
    ):
        """Apply estimated cost to a resource"""
        cost_data = self._get_estimated_cost_for_resource(resource)
        if cost_data:
            resource.cost_data = cost_data
            resource.cost_history = self._create_cost_records(cost_data)
            resource.cost_forecast = self._get_cost_forecast(resource, end_date)
            resource.optimization_suggestions = self._get_optimization_suggestions(resource)
    
    def _calculate_resource_cost_weight(self, resource: 'ResourceInfo') -> float:
        """Calculate a weight for cost distribution based on resource characteristics"""
        # Get resource category
        resource_category = None
        if (hasattr(resource, 'additional_info') and 
            resource.additional_info and 
            'resource_category' in resource.additional_info):
            resource_category = resource.additional_info['resource_category']
        
        if resource_category == 'ec2_instance':
            # Weight based on instance type (larger instances get higher weight)
            return self._get_instance_type_weight(resource.type or 't3.micro')
        elif resource_category == 'ebs_volume':
            # Weight based on volume size and type
            size_gb = resource.additional_info.get('size_gb', 20) if resource.additional_info else 20
            volume_type = resource.additional_info.get('volume_type', 'gp2') if resource.additional_info else 'gp2'
            
            # Higher IOPS volumes get higher weight
            type_multiplier = {'gp2': 1.0, 'gp3': 1.1, 'io1': 2.0, 'io2': 2.0, 'sc1': 0.5, 'st1': 0.7}.get(volume_type, 1.0)
            return size_gb * type_multiplier
        elif resource_category in ['security_group', 'network_interface']:
            # These are typically free, so very low weight
            return 0.01
        else:
            # Default weight
            return 1.0
    
    def _get_instance_type_weight(self, instance_type: str) -> float:
        """Get relative weight for instance types based on typical cost"""
        instance_type_lower = instance_type.lower()
        
        # Weight mapping based on relative costs
        weight_map = {
            'nano': 0.25, 'micro': 0.5, 'small': 1.0, 'medium': 2.0, 'large': 4.0,
            'xlarge': 8.0, '2xlarge': 16.0, '4xlarge': 32.0, '8xlarge': 64.0,
            '12xlarge': 96.0, '16xlarge': 128.0, '24xlarge': 192.0
        }
        
        # Find size in instance type
        for size, weight in weight_map.items():
            if size in instance_type_lower:
                return weight
        
        # Default weight for unknown instance types
        return 4.0  # Assume 'large' equivalent
    
    def _get_service_filter_for_resource(self, resource: 'ResourceInfo') -> Optional[str]:
        """Get the appropriate AWS service filter for a resource type"""
        # Map resource categories to AWS services in Cost Explorer
        service_mapping = {
            'ec2_instance': 'Amazon Elastic Compute Cloud - Compute',
            'ebs_volume': 'Amazon Elastic Block Store',
            'security_group': 'Amazon Elastic Compute Cloud - Compute',
            'network_interface': 'Amazon Elastic Compute Cloud - Compute',
            'classic_elb': 'AWS Elastic Load Balancing',
            'alb_nlb': 'AWS Elastic Load Balancing'
        }
        
        # First check for resource category in additional_info
        if (hasattr(resource, 'additional_info') and 
            resource.additional_info and 
            'resource_category' in resource.additional_info):
            category = resource.additional_info['resource_category']
            if category in service_mapping:
                return service_mapping[category]
        
        # Fallback: determine resource type from the resource info
        if hasattr(resource, 'type') and resource.type:
            type_lower = resource.type.lower()
            if 'gb' in type_lower and ('gp2' in type_lower or 'gp3' in type_lower or 'io1' in type_lower):
                return service_mapping['ebs_volume']
            elif any(instance_type in type_lower for instance_type in ['t2.', 't3.', 'm5.', 'c5.', 'r5.']):
                return service_mapping['ec2_instance']
            elif 'vpc-' in resource.type:
                return service_mapping['security_group']
            elif 'interface' in type_lower:
                return service_mapping['network_interface']
        
        # Default to EC2 compute if we can't determine the type
        return service_mapping['ec2_instance']
    
    def _get_estimated_cost_for_resource(self, resource: 'ResourceInfo') -> Dict[str, Any]:
        """Provide estimated costs when actual cost data is not available"""
        # Improved estimation based on resource category and details
        
        # Check for resource category in additional_info first
        resource_category = None
        if (hasattr(resource, 'additional_info') and 
            resource.additional_info and 
            'resource_category' in resource.additional_info):
            resource_category = resource.additional_info['resource_category']
        
        # Calculate estimated cost based on resource category and details
        estimated_cost = 0.0
        service_name = 'Unknown'
        
        if resource_category == 'ec2_instance':
            # Estimate based on instance type
            estimated_cost = self._estimate_ec2_instance_cost(resource)
            service_name = 'EC2-Instance'
        elif resource_category == 'ebs_volume':
            # Estimate based on volume size and type
            estimated_cost = self._estimate_ebs_volume_cost(resource)
            service_name = 'EBS-Volume'
        elif resource_category == 'security_group':
            estimated_cost = 0.0  # Security groups are free
            service_name = 'Security-Group'
        elif resource_category == 'network_interface':
            estimated_cost = 0.0  # Basic network interfaces are free
            service_name = 'Network-Interface'
        else:
            # Fallback logic for resources without category
            if hasattr(resource, 'type') and resource.type:
                type_lower = resource.type.lower()
                if any(instance_type in type_lower for instance_type in ['t2.', 't3.', 'm5.', 'c5.', 'r5.']):
                    estimated_cost = self._estimate_ec2_instance_cost(resource)
                    service_name = 'EC2-Instance'
                elif 'gb' in type_lower:
                    estimated_cost = self._estimate_ebs_volume_cost(resource)
                    service_name = 'EBS-Volume'
        
        return {
            'total_cost': estimated_cost,
            'service_breakdown': {service_name: estimated_cost},
            'service': service_name,
            'is_estimated': True
        }
    
    def _estimate_ec2_instance_cost(self, resource: 'ResourceInfo') -> float:
        """Estimate EC2 instance cost based on instance type"""
        if not hasattr(resource, 'type') or not resource.type:
            return 50.0  # Default estimate
        
        instance_type = resource.type.lower()
        
        # Rough monthly cost estimates for common instance types
        cost_estimates = {
            't2.nano': 4.5,
            't2.micro': 9.0,
            't2.small': 18.0,
            't2.medium': 36.0,
            't2.large': 72.0,
            't3.nano': 4.0,
            't3.micro': 8.5,
            't3.small': 17.0,
            't3.medium': 34.0,
            't3.large': 68.0,
            't3.xlarge': 136.0,
            'm5.large': 75.0,
            'm5.xlarge': 150.0,
            'c5.large': 70.0,
            'c5.xlarge': 140.0,
            'r5.large': 100.0,
            'r5.xlarge': 200.0
        }
        
        # Find matching instance type
        for inst_type, cost in cost_estimates.items():
            if inst_type in instance_type:
                return cost
        
        # Default estimate if instance type not found
        return 50.0
    
    def _estimate_ebs_volume_cost(self, resource: 'ResourceInfo') -> float:
        """Estimate EBS volume cost based on size and type"""
        if not hasattr(resource, 'additional_info') or not resource.additional_info:
            return 10.0  # Default estimate
        
        # Get volume size
        size_gb = resource.additional_info.get('size_gb', 20)  # Default 20 GB
        volume_type = resource.additional_info.get('volume_type', 'gp2')
        
        # Cost per GB per month for different volume types
        cost_per_gb = {
            'gp2': 0.10,
            'gp3': 0.08,
            'io1': 0.125,
            'io2': 0.125,
            'sc1': 0.025,
            'st1': 0.045
        }
        
        price_per_gb = cost_per_gb.get(volume_type, 0.10)
        return size_gb * price_per_gb
    
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
        
        # Get resource category for more accurate suggestions
        resource_category = None
        if (hasattr(resource, 'additional_info') and 
            resource.additional_info and 
            'resource_category' in resource.additional_info):
            resource_category = resource.additional_info['resource_category']
        
        # Optimization suggestions based on resource category
        if resource_category == 'ec2_instance':
            # EC2 instance optimization
            if current_cost > 50:  # Lower threshold for more suggestions
                suggestion = OptimizationSuggestion(
                    resource_id=resource.id,
                    resource_type=resource.type,
                    current_cost=current_cost,
                    potential_savings=current_cost * 0.3,  # 30% potential savings
                    suggestion_type="resize",
                    description=f"Consider downsizing instance type {resource.type} for cost optimization",
                    implementation_steps=[
                        "Analyze current CPU and memory usage patterns",
                        "Identify smaller instance types that meet requirements",
                        "Test performance with smaller instances in non-production",
                        "Implement gradual migration during maintenance window"
                    ],
                    risk_level="medium"
                )
                suggestions.append(suggestion)
        elif resource_category == 'ebs_volume':
            # EBS volume optimization
            if current_cost > 20:  # Threshold for volume optimization
                suggestion = OptimizationSuggestion(
                    resource_id=resource.id,
                    resource_type=resource.type,
                    current_cost=current_cost,
                    potential_savings=current_cost * 0.2,  # 20% potential savings
                    suggestion_type="volume_optimization",
                    description=f"Consider optimizing EBS volume {resource.type}",
                    implementation_steps=[
                        "Review volume utilization and IOPS requirements",
                        "Consider switching to gp3 volumes for better cost/performance",
                        "Evaluate if volume size can be reduced",
                        "Implement volume type migration during low-traffic periods"
                    ],
                    risk_level="low"
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