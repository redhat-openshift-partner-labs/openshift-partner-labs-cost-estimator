"""
Example RDS Service Implementation

This file demonstrates how to add a new AWS service to the modular framework.
To use this service:

1. Copy this file to services/rds_service.py
2. Add to services/registry.py:
   from .rds_service import RDSService
   SERVICE_REGISTRY['RDS'] = RDSService()
3. Import and use:
   from services import RDSService, SERVICE_REGISTRY

This example shows the complete implementation of an RDS service that discovers
RDS instances, snapshots, and subnet groups tagged for a Kubernetes cluster.
"""

import boto3
from botocore.exceptions import ClientError
from typing import Dict, List, Any

# Import the base classes from the services package
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from services.base import AWSService, ResourceInfo


class RDSService(AWSService):
    """
    RDS (Relational Database Service) implementation
    
    This service discovers RDS instances, snapshots, and subnet groups
    that are tagged for a specific Kubernetes cluster.
    
    Resource Types:
    - instances: RDS database instances
    - snapshots: RDS database snapshots
    - subnet_groups: RDS subnet groups
    
    Usage:
        from services import RDSService
        service = RDSService()
        session = boto3.Session()
        client = service.get_client(session)
        resources = service.search_resources(client, 'tag-key', 'tag-value')
    """
    
    def __init__(self):
        super().__init__("RDS", ["instances", "snapshots", "subnet_groups"])
    
    def get_client(self, session: boto3.Session):
        """Return the RDS client"""
        return session.client('rds')
    
    def search_resources(self, client, tag_key: str, tag_value: str) -> Dict[str, List[ResourceInfo]]:
        """Search for RDS resources with the specified tag
        
        Args:
            client: RDS boto3 client
            tag_key (str): Tag key to search for
            tag_value (str): Tag value to search for
            
        Returns:
            Dict[str, List[ResourceInfo]]: Dictionary mapping resource types to lists of resources
        """
        resources = {rt: [] for rt in self.resource_types}
        
        # RDS Instances
        try:
            paginator = client.get_paginator('describe_db_instances')
            for page in paginator.paginate():
                for instance in page['DBInstances']:
                    # Check tags for this instance
                    try:
                        tags = client.list_tags_for_resource(
                            ResourceName=instance['DBInstanceArn']
                        )['TagList']
                        
                        for tag in tags:
                            if tag['Key'] == tag_key and tag['Value'] == tag_value:
                                resources['instances'].append(ResourceInfo(
                                    id=instance['DBInstanceIdentifier'],
                                    name=instance['DBInstanceIdentifier'],
                                    state=instance['DBInstanceStatus'],
                                    type=instance['DBInstanceClass'],
                                    additional_info={
                                        'engine': instance['Engine'],
                                        'engine_version': instance.get('EngineVersion', 'N/A'),
                                        'storage': f"{instance['AllocatedStorage']} GB",
                                        'storage_type': instance.get('StorageType', 'N/A'),
                                        'multi_az': instance.get('MultiAZ', False),
                                        'endpoint': instance.get('Endpoint', {}).get('Address', 'N/A'),
                                        'port': instance.get('Endpoint', {}).get('Port', 'N/A')
                                    }
                                ))
                                break
                    except ClientError as e:
                        # Skip instances where we can't access tags
                        print(f"Warning: Cannot access tags for RDS instance {instance['DBInstanceIdentifier']}: {e}")
                        continue
                        
        except ClientError as e:
            self.handle_error(e, 'instances')
        
        # RDS Snapshots
        try:
            paginator = client.get_paginator('describe_db_snapshots')
            for page in paginator.paginate():
                for snapshot in page['DBSnapshots']:
                    try:
                        tags = client.list_tags_for_resource(
                            ResourceName=snapshot['DBSnapshotArn']
                        )['TagList']
                        
                        for tag in tags:
                            if tag['Key'] == tag_key and tag['Value'] == tag_value:
                                resources['snapshots'].append(ResourceInfo(
                                    id=snapshot['DBSnapshotIdentifier'],
                                    name=snapshot['DBSnapshotIdentifier'],
                                    state=snapshot['Status'],
                                    type=snapshot.get('SnapshotType', 'N/A'),
                                    additional_info={
                                        'db_instance': snapshot.get('DBInstanceIdentifier', 'N/A'),
                                        'engine': snapshot.get('Engine', 'N/A'),
                                        'storage': f"{snapshot.get('AllocatedStorage', 0)} GB",
                                        'created_time': snapshot.get('SnapshotCreateTime', 'N/A')
                                    }
                                ))
                                break
                    except ClientError as e:
                        # Skip snapshots where we can't access tags
                        print(f"Warning: Cannot access tags for RDS snapshot {snapshot['DBSnapshotIdentifier']}: {e}")
                        continue
                        
        except ClientError as e:
            self.handle_error(e, 'snapshots')
        
        # RDS Subnet Groups
        try:
            paginator = client.get_paginator('describe_db_subnet_groups')
            for page in paginator.paginate():
                for subnet_group in page['DBSubnetGroups']:
                    try:
                        tags = client.list_tags_for_resource(
                            ResourceName=subnet_group['DBSubnetGroupArn']
                        )['TagList']
                        
                        for tag in tags:
                            if tag['Key'] == tag_key and tag['Value'] == tag_value:
                                resources['subnet_groups'].append(ResourceInfo(
                                    id=subnet_group['DBSubnetGroupName'],
                                    name=subnet_group['DBSubnetGroupName'],
                                    state='active',  # Subnet groups don't have a state field
                                    type=subnet_group.get('VpcId', 'N/A'),
                                    additional_info={
                                        'description': subnet_group.get('DBSubnetGroupDescription', 'N/A'),
                                        'subnets': [subnet['SubnetIdentifier'] for subnet in subnet_group['Subnets']],
                                        'vpc': subnet_group.get('VpcId', 'N/A')
                                    }
                                ))
                                break
                    except ClientError as e:
                        # Skip subnet groups where we can't access tags
                        print(f"Warning: Cannot access tags for RDS subnet group {subnet_group['DBSubnetGroupName']}: {e}")
                        continue
                        
        except ClientError as e:
            self.handle_error(e, 'subnet_groups')
        
        return resources


# Example usage and testing
if __name__ == '__main__':
    """
    Example usage of the RDS service
    
    This demonstrates how to use the RDS service in isolation for testing
    or integration into other applications.
    """
    
    # Create service instance
    rds_service = RDSService()
    
    # Create AWS session (you would use real credentials in production)
    session = boto3.Session()
    
    # Get RDS client
    client = rds_service.get_client(session)
    
    # Search for resources (replace with actual tag key/value)
    tag_key = "kubernetes.io/cluster/example-cluster"
    tag_value = "owned"
    
    try:
        resources = rds_service.search_resources(client, tag_key, tag_value)
        
        # Print results
        print(f"RDS Resources found for tag {tag_key}:{tag_value}")
        for resource_type, resource_list in resources.items():
            print(f"\n{resource_type.title()} ({len(resource_list)}):")
            for resource in resource_list:
                print(f"  - {resource.id} ({resource.state})")
                
    except Exception as e:
        print(f"Error searching RDS resources: {e}")
    
    print("\nTo integrate this service into the main framework:")
    print("1. Copy this file to services/rds_service.py")
    print("2. Add to services/registry.py:")
    print("   from .rds_service import RDSService")
    print("   SERVICE_REGISTRY['RDS'] = RDSService()")
    print("3. Use with main script:")
    print("   python main.py --cluster-uid your-cluster --services RDS") 