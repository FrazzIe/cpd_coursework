import os
import json
import boto3
from time import sleep
from botocore.exceptions import ClientError
from injector import injectLambdaCode

# Load JSON files
def loadJSON(path):
	try:
		with open(path, "r") as file:
			data = file.read()
			return json.loads(data)
	except FileNotFoundError:
		print("File not found: {}".format(path))
	except Exception:
		print("Something went wrong when loading: {}".format(path))

	raise SystemExit()

# https://stackoverflow.com/questions/23019166/boto-what-is-the-best-way-to-check-if-a-cloudformation-stack-is-exists
# Get status of a named stack
def getStackStatus(cf, name):
	try:
		data = cf.describe_stacks(StackName = name)
	except ClientError:
		return "CLIENT_ERROR"

	return data["Stacks"][0]["StackStatus"]

# Check if a named stack exists
def doesStackExist(cf, name):
	status = getStackStatus(cf, name)
	switch = {
		"CLIENT_ERROR": False,
		"CREATE_FAILED": False,
		"ROLLBACK_FAILED": False,
		"DELETE_COMPLETE": False
	}

	return switch.get(status, True)

# Create a CloudFormation stack with a template
def createStack(cf, setting, template):
	waitCount = 0
	updateTime = 5
	currentStatus = None

	cf.create_stack(
		StackName = setting["stackName"],
		TemplateBody = json.dumps(template),
		Parameters = [
			{
				"ParameterKey": "SentimentPhoneNumber",
				"ParameterValue": setting["phoneNumber"],
				"UsePreviousValue": False
			}
		],
		TimeoutInMinutes = 20,
		OnFailure = "DELETE",
		Capabilities = [ "CAPABILITY_NAMED_IAM" ]
	)

	while True:
		if waitCount % updateTime == 0:
			currentStatus = getStackStatus(cf, setting["stackName"])
			exists = getStackStatus(cf, setting["stackName"])

			if exists and currentStatus == "CREATE_COMPLETE":
				print("\nStack created!")
				return True
			elif not exists:
				print("\nStack creation failed.. terminating")
				return False
		sleep(1)
		waitCount = waitCount + 1
		print(">> [ {} ] Status: {}, Seconds elapsed: {}".format("/" if waitCount % 2 else "\\", currentStatus, waitCount), end = "\r")

# Gets a list of a *.mp3 files to be uploaded
def getAudioFiles(srcDir):
	audio = []

	if not os.path.isdir(srcDir):
		print("Error: audio directory doesn't exist!")
		return audio

	with os.scandir(srcDir) as files:
		for file in files:
			if file.name.endswith(".mp3"):
				audio.append(file.path)

	return audio

# Upload a file to a specified bucket directory
def uploadFile(s3, bucket, filePath, uploadPath):
	fileName = os.path.basename(filePath)

	try:
		s3.upload_file(filePath, bucket, uploadPath.format(fileName))
		return True
	except Exception:
		print("Error: {} failed to upload", fileName)

	return False

# Load config files
# Inject python into CloudFormation Lambda Functions
# Create a CloudFormation stack
# Upload audio files to a bucket
def main():
	settings = loadJSON("settings.json")
	template = loadJSON("{}.template".format(settings["stackName"]))

	cf = boto3.client("cloudformation")
	s3 = boto3.client("s3")

	if doesStackExist(cf, settings["stackName"]):
		print("Stack already exists: {}".format(settings["stackName"]))
		return

	template = injectLambdaCode(settings["lambdaLocation"], template)

	if not createStack(cf, settings, template):
		return

	audioFiles = getAudioFiles(settings["audioLocation"])

	for file in audioFiles:
		waitCount = 0
		updateTime = 5
		success = uploadFile(s3, "{}-bucket".format(settings["stackName"]), file, "audio/{}")
		if success:
			while True:
				print(">> [ {} ] File: {}, Seconds elapsed: {}/{}".format("/" if waitCount % 2 else "\\", file, waitCount, settings["secondsBetweenUploads"]), end = "\r")
				if waitCount == settings["secondsBetweenUploads"]:
					print("\nFinished: {}".format(file))
					break
				sleep(1)
				waitCount = waitCount + 1

if __name__ == "__main__":
	main()