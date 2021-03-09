import os
import json
import time
import boto3
from botocore.exceptions import ClientError

cloudFormation = boto3.client("cloudformation")

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
	TemplateBody = cfTemplate,
	DisableRollback = False,
	RollbackConfiguration = {
		"RollbackTriggers": [
			{
				"Arn": "string",
				"Type": "string"
			}
		],
		MonitoringTimeInMinutes: 15
	},
	TimeoutInMinutes = 15
	OnFailure = "DELETE"
)

waitCount = 0
updateTime = 5
currentStatus = None

while True:
	if waitCount % updateTime == 0:
		currentStatus = stackStatus(settings["stack"])
		exists = stackExists(settings["stack"])

		if exists and status == "CREATE_COMPLETE":
			print("\nStack created!")
			break
		elif not exists:
			print("\nStack creation failed.. terminating")
			raise SystemExit
	time.sleep(1)
	waitCount = waitCount + 1
	print(">> [ {} ] Status: {}, Seconds elapsed: {}".format("/" if waitCount % 2 else "\\", currentStatus, waitCount), end = "\r")