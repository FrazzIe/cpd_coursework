# Snippet from CloudFormation template
# Called after S3 Bucket sends a notification to SQS

import boto3
import json
import time
from botocore.exceptions import ClientError

transcriptDir = "transcriptions/"
ts = boto3.client("transcribe")
s3 = boto3.client("s3")

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

def fetchTranscript(bucket, job):
	bucketPath = "{}{}.json".format(transcriptDir, job)
	filePath = "/tmp/{}.json".format(job)

	try:
		s3.download_file(bucket, bucketPath, filePath)
		try:
			with open(filePath, "r") as file:
				data = file.read()
				return False, json.loads(data)
		except FileNotFoundError:
			return True, "Transcript file not found"
	except ClientError as error:
		print(error)
		return True, "An error occured when fetching the transcript"

def handler(event, context):
	if not event:
		return {
			"statusCode": 500,
			"body": json.dumps("Event undefined")
		}

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
		return {
			"statusCode": 500,
			"body": json.dumps("Couldn't find bucket/file")
		}
	elif not job:
		return {
			"statusCode": 500,
			"body": json.dumps("Couldn't find job id")
		}

	status = startTranscriptionJob(bucket, file, job)

	if status != "COMPLETED":
		msg = "Transcription {} is incomplete with status: {}".format(job, status)
		print(msg)
		return {
			"statusCode": 500,
			"body": json.dumps(msg)
		}

	err, transcript = fetchTranscript(bucket, job)

	if err:
		msg = "Error occurred: {}".format(transcript)
		print(msg)
		return {
			"statusCode": 500,
			"body": json.dumps(msg)
		}

	print(transcript)


	return {
		"statusCode": 200,
		"body": json.dumps("Transcription {} created".format(job))
	}