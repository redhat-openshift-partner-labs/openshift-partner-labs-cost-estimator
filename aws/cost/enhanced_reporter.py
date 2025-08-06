"""
Enhanced cost reporting with beautiful formatting and visualization.

This module provides comprehensive cost reporting capabilities with
rich console output, charts, and detailed analysis.
"""

from typing import Dict, List, Any, Optional
import os
from .cost_aggregator import ComprehensiveCostSummary, ResourceCostSummary
from .cost_categories import CostCategory, CostPriority
from termcolor import colored


class EnhancedCostReporter:
    """Enhanced cost reporter with rich formatting and analysis"""
    
    def __init__(self):
        self.currency_symbol = "$"
        self.console_width = 80
    
    def print_comprehensive_cost_summary(self, summary: ComprehensiveCostSummary):
        """Print a comprehensive, beautifully formatted cost summary"""
        self._print_header(summary)
        self._print_cost_overview(summary)
        self._print_cost_breakdowns(summary)
        self._print_top_resources(summary)
        self._print_cost_analysis(summary)
        self._print_optimization_recommendations(summary)
        self._print_footer(summary)
    
    def _print_header(self, summary: ComprehensiveCostSummary):
        """Print report header"""
        print("=" * self.console_width)
        print(colored("AWS COST ESTIMATION REPORT", "cyan", attrs=["bold"]).center(self.console_width))
        print("=" * self.console_width)
        print(f"Cluster ID: {colored(summary.cluster_id, 'yellow')}")
        print(f"Analysis Date: {colored(summary.analysis_date.strftime('%Y-%m-%d %H:%M:%S'), 'white')}")
        print(f"Period: {colored(f'{summary.period_days} days', 'white')}")
        print(f"Primary Region: {colored(summary.region, 'white')}")
        print("-" * self.console_width)
    
    def _print_cost_overview(self, summary: ComprehensiveCostSummary):
        """Print high-level cost overview"""
        print(colored("💰 COST OVERVIEW", "green", attrs=["bold"]))
        print()
        
        # Total costs with color coding
        total_color = self._get_cost_color(summary.total_monthly_cost)
        billable_color = self._get_cost_color(summary.total_billable_cost)
        
        print(f"  Total Monthly Cost:     {colored(f'{self.currency_symbol}{summary.total_monthly_cost:.2f}', total_color, attrs=['bold'])}")
        print(f"  Billable Resources:     {colored(f'{self.currency_symbol}{summary.total_billable_cost:.2f}', billable_color)}")
        print(f"  Free Resources:         {colored(f'{self.currency_symbol}{summary.total_monthly_cost - summary.total_billable_cost:.2f}', 'green')}")
        print()
        
        # Resource counts
        total_resources = summary.total_resources
        billable_pct = (summary.billable_resources / total_resources * 100) if total_resources > 0 else 0
        
        print(f"  Total Resources:        {colored(str(summary.total_resources), 'white')}")
        print(f"  Billable Resources:     {colored(f'{summary.billable_resources} ({billable_pct:.1f}%)', 'yellow')}")
        print(f"  Free Resources:         {colored(f'{summary.free_resources} ({100-billable_pct:.1f}%)', 'green')}")
        
        print("-" * self.console_width)
    
    def _print_cost_breakdowns(self, summary: ComprehensiveCostSummary):
        """Print detailed cost breakdowns"""
        print(colored("📊 COST BREAKDOWN ANALYSIS", "blue", attrs=["bold"]))
        print()
        
        # Cost by category
        self._print_breakdown_section("By Cost Category", summary.cost_by_category, summary.total_monthly_cost)
        
        # Cost by service
        if summary.cost_by_service:
            top_services = dict(sorted(summary.cost_by_service.items(), key=lambda x: x[1], reverse=True)[:8])
            self._print_breakdown_section("By AWS Service", top_services, summary.total_monthly_cost)
        
        # Cost by priority
        self._print_breakdown_section("By Cost Priority", summary.cost_by_priority, summary.total_monthly_cost)
        
        print("-" * self.console_width)
    
    def _print_breakdown_section(self, title: str, breakdown: Dict, total_cost: float):
        """Print a cost breakdown section"""
        print(f"  {colored(title, 'cyan')}:")
        
        if not breakdown:
            print("    No data available")
            print()
            return
        
        # Sort by cost descending
        sorted_items = sorted(breakdown.items(), key=lambda x: x[1], reverse=True)
        
        for item, cost in sorted_items:
            if cost <= 0:
                continue
                
            percentage = (cost / total_cost * 100) if total_cost > 0 else 0
            cost_color = self._get_cost_color(cost)
            
            # Format item name
            item_name = self._format_enum_value(item) if hasattr(item, 'value') else str(item)
            
            # Create visual bar
            bar_width = int(percentage / 2) if percentage > 0 else 0
            bar = "█" * min(bar_width, 40)
            
            print(f"    {item_name:<25} {colored(f'{self.currency_symbol}{cost:>8.2f}', cost_color)} ({percentage:>5.1f}%) {colored(bar, cost_color)}")
        
        print()
    
    def _print_top_resources(self, summary: ComprehensiveCostSummary):
        """Print top cost resources"""
        print(colored("🏆 HIGHEST COST RESOURCES", "magenta", attrs=["bold"]))
        print()
        
        if not summary.highest_cost_resources:
            print("  No billable resources found")
            print("-" * self.console_width)
            return
        
        # Table header
        print(f"  {'Rank':<4} {'Resource Name':<25} {'Type':<15} {'Service':<15} {'Monthly Cost':<12}")
        print("  " + "-" * 70)
        
        for i, resource in enumerate(summary.highest_cost_resources[:10], 1):
            if resource.total_cost <= 0:
                continue
                
            cost_color = self._get_cost_color(resource.total_cost)
            resource_name = (resource.resource_name or resource.resource_id)[:24]
            resource_type = resource.resource_type[:14]
            service = resource.service[:14]
            
            print(f"  {i:<4} {resource_name:<25} {resource_type:<15} {service:<15} {colored(f'{self.currency_symbol}{resource.total_cost:.2f}', cost_color)}")
        
        print("-" * self.console_width)
    
    def _print_cost_analysis(self, summary: ComprehensiveCostSummary):
        """Print cost distribution analysis"""
        print(colored("📈 COST ANALYSIS", "yellow", attrs=["bold"]))
        print()
        
        analysis = summary.cost_distribution_analysis
        
        if not analysis:
            print("  Analysis data not available")
            print("-" * self.console_width)
            return
        
        # Resource distribution
        counts = analysis.get('resource_counts', {})
        print("  Resource Cost Distribution:")
        print(f"    High Cost (≥${analysis.get('cost_thresholds', {}).get('high_cost_resource', 50)}/month):   {colored(str(counts.get('high_cost', 0)), 'red')}")
        print(f"    Medium Cost (${analysis.get('cost_thresholds', {}).get('medium_cost_resource', 10)}-${analysis.get('cost_thresholds', {}).get('high_cost_resource', 50)}/month): {colored(str(counts.get('medium_cost', 0)), 'yellow')}")
        print(f"    Low Cost (<${analysis.get('cost_thresholds', {}).get('medium_cost_resource', 10)}/month):     {colored(str(counts.get('low_cost', 0)), 'green')}")
        print(f"    Free Resources:          {colored(str(counts.get('zero_cost', 0)), 'green')}")
        print()
        
        # Cost concentration
        concentration = analysis.get('cost_concentration', {})
        top_5_pct = concentration.get('top_5_percentage', 0)
        avg_cost = concentration.get('average_cost_per_resource', 0)
        
        print("  Cost Concentration:")
        print(f"    Top 5 Resources:         {colored(f'{top_5_pct:.1f}%', 'cyan')} of total cost")
        print(f"    Average Cost/Resource:   {colored(f'{self.currency_symbol}{avg_cost:.2f}', 'white')}")
        median_cost = concentration.get('median_cost', 0)
        print(f"    Median Cost:             {colored(f'{self.currency_symbol}{median_cost:.2f}', 'white')}")
        
        print("-" * self.console_width)
    
    def _print_optimization_recommendations(self, summary: ComprehensiveCostSummary):
        """Print optimization recommendations"""
        print(colored("🔧 OPTIMIZATION RECOMMENDATIONS", "red", attrs=["bold"]))
        print()
        
        optimization = summary.optimization_potential
        
        if not optimization:
            print("  Optimization analysis not available")
            print("-" * self.console_width)
            return
        
        # Overall assessment
        needs_opt = optimization.get('needs_optimization', False)
        priority = optimization.get('optimization_priority', 'LOW')
        potential_savings = optimization.get('total_potential_savings', 0)
        savings_pct = optimization.get('savings_percentage', 0)
        
        priority_color = {'HIGH': 'red', 'MEDIUM': 'yellow', 'LOW': 'green'}.get(priority, 'white')
        
        print(f"  Overall Assessment:      {colored('Optimization Recommended' if needs_opt else 'Well Optimized', priority_color)}")
        print(f"  Optimization Priority:   {colored(priority, priority_color)}")
        print(f"  Potential Savings:       {colored(f'{self.currency_symbol}{potential_savings:.2f}/month ({savings_pct:.1f}%)', 'green')}")
        print()
        
        # Specific recommendations
        suggestions = optimization.get('optimization_suggestions', [])
        if suggestions:
            print("  Specific Recommendations:")
            for i, suggestion in enumerate(suggestions[:5], 1):  # Top 5 suggestions
                resource_id = suggestion.get('resource_id', 'Unknown')[:20]
                suggestion_type = suggestion.get('type', 'Unknown')
                potential_savings = suggestion.get('potential_monthly_savings', 0)
                complexity = suggestion.get('complexity', 'UNKNOWN')
                
                complexity_color = {'LOW': 'green', 'MEDIUM': 'yellow', 'HIGH': 'red'}.get(complexity, 'white')
                
                print(f"    {i}. {suggestion_type}")
                print(f"       Resource: {resource_id}")
                print(f"       Potential Savings: {colored(f'{self.currency_symbol}{potential_savings:.2f}/month', 'green')}")
                print(f"       Complexity: {colored(complexity, complexity_color)}")
                print(f"       {suggestion.get('description', 'No description available')}")
                print()
        else:
            print("  No specific recommendations available")
        
        print("-" * self.console_width)
    
    def _print_footer(self, summary: ComprehensiveCostSummary):
        """Print report footer"""
        print(colored("📝 REPORT NOTES", "white", attrs=["bold"]))
        print()
        print("  • Costs are estimated based on AWS pricing data and resource configurations")
        print("  • Actual costs may vary based on usage patterns, data transfer, and other factors")
        print("  • Free tier usage and credits are not included in these estimates")
        print("  • Optimization recommendations are suggestions and should be evaluated carefully")
        print()
        
        # Confidence indicators
        estimated_count = len([r for r in summary.resource_summaries if r.is_estimated])
        total_count = len(summary.resource_summaries)
        confidence_pct = ((total_count - estimated_count) / total_count * 100) if total_count > 0 else 0
        
        confidence_color = 'green' if confidence_pct > 80 else 'yellow' if confidence_pct > 60 else 'red'
        print(f"  Cost Estimation Confidence: {colored(f'{confidence_pct:.1f}%', confidence_color)} ({total_count - estimated_count}/{total_count} resources with precise pricing)")
        
        print("=" * self.console_width)
    
    def _get_cost_color(self, cost: float) -> str:
        """Get appropriate color for cost amount"""
        if cost >= 100:
            return 'red'
        elif cost >= 50:
            return 'yellow'
        elif cost > 0:
            return 'green'
        else:
            return 'white'
    
    def _format_enum_value(self, enum_item) -> str:
        """Format enum values for display"""
        if hasattr(enum_item, 'value'):
            # Convert snake_case to Title Case
            return enum_item.value.replace('_', ' ').title()
        return str(enum_item)
    
    def generate_html_report(self, summary: ComprehensiveCostSummary, filepath: str):
        """Generate an HTML cost report"""
        html_content = f"""
<!DOCTYPE html>
<html>
<head>
    <title>AWS Cost Estimation Report - {summary.cluster_id}</title>
    <style>
        body {{ font-family: Arial, sans-serif; margin: 40px; }}
        .header {{ background-color: #232f3e; color: white; padding: 20px; text-align: center; }}
        .overview {{ background-color: #f8f9fa; padding: 20px; margin: 20px 0; }}
        .cost-high {{ color: #d73027; font-weight: bold; }}
        .cost-medium {{ color: #fc8d59; font-weight: bold; }}
        .cost-low {{ color: #91bfdb; font-weight: bold; }}
        .cost-free {{ color: #4575b4; font-weight: bold; }}
        table {{ border-collapse: collapse; width: 100%; margin: 20px 0; }}
        th, td {{ border: 1px solid #ddd; padding: 8px; text-align: left; }}
        th {{ background-color: #f2f2f2; }}
        .recommendation {{ background-color: #fff3cd; padding: 15px; margin: 10px 0; border-left: 4px solid #ffc107; }}
    </style>
</head>
<body>
    <div class="header">
        <h1>AWS Cost Estimation Report</h1>
        <p>Cluster: {summary.cluster_id} | Date: {summary.analysis_date.strftime('%Y-%m-%d %H:%M:%S')}</p>
    </div>
    
    <div class="overview">
        <h2>Cost Overview</h2>
        <p><strong>Total Monthly Cost:</strong> <span class="cost-high">${summary.total_monthly_cost:.2f}</span></p>
        <p><strong>Billable Resources:</strong> <span class="cost-medium">${summary.total_billable_cost:.2f}</span></p>
        <p><strong>Total Resources:</strong> {summary.total_resources} ({summary.billable_resources} billable, {summary.free_resources} free)</p>
    </div>
    
    <h2>Top Cost Resources</h2>
    <table>
        <tr>
            <th>Resource Name</th>
            <th>Type</th>
            <th>Service</th>
            <th>Monthly Cost</th>
            <th>Estimated</th>
        </tr>
        {"".join([f'''
        <tr>
            <td>{r.resource_name or r.resource_id}</td>
            <td>{r.resource_type}</td>
            <td>{r.service}</td>
            <td class="{'cost-high' if r.total_cost >= 50 else 'cost-medium' if r.total_cost >= 10 else 'cost-low'}">${r.total_cost:.2f}</td>
            <td>{'Yes' if r.is_estimated else 'No'}</td>
        </tr>
        ''' for r in summary.highest_cost_resources[:10]])}
    </table>
    
    <h2>Cost by Category</h2>
    <table>
        <tr>
            <th>Category</th>
            <th>Cost</th>
            <th>Percentage</th>
        </tr>
        {"".join([f'''
        <tr>
            <td>{self._format_enum_value(category)}</td>
            <td class="{'cost-high' if cost >= 50 else 'cost-medium' if cost >= 10 else 'cost-low'}">${cost:.2f}</td>
            <td>{(cost/summary.total_monthly_cost*100):.1f}%</td>
        </tr>
        ''' for category, cost in sorted(summary.cost_by_category.items(), key=lambda x: x[1], reverse=True)])}
    </table>
    
    <h2>Optimization Recommendations</h2>
    {"".join([f'''
    <div class="recommendation">
        <h4>{suggestion.get('type', 'Unknown')}</h4>
        <p><strong>Resource:</strong> {suggestion.get('resource_id', 'Unknown')}</p>
        <p><strong>Potential Savings:</strong> ${suggestion.get('potential_monthly_savings', 0):.2f}/month</p>
        <p><strong>Complexity:</strong> {suggestion.get('complexity', 'Unknown')}</p>
        <p>{suggestion.get('description', 'No description available')}</p>
    </div>
    ''' for suggestion in summary.optimization_potential.get('optimization_suggestions', [])[:5]])}
    
    <hr>
    <p><small>Generated on {summary.analysis_date.strftime('%Y-%m-%d %H:%M:%S')} | 
    Cost estimates are based on AWS pricing data and may vary from actual usage</small></p>
</body>
</html>
        """
        
        with open(filepath, 'w') as f:
            f.write(html_content)
        
        print(f"HTML report generated: {filepath}")
    
    def print_quick_summary(self, summary: ComprehensiveCostSummary):
        """Print a quick, concise cost summary"""
        print(colored("💰 QUICK COST SUMMARY", "cyan", attrs=["bold"]))
        
        total_color = self._get_cost_color(summary.total_monthly_cost)
        print(f"Total Monthly Cost: {colored(f'{self.currency_symbol}{summary.total_monthly_cost:.2f}', total_color, attrs=['bold'])}")
        print(f"Resources: {summary.total_resources} total ({summary.billable_resources} billable)")
        
        if summary.optimization_potential and summary.optimization_potential.get('needs_optimization'):
            savings = summary.optimization_potential.get('total_potential_savings', 0)
            print(f"💡 Optimization Opportunity: {colored(f'{self.currency_symbol}{savings:.2f}/month savings', 'green')}")
        
        print("-" * 50)
    
    def print_cost_trend_analysis(self, trend_data: Dict[str, Any]):
        """Print cost trend analysis with historical patterns
        
        Args:
            trend_data: Dictionary containing trend analysis data
                {
                    'historical_costs': [{'date': '2025-01-01', 'cost': 100.0}, ...],
                    'growth_rate': 15.2,  # Percentage
                    'trend_direction': 'INCREASING',  # INCREASING, DECREASING, STABLE
                    'projected_next_month': 1150.0,
                    'cost_volatility': 'LOW',  # LOW, MEDIUM, HIGH
                    'seasonal_patterns': {...}
                }
        """
        print(colored("📈 COST TREND ANALYSIS", "magenta", attrs=["bold"]))
        print()
        
        if not trend_data:
            print("  Trend analysis not available - requires historical cost data")
            print("-" * self.console_width)
            return
        
        # Historical trend
        historical_costs = trend_data.get('historical_costs', [])
        if historical_costs and len(historical_costs) >= 2:
            print("  Cost History (Last 30 Days):")
            
            # Show simple trend visualization
            costs = [entry['cost'] for entry in historical_costs[-7:]]  # Last 7 days
            if costs:
                max_cost = max(costs)
                print("    " + " ".join([
                    f"Day {i+1}: {self.currency_symbol}{cost:.0f} {'▲' if cost > costs[0] else '▼' if cost < costs[0] else '='}"
                    for i, cost in enumerate(costs)
                ]))
            print()
        
        # Growth rate and direction
        growth_rate = trend_data.get('growth_rate', 0)
        trend_direction = trend_data.get('trend_direction', 'STABLE')
        
        direction_color = {
            'INCREASING': 'red' if growth_rate > 20 else 'yellow',
            'DECREASING': 'green',
            'STABLE': 'blue'
        }.get(trend_direction, 'white')
        
        direction_icon = {
            'INCREASING': '📈',
            'DECREASING': '📉', 
            'STABLE': '📊'
        }.get(trend_direction, '📊')
        
        print(f"  {direction_icon} Cost Trend:")
        print(f"    Direction:              {colored(trend_direction, direction_color)}")
        print(f"    Monthly Growth Rate:    {colored(f'{growth_rate:+.1f}%', direction_color)}")
        
        # Projected next month cost
        projected = trend_data.get('projected_next_month', 0)
        if projected > 0:
            projected_color = self._get_cost_color(projected)
            print(f"    Projected Next Month:   {colored(f'{self.currency_symbol}{projected:.2f}', projected_color)}")
        
        # Cost volatility
        volatility = trend_data.get('cost_volatility', 'UNKNOWN')
        volatility_color = {'LOW': 'green', 'MEDIUM': 'yellow', 'HIGH': 'red'}.get(volatility, 'white')
        volatility_icon = {'LOW': '🟢', 'MEDIUM': '🟡', 'HIGH': '🔴'}.get(volatility, '⚪')
        
        print(f"    Cost Volatility:        {volatility_icon} {colored(volatility, volatility_color)}")
        print()
        
        # Seasonal patterns (if available)
        seasonal = trend_data.get('seasonal_patterns', {})
        if seasonal:
            print("  Seasonal Patterns:")
            peak_month = seasonal.get('peak_month', 'Unknown')
            low_month = seasonal.get('low_month', 'Unknown')
            print(f"    Typical Peak Month:     {colored(peak_month, 'red')}")
            print(f"    Typical Low Month:      {colored(low_month, 'green')}")
            print()
        
        print("-" * self.console_width)
    
    def print_cost_forecast(self, forecast_data: Dict[str, Any]):
        """Print cost forecasting analysis
        
        Args:
            forecast_data: Dictionary containing forecast data
                {
                    'forecast_period_days': 90,
                    'forecasted_total_cost': 3500.0,
                    'confidence_interval': {'low': 3200.0, 'high': 3800.0},
                    'monthly_breakdown': [
                        {'month': '2025-02', 'predicted_cost': 1100.0},
                        {'month': '2025-03', 'predicted_cost': 1150.0},
                        {'month': '2025-04', 'predicted_cost': 1250.0}
                    ],
                    'cost_drivers': ['EC2 Instance Growth', 'Storage Expansion'],
                    'forecast_confidence': 'MEDIUM'
                }
        """
        print(colored("🔮 COST FORECAST", "cyan", attrs=["bold"]))
        print()
        
        if not forecast_data:
            print("  Cost forecasting not available - requires historical data")
            print("-" * self.console_width)
            return
        
        # Forecast overview
        forecast_period = forecast_data.get('forecast_period_days', 0)
        forecasted_cost = forecast_data.get('forecasted_total_cost', 0)
        confidence = forecast_data.get('forecast_confidence', 'UNKNOWN')
        
        confidence_color = {'HIGH': 'green', 'MEDIUM': 'yellow', 'LOW': 'red'}.get(confidence, 'white')
        forecast_color = self._get_cost_color(forecasted_cost)
        
        print(f"  Forecast Period:         {colored(f'{forecast_period} days', 'white')}")
        print(f"  Predicted Total Cost:    {colored(f'{self.currency_symbol}{forecasted_cost:.2f}', forecast_color, attrs=['bold'])}")
        print(f"  Forecast Confidence:     {colored(confidence, confidence_color)}")
        
        # Confidence interval
        interval = forecast_data.get('confidence_interval', {})
        if interval:
            low = interval.get('low', 0)
            high = interval.get('high', 0)
            print(f"  Confidence Range:        {colored(f'{self.currency_symbol}{low:.2f}', 'green')} - {colored(f'{self.currency_symbol}{high:.2f}', 'yellow')}")
        
        print()
        
        # Monthly breakdown
        monthly_breakdown = forecast_data.get('monthly_breakdown', [])
        if monthly_breakdown:
            print("  Monthly Forecast:")
            for month_data in monthly_breakdown:
                month = month_data.get('month', 'Unknown')
                cost = month_data.get('predicted_cost', 0)
                cost_color = self._get_cost_color(cost)
                print(f"    {month}:  {colored(f'{self.currency_symbol}{cost:.2f}', cost_color)}")
            print()
        
        # Cost drivers
        cost_drivers = forecast_data.get('cost_drivers', [])
        if cost_drivers:
            print("  Primary Cost Drivers:")
            for driver in cost_drivers[:5]:  # Top 5 drivers
                print(f"    • {driver}")
            print()
        
        print("-" * self.console_width)