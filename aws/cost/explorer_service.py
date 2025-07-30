"""
AWS Cost Explorer service for retrieving cost and usage data.
"""

from .base import CostService
from typing import Dict, List, Any, Optional
from datetime import datetime, timedelta
import boto3


class CostExplorerService(CostService):
    """Service for interacting with AWS Cost Explorer API"""
    
    def __init__(self):
        super().__init__("CostExplorer")
        self.client = None
    
    def get_client(self, session: boto3.Session):
        """Get the Cost Explorer client"""
        if not self.client:
            self.client = session.client('ce')
        return self.client
    
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
        
        try:
            # Build the request parameters
            request_params = {
                'TimePeriod': {
                    'Start': start_date.strftime('%Y-%m-%d'),
                    'End': end_date.strftime('%Y-%m-%d')
                },
                'Granularity': granularity,
                'Metrics': metrics,
                'GroupBy': group_by or []
            }
            
            # Only add Filter if filter_expression is not None
            if filter_expression is not None:
                request_params['Filter'] = filter_expression
            
            response = self.client.get_cost_and_usage(**request_params)
            return response
        except Exception as e:
            self.handle_error(e, 'get_cost_and_usage')
            return {}
    
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
        except Exception as e:
            self.handle_error(e, 'get_cost_forecast')
            return {}
    
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
        except Exception as e:
            self.handle_error(e, 'get_reservation_coverage')
            return {}
    
    def get_dimension_values(
        self,
        dimension: str,
        start_date: datetime,
        end_date: datetime
    ) -> Dict[str, Any]:
        """Get dimension values for cost analysis"""
        try:
            response = self.client.get_dimension_values(
                Dimension=dimension,
                TimePeriod={
                    'Start': start_date.strftime('%Y-%m-%d'),
                    'End': end_date.strftime('%Y-%m-%d')
                }
            )
            return response
        except Exception as e:
            self.handle_error(e, 'get_dimension_values')
            return {}
    
    def get_tags(
        self,
        start_date: datetime,
        end_date: datetime
    ) -> Dict[str, Any]:
        """Get available tags for cost analysis"""
        try:
            response = self.client.get_tags(
                TimePeriod={
                    'Start': start_date.strftime('%Y-%m-%d'),
                    'End': end_date.strftime('%Y-%m-%d')
                }
            )
            return response
        except Exception as e:
            self.handle_error(e, 'get_tags')
            return {} 