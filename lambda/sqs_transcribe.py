# Snippet from CloudFormation template
# Called after S3 Bucket sends a notification to SQS

import boto3
import json
import time
from botocore.exceptions import ClientError

transcriptDir = "transcriptions/"
ts = boto3.client("transcribe")

def getEventData(event):
	try:
		data = json.loads(event["Records"][0]["body"])
		if "Event" in data:
			if data["Event"] == "s3:TestEvent":
				return True, "Ignore test event"
		return False, data["Records"][0]
	except Exception:
		return True, "Something went wrong when fetching event data!"

def getBucketUri(bucket, file):
	return "s3://{}/{}".format(bucket, file.replace("%5C", "/"))

def getTranscriptionStatus(job):
	try:
		data = ts.get_transcription_job(TranscriptionJobName = job)
	except ClientError as error:
		print(error)
		return "CLIENT_ERROR"
	return data["TranscriptionJob"]["TranscriptionJobStatus"]

def startTranscriptionJob(bucket, file, job):
	uri = getBucketUri(bucket, file)
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
		status = getTranscriptionStatus(job)
		if status in states:
			break
		time.sleep(5)
	return status

def handler(event, context):
	if not event:
		raise SystemExit

	err, data = getEventData(event)

	if err:
		print("Error occurred: {}".format(data))
		return {
			"statusCode": 500,
			"body": json.dumps("Error occurred: {}".format(data))
		}

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
		msg = "Transcription {} is incomplete with status: {}".format(job, status)
		print(msg)
		return {
			"statusCode": 500,
			"body": json.dumps(msg)
		}
		raise SystemExit

	return {
		"statusCode": 200,
		"body": json.dumps("Transcription {} created".format(job))
	}