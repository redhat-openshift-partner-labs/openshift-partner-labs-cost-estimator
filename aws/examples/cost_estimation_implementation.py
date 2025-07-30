"""
Concrete Implementation Example: AWS Cost Explorer Integration

This file demonstrates a working implementation of the cost estimation framework
that can be integrated into the main modular framework.
"""

import boto3
from botocore.exceptions import ClientError
from typing import Dict, List, Any, Optional
from dataclasses import dataclass
from datetime import datetime, timedelta
import json
import csv
from abc import ABC, abstractmethod


@dataclass
class CostRecord:
    """Represents a cost record for a specific time period"""
    start_date: datetime
    end_date: datetime
    amount: float
    service: str
    currency: str = "USD"
    unit: str = "Hrs"
    usage_type: Optional[str] = None
    operation: Optional[str] = None
    region: Optional[str] = None


@dataclass
class CostSummary:
    """Summary of costs for a resource or group of resources"""
    total_cost: float
    period_start: datetime
    period_end: datetime
    cost_breakdown: Dict[str, float]
    resource_count: int
    average_cost_per_resource: float
    cost_trend: str
    forecast_30_days: float
    forecast_90_days: float
    currency: str = "USD"


@dataclass
class OptimizationSuggestion:
    """Cost optimization suggestion"""
    resource_id: str
    resource_type: str
    current_cost: float
    potential_savings: float
    suggestion_type: str
    description: str
    implementation_steps: List[str]
    risk_level: str


class CostExplorerService:
    """Service for interacting with AWS Cost Explorer API"""
    
    def __init__(self, session: boto3.Session):
        self.client = session.client('ce')
        self.session = session
    
    def get_cost_and_usage(
        self,
        start_date: datetime,
        end_date: datetime,
        granularity: str = 'MONTHLY',
        metrics: List[str] = None,
        group_by: List[Dict] = None,
        filter_expression: Dict = None
    ) -> Dict[str, Any]:
        """Get cost and usage data from Cost Explorer"""
        if metrics is None:
            metrics = ['UnblendedCost']
        
        if group_by is None:
            group_by = [
                {'Type': 'DIMENSION', 'Key': 'SERVICE'},
                {'Type': 'DIMENSION', 'Key': 'USAGE_TYPE'}
            ]
        
        try:
            response = self.client.get_cost_and_usage(
                TimePeriod={
                    'Start': start_date.strftime('%Y-%m-%d'),
                    'End': end_date.strftime('%Y-%m-%d')
                },
                Granularity=granularity,
                Metrics=metrics,
                GroupBy=group_by,
                Filter=filter_expression
            )
            return response
        except ClientError as e:
            print(f"Error getting cost and usage data: {e}")
            return {'ResultsByTime': [], 'GroupDefinitions': []}
    
    def get_cost_and_usage_by_tags(
        self,
        start_date: datetime,
        end_date: datetime,
        tag_key: str,
        tag_value: str,
        granularity: str = 'MONTHLY'
    ) -> Dict[str, Any]:
        """Get cost and usage data filtered by specific tags"""
        filter_expression = {
            'Tags': {
                'Key': tag_key,
                'Values': [tag_value]
            }
        }
        
        return self.get_cost_and_usage(
            start_date, end_date, granularity,
            filter_expression=filter_expression
        )
    
    def get_cost_forecast(
        self,
        start_date: datetime,
        end_date: datetime,
        metric: str = 'UNBLENDED_COST',
        granularity: str = 'MONTHLY'
    ) -> Dict[str, Any]:
        """Get cost forecast from Cost Explorer"""
        try:
            response = self.client.get_cost_forecast(
                TimePeriod={
                    'Start': start_date.strftime('%Y-%m-%d'),
                    'End': end_date.strftime('%Y-%m-%d')
                },
                Metric=metric,
                Granularity=granularity
            )
            return response
        except ClientError as e:
            print(f"Error getting cost forecast: {e}")
            return {'ForecastResultsByTime': []}
    
    def get_reservation_coverage(
        self,
        start_date: datetime,
        end_date: datetime,
        granularity: str = 'MONTHLY'
    ) -> Dict[str, Any]:
        """Get reservation coverage data"""
        try:
            response = self.client.get_reservation_coverage(
                TimePeriod={
                    'Start': start_date.strftime('%Y-%m-%d'),
                    'End': end_date.strftime('%Y-%m-%d')
                },
                Granularity=granularity
            )
            return response
        except ClientError as e:
            print(f"Error getting reservation coverage: {e}")
            return {'CoveragesByTime': []}


