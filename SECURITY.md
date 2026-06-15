# Security

## Reporting a Vulnerability

If you discover a potential security issue in this project, we ask that you notify AWS/Amazon Security via our
[vulnerability reporting page](http://aws.amazon.com/security/vulnerability-reporting/).

Please do **not** create a public GitHub issue for security vulnerabilities.

## Security Considerations

This project is a sample implementation for educational and demonstration purposes. It is **not** intended for
production use without additional security hardening.

### Production Recommendations

If you plan to adapt this code for production use, consider the following:

#### Authentication & Authorization
- Implement least-privilege IAM policies (replace broad policies like `AmazonRedshiftFullAccess` with scoped resource-level permissions)
- Use IAM roles instead of long-lived credentials
- Restrict QuickSight dashboard permissions to specific users/groups rather than namespace-wide access
- Enable MFA for all AWS console access

#### Secrets Management
- Never commit credentials, account IDs, or ARNs to source control
- Use `config/datasource.local.json` (git-ignored) for real credentials
- Rotate Secrets Manager secrets on a regular schedule
- Use AWS KMS customer-managed keys for encryption at rest

#### Network Security
- Keep Redshift clusters in private subnets (no public accessibility)
- Use VPC endpoints for all AWS service communication
- Restrict security group rules to minimum required ports and sources
- Enable VPC Flow Logs for network monitoring

#### Data Protection
- Enable encryption at rest for Redshift clusters (AES-256)
- Enable SSL/TLS for data in transit (Redshift `require_ssl = true`)
- Implement column-level security in QuickSight for PII fields
- Use Row-Level Security (RLS) in QuickSight datasets for multi-tenant access

#### Logging & Monitoring
- Enable AWS CloudTrail for API audit logging
- Enable QuickSight audit logging
- Set up CloudWatch alarms for failed API calls and unusual activity
- Monitor Redshift query logs for unauthorized access patterns

#### Code Security
- Pin all Python dependency versions
- Run `pip audit` or `safety check` regularly for known vulnerabilities
- Validate and sanitize all inputs before passing to AWS APIs
- Never log or print secrets, ARNs with account IDs, or PII

#### Deployment
- Use infrastructure-as-code (CloudFormation/CDK) for reproducible deployments
- Implement separate environments (dev/staging/prod) with isolated accounts
- Use CI/CD pipelines with security scanning gates
- Tag all AWS resources for cost allocation and access control

## Dependencies

This project uses the following key dependencies:
- `boto3` — AWS SDK for Python (Apache 2.0)

Ensure you keep dependencies updated and review security advisories regularly.
