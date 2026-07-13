# NimbusFlow

A serverless AWS platform demonstrating three distinct event-driven trigger patterns — HTTP request, storage event, and scheduled time — all built on a shared design philosophy: **serverless-first, least-privilege IAM, and no idle compute.**

Built entirely on AWS Free Tier via the AWS Console, in the `ap-south-1` (Mumbai) region.

---

## Overview

Rather than three disconnected demo projects, NimbusFlow is one platform where every component follows the same underlying shape:

```
Trigger fires → Lambda function reacts → Action happens
```

Only the trigger source changes across components:

| Component | Trigger | AWS Services |
|---|---|---|
| URL Shortener | HTTP request | API Gateway, Lambda, DynamoDB |
| Image Processing Pipeline | File upload (storage event) | S3, Lambda, SNS |
| Cost Automation | Scheduled time | EventBridge, Lambda, EC2 |

No component runs on always-on compute — everything only executes (and only costs money) when actually triggered.

---

## Architecture

![Architecture Diagram]
<img width="2692" height="10336" alt="image" src="https://github.com/user-attachments/assets/0e84f108-d06a-4c64-bc3b-91c37b4b594b" />


---

## Components

### 1. URL Shortener
A serverless API that generates short codes for long URLs and redirects on lookup.

- **POST** request → Lambda generates a random short code → stored in DynamoDB
- **GET** request to the short link → Lambda looks up the code → returns an HTTP redirect
- DynamoDB used in on-demand capacity mode to stay within Free Tier
- IAM permissions scoped to exactly `PutItem` / `GetItem` on this table only

### 2. Image Processing Pipeline
An event-driven pipeline that automatically processes images on upload.

- Upload to an S3 "input" bucket triggers a Lambda function
- Lambda uses a custom-built Pillow layer to resize (max 800×800, aspect-ratio preserved) and watermark the image
- Processed image is written to a separate "output" S3 bucket
- A notification is published via SNS on successful processing
- IAM permissions scoped per-bucket (`GetObject` on input, `PutObject` on output) plus a scoped `sns:Publish`

### 3. Cost Automation
A scheduled safety net that stops and starts tagged EC2 instances automatically, so test/dev resources don't run (and cost money) unattended.

- Two EventBridge scheduled rules (cron-based) — one triggers a "stop" action, one triggers a "start" action
- A single Lambda function handles both directions, branching on an `action` input passed by whichever rule fired
- Instances are targeted by tag (not hardcoded instance IDs), so the automation scales to any instance tagged appropriately
- IAM policy uses a wildcard resource for EC2 start/stop/describe, since these actions don't support resource-level ARN restriction the way S3/DynamoDB do — a documented, deliberate simplification rather than an oversight

---

## Extent of Application

While initially provisioned manually via the AWS Management Console to establish baseline familiarity with each service's configuration surface, the NimbusFlow architecture is designed as a modular blueprint that translates directly into enterprise, high-scale automation:

* **Infrastructure-as-Code (IaC) Readiness:** The decoupled service topology, strict naming conventions, and isolated IAM roles serve as a direct template for declarative deployment tools. The configuration parameters can be mapped seamlessly into Terraform modules, OpenTofu, or AWS Cloud Development Kit (CDK) configurations.
* **Scale-Independent Economics:** By relying exclusively on serverless billing and trigger models—including AWS Lambda's millisecond execution compute, S3 object notification events, and DynamoDB's on-demand capacity mode—the architecture maintains a true zero-cost baseline when idle. When traffic bursts occur, the platform auto-scales natively to handle thousands of concurrent invocations without structural modifications.
* **Pluggable Architecture:** The compute layer is fully decoupled from ingestion, meaning the business logic inside the Lambda handlers functions independently of the entry triggers. Developers can easily swap out or append business logic—such as replacing the Pillow image manipulation code with an optical character recognition (OCR) engine, or extending the EC2 scheduler to manage RDS database clusters—without altering the underlying infrastructure triggers.

---

## Design Decisions & Trade-offs

- **Console-first, not Terraform** — built manually through the AWS Console to build hands-on familiarity with each service's configuration surface before automating it. A Terraform version is a natural next iteration.
- **Least-privilege IAM per function** — every Lambda has its own scoped role/policy rather than one shared broad role, except where AWS's IAM model doesn't support finer scoping (documented explicitly where this applies).
- **Free Tier discipline** — every service choice (Lambda, DynamoDB on-demand, S3, SNS, EventBridge) was picked specifically to stay within AWS's always-free tier rather than the 12-month trial tier, so the platform can run indefinitely without cost risk.

---

## Bugs Encountered & Fixed

Debugging real issues was a significant part of building this — documenting them here rather than hiding them:

| Issue | Root Cause | Fix |
|---|---|---|
| Lambda not reading HTTP method correctly | HTTP API uses payload format v2, not the older REST API v1 shape | Read method via `event['requestContext']['http']['method']` instead of `event['httpMethod']` |
| No logs appearing for a Lambda function | IAM role had a scoped custom policy but was missing `AWSLambdaBasicExecutionRole`, so no CloudWatch log group was ever created | Attached the AWS-managed logging policy alongside the custom scoped policy |
| Image-processing Lambda layer not loading | Lambda function was created with `arm64` architecture, but the custom Pillow layer was built for `x86_64` | Recreated the function with matching `x86_64` architecture |
| Image-processing Lambda timing out | Default 128 MB memory / 3 second timeout wasn't enough for download → resize → watermark → upload → publish | Increased to 256 MB memory / 30 second timeout, still within Free Tier |
| Cost-automation Lambda returning "no tagged instances found" despite correct tagging | Tag value on the EC2 instance was lowercase (`true`), but the Lambda code checked for `True` — tag values are case-sensitive strings | Updated the Lambda code to match the actual tag value exactly |

---

## Tech Stack

`AWS Lambda` · `API Gateway` · `DynamoDB` · `S3` · `SNS` · `EventBridge` · `EC2` · `IAM` · `Python 3.12` · `Pillow`

---

## Notes

- This project runs entirely on AWS Free Tier resources. No component requires paid infrastructure.
- Sensitive identifiers (API endpoint IDs, ARNs, account IDs) have intentionally been left out of this repository. Environment-specific configuration should be supplied via environment variables or a `.env` file (not committed) if you deploy this yourself.
