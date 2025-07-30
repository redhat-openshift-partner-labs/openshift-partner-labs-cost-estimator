"""
Tests for the cost estimation feature.

This module tests the cost estimation functionality including:
- Cost service base classes
- Cost Explorer service
- Cost Analyzer service
- Cost Reporter service
- Integration with existing services
"""

import unittest
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime, timedelta
from typing import Dict, List, Any

# Import cost services
from cost.base import CostRecord, CostSummary, OptimizationSuggestion, CostService
from cost.explorer_service import CostExplorerService
from cost.analyzer_service import CostAnalyzerService
from cost.reporter_service import CostReporterService
from cost.registry import COST_SERVICE_REGISTRY, get_available_cost_services

# Import existing services for integration testing
from services.base import ResourceInfo, AWSService
from services import SERVICE_REGISTRY


class TestCostDataStructures(unittest.TestCase):
    """Test cost data structures"""
    
    def test_cost_record_creation(self):
        """Test CostRecord creation"""
        start_date = datetime.now() - timedelta(days=30)
        end_date = datetime.now()
        
        record = CostRecord(
            start_date=start_date,
            end_date=end_date,
            amount=100.50,
            service="EC2",
            usage_type="BoxUsage"
        )
        
        self.assertEqual(record.amount, 100.50)
        self.assertEqual(record.service, "EC2")
        self.assertEqual(record.currency, "USD")
        self.assertEqual(record.unit, "Hrs")
    
    def test_cost_summary_creation(self):
        """Test CostSummary creation"""
        start_date = datetime.now() - timedelta(days=30)
        end_date = datetime.now()
        
        summary = CostSummary(
            total_cost=500.75,
            period_start=start_date,
            period_end=end_date,
            cost_breakdown={"EC2": 300.25, "EBS": 200.50},
            resource_count=5,
            average_cost_per_resource=100.15,
            cost_trend="increasing",
            forecast_30_days=600.00,
            forecast_90_days=1800.00
        )
        
        self.assertEqual(summary.total_cost, 500.75)
        self.assertEqual(summary.resource_count, 5)
        self.assertEqual(summary.cost_trend, "increasing")
    
    def test_optimization_suggestion_creation(self):
        """Test OptimizationSuggestion creation"""
        suggestion = OptimizationSuggestion(
            resource_id="i-1234567890abcdef0",
            resource_type="t3.large",
            current_cost=150.00,
            potential_savings=45.00,
            suggestion_type="resize",
            description="Consider downsizing to t3.medium",
            implementation_steps=["Step 1", "Step 2"],
            risk_level="low"
        )
        
        self.assertEqual(suggestion.resource_id, "i-1234567890abcdef0")
        self.assertEqual(suggestion.potential_savings, 45.00)
        self.assertEqual(suggestion.risk_level, "low")


class TestCostExplorerService(unittest.TestCase):
    """Test CostExplorerService"""
    
    def setUp(self):
        self.service = CostExplorerService()
        self.mock_session = Mock()
        self.mock_client = Mock()
        self.mock_session.client.return_value = self.mock_client
    
    def test_service_initialization(self):
        """Test service initialization"""
        self.assertEqual(self.service.service_name, "CostExplorer")
    
    def test_get_client(self):
        """Test client creation"""
        client = self.service.get_client(self.mock_session)
        self.mock_session.client.assert_called_once_with('ce')
        self.assertEqual(client, self.mock_client)
    
    @patch('cost.explorer_service.CostExplorerService.handle_error')
    def test_get_cost_and_usage_success(self, mock_handle_error):
        """Test successful cost and usage retrieval"""
        self.service.client = self.mock_client
        
        # Mock successful response
        mock_response = {
            'ResultsByTime': [
                {
                    'TimePeriod': {'Start': '2024-01-01', 'End': '2024-01-02'},
                    'Total': {'UnblendedCost': {'Amount': '100.50', 'Unit': 'USD'}}
                }
            ]
        }
        self.mock_client.get_cost_and_usage.return_value = mock_response
        
        start_date = datetime.now() - timedelta(days=30)
        end_date = datetime.now()
        
        result = self.service.get_cost_and_usage(start_date, end_date)
        
        self.assertEqual(result, mock_response)
        self.mock_client.get_cost_and_usage.assert_called_once()
    
    @patch('cost.explorer_service.CostExplorerService.handle_error')
    def test_get_cost_and_usage_error(self, mock_handle_error):
        """Test error handling in cost and usage retrieval"""
        self.service.client = self.mock_client
        self.mock_client.get_cost_and_usage.side_effect = Exception("API Error")
        
        start_date = datetime.now() - timedelta(days=30)
        end_date = datetime.now()
        
        result = self.service.get_cost_and_usage(start_date, end_date)
        
        self.assertEqual(result, {})
        mock_handle_error.assert_called_once()