class CostAnalyzer:
    """Analyzes cost data and provides insights"""
    
    def __init__(self, cost_explorer_service: CostExplorerService):
        self.ce_service = cost_explorer_service
    
    def analyze_resource_costs(
        self,
        resources: List[Any],  # List[ResourceInfo] - using Any for compatibility
        start_date: datetime,
        end_date: datetime
    ) -> List[Any]:
        """Analyze costs for a list of resources"""
        # This would be implemented to enrich ResourceInfo objects with cost data
        # For now, we'll return the resources as-is
        return resources
    
    def generate_cost_summary(
        self,
        resources: List[Any],
        period_start: datetime,
        period_end: datetime,
        tag_key: str,
        tag_value: str
    ) -> CostSummary:
        """Generate cost summary for resources"""
        # Get cost data from Cost Explorer
        cost_data = self.ce_service.get_cost_and_usage_by_tags(
            period_start, period_end, tag_key, tag_value
        )
        
        # Calculate total cost
        total_cost = 0.0
        cost_breakdown = {}
        
        for result in cost_data.get('ResultsByTime', []):
            for group in result.get('Groups', []):
                service = group['Keys'][0]  # First key is SERVICE
                cost = float(group['Metrics']['UnblendedCost']['Amount'])
                total_cost += cost
                
                if service not in cost_breakdown:
                    cost_breakdown[service] = 0.0
                cost_breakdown[service] += cost
        
        # Calculate averages and trends
        resource_count = len(resources)
        average_cost_per_resource = total_cost / resource_count if resource_count > 0 else 0.0
        
        # Simple trend calculation (could be enhanced with historical data)
        cost_trend = "stable"  # Placeholder
        
        # Get forecasts
        forecast_30 = self._get_forecast(period_end, 30)
        forecast_90 = self._get_forecast(period_end, 90)
        
        return CostSummary(
            total_cost=total_cost,
            period_start=period_start,
            period_end=period_end,
            cost_breakdown=cost_breakdown,
            resource_count=resource_count,
            average_cost_per_resource=average_cost_per_resource,
            cost_trend=cost_trend,
            forecast_30_days=forecast_30,
            forecast_90_days=forecast_90
        )
    
    def _get_forecast(self, start_date: datetime, days: int) -> float:
        """Get cost forecast for specified number of days"""
        end_date = start_date + timedelta(days=days)
        
        try:
            forecast_data = self.ce_service.get_cost_forecast(start_date, end_date)
            total_forecast = 0.0
            
            for result in forecast_data.get('ForecastResultsByTime', []):
                total_forecast += float(result['MeanValue'])
            
            return total_forecast
        except Exception as e:
            print(f"Error getting forecast: {e}")
            return 0.0
    
    def identify_optimization_opportunities(
        self,
        resources: List[Any]
    ) -> List[OptimizationSuggestion]:
        """Identify cost optimization opportunities"""
        suggestions = []
        
        # Example optimization logic for EC2 instances
        for resource in resources:
            if hasattr(resource, 'type') and resource.type and 't3.' in resource.type:
                # Suggest downsizing for t3 instances
                current_cost = 50.0  # Placeholder - would come from actual cost data
                potential_savings = current_cost * 0.3  # 30% savings estimate
                
                suggestion = OptimizationSuggestion(
                    resource_id=resource.id,
                    resource_type=resource.type,
                    current_cost=current_cost,
                    potential_savings=potential_savings,
                    suggestion_type="resize",
                    description=f"Consider downsizing {resource.type} to a smaller instance type",
                    implementation_steps=[
                        "1. Stop the instance",
                        "2. Change instance type",
                        "3. Start the instance"
                    ],
                    risk_level="low"
                )
                suggestions.append(suggestion)
        
        return suggestions


