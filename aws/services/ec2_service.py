"""
EC2 service implementation for AWS resource discovery.
"""

from .base import AWSService, ResourceInfo
from botocore.exceptions import ClientError
from typing import Dict, List
import boto3


class EC2Service(AWSService):
    """EC2 service implementation"""
    
    def __init__(self):
        super().__init__("EC2", ["instances", "volumes", "security_groups", "network_interfaces"])
    
    def get_client(self, session: boto3.Session):
        return session.client('ec2')
    
    def search_resources(self, client, tag_key: str, tag_value: str) -> Dict[str, List[ResourceInfo]]:
        resources = {rt: [] for rt in self.resource_types}
        
        # Common tag filter
        tag_filter = [{'Name': f'tag:{tag_key}', 'Values': [tag_value]}]
        
        # EC2 Instances
        try:
            paginator = client.get_paginator('describe_instances')
            for page in paginator.paginate(Filters=tag_filter):
                for reservation in page['Reservations']:
                    for instance in reservation['Instances']:
                        resources['instances'].append(ResourceInfo(
                            id=instance['InstanceId'],
                            state=instance['State']['Name'],
                            type=instance.get('InstanceType', 'N/A'),
                            additional_info={
                                'launch_time': instance.get('LaunchTime'),
                                'resource_category': 'ec2_instance'
                            }
                        ))
        except ClientError as e:
            self.handle_error(e, 'instances')
        
        # EBS Volumes
        try:
            paginator = client.get_paginator('describe_volumes')
            for page in paginator.paginate(Filters=tag_filter):
                for volume in page['Volumes']:
                    resources['volumes'].append(ResourceInfo(
                        id=volume['VolumeId'],
                        state=volume['State'],
                        type=f"{volume['Size']} GB {volume.get('VolumeType', 'gp2')}",
                        additional_info={
                            'volume_type': volume.get('VolumeType'),
                            'size_gb': volume['Size'],
                            'resource_category': 'ebs_volume'
                        }
                    ))
        except ClientError as e:
            self.handle_error(e, 'volumes')
        
        # Security Groups
        try:
            paginator = client.get_paginator('describe_security_groups')
            for page in paginator.paginate(Filters=tag_filter):
                for sg in page['SecurityGroups']:
                    resources['security_groups'].append(ResourceInfo(
                        id=sg['GroupId'],
                        name=sg['GroupName'],
                        type=sg.get('VpcId', 'N/A'),
                        additional_info={
                            'description': sg.get('Description'),
                            'resource_category': 'security_group'
                        }
                    ))
        except ClientError as e:
            self.handle_error(e, 'security_groups')
        
        # Network Interfaces
        try:
            paginator = client.get_paginator('describe_network_interfaces')
            for page in paginator.paginate(Filters=tag_filter):
                for ni in page['NetworkInterfaces']:
                    resources['network_interfaces'].append(ResourceInfo(
                        id=ni['NetworkInterfaceId'],
                        state=ni['Status'],
                        type=ni.get('InterfaceType', 'N/A'),
                        additional_info={
                            'subnet_id': ni.get('SubnetId'),
                            'resource_category': 'network_interface'
                        }
                    ))
        except ClientError as e:
            self.handle_error(e, 'network_interfaces')
        
        return resources 