import splunk.Intersplunk 
from multiprocessing import Process
from signal import signal, SIGTERM
from time import sleep
import atexit
import requests
import os
import urllib
import urllib2
import time
import splunk.clilib.cli_common
import json
import sys
import splunk.rest
import datetime
import re
import logging
import logging.handlers
import sys
import json
import splunklib.client as client


def setup_logger(level):
    logger = logging.getLogger('my_search_command')
    logger.propagate = False  # Prevent the log messages from being duplicated in the python.log file
    logger.setLevel(level)

    file_handler = logging.handlers.RotatingFileHandler(
        os.environ['SPLUNK_HOME'] + '/var/log/splunk/googledrive.log', maxBytes=25000000, backupCount=5)
    formatter = logging.Formatter('%(asctime)s %(levelname)s %(message)s')
    file_handler.setFormatter(formatter)

    logger.addHandler(file_handler)

    return logger


def RefreshToken(refresh_token, user, sessionKey):
    try:
        #Refresh Token 
        req = urllib2.Request('https://eop2idyodk.execute-api.us-west-2.amazonaws.com/prod/refreshgoogledrivekey?refresh_token='+refresh_token)
        response = urllib2.urlopen(req)
        codes = response.read()
        DeleteToken(sessionKey, user)
	codes=codes.replace("}", ", \"RefreshToken\": \""+refresh_token+"\"}")
        CreateToken(sessionKey, codes, user, user)
        return codes
    except Exception as e:
        logger.info(str(e))

def ListTokens(sessionKey):
    splunkService = client.connect(token=sessionKey,app='google_drive')
    for storage_password in splunkService.storage_passwords:
        logger.info(storage_password.name)

def CreateToken(sessionKey, password, user, realm):
    splunkService = client.connect(token=sessionKey,app='google_drive')
    splunkService.storage_passwords.create(password, user, realm)

def DeleteToken(sessionKey, user):
    splunkService = client.connect(token=sessionKey,app='google_drive')
    try:
        splunkService.storage_passwords.delete(user,user)
    except Exception as e:
        logger.info(str(e))

def GetTokens(sesssionKey):
    splunkService = client.connect(token=sessionKey,app='google_drive')   
    return splunkService.storage_passwords

def GetChanges(api_key, page_token, results, logger):
	try:
		r=requests.get('https://www.googleapis.com/drive/v3/changes?pageSize=1000&pageToken'+page_token+'&access_token='+api_key)

		r = json.loads(r.text)

		for change in r["changes"]:
			result={}
		if "file" in change:
			if "name" in change["file"]:
				result["name"] = change["file"]["name"]
			else:
				result["name"] = "(None)"
		
			if "id" in change["file"]:
				result["id"] = change["file"]["id"]
			else:
				result["id"] = "(None)"
		
			if "mimeType" in change["file"]:
				result["mimeType"] = change["file"]["mimeType"]
			else:
				result["mimeType"] = "(None)"
			results.append(result)
	
		if 'nextPageToken' in r:
			page_token=r["nextPageToken"]
			GetChanges(api_key, page_token, results, logger)	
		else:
			return results
	except Exception as e:
		logger.info(str(e))
		return results

now = datetime.datetime.now()

logger = setup_logger(logging.INFO)


results,dummy,settings = splunk.Intersplunk.getOrganizedResults()
sessionKey = settings.get("sessionKey")

for result in results:
	try:
		#Get Google Drive Name and API Creds from Password Store
		username=result['username']
		password=result['clear_password']

		#Parse JSON API Creds
		tokens = json.loads(password)
	
		#Get Refresh Token
		refreshtoken = tokens["RefreshToken"]

		#Get the API Key and Refresh Token
		new_creds = RefreshToken(refreshtoken, username, sessionKey)
		
		#Get New API Key	
		new_creds = json.loads(new_creds)
		api_key=new_creds["APIKey"]

        	
	except Exception as e:
		logger.info(str(e))
		
q = requests.get('https://www.googleapis.com/drive/v3/changes/startPageToken?access_token='+api_key)
q = json.loads(q.text)

startPageToken = q["startPageToken"]
startPageToken="757166"
r=requests.get('https://www.googleapis.com/drive/v3/changes?pageSize=1000&pageToken='+startPageToken+'&access_token='+api_key)

r = json.loads(r.text)

results = []
for change in r["changes"]:
	result={}
	if "file" in change:
		if "name" in change["file"]:
			result["name"] = change["file"]["name"]
		else:
			result["name"] = "(None)"
		
		if "id" in change["file"]:
			result["id"] = change["file"]["id"]
		else:
			result["id"] = "(None)"
		
		if "mimeType" in change["file"]:
			result["mimeType"] = change["file"]["mimeType"]
		else:
			result["mimeType"] = "(None)"
		results.append(result)

#if 'nextPageToken' in r:
#	page_token=r["nextPageToken"]
#	results = GetChanges(api_key, page_token, results, logger)

splunk.Intersplunk.outputResults(results)
