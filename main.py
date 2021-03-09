import json
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

settings = loadJSON("settings.json")
cfTemplate = loadJSON("{}.template".format(settings["stack"]))

if stackExists(settings["stack"]):
	print("Stack already exists: {}".format(settings["stack"]))
	raise SystemExit

print("doesn't exist cont")