class TestCostAnalyzerService(unittest.TestCase):
    """Test CostAnalyzerService"""
    
    def setUp(self):
        self.service = CostAnalyzerService()
        self.mock_explorer = Mock()
        self.service.set_explorer_service(self.mock_explorer)
    
    def test_service_initialization(self):
        """Test service initialization"""
        self.assertEqual(self.service.service_name, "CostAnalyzer")
    
    def test_generate_cost_summary(self):
        """Test cost summary generation"""
        # Create mock resources with cost data
        resources = [
            ResourceInfo(
                id="i-1",
                cost_data={"total_cost": 100.0, "service": "EC2"}
            ),
            ResourceInfo(
                id="i-2", 
                cost_data={"total_cost": 200.0, "service": "EBS"}
            )
        ]
        
        start_date = datetime.now() - timedelta(days=30)
        end_date = datetime.now()
        
        summary = self.service.generate_cost_summary(resources, start_date, end_date)
        
        self.assertEqual(summary.total_cost, 300.0)
        self.assertEqual(summary.resource_count, 2)
        self.assertEqual(summary.average_cost_per_resource, 150.0)
        self.assertIn("EC2", summary.cost_breakdown)
        self.assertIn("EBS", summary.cost_breakdown)
    
    def test_identify_optimization_opportunities(self):
        """Test optimization opportunity identification"""
        # Create mock resources with cost data
        resources = [
            ResourceInfo(
                id="i-1",
                type="t3.large instance",
                cost_data={"total_cost": 150.0}
            )
        ]
        
        suggestions = self.service.identify_optimization_opportunities(resources)
        
        # Should find optimization suggestions for high-cost instances
        self.assertGreater(len(suggestions), 0)
        self.assertEqual(suggestions[0].resource_id, "i-1")
        self.assertEqual(suggestions[0].suggestion_type, "resize")


class TestCostReporterService(unittest.TestCase):
    """Test CostReporterService"""
    
    def setUp(self):
        self.service = CostReporterService()
    
    def test_service_initialization(self):
        """Test service initialization"""
        self.assertEqual(self.service.service_name, "CostReporter")
    
    def test_print_cost_summary(self):
        """Test cost summary printing"""
        start_date = datetime.now() - timedelta(days=30)
        end_date = datetime.now()
        
        summary = CostSummary(
            total_cost=500.75,
            period_start=start_date,
            period_end=end_date,
            cost_breakdown={"EC2": 300.25, "EBS": 200.50},
            resource_count=5,
            average_cost_per_resource=100.15,
            cost_trend="increasing",
            forecast_30_days=600.00,
            forecast_90_days=1800.00
        )
        
        # This should not raise any exceptions
        self.service.print_cost_summary(summary, "test-cluster")
    
    def test_print_optimization_suggestions(self):
        """Test optimization suggestions printing"""
        suggestions = [
            OptimizationSuggestion(
                resource_id="i-1",
                resource_type="t3.large",
                current_cost=150.00,
                potential_savings=45.00,
                suggestion_type="resize",
                description="Test suggestion",
                implementation_steps=["Step 1"],
                risk_level="low"
            )
        ]
        
        # This should not raise any exceptions
        self.service.print_optimization_suggestions(suggestions)
    
    def test_export_to_json(self):
        """Test JSON export"""
        start_date = datetime.now() - timedelta(days=30)
        end_date = datetime.now()
        
        summary = CostSummary(
            total_cost=500.75,
            period_start=start_date,
            period_end=end_date,
            cost_breakdown={"EC2": 300.25},
            resource_count=2,
            average_cost_per_resource=250.375,
            cost_trend="stable",
            forecast_30_days=500.75,
            forecast_90_days=1502.25
        )
        
        resources = {
            "EC2": [
                ResourceInfo(id="i-1", cost_data={"total_cost": 300.25}),
                ResourceInfo(id="i-2", cost_data={"total_cost": 200.50})
            ]
        }
        
        # Test JSON export
        with patch('builtins.open', create=True) as mock_open:
            mock_file = Mock()
            mock_open.return_value.__enter__.return_value = mock_file
            
            self.service.export_to_json(summary, resources, "test.json")
            
            mock_file.write.assert_called()
    
    def test_export_to_csv(self):
        """Test CSV export"""
        start_date = datetime.now() - timedelta(days=30)
        end_date = datetime.now()
        
        summary = CostSummary(
            total_cost=500.75,
            period_start=start_date,
            period_end=end_date,
            cost_breakdown={"EC2": 300.25},
            resource_count=1,
            average_cost_per_resource=500.75,
            cost_trend="stable",
            forecast_30_days=500.75,
            forecast_90_days=1502.25
        )
        
        resources = {
            "EC2": [ResourceInfo(id="i-1", cost_data={"total_cost": 300.25})]
        }
        
        # Test CSV export
        with patch('builtins.open', create=True) as mock_open:
            mock_file = Mock()
            mock_open.return_value.__enter__.return_value = mock_file
            
            self.service.export_to_csv(summary, resources, "test.csv")
            
            mock_file.write.assert_called()


