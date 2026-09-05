<a id="top"></a>

# 🧠 Design Concepts & Rationale

This file explains **why** each decision was made — the questions most likely to come up in an interview.

## 📋 Quick Navigation

| Topic | Section |
|---|---|
| 🌍 | [Frontend Delivery](#frontend) |
| 🛡️ | [Security Decisions](#security) |
| ⚡ | [Serverless Layer](#serverless) |
| 💰 | [Cost Decisions](#cost) |

---

<a id="frontend"></a>
## 🌍 Frontend Delivery

| Question | Answer |
|---|---|
| Why CloudFront in front of S3 instead of S3 static website hosting alone? | S3 static website hosting only serves HTTP and requires the bucket to be public. CloudFront adds HTTPS, caching, and — critically — lets the bucket stay completely private. |
| Why Origin Access Control (OAC) instead of a public bucket policy? | The reference design makes the bucket public with `Principal: *`, so anyone who finds the bucket URL can read it directly, bypassing CloudFront entirely. OAC scopes read access to the CloudFront distribution only — a direct S3 URL request returns `Access Denied`. Same content, smaller attack surface. |
| Why not enable Static Website Hosting on the bucket? | That feature is what forces the bucket to be public in the first place. With OAC, CloudFront reads the bucket through the regular S3 REST API, so website hosting isn't needed at all. |

---

<a id="security"></a>
## 🛡️ Security Decisions

| Question | Answer |
|---|---|
| Why restrict CORS to the CloudFront domain instead of `*`? | With `*`, any website on the internet could call this API from a user's browser and submit messages on their behalf, or scrape the `/stats` endpoint. Scoping it to the real frontend domain means only this site's pages can call the API. |
| Why does the IAM policy allow `sns:Publish` on `*` instead of the specific topic ARN? | SNS doesn't support resource-level permissions for `Publish` the way S3 and DynamoDB support scoping to a specific bucket or table ARN. This is a limitation of the service, not a design choice — it's worth knowing the difference when asked in an interview. |
| Why validate the message category against a fixed whitelist instead of accepting any string? | Free-text fields that flow into emails and logs are a common injection surface. A whitelist means the value is always one of a few known-safe strings. |
| Why does a failed SNS publish not fail the whole request? | The message is already safely written to DynamoDB by that point. If the notification email fails to send, the user's submission shouldn't be lost or shown as an error — the data is what matters most. |

---

<a id="serverless"></a>
## ⚡ Serverless Layer

| Question | Answer |
|---|---|
| Why API Gateway between the frontend and Lambda instead of Lambda Function URLs? | API Gateway gives a stable path structure (`/feedback`, `/stats`) with built-in CORS configuration and room to add rate limiting or an API key later, without changing the frontend code. |
| Why does `/stats` use `Scan` on DynamoDB instead of a counter stored separately? | At this scale (a personal contact form), a full table scan for a count is negligible in cost and complexity. A dedicated counter item would be the right call at higher volume, but would be premature optimization here. |
| Why is the error message returned to the client generic ("Something went wrong") instead of the actual exception? | Returning raw exception text can leak internal details — table names, stack traces, library versions — to anyone probing the API. The real error is logged to CloudWatch where it's still fully visible for debugging. |

---

<a id="cost"></a>
## 💰 Cost Decisions

| Question | Answer |
|---|---|
| Why is there no cleanup step for this project, unlike the ATS CV project? | This architecture has zero components billed by the hour — no EC2, no load balancer. S3, CloudFront, API Gateway, Lambda, DynamoDB, and SNS all have an always-free tier or effectively-zero idle cost, so there's nothing to shut down to avoid charges. |
| Why On-Demand capacity mode for DynamoDB instead of Provisioned? | On-Demand charges per request with no capacity planning needed — ideal for a low, unpredictable traffic pattern like a contact form, where guessing a provisioned throughput would either overpay or throttle real users. |

---

<div align="center">

**[⬆ Back to top](#top)**

</div>
