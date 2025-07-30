#!/usr/bin/env python3
"""
Test script for the modular AWS resource discovery framework

This script validates that the refactored code works correctly and demonstrates
the modular architecture.
"""

import sys
import os
import unittest
from unittest.mock import Mock, patch, MagicMock
from typing import Dict, List

# Add the current directory to the path so we can import modules
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from services import (
    AWSService, ResourceInfo, EC2Service, ELBService, 
    SERVICE_REGISTRY
)
from utils.formatter import ResourceFormatter
from utils.discoverer import AWSResourceDiscoverer


class TestResourceInfo(unittest.TestCase):
    """Test the ResourceInfo dataclass"""
    
    def test_resource_info_creation(self):
        """Test creating a ResourceInfo object"""
        resource = ResourceInfo(
            id="i-1234567890abcdef0",
            name="test-instance",
            state="running",
            type="t3.micro",
            additional_info={"launch_time": "2023-01-01T00:00:00Z"}
        )
        
        self.assertEqual(resource.id, "i-1234567890abcdef0")
        self.assertEqual(resource.name, "test-instance")
        self.assertEqual(resource.state, "running")
        self.assertEqual(resource.type, "t3.micro")
        self.assertEqual(resource.additional_info["launch_time"], "2023-01-01T00:00:00Z")


class TestEC2Service(unittest.TestCase):
    """Test the EC2Service implementation"""
    
    def setUp(self):
        self.service = EC2Service()
        self.mock_client = Mock()
        self.mock_session = Mock()
    
    def test_service_initialization(self):
        """Test EC2Service initialization"""
        self.assertEqual(self.service.service_name, "EC2")
        self.assertEqual(self.service.resource_types, [
            "instances", "volumes", "security_groups", "network_interfaces"
        ])
    
    def test_get_client(self):
        """Test getting EC2 client"""
        mock_session = Mock()
        client = self.service.get_client(mock_session)
        mock_session.client.assert_called_once_with('ec2')
    
    def test_search_resources_with_mock_data(self):
        """Test searching resources with mock AWS responses"""
        # Mock paginator responses for different resource types
        mock_instances_paginator = Mock()
        mock_instances_page = {
            'Reservations': [{
                'Instances': [{
                    'InstanceId': 'i-1234567890abcdef0',
                    'State': {'Name': 'running'},
                    'InstanceType': 't3.micro',
                    'LaunchTime': '2023-01-01T00:00:00Z'
                }]
            }]
        }
        mock_instances_paginator.paginate.return_value = [mock_instances_page]
        
        mock_volumes_paginator = Mock()
        mock_volumes_page = {'Volumes': []}
        mock_volumes_paginator.paginate.return_value = [mock_volumes_page]
        
        mock_sg_paginator = Mock()
        mock_sg_page = {'SecurityGroups': []}
        mock_sg_paginator.paginate.return_value = [mock_sg_page]
        
        mock_ni_paginator = Mock()
        mock_ni_page = {'NetworkInterfaces': []}
        mock_ni_paginator.paginate.return_value = [mock_ni_page]
        
        # Configure the client to return different paginators for different calls
        def get_paginator_side_effect(operation):
            if operation == 'describe_instances':
                return mock_instances_paginator
            elif operation == 'describe_volumes':
                return mock_volumes_paginator
            elif operation == 'describe_security_groups':
                return mock_sg_paginator
            elif operation == 'describe_network_interfaces':
                return mock_ni_paginator
            else:
                raise ValueError(f"Unknown operation: {operation}")
        
        self.mock_client.get_paginator.side_effect = get_paginator_side_effect
        
        # Test the search
        result = self.service.search_resources(
            self.mock_client, 
            "kubernetes.io/cluster/test-cluster", 
            "owned"
        )
        
        # Verify the structure
        self.assertIn('instances', result)
        self.assertIn('volumes', result)
        self.assertIn('security_groups', result)
        self.assertIn('network_interfaces', result)
        
        # Verify we got one instance
        self.assertEqual(len(result['instances']), 1)
        instance = result['instances'][0]
        self.assertEqual(instance.id, 'i-1234567890abcdef0')
        self.assertEqual(instance.state, 'running')
        self.assertEqual(instance.type, 't3.micro')


class TestELBService(unittest.TestCase):
    """Test the ELBService implementation"""
    
    def setUp(self):
        self.service = ELBService()
        self.mock_session = Mock()
    
    def test_service_initialization(self):
        """Test ELBService initialization"""
        self.assertEqual(self.service.service_name, "ELB")
        self.assertEqual(self.service.resource_types, ["classic_elbs", "albs_nlbs"])
    
    def test_get_client(self):
        """Test getting ELB client (should return None for multi-client service)"""
        mock_session = Mock()
        client = self.service.get_client(mock_session)
        self.assertIsNone(client)


