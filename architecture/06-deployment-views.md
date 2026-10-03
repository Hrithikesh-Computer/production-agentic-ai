# AWS Deployment View (Candidate)

**Status:** Illustrative mapping for discussion; not a selected customer deployment or repository implementation.
**Cloud assumption:** AWS is used only to make one mapping concrete. The customer cloud, CRM hosting/network, identity provider, provider choice, and region are unknown.

## Mapping

| Logical container / concern | Candidate AWS service | Boundary and decision notes |
|---|---|---|
| Browser UI and edge protection | S3 private origin + CloudFront + AWS WAF | Static UI only. Keep S3 origin private; confirm customer DNS, certificate, WAF rules, and browser security requirements. |
| User API and identity validation | API Gateway HTTP API with JWT authorizer and private VPC integration | Validate customer IdP issuer/audience and token claims. API Gateway authentication is not action authorization; pass verified identity/tenant context to the authority gateway. Confirm private integration topology and rate limits. |
| Agent API/orchestrator | ECS Fargate service in private subnets, across at least two availability zones for a production availability target | Task role has only required model, CRM-adapter, queue, and audit permissions. No public IP. Autoscaling limits must align with model/CRM quotas. |
| Authority and approval gateway | Separate ECS Fargate service in private subnets | Evaluates domain actions and binds approval to proposal/record version. If using an external PDP, deploy it behind this boundary and define policy distribution, availability, and fail-closed write behavior. |
| Approval workflow | SQS for asynchronous work/notifications plus DynamoDB conditional state for proposal, decision, expiry, and one-time execution state | Queue delivery is at-least-once; consumers must be idempotent. DynamoDB conditional writes can support atomic state transitions, subject to implementation and tests. Human UI needs an authenticated reviewer API. |
| CRM connector | ECS Fargate service in private subnets | Use delegated user authorization or a narrowly scoped integration identity, selected with customer IAM/CRM owners. Egress only through approved NAT/firewall, VPN, or Direct Connect path; exact path depends on CRM location. |
| Customer CRM | Existing customer CRM, external to this AWS account | Continue CRM-native row/field/object authorization. Use conditional updates/version checks and idempotency if the API supports them; not assumed. |
| Model invocation | Amazon Bedrock as a candidate, or an approved external provider behind controlled egress | Provider, model, region, data retention/training configuration, private connectivity, and contractual terms must be selected after privacy/security review. Do not send credentials or unnecessary CRM fields. |
| Audit event store | Structured app events delivered to a restricted S3 bucket with Object Lock where retention policy requires it; CloudWatch Logs for operational diagnostics | Separate security/audit events from debug logs. Define encryption, retention, legal hold, access, deletion, export, and audit-write failure behavior. Object Lock configuration and account controls require verification; no immutability claim is made here. |
| Secrets and encryption keys | AWS Secrets Manager and AWS KMS | Store CRM integration secrets only if a service credential is chosen. Use task roles for AWS service access. Define rotation, break-glass, and key ownership. This is not a decision to store delegated user tokens long-term. |
| Metrics, traces, and alerts | CloudWatch metrics/logs; OpenTelemetry collector/export only if the chosen instrumentation path requires it | Emit request/policy/approval/CRM/model timing and error metrics without raw prompt/CRM content by default. Confirm retention and export controls. |
| Network and admin plane | VPC private subnets, security groups, VPC endpoints where applicable, centralized AWS account logging and CloudTrail | Use separate environment/accounts and restricted admin roles. Network segmentation, egress inspection, account vending, and landing-zone standards are customer-specific. |

## Deployment flow

[Open the AWS deployment flow diagram](diagrams/aws-deployment.mmd).

1. Employee and reviewer reach the static UI through CloudFront/WAF. API requests go through API Gateway, which validates the customer IdP token before private integration.
2. The agent service validates task scope through the authority gateway. CRM calls go through the connector, which must obtain a fresh action-bound decision before contacting the CRM.
3. The agent invokes the approved model endpoint using its task role or controlled egress. Data minimization and provider settings remain mandatory regardless of network path.
4. Write proposals enter the approval workflow. The reviewer acts through the authenticated UI; the authority gateway records a decision and rechecks current state immediately before execution.
5. Application audit events flow to the restricted audit store; operational logs, metrics, and traces use a separate diagnostic path.

## Failure behavior to design

- **JWT/IdP unavailable or invalid:** reject new protected requests; do not use cached identity past its approved lifetime.
- **Authority/PDP unavailable:** fail closed for writes; define safe read degradation explicitly.
- **Queue or state store unavailable:** do not claim an approval is recorded; do not execute a write.
- **CRM timeout after write request:** classify outcome as unknown, query/reconcile before retry, and use idempotency/conditional updates where supported.
- **Audit destination unavailable:** define whether operations pause, buffer in a bounded durable outbox, or proceed with a high-severity alert; never silently drop security events.
- **Model unavailable:** return a controlled error or deterministic non-model fallback; do not broaden CRM access.

## Customer decisions required

Choose the AWS account/region and landing zone; identity provider and claim mapping; CRM connection and authorization model; model/provider and data contract; approval separation-of-duties rules; audit retention/legal hold; availability, RTO/RPO, and latency targets; egress policy; and operational owners. This diagram is not IaC, a deployment runbook, a security certification, or evidence that any listed service is deployed.