class CostReportExporter:
    """Export cost reports in various formats"""
    
    @staticmethod
    def export_to_json(
        cost_summary: CostSummary,
        resources: Dict[str, List[Any]],
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
            'resources': {}
        }
        
        # Add resource data
        for service_name, resource_list in resources.items():
            report_data['resources'][service_name] = []
            for resource in resource_list:
                resource_data = {
                    'id': resource.id,
                    'name': getattr(resource, 'name', None),
                    'type': getattr(resource, 'type', None),
                    'state': getattr(resource, 'state', None)
                }
                report_data['resources'][service_name].append(resource_data)
        
        with open(filename, 'w') as f:
            json.dump(report_data, f, indent=2)
    
    @staticmethod
    def export_to_csv(
        cost_summary: CostSummary,
        resources: Dict[str, List[Any]],
        filename: str
    ):
        """Export cost report to CSV format"""
        with open(filename, 'w', newline='') as f:
            writer = csv.writer(f)
            
            # Write cost summary
            writer.writerow(['Cost Summary'])
            writer.writerow(['Total Cost', f"${cost_summary.total_cost:.2f}"])
            writer.writerow(['Currency', cost_summary.currency])
            writer.writerow(['Period Start', cost_summary.period_start.strftime('%Y-%m-%d')])
            writer.writerow(['Period End', cost_summary.period_end.strftime('%Y-%m-%d')])
            writer.writerow(['Resource Count', cost_summary.resource_count])
            writer.writerow(['Average Cost per Resource', f"${cost_summary.average_cost_per_resource:.2f}"])
            writer.writerow(['Cost Trend', cost_summary.cost_trend])
            writer.writerow(['30-day Forecast', f"${cost_summary.forecast_30_days:.2f}"])
            writer.writerow(['90-day Forecast', f"${cost_summary.forecast_90_days:.2f}"])
            writer.writerow([])
            
            # Write cost breakdown
            writer.writerow(['Cost Breakdown by Service'])
            for service, cost in cost_summary.cost_breakdown.items():
                writer.writerow([service, f"${cost:.2f}"])
            writer.writerow([])
            
            # Write resources
            writer.writerow(['Resources'])
            writer.writerow(['Service', 'Resource ID', 'Name', 'Type', 'State'])
            for service_name, resource_list in resources.items():
                for resource in resource_list:
                    writer.writerow([
                        service_name,
                        resource.id,
                        getattr(resource, 'name', ''),
                        getattr(resource, 'type', ''),
                        getattr(resource, 'state', '')
                    ])
    
    @staticmethod
    def export_to_html(
        cost_summary: CostSummary,
        resources: Dict[str, List[Any]],
        filename: str
    ):
        """Export cost report to HTML format with charts"""
        html_content = f"""
<!DOCTYPE html>
<html>
<head>
    <title>AWS Cost Report</title>
    <style>
        body {{ font-family: Arial, sans-serif; margin: 20px; }}
        .header {{ background-color: #f0f0f0; padding: 20px; border-radius: 5px; }}
        .summary {{ margin: 20px 0; }}
        .breakdown {{ margin: 20px 0; }}
        .resources {{ margin: 20px 0; }}
        table {{ border-collapse: collapse; width: 100%; }}
        th, td {{ border: 1px solid #ddd; padding: 8px; text-align: left; }}
        th {{ background-color: #f2f2f2; }}
        .cost {{ color: #d32f2f; font-weight: bold; }}
    </style>
</head>
<body>
    <div class="header">
        <h1>AWS Cost Report</h1>
        <p>Generated on: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
    </div>
    
    <div class="summary">
        <h2>Cost Summary</h2>
        <table>
            <tr><td>Total Cost</td><td class="cost">${cost_summary.total_cost:.2f} {cost_summary.currency}</td></tr>
            <tr><td>Period</td><td>{cost_summary.period_start.strftime('%Y-%m-%d')} to {cost_summary.period_end.strftime('%Y-%m-%d')}</td></tr>
            <tr><td>Resources</td><td>{cost_summary.resource_count}</td></tr>
            <tr><td>Average Cost per Resource</td><td class="cost">${cost_summary.average_cost_per_resource:.2f}</td></tr>
            <tr><td>Cost Trend</td><td>{cost_summary.cost_trend}</td></tr>
            <tr><td>30-day Forecast</td><td class="cost">${cost_summary.forecast_30_days:.2f}</td></tr>
            <tr><td>90-day Forecast</td><td class="cost">${cost_summary.forecast_90_days:.2f}</td></tr>
        </table>
    </div>
    
    <div class="breakdown">
        <h2>Cost Breakdown by Service</h2>
        <table>
            <tr><th>Service</th><th>Cost</th></tr>
"""
        
        for service, cost in cost_summary.cost_breakdown.items():
            html_content += f'            <tr><td>{service}</td><td class="cost">${cost:.2f}</td></tr>\n'
        
        html_content += """
        </table>
    </div>
    
    <div class="resources">
        <h2>Resources</h2>
        <table>
            <tr><th>Service</th><th>Resource ID</th><th>Name</th><th>Type</th><th>State</th></tr>
"""
        
        for service_name, resource_list in resources.items():
            for resource in resource_list:
                html_content += f'            <tr><td>{service_name}</td><td>{resource.id}</td><td>{getattr(resource, "name", "")}</td><td>{getattr(resource, "type", "")}</td><td>{getattr(resource, "state", "")}</td></tr>\n'
        
        html_content += """
        </table>
    </div>
</body>
</html>
"""
        
        with open(filename, 'w') as f:
            f.write(html_content)


