"""
Cost reporting service for generating cost reports and exports.
"""

from .base import CostService, CostSummary, OptimizationSuggestion
from typing import Dict, List, Any
import json
import csv
from datetime import datetime


class CostReporterService(CostService):
    """Service for generating cost reports and exports"""
    
    def __init__(self):
        super().__init__("CostReporter")
    
    def get_client(self, session):
        """Reporter doesn't need a direct client"""
        return None
    
    def print_cost_summary(self, cost_summary: CostSummary, cluster_uid: str):
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
    
    def print_optimization_suggestions(self, suggestions: List[OptimizationSuggestion]):
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
    
    def export_to_json(
        self,
        cost_summary: CostSummary,
        resources: Dict[str, List['ResourceInfo']],
        filename: str
    ):
        """Export cost report to JSON format"""
        report_data = {
            'cost_summary': {
                'total_cost': cost_summary.total_cost,
                'currency': cost_summary.currency,
                'period_start': cost_summary.period_start.isoformat(),
                'period_end': cost_summary.period_end.isoformat(),
                'resource_count': cost_summary.resource_count,
                'average_cost_per_resource': cost_summary.average_cost_per_resource,
                'cost_trend': cost_summary.cost_trend,
                'forecast_30_days': cost_summary.forecast_30_days,
                'forecast_90_days': cost_summary.forecast_90_days,
                'cost_breakdown': cost_summary.cost_breakdown
            },
            'resources': self._serialize_resources(resources),
            'export_timestamp': datetime.now().isoformat()
        }
        
        with open(filename, 'w') as f:
            json.dump(report_data, f, indent=2)
    
    def export_to_csv(
        self,
        cost_summary: CostSummary,
        resources: Dict[str, List['ResourceInfo']],
        filename: str
    ):
        """Export cost report to CSV format"""
        with open(filename, 'w', newline='') as f:
            writer = csv.writer(f)
            
            # Write cost summary
            writer.writerow(['Cost Summary'])
            writer.writerow(['Total Cost', cost_summary.total_cost])
            writer.writerow(['Currency', cost_summary.currency])
            writer.writerow(['Resource Count', cost_summary.resource_count])
            writer.writerow(['Average Cost per Resource', cost_summary.average_cost_per_resource])
            writer.writerow(['Cost Trend', cost_summary.cost_trend])
            writer.writerow(['30-day Forecast', cost_summary.forecast_30_days])
            writer.writerow(['90-day Forecast', cost_summary.forecast_90_days])
            writer.writerow([])
            
            # Write cost breakdown
            writer.writerow(['Cost Breakdown by Service'])
            for service, cost in cost_summary.cost_breakdown.items():
                writer.writerow([service, cost])
            writer.writerow([])
            
            # Write resource details
            writer.writerow(['Resource Details'])
            writer.writerow(['Service', 'Resource Type', 'ID', 'Name', 'State', 'Cost'])
            for service_name, resource_list in resources.items():
                for resource in resource_list:
                    cost = resource.cost_data.get('total_cost', 0.0) if resource.cost_data else 0.0
                    writer.writerow([
                        service_name,
                        resource.type or 'Unknown',
                        resource.id,
                        resource.name or resource.id,
                        resource.state or 'Unknown',
                        cost
                    ])
    
    def export_to_html(
        self,
        cost_summary: CostSummary,
        resources: Dict[str, List['ResourceInfo']],
        filename: str
    ):
        """Export cost report to HTML format"""
        html_content = f"""
<!DOCTYPE html>
<html>
<head>
    <title>Cost Report</title>
    <style>
        body {{ font-family: Arial, sans-serif; margin: 20px; }}
        .header {{ background-color: #f0f0f0; padding: 10px; border-radius: 5px; }}
        .summary {{ margin: 20px 0; }}
        .breakdown {{ margin: 20px 0; }}
        .resources {{ margin: 20px 0; }}
        table {{ border-collapse: collapse; width: 100%; }}
        th, td {{ border: 1px solid #ddd; padding: 8px; text-align: left; }}
        th {{ background-color: #f2f2f2; }}
        .cost {{ color: #d32f2f; font-weight: bold; }}
        .savings {{ color: #388e3c; font-weight: bold; }}
    </style>
</head>
<body>
    <div class="header">
        <h1>AWS Cost Report</h1>
        <p>Generated on: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
    </div>
    
    <div class="summary">
        <h2>Cost Summary</h2>
        <p><strong>Total Cost:</strong> <span class="cost">${cost_summary.total_cost:.2f} {cost_summary.currency}</span></p>
        <p><strong>Resources:</strong> {cost_summary.resource_count}</p>
        <p><strong>Average Cost per Resource:</strong> ${cost_summary.average_cost_per_resource:.2f}</p>
        <p><strong>Cost Trend:</strong> {cost_summary.cost_trend}</p>
        <p><strong>30-day Forecast:</strong> ${cost_summary.forecast_30_days:.2f}</p>
        <p><strong>90-day Forecast:</strong> ${cost_summary.forecast_90_days:.2f}</p>
    </div>
    
    <div class="breakdown">
        <h2>Cost Breakdown by Service</h2>
        <table>
            <tr><th>Service</th><th>Cost</th></tr>
"""
        
        for service, cost in cost_summary.cost_breakdown.items():
            html_content += f"            <tr><td>{service}</td><td class='cost'>${cost:.2f}</td></tr>\n"
        
        html_content += """        </table>
    </div>
    
    <div class="resources">
        <h2>Resource Details</h2>
        <table>
            <tr><th>Service</th><th>Resource Type</th><th>ID</th><th>Name</th><th>State</th><th>Cost</th></tr>
"""
        
        for service_name, resource_list in resources.items():
            for resource in resource_list:
                cost = resource.cost_data.get('total_cost', 0.0) if resource.cost_data else 0.0
                html_content += f"""            <tr>
                <td>{service_name}</td>
                <td>{resource.type or 'Unknown'}</td>
                <td>{resource.id}</td>
                <td>{resource.name or resource.id}</td>
                <td>{resource.state or 'Unknown'}</td>
                <td class='cost'>${cost:.2f}</td>
            </tr>
"""
        
        html_content += """        </table>
    </div>
</body>
</html>"""
        
        with open(filename, 'w') as f:
            f.write(html_content)
    
    def _serialize_resources(self, resources: Dict[str, List['ResourceInfo']]) -> Dict[str, List[Dict]]:
        """Serialize resources for JSON export"""
        serialized = {}
        for service_name, resource_list in resources.items():
            serialized[service_name] = []
            for resource in resource_list:
                resource_data = {
                    'id': resource.id,
                    'name': resource.name,
                    'type': resource.type,
                    'state': resource.state,
                    'region': resource.region,
                    'cost_data': resource.cost_data
                }
                serialized[service_name].append(resource_data)
        return serialized 