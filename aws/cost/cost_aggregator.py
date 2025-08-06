"""
Cost aggregation and analysis for AWS resources.

This module provides comprehensive cost aggregation, analysis, and reporting
capabilities for discovered AWS resources.
"""

from typing import Dict, List, Any, Optional
from dataclasses import dataclass, field
from datetime import datetime, timedelta
import json
from .cost_categories import CostCategory, CostClassifier, CostPriority


@dataclass
class ResourceCostSummary:
    """Summary of costs for a single resource"""
    resource_id: str
    resource_name: Optional[str]
    resource_type: str
    service: str
    region: str
    cost_category: CostCategory
    cost_priority: CostPriority
    total_cost: float
    service_breakdown: Dict[str, float]
    is_estimated: bool
    pricing_source: str
    additional_details: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ComprehensiveCostSummary:
    """Comprehensive cost summary for all discovered resources"""
    cluster_id: str
    region: str
    analysis_date: datetime
    period_days: int
    
    # Overall totals
    total_monthly_cost: float
    total_billable_cost: float
    total_resources: int
    billable_resources: int
    free_resources: int
    
    # Cost breakdowns
    cost_by_category: Dict[CostCategory, float]
    cost_by_service: Dict[str, float] 
    cost_by_priority: Dict[CostPriority, float]
    cost_by_region: Dict[str, float]
    
    # Resource details
    resource_summaries: List[ResourceCostSummary]
    highest_cost_resources: List[ResourceCostSummary]
    
    # Analysis insights
    cost_distribution_analysis: Dict[str, Any]
    optimization_potential: Dict[str, Any]
    cost_trends: Dict[str, Any] = field(default_factory=dict)


