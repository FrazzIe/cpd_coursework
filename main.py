import os
import json
import time
import boto3
from botocore.exceptions import ClientError

cloudFormation = boto3.client("cloudformation")
s3 = boto3.client("s3")

def loadJSON(path):
	obj = None

	try:
		with open(path, "r") as file:
			data = file.read()
			obj = json.loads(data)
	except FileNotFoundError:
		print("File not found: {}".format(path))
		raise SystemExit

	return obj

#https://stackoverflow.com/questions/23019166/boto-what-is-the-best-way-to-check-if-a-cloudformation-stack-is-exists
def stackStatus(name):
	try:
		data = cloudFormation.describe_stacks(StackName = name)
	except ClientError:
		return "CLIENT_ERROR"

	return data["Stacks"][0]["StackStatus"]

def stackExists(name):
	status = stackStatus(name)
	switch = {
		"CLIENT_ERROR": False,
		"CREATE_FAILED": False,
		"ROLLBACK_FAILED": False,
		"DELETE_COMPLETE": False
	}

	return switch.get(status, True)

def getAudioFiles():
	audio = []
	with os.scandir("input") as files:
		for file in files:
			if file.name.endswith(".mp3"):
				audio.append(file.path)
	return audio

settings = loadJSON("settings.json")
cfTemplate = loadJSON("{}.template".format(settings["stack"]))

if stackExists(settings["stack"]):
	print("Stack already exists: {}".format(settings["stack"]))
	raise SystemExit

stackId = cloudFormation.create_stack(
	StackName = settings["stack"],
	TemplateBody = json.dumps(cfTemplate),
	TimeoutInMinutes = 15,
	OnFailure = "DO_NOTHING",
	Capabilities = [ "CAPABILITY_NAMED_IAM" ]
)

waitCount = 0
updateTime = 5
currentStatus = None

while True:
	if waitCount % updateTime == 0:
		currentStatus = stackStatus(settings["stack"])
		exists = stackExists(settings["stack"])

		if exists and currentStatus == "CREATE_COMPLETE":
			print("\nStack created!")
			break
		elif not exists:
			print("\nStack creation failed.. terminating")
			raise SystemExit
	time.sleep(1)
	waitCount = waitCount + 1
	print(">> [ {} ] Status: {}, Seconds elapsed: {}".format("/" if waitCount % 2 else "\\", currentStatus, waitCount), end = "\r")

audioFiles = getAudioFiles()

for file in audioFiles:
	s3.upload_file(file, "{}-bucket".format(settings["stack"]), "audio/{}".format(os.path.basename(file)))
	waitCount = 0
	while True:
		print(">> [ {} ] File: {}, Seconds elapsed: {}/30".format("/" if waitCount % 2 else "\\", file, waitCount), end = "\r")
		if waitCount == 30:
			print("\nFinished: {}".format(file))
			break
		time.sleep(1)
		waitCount = waitCount + 1
