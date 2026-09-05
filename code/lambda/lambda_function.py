import json
import os
import re
import uuid
import boto3
from datetime import datetime

dynamodb = boto3.resource("dynamodb")
sns = boto3.client("sns")

TABLE_NAME     = os.environ["TABLE_NAME"]
TOPIC_ARN      = os.environ["TOPIC_ARN"]
ALLOWED_ORIGIN = os.environ.get("ALLOWED_ORIGIN", "*")
table = dynamodb.Table(TABLE_NAME)

EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
ALLOWED_CATEGORIES = {"general", "support", "bug", "feedback"}
MAX_MESSAGE_LENGTH = 2000
MAX_SHORT_FIELD_LENGTH = 200


def lambda_handler(event, context):
    try:
        method = event.get("httpMethod", "")
        path   = event.get("path", "")

        if method == "POST" and path == "/feedback":
            return handle_feedback(event)
        elif method == "GET" and path == "/stats":
            return handle_stats()
        else:
            return _response(404, {"error": "Not found"})

    except Exception as e:
        print(f"ERROR: {e}")
        return _response(500, {"error": "Something went wrong. Please try again later."})


def handle_feedback(event):
    body = event.get("body", "{}")
    if isinstance(body, str):
        body = json.loads(body)

    required_fields = ["name", "email", "subject", "category", "message"]
    missing = [f for f in required_fields if not str(body.get(f, "")).strip()]
    if missing:
        return _response(400, {"error": "Missing fields: " + ", ".join(missing)})

    name     = body["name"].strip()[:MAX_SHORT_FIELD_LENGTH]
    email    = body["email"].strip()[:MAX_SHORT_FIELD_LENGTH]
    subject  = body["subject"].strip()[:MAX_SHORT_FIELD_LENGTH]
    category = body["category"].strip().lower()
    message  = body["message"].strip()[:MAX_MESSAGE_LENGTH]

    if not EMAIL_RE.match(email):
        return _response(400, {"error": "Invalid email format"})

    if category not in ALLOWED_CATEGORIES:
        return _response(400, {"error": "Invalid category"})

    message_id = str(uuid.uuid4())

    table.put_item(Item={
        "message_id": message_id,
        "name":       name,
        "email":      email,
        "subject":    subject,
        "category":   category,
        "message":    message,
        "created_at": datetime.utcnow().isoformat(),
    })

    notification_text = (
        f"New feedback received\n\n"
        f"From: {name} ({email})\n"
        f"Category: {category}\n"
        f"Subject: {subject}\n\n"
        f"Message:\n{message}"
    )

    try:
        sns.publish(
            TopicArn=TOPIC_ARN,
            Subject=f"New Feedback: {subject}"[:100],
            Message=notification_text,
        )
    except Exception as e:
        print(f"SNS publish failed: {e}")

    return _response(200, {
        "message_id": message_id,
        "message": "Your message has been sent successfully!",
    })


def handle_stats():
    result = table.scan(Select="COUNT")
    return _response(200, {
        "total_messages": result.get("Count", 0),
    })


def _response(code, body):
    return {
        "statusCode": code,
        "headers": {
            "Content-Type": "application/json",
            "Access-Control-Allow-Origin": ALLOWED_ORIGIN
        },
        "body": json.dumps(body, ensure_ascii=False, default=str),
    }
