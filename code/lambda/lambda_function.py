"""
Serverless Feedback & Contact Form — Lambda Function
=====================================================
Handles two endpoints:
  POST /feedback  →  save message + send email via SNS
  GET  /stats     →  return total message count

Environment Variables required:
  TABLE_NAME  = feedback-messages
  TOPIC_ARN   = arn:aws:sns:us-east-1:XXXX:feedback-notifications
"""

import json
import os
import uuid
import boto3
from datetime import datetime

# ── AWS clients ────────────────────────────────────────────
dynamodb  = boto3.resource("dynamodb")
sns       = boto3.client("sns")

TABLE_NAME = os.environ["TABLE_NAME"]   # feedback-messages
TOPIC_ARN  = os.environ["TOPIC_ARN"]   # SNS topic ARN

table = dynamodb.Table(TABLE_NAME)


# ══════════════════════════════════════════════════════════
#  MAIN HANDLER
# ══════════════════════════════════════════════════════════
def lambda_handler(event, context):
    method = event.get("httpMethod", "")
    path   = event.get("path", "")

    # ── Route: POST /feedback ──────────────────────────────
    if method == "POST" and path == "/feedback":
        return handle_submit(event)

    # ── Route: GET /stats ──────────────────────────────────
    if method == "GET" and path == "/stats":
        return handle_stats()

    return _response(404, {"error": "Endpoint not found"})


# ══════════════════════════════════════════════════════════
#  POST /feedback  —  Save message & send email
# ══════════════════════════════════════════════════════════
def handle_submit(event):
    try:
        # Parse body
        raw  = event.get("body", "{}")
        body = json.loads(raw) if isinstance(raw, str) else raw

        # Validate required fields
        required = ["name", "email", "subject", "message"]
        missing  = [f for f in required if not body.get(f, "").strip()]
        if missing:
            return _response(400, {
                "error": f"Missing required fields: {', '.join(missing)}"
            })

        # Build record
        message_id = str(uuid.uuid4())
        record = {
            "message_id": message_id,
            "name":       body["name"].strip(),
            "email":      body["email"].strip(),
            "subject":    body["subject"].strip(),
            "category":   body.get("category", "general"),
            "message":    body["message"].strip(),
            "status":     "new",
            "created_at": datetime.utcnow().isoformat(),
        }

        # Save to DynamoDB
        table.put_item(Item=record)

        # Send email notification via SNS
        _send_notification(record)

        return _response(200, {
            "message_id": message_id,
            "message":    "Your message has been sent successfully!",
        })

    except Exception as e:
        print(f"Error in handle_submit: {e}")
        return _response(500, {"error": "Internal server error. Please try again."})


# ══════════════════════════════════════════════════════════
#  GET /stats  —  Return total message count
# ══════════════════════════════════════════════════════════
def handle_stats():
    try:
        result = table.scan(Select="COUNT")
        total  = result.get("Count", 0)
        return _response(200, {"total_messages": total})
    except Exception as e:
        print(f"Error in handle_stats: {e}")
        return _response(500, {"error": str(e)})


# ══════════════════════════════════════════════════════════
#  SNS Email Notification
# ══════════════════════════════════════════════════════════
def _send_notification(record):
    """Sends an email to the site owner via SNS."""
    subject = f"[FeedbackHub] New message: {record['subject']}"

    body = f"""
You received a new message on FeedbackHub!

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  From     : {record['name']}
  Email    : {record['email']}
  Category : {record['category']}
  Subject  : {record['subject']}
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Message:
{record['message']}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Message ID : {record['message_id']}
Received   : {record['created_at']} UTC
    """.strip()

    sns.publish(
        TopicArn=TOPIC_ARN,
        Subject=subject,
        Message=body,
    )


# ══════════════════════════════════════════════════════════
#  Helper: standard HTTP response
# ══════════════════════════════════════════════════════════
def _response(status_code, body_dict):
    return {
        "statusCode": status_code,
        "headers": {
            "Content-Type":                "application/json",
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Methods": "GET,POST,OPTIONS",
            "Access-Control-Allow-Headers": "Content-Type",
        },
        "body": json.dumps(body_dict, ensure_ascii=False),
    }
