# Snippet from CloudFormation template
# Called after S3 Bucket sends a notification to SQS

import boto3
import json

def getEventData(event):
	try:
		data = json.loads(event["Records"][0]["body"])
		return data["Records"][0]
	except Exception:
		print("Something went wrong when fetching event data!")
		raise SystemExit
def handler(event, context):
	if not event:
		raise SystemExit

	data = getEventData(event)
