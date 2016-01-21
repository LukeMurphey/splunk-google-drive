import logging
import os
import sys
import json
import cherrypy
import re
import base64

from splunk import AuthorizationFailed, ResourceNotFound
import splunk.appserver.mrsparkle.controllers as controllers
import splunk.appserver.mrsparkle.lib.util as util
from splunk.appserver.mrsparkle.lib import jsonresponse
from splunk.appserver.mrsparkle.lib.util import make_splunkhome_path
import splunk.clilib.bundle_paths as bundle_paths
from splunk.util import normalizeBoolean as normBool
from splunk.appserver.mrsparkle.lib.decorators import expose_page
from splunk.appserver.mrsparkle.lib.routes import route
import splunk.entity as entity
from splunk.rest import simpleRequest

def setup_logger(level):
    """
    Setup a logger for the REST handler.
    """

    logger = logging.getLogger('splunk.appserver.google_drive.controllers.ServiceAccountKeys')
    logger.propagate = False # Prevent the log messages from being duplicated in the python.log file
    logger.setLevel(level)

    file_handler = logging.handlers.RotatingFileHandler(make_splunkhome_path(['var', 'log', 'splunk', 'google_drive_service_account_keys_controller.log']), maxBytes=25000000, backupCount=5)

    formatter = logging.Formatter('%(asctime)s %(levelname)s %(message)s')
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)
    return logger

logger = setup_logger(logging.DEBUG)

class ServiceAccountKeys(controllers.BaseController):
    '''
    A controller for managing Google OAuth2 service account keys
    '''
 
    DEFAULT_NAMESPACE ="google_drive"
    DEFAULT_OWNER = "nobody"
 
    def is_file_name_valid(self, lookup_file):     
        """
        Indicate if the lookup file is valid (doesn't contain invalid characters such as "..").
        """
         
        allowed_path = re.compile("^[-A-Z0-9_ ]+([.][-A-Z0-9_ ]+)*$", re.IGNORECASE)
        
        if not allowed_path.match(lookup_file):
            return False
        else:
            return True
    
    def render_error_json(self, msg):
        output = jsonresponse.JsonResponse()
        output.data = []
        output.success = False
        output.addError(msg)
        cherrypy.response.status = 400
        return self.render_json(output, set_mime='text/plain')
 
    def setAppAsConfigured(self):

        session_key = cherrypy.session.get('sessionKey')
        
        postargs = {
                    'output_mode': 'json',
                    'configured' : 'true'
        }
        
        response, _ = simpleRequest('/services/apps/local/google_drive', sessionKey=session_key, method='POST', postargs=postargs, raiseAllErrors=False)

        if response.status == 200:
            return True
        else:
            return False
 
    def setKeyForDefaultInput(self, file_name):
        
        entity_entry = self.getDefaultGoogleDriveInputEntity()
        
        session_key = cherrypy.session.get('sessionKey')
        
        entity_entry['service_account_key_file'] = file_name
        entity_entry.namespace = ServiceAccountKeys.DEFAULT_NAMESPACE
        entity_entry.owner = ServiceAccountKeys.DEFAULT_OWNER
        entity.setEntity(entity_entry, sessionKey=session_key)
        
        self.setAppAsConfigured()
 
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
        
    def getDefaultGoogleDriveInputEntity(self):
        session_key = cherrypy.session.get('sessionKey')
        return entity.getEntity('admin/conf-inputs', 'google_spreadsheet', sessionKey=session_key)
        
    @expose_page(must_login=True, methods=['GET']) 
    def getDefaultServiceAccountKeyInfo(self, **kwargs):
        
        file_name = None
        service_account_email = None
        
        # Get the existing service key
        session_key = cherrypy.session.get('sessionKey')
        default_password_entry = self.getDefaultGoogleDriveInputEntity()
        
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
 
    @expose_page(must_login=True, methods=['POST']) 
    def uploadServiceAccountKey(self, file_contents, file_name):
        
        # Ensure that the file name is valid
        if not self.is_file_name_valid(file_name):
            return self.render_error_json(_("The service account key filename contains disallowed characters"))
        
        # Decode the content (it is sent as a base64 encoded file)
        file_contents_decoded = base64.b64decode(file_contents.split(',')[1])
        
        # Parse the key and make sure it is valid
        service_account_email = None
        private_key_id = None
        
        try:
            account_key = json.loads(file_contents_decoded)
            
            # Stop if the client email address is not included
            if 'client_email' not in account_key:
                return self.render_error_json(_("The service account key did not include a client email address"))
            
            # Get the email address and key ID
            else:
                service_account_email = account_key['client_email']
                private_key_id = account_key.get('private_key_id', None)
            
        except ValueError as e:
            return self.render_error_json(_("The service account key filename is invalid"))
        
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
        self.setKeyForDefaultInput(file_name)
        
        # Return the information
        return self.render_json({
                                 'filename' : file_name,
                                 'private_key_id' : private_key_id,
                                 'service_account_email' : service_account_email
                                 })
        