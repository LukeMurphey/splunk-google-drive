

import logging
import sys
import os
import re
import json
import base64

from splunk.clilib.bundle_paths import make_splunkhome_path
from splunk import ResourceNotFound
import splunk.entity as entity
from splunk.rest import simpleRequest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from google_drive_app import rest_handler
from google_drive_app.six.moves.urllib.parse import quote_plus
from google_drive_app import SERVICE_KEY_REALM, SERVICE_KEY_USERNAME

path_to_mod_input_lib = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'modular_input.zip')
sys.path.insert(0, path_to_mod_input_lib)
from modular_input.secure_password import get_secure_password, get_secure_password_stanza

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

    def removeServiceAccountKeyJSON(self, stanza, session_key):
        response, _ = simpleRequest('/services/storage/passwords/' + quote_plus(stanza), sessionKey=session_key, method='DELETE')

        # Check response
        if response.status == 200 or response.status == 201:
            return True
        else:
            return False

    def uploadServiceAccountKeyJSON(self, file_contents, session_key):
        # Determine if the key already exists
        existing_key = self.get_raw_key_info_from_secure_storage(session_key)
        
        # Get secure password stanza
        stanza = get_secure_password_stanza(SERVICE_KEY_USERNAME, SERVICE_KEY_REALM)

        # Make up the argument array
        if existing_key is None:
            postargs = {
                'name': SERVICE_KEY_USERNAME,
                'password': file_contents,
                'realm': SERVICE_KEY_REALM,
                'output_mode': 'json',
            }
        else:
            self.logger.warn("Service key already exists")

            postargs = {
                'password': file_contents,
                'output_mode': 'json',
            }

        try:
            response, content = simpleRequest('/services/storage/passwords/' + quote_plus(stanza), postargs=postargs, sessionKey=session_key, method='POST')

            # Check response
            if response.status == 200 or response.status == 201:
                # Parse the output
                return self.render_json({
                                        'filename' : '',
                                        'private_key_id' : 'private_key_id',
                                        'service_account_email' : 'service_account_email'
                                        })
            else:
                self.logger.warn("Unable to save the key file, status=%i, response=%r", response.status, content)
                return self.render_error_json("Unable to save the key file")
        except:
            return self.render_error_json("Unable to save the key file")

    def uploadServiceAccountKey(self, file_name, file_contents, session_key):
        # Ensure that the file name is valid
        if not self.is_file_name_valid(file_name):
            return self.render_error_json("The service account key filename contains disallowed characters")

        # Parse the key and make sure it is valid
        service_account_email = None
        private_key_id = None
        account_key = None

        try:
            account_key = json.loads(file_contents)
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
        
        with open(service_key_file_path, 'wb') as fh:
            fh.write(file_contents)
        
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
        # if file_name is None or len(file_name.strip()) == 0:
        #     return self.render_error_json('The file name was not provided')

        if file_contents is None or len(file_contents.strip()) == 0:
            return self.render_error_json('The key file was not provided')

        # Remove the mime-type prefix
        try:
            file_contents = file_contents.split(',')[1]
        except IndexError:
            return self.render_error_json('Unable to parse the file contents.')

        # Upload via secure storage
        return self.uploadServiceAccountKeyJSON(file_contents, request_info.session_key)

    def get_raw_key_info_from_secure_storage(self, session_key):
        # Get the proxy password from secure storage (if it exists)
        return get_secure_password(realm=SERVICE_KEY_REALM,
                                   username=SERVICE_KEY_USERNAME,
                                   session_key=session_key)

    def get_key_info_from_secure_storage(self, session_key):
        # Get the key from secure storage (if it exists)
        key_contents = self.get_raw_key_info_from_secure_storage(session_key)

        # Stop if we don't get anything
        if key_contents is None:
            return None, None
        
        # If we found the key, parse it
        key_dict = None
        try:
            key_dict = json.loads(key_contents['clear_password'])

            service_account_email = key_dict.get('client_email', None)
            private_key_id = key_dict.get('private_key_id', None)

            return service_account_email, private_key_id
        except:
            self.logger.exception("Unable to parse the service account key")
            return None, None

    def get_key_info_from_file_system(self, session_key):
        # Get the existing service key
        default_password_entry = self.getDefaultGoogleDriveInputEntity(session_key)

        # Make sure the file name is specified in the default entry
        if 'service_account_key_file' in default_password_entry:
            file_name = default_password_entry['service_account_key_file']

            service_account_email, private_key_id = self.getInfoFromKeyFile(file_name)

            return service_account_email, private_key_id, file_name
        
        return None, None, None

    def get_key(self, request_info, **kwargs):
        try:
            file_name = None
            service_account_email = None
            private_key_id = None

            # Try getting the information from secure storage
            service_account_email, private_key_id = self.get_key_info_from_secure_storage(request_info.session_key)

            # Try loading the key from the file-system otherwise
            if service_account_email is None:
                service_account_email, private_key_id, file_name = self.get_key_info_from_file_system(request_info.session_key)

            # Return the information
            return self.render_json({
                                    'filename' : file_name,
                                    'service_account_email' : service_account_email,
                                    'private_key_id' : private_key_id
                                    })
        except:
            self.logger.exception("Exception generated when attempting to get the key")
            return self.render_error_json("Exception generated when attempting to get the key")
