

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
from google_drive_app.six import binary_type
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

    def getKeyFileContents(self, session_key):
        default_password_entry = self.getDefaultGoogleDriveInputEntity(session_key)

        # Make sure the file name is specified in the default entry
        if 'service_account_key_file' in default_password_entry:
            file_name = default_password_entry['service_account_key_file']
            service_key_file_path = make_splunkhome_path(['etc', 'apps', 'google_drive', 'service_account_keys', file_name])
            service_key = None
            
            with open(service_key_file_path, 'r') as fh:
                service_key = fh.read()

                return service_key

        return None

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

    def refreshServiceAccountKey(self, session_key):
        stanza = get_secure_password_stanza(SERVICE_KEY_USERNAME, SERVICE_KEY_REALM)
        _, _ = simpleRequest('/services/storage/passwords/_reload' + quote_plus(stanza), sessionKey=session_key)

    def removeServiceAccountKey(self, session_key):
        stanza = get_secure_password_stanza(SERVICE_KEY_USERNAME, SERVICE_KEY_REALM)
        self.logger.warn("About to delete service key, stanza=%s", stanza)

        response, _ = simpleRequest('/servicesNS/nobody/search/storage/passwords/' + quote_plus(stanza), sessionKey=session_key, method='DELETE')

        # Check response
        if response.status == 200 or response.status == 201:
            return True
        else:
            return False

    def uploadServiceAccountKeyJSON(self, file_contents, session_key):
        # Parse the output
        service_account_email = None
        private_key_id = None

        try:
            service_account_email, private_key_id = self.parseServiceAccountKey(file_contents, is_base64=True)
        except ValueError as e:
            return self.render_error_json(str(e))

        # Determine if the key already exists
        existing_key = self.retrieve_raw_key_info_from_secure_storage(session_key)
        
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
            self.logger.info("Service key already exists; it wil be replaced with a new one")

            postargs = {
                'password': file_contents,
                'output_mode': 'json',
            }

        try:
            response, content = simpleRequest('/services/storage/passwords/' + quote_plus(stanza), postargs=postargs, sessionKey=session_key, method='POST')

            # Check response
            if response.status == 200 or response.status == 201:

                # Return a response
                return self.render_json({
                                        'filename' : '',
                                        'private_key_id' : private_key_id,
                                        'service_account_email' : service_account_email
                                        })
            else:
                self.logger.warn("Unable to save the key file, status=%i, response=%r", response.status, content)
                return self.render_error_json("Unable to save the key file")
        except:
            return self.render_error_json("Unable to save the key file")

    def migrateKeyToSecureStorage(self, session_key):

        # Find out if we have a key on the file-system
        service_account_email, _, _ = self.retrieve_key_info_from_file_system(session_key)
        
        if service_account_email is None:
            return False

        # Find out if we have a key in secure storage
        existing_key = self.retrieve_raw_key_info_from_secure_storage(session_key)

        if existing_key is not None:
            return False

        # Read in the file
        service_key = None
        try:
            service_key = self.getKeyFileContents(session_key)
        except:
            self.logger.error('Unable to load the key file for migration')

        # Convert the string to bytes so that it can be encoded
        if not isinstance(service_key, binary_type):
            service_key = service_key.encode('utf-8')

        # Base64 encode the key
        service_key_encoded = base64.b64encode(service_key)
        service_key_encoded = service_key_encoded.decode('utf-8')

        # Convert the key over
        response = self.uploadServiceAccountKeyJSON(service_key_encoded, session_key)

        if response is not None:
            if 'success' in response and not response.get('success', False):
                self.logger.info('Unable to load the key file for migration: %s', response['message'])

            return response

    def parseServiceAccountKey(self, file_contents, is_base64=False):

        # Decode the content from base64 if necessary
        if is_base64:
            file_contents = base64.b64decode(file_contents)
            file_contents = file_contents.decode('utf-8')

        # Try to parse the file
        account_key = None
        try:
            account_key = json.loads(file_contents)
        except:
            self.logger.warn("Unable to parse service account key")
            raise ValueError('Key could not be parsed')

        # Verify that it includes the email
        if 'client_email' not in account_key:
            raise ValueError('Service account key is missing the client_email')

        # Get the parameters to return
        service_account_email = account_key['client_email']
        private_key_id = account_key.get('private_key_id', None)

        return service_account_email, private_key_id

    def uploadServiceAccountKey(self, file_name, file_contents, session_key):
        # Ensure that the file name is valid
        if not self.is_file_name_valid(file_name):
            return self.render_error_json("The service account key filename contains disallowed characters")

        # Parse the key and make sure it is valid
        service_account_email = None
        private_key_id = None

        try:
            service_account_email, private_key_id = self.parseServiceAccountKey(file_contents, is_base64=True)
        except ValueError as e:
            return self.render_error_json(str(e))

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

    def post_key_migrate(self, request_info, **kwargs):
        # Migrate the key if necessary
        migrated = self.migrateKeyToSecureStorage(request_info.session_key)

        # Get the updated key information
        response_json = self.get_key(request_info)

        # Note whether we migrated the key
        response_json['migrated'] = migrated

        return response_json

    def post_key(self, request_info, file_name=None, file_contents=None, **kwargs):
        if file_contents is None or len(file_contents.strip()) == 0:
            return self.render_error_json('The key file was not provided')

        # Remove the mime-type prefix
        try:
            file_contents = file_contents.split(',')[1]
        except IndexError:
            return self.render_error_json('Unable to parse the file contents.')

        # Upload via secure storage
        return self.uploadServiceAccountKeyJSON(file_contents, request_info.session_key)

    def retrieve_raw_key_info_from_secure_storage(self, session_key):
        # Get the proxy password from secure storage (if it exists)
        return get_secure_password(realm=SERVICE_KEY_REALM,
                                   username=SERVICE_KEY_USERNAME,
                                   session_key=session_key)

    def retrieve_key_info_from_secure_storage(self, session_key):
        # Get the key from secure storage (if it exists)
        key_contents = self.retrieve_raw_key_info_from_secure_storage(session_key)

        # Stop if we don't get anything
        if key_contents is None:
            return None, None
        
        # If we found the key, parse it
        try:
            return self.parseServiceAccountKey(key_contents['content']['clear_password'], is_base64=True)
        except:
            self.logger.exception("Unable to parse the service account key")
            return None, None

    def retrieve_key_info_from_file_system(self, session_key):
        # Get the existing service key
        default_password_entry = self.getDefaultGoogleDriveInputEntity(session_key)

        # Make sure the file name is specified in the default entry
        if 'service_account_key_file' in default_password_entry:
            file_name = default_password_entry['service_account_key_file']

            service_account_email, private_key_id = self.getInfoFromKeyFile(file_name)

            return service_account_email, private_key_id, file_name
        
        return None, None, None

    def post_remove_key(self, request_info, **kwargs):
        try:
            success = self.removeServiceAccountKey(request_info.session_key)
            response = self.get_key(request_info)

            if success:
                self.logger.info("Removed service account key from secure storage")
                response['message'] = 'existing key removed'
            else:
                self.logger.warn("Failed to remove service account key from secure storage")
                response['message'] = 'existing key was not removed'

            return response
        except:
            self.logger.exception("Exception generated when attempting to remove the old key")
            return self.render_error_json("Exception generated when attempting to remove the old key")

    def get_key(self, request_info, **kwargs):
        try:
            file_name = None
            service_account_email = None
            private_key_id = None

            # Try getting the information from secure storage
            service_account_email, private_key_id = self.retrieve_key_info_from_secure_storage(request_info.session_key)

            # Try loading the key from the file-system otherwise
            if service_account_email is None:
                service_account_email, private_key_id, file_name = self.retrieve_key_info_from_file_system(request_info.session_key)

            # Return the information
            return self.render_json({
                                    'filename' : file_name,
                                    'service_account_email' : service_account_email,
                                    'private_key_id' : private_key_id
                                    })
        except:
            self.logger.exception("Exception generated when attempting to get the key")
            return self.render_error_json("Exception generated when attempting to get the key")
