# OpenShift Partner Labs Cost Estimator

A multi-cloud cost estimation tool for OpenShift Partner Labs that discovers cloud resources tagged with specific cluster UIDs and provides cost estimation and optimization suggestions.

## Overview

This tool helps you:
- **Discover** cloud resources associated with OpenShift clusters via tags
- **Estimate** costs for running infrastructure (even for stopped instances)
- **Optimize** spending with actionable suggestions
- **Export** cost reports in multiple formats (JSON, CSV, HTML)

Currently, supports **AWS** with planned support for **GCP** and **IBM Cloud**.

## Architecture

The project follows a modular architecture organized by cloud provider:

```
aws/
├── services/           # AWS service discovery modules (EC2, ELB, etc.)
├── cost/              # Cost estimation and analysis services
├── utils/             # Formatting and orchestration utilities
├── main.py            # CLI interface and orchestration
└── examples/          # Implementation examples and templates
```

### Key Features
- **Service Registry Pattern**: Pluggable architecture for AWS services
- **Tag-based Discovery**: Finds resources using cluster UIDs
- **Cost Estimation**: Optional integration with AWS Cost Explorer and Pricing APIs
- **Modular Design**: Easy to extend with new AWS services
- **Multiple Export Formats**: JSON, CSV, and HTML reports

## Installation

