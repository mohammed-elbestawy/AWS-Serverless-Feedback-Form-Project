<div align="center">

# 🛠️ Build Log — Serverless Feedback Form

A record of every resource created, plus the security improvement made over the common reference design.

![AWS](https://img.shields.io/badge/AWS-Free%20Tier-FF9900?style=flat-square&logo=amazonaws&logoColor=white)
![Python](https://img.shields.io/badge/Python-3.12-3776AB?style=flat-square&logo=python&logoColor=white)
![Region](https://img.shields.io/badge/Region-us--east--1-232F3E?style=flat-square)

</div>

---

### Contents
- 🗃️ [DynamoDB Table](#dynamodb)
- 📣 [SNS Topic & Subscription](#sns)
- 🔐 [IAM Role & Policy](#iam)
- ⚡ [Lambda Function](#lambda)
- 🔌 [API Gateway](#api-gateway)
- 🛠️ [Frontend Config](#frontend-config)
- 🪣 [S3 Bucket (Private)](#s3-bucket)
- 🌍 [CloudFront + OAC](#cloudfront)
- 🔒 [CORS Restriction](#cors)
- ✅ [End-to-End Test](#e2e-test)

---

<a id="dynamodb"></a>
## 🗃️ DynamoDB Table

The database that stores every submitted message.

| Setting | Value |
|:---|:---|
| Name | `feedback-messages` |
| Partition key | `message_id` (String) |
| Capacity mode | On-demand |

---

<a id="sns"></a>
## 📣 SNS Topic & Subscription

Sends an instant email to the site owner whenever a new message comes in.

| Setting | Value |
|:---|:---|
| Topic name | `feedback-notifications` |
| Type | Standard |
| Subscription protocol | Email |
| Subscription status | Confirmed |

![SNS subscription confirmed](screenshots/02-sns-subscription.png)

---

<a id="iam"></a>
## 🔐 IAM Role & Policy

The exact permissions the Lambda function needs — nothing more than what it actually uses.

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "logs:CreateLogGroup",
        "logs:CreateLogStream",
        "logs:PutLogEvents"
      ],
      "Resource": "*"
    },
    {
      "Effect": "Allow",
      "Action": [
        "dynamodb:PutItem",
        "dynamodb:Scan"
      ],
      "Resource": "arn:aws:dynamodb:*:*:table/feedback-messages"
    },
    {
      "Effect": "Allow",
      "Action": "sns:Publish",
      "Resource": "*"
    }
  ]
}
```

> `sns:Publish` is scoped to `*` instead of a specific topic ARN — not a looser design choice. SNS doesn't support resource-level restriction on `Publish` the way S3 and DynamoDB support restricting actions to a specific bucket or table ARN.

![IAM role](screenshots/03-iam-role.png)

---

<a id="lambda"></a>
## ⚡ Lambda Function

Validates the incoming message, saves it to DynamoDB, and publishes a notification to SNS.

| Setting | Value |
|:---|:---|
| Name | `feedback-handler` |
| Runtime | Python 3.12 |
| Role | `feedback-lambda-role` |
| Env vars | `TABLE_NAME`, `TOPIC_ARN`, `ALLOWED_ORIGIN` |
| Timeout | 15 sec |

Full code: [`code/lambda/lambda_function.py`](code/lambda/lambda_function.py)

**Hardening over the common reference implementation:**
- Errors are logged to CloudWatch, never returned to the client
- Category field is validated against a fixed whitelist
- Message length is capped to prevent oversized payloads
- A failed SNS publish doesn't fail the whole request — the message is already saved

---

<a id="api-gateway"></a>
## 🔌 API Gateway

The link between the frontend form and the Lambda function.

| Setting | Value |
|:---|:---|
| API name | `feedback-api` (REST, Regional) |
| Resources | `POST /feedback`, `GET /stats` |
| Integration | Lambda proxy + CORS enabled |
| Stage | `prod` |

![API Gateway invoke URL](screenshots/05-apigateway-invoke.png)

---

<a id="frontend-config"></a>
## 🛠️ Frontend Config

`script.js` updated locally with the real API Gateway Invoke URL, before uploading the frontend files to S3.

---

<a id="s3-bucket"></a>
## 🪣 S3 Bucket (Private)

Where the static frontend files live — kept fully private, unlike the common reference design.

| Setting | Value |
|:---|:---|
| Name | `feedback-frontend-<account-id>` |
| Region | us-east-1 |
| Block all public access | On |
| Static website hosting | Not enabled |

![S3 bucket — public access blocked](screenshots/07-s3-bucket.png)

---

<a id="cloudfront"></a>
## 🌍 CloudFront + Origin Access Control

The CDN that delivers the site over HTTPS, and the only thing allowed to read from the S3 bucket.

| Setting | Value |
|:---|:---|
| Origin | S3 bucket (private, via OAC) |
| Origin access | Origin Access Control (OAC) |
| Viewer protocol policy | Redirect HTTP to HTTPS |
| Default root object | `index.html` |

> **Issue avoided:** the common reference design makes the bucket public and relies on a wildcard bucket policy (`Principal: *`). This project uses OAC instead — the bucket policy only trusts the CloudFront distribution itself, so a direct S3 URL request returns `Access Denied`.

![CloudFront distribution enabled](screenshots/08-cloudfront-distribution.png)
![S3 bucket policy scoped to CloudFront](screenshots/08-s3-bucket-policy.png)

---

<a id="cors"></a>
## 🔒 CORS Restriction

The Lambda's `ALLOWED_ORIGIN` environment variable updated from `*` to the real CloudFront domain, so only this site's frontend can call the API.

![Lambda allowed origin updated](screenshots/09-lambda-allowed-origin.png)

---

<a id="e2e-test"></a>
## ✅ End-to-End Test

Confirms the whole chain — form, backend, storage, and notification — actually works together.

| Check | Result |
|:---|:---:|
| Form submission | ✅ Success message shown |
| Email notification | ✅ Received |
| DynamoDB record | ✅ Saved |
| Live counter | ✅ Updated |

![Form submitted successfully](screenshots/10-fulltest-form.png)
![Email notification received](screenshots/10-fulltest-email.png)
![Message saved in DynamoDB](screenshots/10-fulltest-dynamodb.png)
