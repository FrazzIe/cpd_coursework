# Format *.py files to be used in a cloud formation template

import os
import json
import python_minifier

scriptName = os.path.basename(__file__)
scriptDir = os.path.dirname(__file__)
outputDir = os.path.join(scriptDir, "output")
output = {}

def getFiles():
	py = []
	with os.scandir(scriptDir) as files:
		for file in files:
			if file.name.endswith(".py") and file.name != scriptName:
				py.append({ "path": file.path, "name": file.name })
	return py

def getFileName(name):
	obj = os.path.splitext(name)
	return obj[0] + ".json"

def getFileStruct():
	return { "Fn::Join": ["\n", []]	}

def populateFile(lines):
	obj = getFileStruct()
	for line in lines:
		obj["Fn::Join"][1].append(line.rstrip())

	return obj

for script in getFiles():
	with open(script["path"], "r") as file:
		minified = python_minifier.minify(file.read(), remove_literal_statements=True, rename_globals=True, preserve_globals=["handler"])
		data = populateFile(minified.splitlines())
		name = getFileName(script["name"])
		with open(os.path.join(outputDir, name), "w") as outfile:
			json.dump(data, outfile, indent = 4)