### Prerequisites
- Python 3.8 or higher
- [uv](https://docs.astral.sh/uv/) for Python package management
- AWS CLI configured with appropriate permissions

### Setup with uv

1. **Clone the repository**:
   ```bash
   git clone <repository-url>
   cd openshift-partner-labs-cost-estimator
   ```

2. **Create and activate virtual environment**:
   ```bash
   # Create virtual environment with uv
   uv venv

   # Activate the virtual environment
   # On Linux/macOS:
   source .venv/bin/activate
   # On Windows:
   # .venv\Scripts\activate
   ```

3. **Install dependencies**:
   ```bash
   uv pip install -r requirements.txt
   ```

### Alternative Installation with pip

If you prefer using pip:
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt
```

## AWS Permissions Required

### Basic Resource Discovery
```json
{
    "Version": "2012-10-17",
    "Statement": [
        {
            "Effect": "Allow",
            "Action": [
                "ec2:DescribeInstances",
                "ec2:DescribeVolumes", 
                "ec2:DescribeSecurityGroups",
                "ec2:DescribeNetworkInterfaces",
                "elasticloadbalancing:DescribeLoadBalancers",
                "elasticloadbalancing:DescribeTargetGroups"
            ],
            "Resource": "*"
        }
    ]
}
```

### Cost Estimation (Optional)
```json
{
    "Version": "2012-10-17", 
    "Statement": [
        {
            "Effect": "Allow",
            "Action": [
                "ce:GetCostAndUsage",
                "ce:GetCostForecast",
                "ce:GetReservationCoverage",
                "ce:GetReservationUtilization",
                "pricing:GetProducts"
            ],
            "Resource": "*"
        }
    ]
}
```

## Usage

### Basic Resource Discovery

Find all AWS resources tagged with a specific OpenShift cluster UID:

```bash
cd aws
python main.py --cluster-uid your-cluster-uid
```

Example output:
```
=== AWS Resource Discovery Results ===
Cluster: your-cluster-uid
Region: us-east-1

EC2 Service - instances (2 found):
  ✓ i-0123456789abcdef0 [running] t3.medium
  ✓ i-0987654321fedcba0 [stopped] t3.large

EC2 Service - volumes (3 found):
  ✓ vol-0123456789abcdef0 [in-use] 20 GB gp3
  ✓ vol-0987654321fedcba0 [in-use] 50 GB gp3
  ✓ vol-0555666777888999a [available] 30 GB gp2

ELB Service - load_balancers (1 found):
  ✓ my-cluster-lb [active] application
```

### Cost Estimation

Include cost analysis for discovered resources:

```bash
python main.py --cluster-uid your-cluster-uid --include-costs
```

Example with costs:
```
=== Cost Analysis Summary ===
Total Estimated Cost (30 days): $156.78

Service Breakdown:
  EC2-Instance: $89.28 (56.9%)
  EBS-Volume: $43.50 (27.7%) 
  ELB-Application: $24.00 (15.3%)

Top 3 Resources by Cost:
1. i-0123456789abcdef0 (t3.medium): $44.64/month
2. i-0987654321fedcba0 (t3.large): $44.64/month  
3. my-cluster-lb (application): $24.00/month

=== Optimization Suggestions ===
💡 High Impact Recommendations:
• Consider stopping unused instances to save ~$89.28/month
• Resize over-provisioned t3.large to t3.medium: ~$22/month savings
• Switch gp2 volumes to gp3 for better price/performance
```

### Export Cost Reports

Export detailed cost analysis to files:

```bash
# Export as JSON
python main.py --cluster-uid your-cluster-uid --include-costs \
  --export-format json --export-file cost-report.json

# Export as CSV  
python main.py --cluster-uid your-cluster-uid --include-costs \
  --export-format csv --export-file cost-report.csv

# Export as HTML
python main.py --cluster-uid your-cluster-uid --include-costs \
  --export-format html --export-file cost-report.html
```

### Advanced Options

```bash
# Specify AWS region
python main.py --cluster-uid your-cluster-uid --region us-west-2

# Custom cost analysis period (default: 30 days)
python main.py --cluster-uid your-cluster-uid --include-costs --days 7

# Verbose output for debugging
python main.py --cluster-uid your-cluster-uid --verbose
```

## Resource Discovery Logic

Resources are discovered by searching for the tag pattern that follows OpenShift installer tagging conventions:

- **Tag Key**: `kubernetes.io/cluster/{cluster-uid}`
- **Tag Value**: `owned`

This matches the standard tagging used by OpenShift when provisioning resources.

## Cost Calculation Notes

- **Stopped EC2 Instances**: Costs are calculated as if instances were running to provide total operational cost estimates
- **EBS Volumes**: Storage costs continue regardless of instance state
- **Load Balancers**: Charged hourly regardless of traffic
- **Security Groups & Network Interfaces**: No direct costs (AWS free resources)

## Testing

Run the test suite to verify functionality:

```bash
# Run all tests
python -m unittest discover -s aws -p "test_*.py"

# Run specific test files
python -m unittest aws.test_modular_framework
python -m unittest aws.test_cost_estimation  

# Run specific test class
python -m unittest aws.test_modular_framework.TestEC2Service
```

## Development

### Adding New AWS Services

1. Create the service file in `aws/services/` inheriting from `AWSService`
2. Implement required methods: `get_client()` and `search_resources()`
3. Register service in `aws/services/registry.py`
4. Use standardized `ResourceInfo` objects for consistency

Example service implementation:
```python
from .base import AWSService, ResourceInfo

class RDSService(AWSService):
    def __init__(self):
        super().__init__("RDS", ["db_instances", "db_clusters"])
    
    def get_client(self, session):
        return session.client('rds')
    
    def search_resources(self, client, tag_key, tag_value):
        # Implementation here
        pass
```

### Service Implementation Guidelines

- Use boto3 paginators for API calls when available
- Handle errors gracefully with `self.handle_error()`
- Follow tag-based discovery patterns
- Store additional metadata in `ResourceInfo.additional_info`

## Troubleshooting

### Common Issues

**Permission Denied Errors**:
- Verify AWS credentials are configured: `aws sts get-caller-identity`
- Check IAM permissions match requirements above
- Ensure AWS region is accessible

**No Resources Found**:
- Verify cluster UID is correct
- Check that resources have the correct OpenShift tags
- Try running with `--verbose` for detailed debug output

**Cost Estimation Errors**:
- Pricing API is only available in `us-east-1` region (handled automatically)
- Cost Explorer requires an opt-in and 24-hour activation period
- Verify Cost Explorer permissions are enabled

## Future Roadmap

- **GCP Support**: Google Cloud Platform resource discovery and cost estimation
- **IBM Cloud Support**: IBM Cloud resource discovery and cost estimation  
- **Unified Interface**: Cross-cloud provider resource management
- **Historical Analysis**: Trend analysis and cost forecasting
- **Budget Alerts**: Integration with cloud-native budget monitoring

## Contributing

1. Fork the repository
2. Create a feature branch
3. Add tests for new functionality
4. Ensure all tests pass
5. Submit a pull request

## License

Apache2.0