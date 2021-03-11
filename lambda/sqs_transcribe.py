# Snippet from CloudFormation template
# Called after S3 Bucket sends a notification to SQS

import os
import boto3
import json
import time
import re
from botocore.exceptions import ClientError

transcriptDir = "transcriptions/"
ts = boto3.client("transcribe")
s3 = boto3.client("s3")
comp = boto3.client("comprehend")
db = boto3.client("dynamodb")
sns = boto3.client("sns")

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

def deleteTranscriptionJob(job):
	try:
		ts.delete_transcription_job(TranscriptionJobName = job)
		return False, ""
	except ClientError as error:
		print(error)
		return True, error
	except Exception as error:
		print(error)
		return True, error

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

def deleteTranscript(job):
	filePath = "/tmp/{}.json".format(job)

	try:
		os.remove(filePath)
		return False, ""
	except Exception as error:
		print(error)
		return True, error

def getTranscriptText(transcript):
	try:
		return False, transcript["results"]["transcripts"][0]["transcript"]
	except Exception:
		return True, "Couldn't get transcript text!"

def getSentimentAnalysis(transcript):
	err, text = getTranscriptText(transcript)

	if err:
		return True, text

	try:
		sentiment = comp.detect_sentiment(
			Text = text,
			LanguageCode = "en"
		)
		return False, sentiment
	except ClientError as error:
		print(error)
		return True, error

def addSentimentToDynamo(fileName, sentiment):
	try:
		db.put_item(
			TableName = "SentimentTable",
			Item = {
				"FileName": {
					"S": fileName
				},
				"Sentiment": {
					"S": sentiment["Sentiment"]
				},
				"Positive": {
					"N": str(sentiment["SentimentScore"]["Positive"])
				},
				"Negative": {
					"N": str(sentiment["SentimentScore"]["Negative"])
				},
				"Mixed": {
					"N": str(sentiment["SentimentScore"]["Mixed"])
				}
			}
		)
		return False, ""
	except ClientError as error:
		print(error)
		return True, error

# https://stackoverflow.com/questions/6478875/regular-expression-matching-e-164-formatted-phone-numbers
def isPhoneValid(phoneNumber):
	pattern = re.compile("^\+[1-9]\d{1,14}$")
	return pattern.match(phoneNumber) is not None

def sendMessage(subject, message):
	phoneNumber = os.environ["PhoneNumber"]

	if isPhoneValid(phoneNumber):
		sns.publish(
			PhoneNumber = phoneNumber,
			Message = message,
			Subject = subject
		)

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

	err, errMsg = deleteTranscriptionJob(job)

	if err:
		msg = "Error occurred: {}".format(errMsg)
		print(msg)
		return {
			"statusCode": 500,
			"body": json.dumps(msg)
		}

	err, errMsg = deleteTranscript(job)

	if err:
		msg = "Error occurred: {}".format(errMsg)
		print(msg)
		return {
			"statusCode": 500,
			"body": json.dumps(msg)
		}

	err, sentiment = getSentimentAnalysis(transcript)

	if err:
		msg = "Error occurred: {}".format(sentiment)
		print(msg)
		return {
			"statusCode": 500,
			"body": json.dumps(msg)
		}

	err, errMsg = addSentimentToDynamo(file, sentiment)

	if err:
		msg = "Error occurred: {}".format(errMsg)
		print(msg)
		return {
			"statusCode": 500,
			"body": json.dumps(msg)
		}

	if sentiment["Sentiment"].lower() == "negative":
		sendMessage("Alert: Sentiment Analysis", """Negative result found!
		File: {}
		Data: {}
		Transcript: {}
		""".format(file, sentiment["SentimentScore"]["Negative"], transcript["results"]["transcripts"][0]["transcript"]))

	return {
		"statusCode": 200,
		"body": json.dumps("Transcription {} created".format(job))
	}