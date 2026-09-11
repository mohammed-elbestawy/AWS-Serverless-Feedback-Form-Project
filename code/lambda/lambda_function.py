import json
import os
import re
import uuid
import boto3
from datetime import datetime
from decimal import Decimal

dynamodb = boto3.resource("dynamodb")
sns = boto3.client("sns")

TABLE_NAME = os.environ["TABLE_NAME"]
TOPIC_ARN  = os.environ["TOPIC_ARN"]
table = dynamodb.Table(TABLE_NAME)

EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


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
        return _response(500, {"error": str(e)})


def handle_feedback(event):
    body = event.get("body", "{}")
    if isinstance(body, str):
        body = json.loads(body)

    required_fields = ["name", "email", "subject", "category", "message"]
    missing = [f for f in required_fields if not body.get(f)]
    if missing:
        return _response(400, {"error": "Missing fields: " + ", ".join(missing)})

    if not EMAIL_RE.match(body["email"]):
        return _response(400, {"error": "Invalid email format"})

    message_id = str(uuid.uuid4())

    table.put_item(Item={
        "message_id": message_id,
        "name":       body["name"],
        "email":      body["email"],
        "subject":    body["subject"],
        "category":   body["category"],
        "message":    body["message"],
        "created_at": datetime.utcnow().isoformat(),
    })

    notification_text = (
        f"New feedback received\n\n"
        f"From: {body['name']} ({body['email']})\n"
        f"Category: {body['category']}\n"
        f"Subject: {body['subject']}\n\n"
        f"Message:\n{body['message']}"
    )

    sns.publish(
        TopicArn=TOPIC_ARN,
        Subject=f"New Feedback: {body['subject']}",
        Message=notification_text,
    )

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
            "Access-Control-Allow-Origin": "*"
        },
        "body": json.dumps(body, ensure_ascii=False, default=str),
    }
