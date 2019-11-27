

import logging
import sys
import os
import re
import json
import base64

from splunk.clilib.bundle_paths import make_splunkhome_path
import splunk.entity as entity
from splunk.rest import simpleRequest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from google_drive_app import rest_handler

def setup_logger(level):
    """
    Setup a logger for the REST handler
    """

    logger = logging.getLogger('splunk.appserver.service_account_keys_rest_handler.rest_handler')
    logger.propagate = False # Prevent the log messages from being duplicated in the python.log file
    logger.setLevel(level)

    log_file_path = make_splunkhome_path(['var', 'log', 'splunk', 'service_account_keys_rest_handler.log'])
    file_handler = logging.handlers.RotatingFileHandler(log_file_path, maxBytes=25000000,
                                                        backupCount=5)

    formatter = logging.Formatter('%(asctime)s %(levelname)s %(message)s')
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)
    return logger

logger = setup_logger(logging.DEBUG)

class ServiceAccountKeysRestHandler(rest_handler.RESTHandler):

    DEFAULT_NAMESPACE ="google_drive"
    DEFAULT_OWNER = "nobody"

    def __init__(self, command_line, command_arg):
        super(ServiceAccountKeysRestHandler, self).__init__(command_line, command_arg, logger)

    def is_file_name_valid(self, lookup_file):     
        """
        Indicate if the lookup file is valid (doesn't contain invalid characters such as "..").
        """
         
        allowed_path = re.compile("^[-A-Z0-9_ ]+([.][-A-Z0-9_ ]+)*$", re.IGNORECASE)
        
        if not allowed_path.match(lookup_file):
            return False
        else:
            return True

    def setAppAsConfigured(self, session_key):
        
        postargs = {
                    'output_mode': 'json',
                    'configured' : 'true'
        }
        
        response, _ = simpleRequest('/services/apps/local/google_drive', sessionKey=session_key, method='POST', postargs=postargs, raiseAllErrors=False)

        if response.status == 200:
            return True
        else:
            return False
 
    def setKeyForDefaultInput(self, file_name, session_key):
        
        entity_entry = self.getDefaultGoogleDriveInputEntity(session_key)
        
        entity_entry['service_account_key_file'] = file_name
        entity_entry.namespace = ServiceAccountKeysRestHandler.DEFAULT_NAMESPACE
        entity_entry.owner = ServiceAccountKeysRestHandler.DEFAULT_OWNER
        entity.setEntity(entity_entry, sessionKey=session_key)
        
        self.setAppAsConfigured(session_key)
 
    def getDefaultGoogleDriveInputEntity(self, session_key):
        return entity.getEntity('admin/conf-inputs', 'google_spreadsheet', sessionKey=session_key)

    def getInfoFromKeyFile(self, file_name):
        
        service_key_file_path = make_splunkhome_path(['etc', 'apps', 'google_drive', 'service_account_keys', file_name])
        service_key = None
        
        try:
            with open(service_key_file_path, 'r') as fh:
                service_key = json.load(fh)
                
                client_email = service_key.get('client_email', None)
                private_key_id = service_key.get('private_key_id', None)
                
                return client_email, private_key_id
                
        except IOError:
            # File could not be loaded
            return None, None
            
        return None, None

    def uploadServiceAccountKey(self, file_name, file_contents, session_key):
        # Ensure that the file name is valid
        if not self.is_file_name_valid(file_name):
            return self.render_error_json("The service account key filename contains disallowed characters")
        
        # Decode the content (it is sent as a base64 encoded file)
        file_contents_decoded = base64.b64decode(file_contents.split(',')[1])
        
        # Parse the key and make sure it is valid
        service_account_email = None
        private_key_id = None
        account_key = None

        try:
            account_key = json.loads(file_contents_decoded)
        except ValueError as e:
            return self.render_error_json("The service account key is invalid")
        
        # Stop if the client email address is not included
        if 'client_email' not in account_key:
            return self.render_error_json("The service account key did not include a client email address")
        
        # Get the email address and key ID
        else:
            service_account_email = account_key['client_email']
            private_key_id = account_key.get('private_key_id', None)

        # Create the service account keys directory if it does not yet exist
        try:
            os.mkdir(make_splunkhome_path(['etc', 'apps', 'google_drive', 'service_account_keys']))
        except OSError as e:
            if e.errno == 17:
                pass # Path already exists, thats ok
            else:
                raise e
        
        # Write out the file
        service_key_file_path = make_splunkhome_path(['etc', 'apps', 'google_drive', 'service_account_keys', file_name])
        
        with open(service_key_file_path, 'w') as fh:
            fh.write(file_contents_decoded)
        
        # Set the input such that this key is used
        self.setKeyForDefaultInput(file_name, session_key)
        
        # Return the information
        return self.render_json({
                                 'filename' : file_name,
                                 'private_key_id' : private_key_id,
                                 'service_account_email' : service_account_email
                                 })

    def post_key(self, request_info, file_name=None, file_contents=None, **kwargs):
        # Make sure the needed values are present
        if file_name is None or len(file_name.strip()) == 0:
            return self.render_error_json('The file name was not provided')

        if file_contents is None or len(file_contents.strip()) == 0:
            return self.render_error_json('The key file was not provided')

        return self.uploadServiceAccountKey(file_name, file_contents, request_info.session_key)

    def get_key(self, request_info, **kwargs):
        file_name = None
        service_account_email = None
        private_key_id = None

        # Get the existing service key
        default_password_entry = self.getDefaultGoogleDriveInputEntity(request_info.session_key)

        # Make sure the file name is specified in the default entry
        if 'service_account_key_file' in default_password_entry:
            file_name = default_password_entry['service_account_key_file']

            service_account_email, private_key_id = self.getInfoFromKeyFile(file_name)

        # Return the information
        return self.render_json({
                                 'filename' : file_name,
                                 'service_account_email' : service_account_email,
                                 'private_key_id' : private_key_id
                                 })