class CostAggregator:
    """Aggregates and analyzes cost data from multiple resources"""
    
    def __init__(self):
        self.cost_thresholds = {
            'high_cost_resource': 50.0,  # $50+/month
            'medium_cost_resource': 10.0,  # $10-50/month
            'optimization_threshold': 100.0  # Consider optimization if total > $100/month
        }
    
    def aggregate_costs(
        self,
        cost_results: Dict[str, Dict[str, Any]], 
        resources: List['ResourceInfo'],
        cluster_id: str,
        region: str,
        period_days: int = 30
    ) -> ComprehensiveCostSummary:
        """Aggregate cost data into a comprehensive summary"""
        
        # Create resource lookup
        resource_lookup = {r.id: r for r in resources}
        
        # Create resource cost summaries
        resource_summaries = []
        total_cost = 0.0
        billable_cost = 0.0
        
        for resource_id, cost_data in cost_results.items():
            resource = resource_lookup.get(resource_id)
            if not resource:
                continue
            
            resource_type = self._determine_resource_type(resource)
            cost_category = CostClassifier.get_cost_category(resource_type)
            cost_priority = CostClassifier.get_cost_priority(resource_type)
            
            cost = cost_data.get('total_cost', 0.0)
            total_cost += cost
            
            if CostClassifier.is_billable(resource_type):
                billable_cost += cost
            
            summary = ResourceCostSummary(
                resource_id=resource.id,
                resource_name=resource.name,
                resource_type=resource_type,
                service=cost_data.get('service', 'Unknown'),
                region=resource.region or region,
                cost_category=cost_category,
                cost_priority=cost_priority,
                total_cost=cost,
                service_breakdown=cost_data.get('service_breakdown', {}),
                is_estimated=cost_data.get('is_estimated', True),
                pricing_source=cost_data.get('pricing_source', 'Unknown'),
                additional_details={
                    'hourly_rate': cost_data.get('hourly_rate'),
                    'monthly_rate_per_gb': cost_data.get('monthly_rate_per_gb'),
                    'data_processing_rate': cost_data.get('data_processing_rate'),
                    'estimated_gb_processed': cost_data.get('estimated_gb_processed'),
                    'estimated_gb_stored': cost_data.get('estimated_gb_stored'),
                    'calculation_failed': cost_data.get('calculation_failed', False)
                }
            )
            resource_summaries.append(summary)
        
        # Calculate breakdowns
        cost_by_category = self._calculate_cost_by_category(resource_summaries)
        cost_by_service = self._calculate_cost_by_service(resource_summaries)
        cost_by_priority = self._calculate_cost_by_priority(resource_summaries)
        cost_by_region = self._calculate_cost_by_region(resource_summaries)
        
        # Get highest cost resources
        highest_cost_resources = sorted(
            resource_summaries, 
            key=lambda x: x.total_cost, 
            reverse=True
        )[:10]  # Top 10 most expensive
        
        # Perform cost analysis
        cost_distribution_analysis = self._analyze_cost_distribution(resource_summaries)
        optimization_potential = self._analyze_optimization_potential(resource_summaries, total_cost)
        
        # Scale costs to monthly if needed
        monthly_multiplier = 30.0 / period_days if period_days != 30 else 1.0
        monthly_total_cost = total_cost * monthly_multiplier
        monthly_billable_cost = billable_cost * monthly_multiplier
        
        return ComprehensiveCostSummary(
            cluster_id=cluster_id,
            region=region,
            analysis_date=datetime.now(),
            period_days=period_days,
            total_monthly_cost=monthly_total_cost,
            total_billable_cost=monthly_billable_cost,
            total_resources=len(resource_summaries),
            billable_resources=len([r for r in resource_summaries if CostClassifier.is_billable(r.resource_type)]),
            free_resources=len([r for r in resource_summaries if CostClassifier.is_free(r.resource_type)]),
            cost_by_category=cost_by_category,
            cost_by_service=cost_by_service,
            cost_by_priority=cost_by_priority,
            cost_by_region=cost_by_region,
            resource_summaries=resource_summaries,
            highest_cost_resources=highest_cost_resources,
            cost_distribution_analysis=cost_distribution_analysis,
            optimization_potential=optimization_potential
        )
    
    def _determine_resource_type(self, resource: 'ResourceInfo') -> str:
        """Determine resource type from various sources"""
        if hasattr(resource, 'additional_info') and resource.additional_info:
            discovery_method = resource.additional_info.get('discovery_method')
            if discovery_method == 'resource_groups_api':
                service = resource.additional_info.get('service', '')
                resource_type = resource.additional_info.get('resource_type', '')
                
                # Map ARN components to our resource categories
                if service == 'ec2':
                    if resource_type == 'instance':
                        return 'instances'
                    elif resource_type == 'volume':
                        return 'volumes'
                    elif 'natgateway' in resource_type:
                        return 'nat_gateways'
                    elif 'elastic-ip' in resource_type:
                        return 'elastic_ips'
                    elif 'vpc-endpoint' in resource_type:
                        return 'vpc_endpoints'
                    elif 'security-group' in resource_type:
                        return 'security_groups'
                elif service == 's3':
                    return 's3_buckets'
                elif service == 'route53':
                    return 'route53_zones'
                elif service == 'elasticloadbalancing':
                    return 'albs_nlbs'
        
        # Fallback to resource type or other_resources
        return getattr(resource, 'type', 'other_resources')
    
    def _calculate_cost_by_category(self, summaries: List[ResourceCostSummary]) -> Dict[CostCategory, float]:
        """Calculate total cost by cost category"""
        category_costs = {}
        for summary in summaries:
            if summary.cost_category not in category_costs:
                category_costs[summary.cost_category] = 0.0
            category_costs[summary.cost_category] += summary.total_cost
        return category_costs
    
    def _calculate_cost_by_service(self, summaries: List[ResourceCostSummary]) -> Dict[str, float]:
        """Calculate total cost by AWS service"""
        service_costs = {}
        for summary in summaries:
            if summary.service not in service_costs:
                service_costs[summary.service] = 0.0
            service_costs[summary.service] += summary.total_cost
        return service_costs
    
    def _calculate_cost_by_priority(self, summaries: List[ResourceCostSummary]) -> Dict[CostPriority, float]:
        """Calculate total cost by priority level"""
        priority_costs = {}
        for summary in summaries:
            if summary.cost_priority not in priority_costs:
                priority_costs[summary.cost_priority] = 0.0
            priority_costs[summary.cost_priority] += summary.total_cost
        return priority_costs
    
    def _calculate_cost_by_region(self, summaries: List[ResourceCostSummary]) -> Dict[str, float]:
        """Calculate total cost by region"""
        region_costs = {}
        for summary in summaries:
            region = summary.region or 'Unknown'
            if region not in region_costs:
                region_costs[region] = 0.0
            region_costs[region] += summary.total_cost
        return region_costs
    
    def _analyze_cost_distribution(self, summaries: List[ResourceCostSummary]) -> Dict[str, Any]:
        """Analyze the distribution of costs across resources"""
        if not summaries:
            return {}
        
        costs = [s.total_cost for s in summaries]
        total_cost = sum(costs)
        
        # Resource count analysis
        high_cost_count = len([s for s in summaries if s.total_cost >= self.cost_thresholds['high_cost_resource']])
        medium_cost_count = len([s for s in summaries if self.cost_thresholds['medium_cost_resource'] <= s.total_cost < self.cost_thresholds['high_cost_resource']])
        low_cost_count = len([s for s in summaries if 0 < s.total_cost < self.cost_thresholds['medium_cost_resource']])
        zero_cost_count = len([s for s in summaries if s.total_cost == 0])
        
        # Top cost contributors
        sorted_summaries = sorted(summaries, key=lambda x: x.total_cost, reverse=True)
        top_5_cost = sum(s.total_cost for s in sorted_summaries[:5])
        top_5_percentage = (top_5_cost / total_cost * 100) if total_cost > 0 else 0
        
        return {
            'total_cost': total_cost,
            'resource_counts': {
                'high_cost': high_cost_count,
                'medium_cost': medium_cost_count,
                'low_cost': low_cost_count,
                'zero_cost': zero_cost_count
            },
            'cost_concentration': {
                'top_5_resources_cost': top_5_cost,
                'top_5_percentage': top_5_percentage,
                'average_cost_per_resource': total_cost / len(summaries),
                'median_cost': sorted(costs)[len(costs) // 2] if costs else 0
            },
            'cost_thresholds': self.cost_thresholds
        }
    
    def _analyze_optimization_potential(self, summaries: List[ResourceCostSummary], total_cost: float) -> Dict[str, Any]:
        """Analyze potential for cost optimization"""
        optimization_suggestions = []
        potential_savings = 0.0
        
        # Analyze high-cost resources for optimization opportunities
        high_cost_resources = [s for s in summaries if s.total_cost >= self.cost_thresholds['high_cost_resource']]
        
        for resource in high_cost_resources:
            suggestions = self._get_resource_optimization_suggestions(resource)
            optimization_suggestions.extend(suggestions)
            potential_savings += sum(s.get('potential_monthly_savings', 0) for s in suggestions)
        
        # Overall optimization assessment
        needs_optimization = total_cost > self.cost_thresholds['optimization_threshold']
        optimization_priority = 'HIGH' if total_cost > 200 else 'MEDIUM' if total_cost > 100 else 'LOW'
        
        return {
            'needs_optimization': needs_optimization,
            'optimization_priority': optimization_priority,
            'total_potential_savings': potential_savings,
            'savings_percentage': (potential_savings / total_cost * 100) if total_cost > 0 else 0,
            'high_cost_resource_count': len(high_cost_resources),
            'optimization_suggestions': optimization_suggestions
        }
    
    def _get_resource_optimization_suggestions(self, resource: ResourceCostSummary) -> List[Dict[str, Any]]:
        """Get optimization suggestions for a specific resource"""
        suggestions = []
        
        if resource.cost_category == CostCategory.BILLABLE_NETWORKING:
            if resource.resource_type == 'nat_gateways':
                suggestions.append({
                    'resource_id': resource.resource_id,
                    'type': 'NAT Gateway Optimization',
                    'description': 'Consider consolidating NAT Gateways or using NAT Instances for dev environments',
                    'potential_monthly_savings': resource.total_cost * 0.5,  # Estimate 50% savings
                    'complexity': 'MEDIUM'
                })
            elif resource.resource_type == 'elastic_ips':
                suggestions.append({
                    'resource_id': resource.resource_id,
                    'type': 'Elastic IP Optimization',
                    'description': 'Release unused Elastic IPs or associate with running instances',
                    'potential_monthly_savings': resource.total_cost,  # Full savings if unused
                    'complexity': 'LOW'
                })
        
        elif resource.cost_category == CostCategory.BILLABLE_COMPUTE:
            if resource.total_cost > 100:  # High-cost compute resources
                suggestions.append({
                    'resource_id': resource.resource_id,
                    'type': 'Instance Right-sizing',
                    'description': 'Analyze instance utilization and consider right-sizing',
                    'potential_monthly_savings': resource.total_cost * 0.2,  # Estimate 20% savings
                    'complexity': 'MEDIUM'
                })
        
        elif resource.cost_category == CostCategory.BILLABLE_STORAGE:
            if resource.resource_type == 's3_buckets':
                suggestions.append({
                    'resource_id': resource.resource_id,
                    'type': 'S3 Storage Class Optimization',
                    'description': 'Consider using Intelligent Tiering or cheaper storage classes',
                    'potential_monthly_savings': resource.total_cost * 0.3,  # Estimate 30% savings
                    'complexity': 'LOW'
                })
        
        return suggestions


def export_cost_summary_to_json(summary: ComprehensiveCostSummary, filepath: str):
    """Export cost summary to JSON file"""
    # Convert dataclass to dict, handling enums and datetime
    def serialize_obj(obj):
        if isinstance(obj, (CostCategory, CostPriority)):
            return obj.value
        elif isinstance(obj, datetime):
            return obj.isoformat()
        elif hasattr(obj, '__dict__'):
            return {k: serialize_obj(v) for k, v in obj.__dict__.items()}
        elif isinstance(obj, list):
            return [serialize_obj(item) for item in obj]
        elif isinstance(obj, dict):
            # Handle dict keys that might be enums
            return {(k.value if hasattr(k, 'value') else str(k)): serialize_obj(v) for k, v in obj.items()}
        return obj
    
    serialized_data = serialize_obj(summary)
    
    with open(filepath, 'w') as f:
        json.dump(serialized_data, f, indent=2)


def export_cost_summary_to_csv(summary: ComprehensiveCostSummary, filepath: str):
    """Export resource cost details to CSV file"""
    import csv
    
    with open(filepath, 'w', newline='') as f:
        writer = csv.writer(f)
        
        # Write header
        writer.writerow([
            'Resource ID', 'Resource Name', 'Resource Type', 'Service', 'Region',
            'Cost Category', 'Cost Priority', 'Monthly Cost', 'Is Estimated', 'Pricing Source'
        ])
        
        # Write resource data
        for resource in summary.resource_summaries:
            writer.writerow([
                resource.resource_id,
                resource.resource_name or '',
                resource.resource_type,
                resource.service,
                resource.region,
                resource.cost_category.value,
                resource.cost_priority.value,
                f"{resource.total_cost:.2f}",
                resource.is_estimated,
                resource.pricing_source
            ])


def generate_cost_trend_analysis(historical_cost_data: List[Dict[str, Any]], 
                                current_cost: float) -> Dict[str, Any]:
    """Generate cost trend analysis from historical data
    
    Args:
        historical_cost_data: List of historical cost entries 
            [{'date': '2025-01-01', 'cost': 100.0}, ...]
        current_cost: Current period cost
        
    Returns:
        Dictionary containing trend analysis
    """
    if not historical_cost_data or len(historical_cost_data) < 2:
        return {
            'historical_costs': [],
            'growth_rate': 0.0,
            'trend_direction': 'STABLE',
            'projected_next_month': current_cost,
            'cost_volatility': 'UNKNOWN',
            'seasonal_patterns': {}
        }
    
    # Sort by date
    sorted_costs = sorted(historical_cost_data, key=lambda x: x['date'])
    costs = [entry['cost'] for entry in sorted_costs]
    
    # Calculate growth rate (comparing first and last periods)
    if len(costs) >= 2:
        first_cost = costs[0] if costs[0] > 0 else 1  # Avoid division by zero
        last_cost = costs[-1]
        growth_rate = ((last_cost - first_cost) / first_cost) * 100
    else:
        growth_rate = 0.0
    
    # Determine trend direction
    if abs(growth_rate) <= 5:
        trend_direction = 'STABLE'
    elif growth_rate > 5:
        trend_direction = 'INCREASING'
    else:
        trend_direction = 'DECREASING'
    
    # Calculate cost volatility (coefficient of variation)
    if len(costs) > 1:
        avg_cost = sum(costs) / len(costs)
        variance = sum((cost - avg_cost) ** 2 for cost in costs) / len(costs)
        std_dev = variance ** 0.5
        coefficient_of_variation = (std_dev / avg_cost) if avg_cost > 0 else 0
        
        if coefficient_of_variation <= 0.1:
            volatility = 'LOW'
        elif coefficient_of_variation <= 0.3:
            volatility = 'MEDIUM'
        else:
            volatility = 'HIGH'
    else:
        volatility = 'UNKNOWN'
    
    # Simple projection for next month (linear trend)
    if len(costs) >= 2:
        # Use simple linear projection
        recent_trend = costs[-1] - costs[-2] if len(costs) >= 2 else 0
        projected_next_month = max(0, costs[-1] + recent_trend)
    else:
        projected_next_month = current_cost
    
    # Basic seasonal pattern analysis (placeholder)
    seasonal_patterns = {}
    if len(sorted_costs) >= 12:  # Need at least a year of data
        monthly_costs = {}
        for entry in sorted_costs:
            month = entry['date'][:7]  # YYYY-MM format
            if month not in monthly_costs:
                monthly_costs[month] = []
            monthly_costs[month].append(entry['cost'])
        
        if len(monthly_costs) >= 12:
            avg_monthly_costs = {month: sum(costs)/len(costs) for month, costs in monthly_costs.items()}
            peak_month = max(avg_monthly_costs, key=avg_monthly_costs.get)
            low_month = min(avg_monthly_costs, key=avg_monthly_costs.get)
            
            seasonal_patterns = {
                'peak_month': peak_month,
                'low_month': low_month,
                'monthly_averages': avg_monthly_costs
            }
    
    return {
        'historical_costs': sorted_costs,
        'growth_rate': growth_rate,
        'trend_direction': trend_direction,
        'projected_next_month': projected_next_month,
        'cost_volatility': volatility,
        'seasonal_patterns': seasonal_patterns
    }


def generate_cost_forecast(historical_cost_data: List[Dict[str, Any]], 
                          forecast_days: int = 90,
                          current_cost: float = 0) -> Dict[str, Any]:
    """Generate cost forecasting analysis
    
    Args:
        historical_cost_data: List of historical cost entries
        forecast_days: Number of days to forecast
        current_cost: Current period cost for baseline
        
    Returns:
        Dictionary containing forecast analysis
    """
    if not historical_cost_data or len(historical_cost_data) < 3:
        # Return basic forecast based on current cost
        return {
            'forecast_period_days': forecast_days,
            'forecasted_total_cost': current_cost * (forecast_days / 30),
            'confidence_interval': {
                'low': current_cost * (forecast_days / 30) * 0.8,
                'high': current_cost * (forecast_days / 30) * 1.2
            },
            'monthly_breakdown': [
                {
                    'month': (datetime.now() + timedelta(days=30*i)).strftime('%Y-%m'),
                    'predicted_cost': current_cost
                } for i in range(1, (forecast_days // 30) + 2)
            ],
            'cost_drivers': ['Insufficient historical data for detailed analysis'],
            'forecast_confidence': 'LOW'
        }
    
    # Sort historical data
    sorted_costs = sorted(historical_cost_data, key=lambda x: x['date'])
    costs = [entry['cost'] for entry in sorted_costs]
    
    # Simple linear trend calculation
    n = len(costs)
    if n >= 3:
        # Calculate trend using least squares
        x_values = list(range(n))
        x_mean = sum(x_values) / n
        y_mean = sum(costs) / n
        
        numerator = sum((x_values[i] - x_mean) * (costs[i] - y_mean) for i in range(n))
        denominator = sum((x_values[i] - x_mean) ** 2 for i in range(n))
        
        if denominator != 0:
            slope = numerator / denominator
            intercept = y_mean - slope * x_mean
        else:
            slope = 0
            intercept = y_mean
    else:
        slope = 0
        intercept = costs[-1] if costs else current_cost
    
    # Generate forecast
    forecast_months = (forecast_days // 30) + 1
    monthly_forecasts = []
    total_forecasted_cost = 0
    
    for i in range(1, forecast_months + 1):
        # Project cost for each month
        future_x = n + i
        predicted_cost = max(0, intercept + slope * future_x)
        
        month_date = datetime.now() + timedelta(days=30*i)
        monthly_forecasts.append({
            'month': month_date.strftime('%Y-%m'),
            'predicted_cost': predicted_cost
        })
        total_forecasted_cost += predicted_cost
    
    # Calculate confidence interval based on historical variance
    if len(costs) > 1:
        avg_cost = sum(costs) / len(costs)
        variance = sum((cost - avg_cost) ** 2 for cost in costs) / len(costs)
        std_dev = variance ** 0.5
        
        # Confidence interval (±1 standard deviation)
        confidence_multiplier = 1.96  # 95% confidence interval
        error_margin = confidence_multiplier * std_dev
        
        confidence_interval = {
            'low': max(0, total_forecasted_cost - error_margin * forecast_months),
            'high': total_forecasted_cost + error_margin * forecast_months
        }
        
        # Determine confidence level
        coefficient_of_variation = (std_dev / avg_cost) if avg_cost > 0 else 1
        if coefficient_of_variation <= 0.1:
            forecast_confidence = 'HIGH'
        elif coefficient_of_variation <= 0.3:
            forecast_confidence = 'MEDIUM'
        else:
            forecast_confidence = 'LOW'
    else:
        confidence_interval = {
            'low': total_forecasted_cost * 0.7,
            'high': total_forecasted_cost * 1.3
        }
        forecast_confidence = 'LOW'
    
    # Identify cost drivers (simplified analysis)
    cost_drivers = []
    if slope > 0:
        cost_drivers.append('Increasing resource usage trend')
        if slope > avg_cost * 0.1:  # Growing more than 10% per period
            cost_drivers.append('Rapid growth pattern detected')
    elif slope < 0:
        cost_drivers.append('Decreasing cost trend')
    else:
        cost_drivers.append('Stable cost pattern')
    
    # Add additional analysis based on cost magnitude
    if total_forecasted_cost > current_cost * 2:
        cost_drivers.append('Significant cost increase projected')
    
    return {
        'forecast_period_days': forecast_days,
        'forecasted_total_cost': total_forecasted_cost,
        'confidence_interval': confidence_interval,
        'monthly_breakdown': monthly_forecasts,
        'cost_drivers': cost_drivers,
        'forecast_confidence': forecast_confidence
    }