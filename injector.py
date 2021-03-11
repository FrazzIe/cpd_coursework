# Inject and minify *.py files into cloud formation lambda functions

import os
import json
import python_minifier

# Gets a file name without the extension
def getFileName(name):
	obj = os.path.splitext(name)
	return obj[0]

# Gets a list of a *.py files in the lambda function directory
def getFiles(srcDir):
	py = []

	if not os.path.isdir(srcDir):
		print("Error: lambda function directory doesn't exist!")
		return py

	with os.scandir(srcDir) as files:
		for file in files:
			if file.name.endswith(".py"):
				py.append({ "path": file.path, "name": getFileName(file.name) })
	return py

# Gets the lambda function ZipFile structure
def getFileStruct():
	return { "Fn::Join": ["\n", []]	}

# Populates the lambda function ZipFile
def populateFile(lines):
	obj = getFileStruct()
	for line in lines:
		obj["Fn::Join"][1].append(line.rstrip())

	return obj


# Injects minified lambda function code into a CloudFormation template
def injectLambdaCode(path, template):
	lambdaFiles = getFiles(path)

	if not "Resources" in template:
		print("Error: Invalid CloudFormation template")
		return template

	for script in lambdaFiles:
		if script["name"] in template["Resources"]:
	return template