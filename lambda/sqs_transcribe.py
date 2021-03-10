# Snippet from CloudFormation template
# Called after S3 Bucket sends a notification to SQS

import boto3
import json
from botocore.exceptions import ClientError

def getEventData(event):
	try:
		data = json.loads(event["Records"][0]["body"])
		return data["Records"][0]
	except Exception:
		print("Something went wrong when fetching event data!")
		raise SystemExit

def getBucketUri(bucket, file):
	return "s3://{}/{}".format(bucket, file.replace("%5C", "/"))

def getTranscriptionStatus(ts, job):
	try:
		data = ts.get_transcription_job(TranscriptionJobName = job)
	except ClientError:
		return "CLIENT_ERROR"
	return data["TranscriptionJob"]["TranscroptionJobStatus"]
def handler(event, context):
	if not event:
		raise SystemExit

	data = getEventData(event)
	bucket = data["s3"]["bucket"]["name"]
	file = data["s3"]["object"]["key"]
	job = context.aws_request_id

	if not bucket or not file:
		print("Couldn't find bucket/file")
		raise SystemExit
	elif not job:
		print("Couldn't find job id")
		raise SystemExit

	uri = getBucketUri(bucket, file)
	ts = boto3.client("transcribe")
	ts.start_transcription_job(
		TranscriptionJobName = job,
		Media = {
			"MediaFileUri": uri
		},
		MediaFormat = "mp3",
		LanguageCode = "en-GB",
		OutputBucketName = bucket,
		OutputKey = "transcriptions/"
	)

	return {
		"statusCode": 200,
		"body": json.dumps("Transcription {} created".format(job))
	}