# Example usage and testing
if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description='Test Cost Estimation Framework')
    parser.add_argument('--cluster-uid', required=True, help='Kubernetes cluster UID')
    parser.add_argument('--profile', help='AWS profile to use')
    parser.add_argument('--region', help='AWS region')
    parser.add_argument('--cost-period', default=30, type=int, help='Cost analysis period in days')
    parser.add_argument('--export-format', choices=['json', 'csv', 'html'], help='Export format')
    parser.add_argument('--export-file', help='Export filename')
    
    args = parser.parse_args()
    
    # Create session
    session_args = {}
    if args.profile:
        session_args['profile_name'] = args.profile
    if args.region:
        session_args['region_name'] = args.region
    
    session = boto3.Session(**session_args)
    
    # Initialize services
    cost_explorer = CostExplorerService(session)
    cost_analyzer = CostAnalyzer(cost_explorer)
    
    # Calculate date range
    end_date = datetime.now()
    start_date = end_date - timedelta(days=args.cost_period)
    
    # Build tag key
    tag_key = f"kubernetes.io/cluster/{args.cluster_uid}"
    tag_value = "owned"
    
    print(f"Testing cost estimation for cluster: {args.cluster_uid}")
    print(f"Period: {start_date.strftime('%Y-%m-%d')} to {end_date.strftime('%Y-%m-%d')}")
    
    try:
        # Mock resources for testing
        mock_resources = [
            type('MockResource', (), {
                'id': 'i-1234567890abcdef0',
                'name': 'test-instance',
                'type': 't3.micro',
                'state': 'running'
            })()
        ]
        
        # Generate cost summary
        cost_summary = cost_analyzer.generate_cost_summary(
            mock_resources, start_date, end_date, tag_key, tag_value
        )
        
        print(f"\n=== Cost Summary ===")
        print(f"Total Cost: ${cost_summary.total_cost:.2f}")
        print(f"Resources: {cost_summary.resource_count}")
        print(f"Average Cost per Resource: ${cost_summary.average_cost_per_resource:.2f}")
        print(f"30-day Forecast: ${cost_summary.forecast_30_days:.2f}")
        
        print(f"\nCost Breakdown:")
        for service, cost in cost_summary.cost_breakdown.items():
            print(f"  {service}: ${cost:.2f}")
        
        # Export if requested
        if args.export_format and args.export_file:
            exporter = CostReportExporter()
            resources_dict = {'EC2': mock_resources}
            
            if args.export_format == 'json':
                exporter.export_to_json(cost_summary, resources_dict, args.export_file)
            elif args.export_format == 'csv':
                exporter.export_to_csv(cost_summary, resources_dict, args.export_file)
            elif args.export_format == 'html':
                exporter.export_to_html(cost_summary, resources_dict, args.export_file)
            
            print(f"\nCost report exported to: {args.export_file}")
        
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc() 