class TestCostRegistry(unittest.TestCase):
    """Test cost service registry"""
    
    def test_get_available_cost_services(self):
        """Test getting available cost services"""
        services = get_available_cost_services()
        expected_services = ['explorer', 'analyzer', 'reporter']
        
        for service in expected_services:
            self.assertIn(service, services)
    
    def test_cost_service_registry(self):
        """Test cost service registry"""
        self.assertIn('explorer', COST_SERVICE_REGISTRY)
        self.assertIn('analyzer', COST_SERVICE_REGISTRY)
        self.assertIn('reporter', COST_SERVICE_REGISTRY)
        
        # Check that services are properly instantiated
        self.assertIsInstance(COST_SERVICE_REGISTRY['explorer'], CostExplorerService)
        self.assertIsInstance(COST_SERVICE_REGISTRY['analyzer'], CostAnalyzerService)
        self.assertIsInstance(COST_SERVICE_REGISTRY['reporter'], CostReporterService)


class TestEnhancedResourceInfo(unittest.TestCase):
    """Test enhanced ResourceInfo with cost data"""
    
    def test_backward_compatibility(self):
        """Test that ResourceInfo maintains backward compatibility"""
        # Old style ResourceInfo should still work
        resource = ResourceInfo(
            id="i-1234567890abcdef0",
            name="test-instance",
            type="t3.micro",
            state="running"
        )
        
        self.assertEqual(resource.id, "i-1234567890abcdef0")
        self.assertEqual(resource.name, "test-instance")
        self.assertIsNone(resource.cost_data)
        self.assertIsNone(resource.cost_history)
        self.assertIsNone(resource.cost_forecast)
        self.assertIsNone(resource.optimization_suggestions)
    
    def test_with_cost_data(self):
        """Test ResourceInfo with cost data"""
        resource = ResourceInfo(
            id="i-1234567890abcdef0",
            name="test-instance",
            type="t3.micro",
            state="running",
            cost_data={"total_cost": 100.50, "service": "EC2"},
            cost_history=[CostRecord(
                start_date=datetime.now() - timedelta(days=30),
                end_date=datetime.now(),
                amount=100.50,
                service="EC2"
            )],
            cost_forecast=[CostRecord(
                start_date=datetime.now(),
                end_date=datetime.now() + timedelta(days=30),
                amount=110.00,
                service="EC2"
            )],
            optimization_suggestions=[OptimizationSuggestion(
                resource_id="i-1234567890abcdef0",
                resource_type="t3.micro",
                current_cost=100.50,
                potential_savings=20.00,
                suggestion_type="resize",
                description="Test suggestion",
                implementation_steps=["Step 1"],
                risk_level="low"
            )]
        )
        
        self.assertEqual(resource.cost_data["total_cost"], 100.50)
        self.assertEqual(len(resource.cost_history), 1)
        self.assertEqual(len(resource.cost_forecast), 1)
        self.assertEqual(len(resource.optimization_suggestions), 1)


class TestIntegrationWithExistingServices(unittest.TestCase):
    """Test integration with existing services"""
    
    def test_awsservice_cost_integration(self):
        """Test that AWSService can integrate with cost services"""
        # Create a mock service that inherits from AWSService
        class MockService(AWSService):
            def get_client(self, session):
                return Mock()
            
            def search_resources(self, client, tag_key, tag_value):
                return {"instances": [ResourceInfo(id="i-1")]}
        
        service = MockService("MockService", ["instances"])
        
        # Test that cost analyzer can be set
        mock_analyzer = Mock()
        service.set_cost_analyzer(mock_analyzer)
        
        self.assertEqual(service.cost_analyzer, mock_analyzer)
    
    def test_cost_enrichment(self):
        """Test cost enrichment of resources"""
        # Create mock resources
        resources = {
            "instances": [
                ResourceInfo(id="i-1"),
                ResourceInfo(id="i-2")
            ]
        }
        
        # Create mock cost analyzer
        mock_analyzer = Mock()
        mock_analyzer.analyze_resource_costs.return_value = [
            ResourceInfo(id="i-1", cost_data={"total_cost": 100.0}),
            ResourceInfo(id="i-2", cost_data={"total_cost": 200.0})
        ]
        
        # Create mock service
        class MockService(AWSService):
            def get_client(self, session):
                return Mock()
            
            def search_resources(self, client, tag_key, tag_value):
                return resources
        
        service = MockService("MockService", ["instances"])
        service.set_cost_analyzer(mock_analyzer)
        
        # Test cost enrichment
        start_date = datetime.now() - timedelta(days=30)
        end_date = datetime.now()
        
        enriched = service.enrich_resources_with_costs(resources, start_date, end_date)
        
        # Verify that cost analyzer was called
        mock_analyzer.analyze_resource_costs.assert_called_once()


if __name__ == '__main__':
    unittest.main() 