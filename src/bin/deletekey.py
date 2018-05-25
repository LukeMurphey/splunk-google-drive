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

def DeleteToken(sessionKey, user):
    splunkService = client.connect(token=sessionKey,app='google_drive')
    try:
        splunkService.storage_passwords.delete(user,user)
    except Exception as e:
        logger.info(str(e))

now = datetime.datetime.now()

logger = setup_logger(logging.INFO)


results,dummy,settings = splunk.Intersplunk.getOrganizedResults()
sessionKey = settings.get("sessionKey")
username=""
for result in results:
	try:
		#Get Google Drive Name and API Creds from Password Store
		username=result['username']
		
		#Get the API Key and Refresh Token
		#new_creds = RefreshToken(refreshtoken, username, sessionKey)
		DeleteToken(sessionKey, username)
		
		#Get New API Key	
		#new_creds = json.loads(new_creds)
		#api_key=new_creds["APIKey"]

        	
	except Exception as e:
		logger.info(str(e))

results = []
result = {}
result["Status"] = "Token Deleted: "+username
results.append(result)
splunk.Intersplunk.outputResults(results)
