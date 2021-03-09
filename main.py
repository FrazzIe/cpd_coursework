import json
import boto3

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
settings = loadJSON("settings.json")
cfTemplate = loadJSON("template.json")