class TestResourceFormatter(unittest.TestCase):
    """Test the ResourceFormatter utility"""
    
    def test_format_resource_info(self):
        """Test formatting a resource with full information"""
        resource = ResourceInfo(
            id="i-1234567890abcdef0",
            name="test-instance",
            state="running",
            type="t3.micro",
            region="us-west-2",
            additional_info={"launch_time": "2023-01-01T00:00:00Z"}
        )
        
        formatted = ResourceFormatter.format_resource_info(resource)
        self.assertIn("test-instance", formatted)
        self.assertIn("state: running", formatted)
        self.assertIn("type: t3.micro", formatted)
        self.assertIn("region: us-west-2", formatted)
        self.assertIn("launch_time: 2023-01-01T00:00:00Z", formatted)
    
    def test_format_resource_info_minimal(self):
        """Test formatting a resource with minimal information"""
        resource = ResourceInfo(id="i-1234567890abcdef0")
        
        formatted = ResourceFormatter.format_resource_info(resource)
        self.assertIn("i-1234567890abcdef0", formatted)
        self.assertNotIn("state:", formatted)
        self.assertNotIn("type:", formatted)


class TestAWSResourceDiscoverer(unittest.TestCase):
    """Test the AWSResourceDiscoverer orchestrator"""
    
    def setUp(self):
        self.mock_session = Mock()
        self.discoverer = AWSResourceDiscoverer(
            self.mock_session, 
            "kubernetes.io/cluster/test-cluster", 
            "owned"
        )
    
    def test_discoverer_initialization(self):
        """Test AWSResourceDiscoverer initialization"""
        self.assertEqual(self.discoverer.tag_key, "kubernetes.io/cluster/test-cluster")
        self.assertEqual(self.discoverer.tag_value, "owned")
        self.assertEqual(self.discoverer.results, {})


class TestServiceRegistry(unittest.TestCase):
    """Test the service registry functionality"""
    
    def test_service_registry_contains_expected_services(self):
        """Test that the service registry contains the expected services"""
        expected_services = ['EC2', 'ELB']
        for service_name in expected_services:
            self.assertIn(service_name, SERVICE_REGISTRY)
            self.assertIsInstance(SERVICE_REGISTRY[service_name], AWSService)
    
    def test_service_registry_services_have_correct_types(self):
        """Test that services in the registry have the correct types"""
        self.assertIsInstance(SERVICE_REGISTRY['EC2'], EC2Service)
        self.assertIsInstance(SERVICE_REGISTRY['ELB'], ELBService)


class TestIntegration(unittest.TestCase):
    """Integration tests for the complete workflow"""
    
    @patch('utils.discoverer.boto3.Session')
    def test_full_discovery_workflow(self, mock_session_class):
        """Test the complete discovery workflow with mocked AWS clients"""
        # Mock the session
        mock_session = Mock()
        mock_session_class.return_value = mock_session
        
        # Mock EC2 client and responses
        mock_ec2_client = Mock()
        mock_instances_paginator = Mock()
        mock_instances_page = {
            'Reservations': [{
                'Instances': [{
                    'InstanceId': 'i-1234567890abcdef0',
                    'State': {'Name': 'running'},
                    'InstanceType': 't3.micro',
                    'LaunchTime': '2023-01-01T00:00:00Z'
                }]
            }]
        }
        mock_instances_paginator.paginate.return_value = [mock_instances_page]
        
        mock_volumes_paginator = Mock()
        mock_volumes_page = {'Volumes': []}
        mock_volumes_paginator.paginate.return_value = [mock_volumes_page]
        
        mock_sg_paginator = Mock()
        mock_sg_page = {'SecurityGroups': []}
        mock_sg_paginator.paginate.return_value = [mock_sg_page]
        
        mock_ni_paginator = Mock()
        mock_ni_page = {'NetworkInterfaces': []}
        mock_ni_paginator.paginate.return_value = [mock_ni_page]
        
        def get_paginator_side_effect(operation):
            if operation == 'describe_instances':
                return mock_instances_paginator
            elif operation == 'describe_volumes':
                return mock_volumes_paginator
            elif operation == 'describe_security_groups':
                return mock_sg_paginator
            elif operation == 'describe_network_interfaces':
                return mock_ni_paginator
            else:
                raise ValueError(f"Unknown operation: {operation}")
        
        mock_ec2_client.get_paginator.side_effect = get_paginator_side_effect
        mock_session.client.return_value = mock_ec2_client
        
        # Create discoverer and run discovery
        discoverer = AWSResourceDiscoverer(
            mock_session, 
            "kubernetes.io/cluster/test-cluster", 
            "owned"
        )
        
        result = discoverer.discover_all_resources()
        
        # Verify the result structure
        self.assertIn('EC2', result)
        self.assertIn('ELB', result)
        
        # Verify EC2 results
        ec2_results = result['EC2']
        self.assertIn('instances', ec2_results)
        self.assertEqual(len(ec2_results['instances']), 1)
        
        # Verify the instance details
        instance = ec2_results['instances'][0]
        self.assertEqual(instance.id, 'i-1234567890abcdef0')
        self.assertEqual(instance.state, 'running')
        self.assertEqual(instance.type, 't3.micro')


def run_tests():
    """Run all tests"""
    # Create test suite
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()
    
    # Add test classes
    test_classes = [
        TestResourceInfo,
        TestEC2Service,
        TestELBService,
        TestResourceFormatter,
        TestAWSResourceDiscoverer,
        TestServiceRegistry,
        TestIntegration
    ]
    
    for test_class in test_classes:
        tests = loader.loadTestsFromTestCase(test_class)
        suite.addTests(tests)
    
    # Run tests
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    return result.wasSuccessful()


if __name__ == '__main__':
    success = run_tests()
    sys.exit(0 if success else 1) 