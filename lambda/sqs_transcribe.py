# Snippet from CloudFormation template
# Called after S3 Bucket sends a notification to SQS

import boto3
import json
import time
from botocore.exceptions import ClientError

transcriptDir = "transcriptions/"

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

def startTranscriptionJob(bucket, file, job):
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
		OutputKey = transcriptDir
	)

	states = ["COMPLETED", "FAILED", "CLIENT_ERROR"]
	while True:
		status = getTranscriptionStatus(ts, job)
		if status in states:
			break
		time.sleep(5)
	return status

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

	status = startTranscriptionJob(bucket, file, job)

	if status != "COMPLETED":
		print("Transcription {} is incomplete with status: {}".format(job, status))
		raise SystemExit

	return {
		"statusCode": 200,
		"body": json.dumps("Transcription {} created".format(job))
	}