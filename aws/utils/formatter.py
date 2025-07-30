"""
Enhanced resource formatting utilities with cost information display.
"""

from services.base import ResourceInfo
from cost.base import CostSummary, OptimizationSuggestion
from typing import Dict, List


class ResourceFormatter:
    """Enhanced formatter with cost information display"""
    
    @staticmethod
    def format_resource_info(resource: ResourceInfo) -> str:
        """Format basic resource information"""
        details = []
        
        if resource.state:
            details.append(f"state: {resource.state}")
        if resource.type:
            details.append(f"type: {resource.type}")
        if resource.region:
            details.append(f"region: {resource.region}")
        
        # Add additional info
        if resource.additional_info:
            for key, value in resource.additional_info.items():
                if key not in ['id', 'name', 'state', 'type', 'region']:
                    details.append(f"{key}: {value}")
        
        detail_str = ", ".join(details) if details else ""
        identifier = resource.name or resource.id
        
        return f"    - {identifier} ({detail_str})" if detail_str else f"    - {identifier}"
    
    @staticmethod
    def format_resource_with_costs(resource: ResourceInfo) -> str:
        """Format a resource with cost information"""
        base_info = ResourceFormatter.format_resource_info(resource)
        
        if resource.cost_data:
            cost_info = f" | Cost: ${resource.cost_data.get('total_cost', 0):.2f}"
            if resource.cost_forecast:
                forecast = resource.cost_forecast[0].amount if resource.cost_forecast else 0
                cost_info += f" | 30-day forecast: ${forecast:.2f}"
            base_info += cost_info
        
        return base_info
    
    @staticmethod
    def print_results(all_resources: Dict[str, Dict[str, List[ResourceInfo]]], cluster_uid: str):
        """Print all discovered resources with optional cost information"""
        print(f"\n=== Discovered Resources for Cluster: {cluster_uid} ===")
        
        total_resources = 0
        for service_name, service_resources in all_resources.items():
            service_total = sum(len(resources) for resources in service_resources.values())
            total_resources += service_total
            
            if service_total > 0:
                print(f"\n{service_name.upper()}:")
                print("-" * 50)
                
                for resource_type, items in service_resources.items():
                    if items:
                        print(f"\n  {resource_type.replace('_', ' ').title()} ({len(items)}):")
                        for item in items:
                            formatted = ResourceFormatter.format_resource_with_costs(item)
                            print(formatted)
                        
                        total_resources += len(items)
        
        print(f"\nTotal Resources Found: {total_resources}")
    
    @staticmethod
    def print_cost_summary(cost_summary: CostSummary, cluster_uid: str):
        """Print detailed cost summary"""
        print(f"\n=== Cost Summary for Cluster: {cluster_uid} ===")
        print(f"Period: {cost_summary.period_start.date()} to {cost_summary.period_end.date()}")
        print(f"Total Cost: ${cost_summary.total_cost:.2f} {cost_summary.currency}")
        print(f"Resources: {cost_summary.resource_count}")
        print(f"Average Cost per Resource: ${cost_summary.average_cost_per_resource:.2f}")
        print(f"Cost Trend: {cost_summary.cost_trend}")
        print(f"30-day Forecast: ${cost_summary.forecast_30_days:.2f}")
        print(f"90-day Forecast: ${cost_summary.forecast_90_days:.2f}")
        
        print("\nCost Breakdown by Service:")
        for service, cost in cost_summary.cost_breakdown.items():
            print(f"  {service}: ${cost:.2f}")
    
    @staticmethod
    def print_optimization_suggestions(suggestions: List[OptimizationSuggestion]):
        """Print cost optimization suggestions"""
        if not suggestions:
            print("\nNo optimization suggestions found.")
            return
        
        print(f"\n=== Cost Optimization Suggestions ({len(suggestions)}) ===")
        total_savings = sum(s.potential_savings for s in suggestions)
        print(f"Total Potential Savings: ${total_savings:.2f}")
        
        for suggestion in suggestions:
            print(f"\nResource: {suggestion.resource_id}")
            print(f"Type: {suggestion.suggestion_type}")
            print(f"Current Cost: ${suggestion.current_cost:.2f}")
            print(f"Potential Savings: ${suggestion.potential_savings:.2f}")
            print(f"Risk Level: {suggestion.risk_level}")
            print(f"Description: {suggestion.description}") 