# Snippet from CloudFormation template
# Called after S3 Bucket sends a notification to SQS

import boto3

def handler(event, content):
	if event:
		try:
			obj = event["Records"][0]
			bucket = obj["s3"]["bucket"]["name"]
			file = obj["s3"]["object"]["key"]
			print(bucket, file, sep = ", ")
		except Exception:
			raise SystemExit