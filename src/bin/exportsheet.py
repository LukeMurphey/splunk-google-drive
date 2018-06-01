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
import csv
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

def GetFiles(api_key, page_token, results, logger):
	try:
		r=requests.get('https://www.googleapis.com/drive/v3/files?pageToken'+page_token+'&access_token='+api_key+'&q=name+contains+%27.spreadsheet%27+or+name+contains+%27csv%27+or+name+contains+%27xls%27')
		r = json.loads(r.text)

		for file in r["files"]:
			result={}
		if "name" in file:
			result["name"] = file["name"]
		else:
			result["name"] = "(None)"
		
		if "id" in file:
			result["id"] = file["id"]
		else:
			result["id"] = "(None)"
		
		if "mimeType" in file:
			result["mimeType"] = file["mimeType"]
		else:
			result["mimeType"] = "(None)"
			results.append(result)
	
		if 'nextPageToken' in r:
			page_token=r["nextPageToken"]
			GetFiles(api_key, page_token, results, logger)	
		else:
			return results
	except Exception as e:
		logger.info(str(e))
		return results
		
def GetSheet(api_key, id, logger):
	try:
		results = []
		r=requests.get('https://www.googleapis.com/drive/v3/files/'+id+'/export?access_token='+api_key+'&mimeType=text/csv')
		reader = csv.reader(r.text.splitlines())
		
		i_row=0
		keys=[]
		for row in reader:
			if i_row==0:
				i_header=0
				for header in row:
					key = {}
					key[i_header]=header
					keys.append(key)
					i_header = i_header + 1
				i_row=i_row+1
				break
		i_row=0

		result = {}
		for row in reader:
			#if i_row==0:
			#	i_row=i_row+1
			#	continue
			i_row_value = 0
			result = {}
			for item in row:
				result[keys[i_row_value][i_row_value]]=item
				i_row_value = i_row_value + 1
			results.append(result)
			i_row=i_row+1		
		return results
   		
	except Exception as e:
		results = []
		result["ERROR"] = str(e)
		results.append(result)
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

		fileId = result['fileId']
		#Parse JSON API Creds
		tokens = json.loads(password)
	
		#Get Refresh Token
		refreshtoken = tokens["RefreshToken"]

		#Get the API Key and Refresh Token
		new_creds = RefreshToken(refreshtoken, username, sessionKey)
		
		#Get New API Key	
		new_creds = json.loads(new_creds)
		api_key=new_creds["APIKey"]
		
		try:
			new = GetSheet(api_key, fileId, logger)
		except Exception as e:
			logger.info(str(e))
		splunk.Intersplunk.outputResults(new)

		
	except Exception as e:
		logger.info(str(e))
		results = []
		result = {}
		result["Error"] = str(e)
		results.append(result)
		splunk.Intersplunk.outputResults(results)
