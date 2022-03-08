
import sys
import time
import base64
import json
import os

import httplib2
from httplib2 import socks

# Import the modular input components
path_to_mod_input_lib = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'modular_input.zip')
sys.path.insert(0, path_to_mod_input_lib)
from modular_input import Field, ModularInput, DurationField, BooleanField, DeprecatedField, FilePathField
from modular_input.secure_password import get_secure_password

from google_drive_app import GoogleLookupSync, SpreadsheetInaccessible, SERVICE_KEY_REALM, SERVICE_KEY_USERNAME
    
class Timer(object):
    """
    This class is used to time durations.
    """
    
    def __init__(self, verbose=False):
        self.verbose = verbose

    def __enter__(self):
        self.start = time.time()
        return self

    def __exit__(self, *args):
        self.end = time.time()
        self.secs = self.end - self.start
        self.msecs = self.secs * 1000  # millisecs

class GoogleDrive(ModularInput):
    """
    The Google Drive input facilitates import of Google Drive documents.
    """
    
    def __init__(self):

        scheme_args = {'title': "Google Drive",
                       'description': "Allows you to ingest information from files on Google Drive",
                       'use_external_validation': "true",
                       'streaming_mode': "xml",
                       'use_single_instance': "true"}
        
        args = [
                Field("path", "Path", "Path to get information on", empty_allowed=False),
                BooleanField("recurse", "Recurse", "If set to true, then the input will go down sub-directories.", empty_allowed=True, required_on_create=False, required_on_edit=False),
                FilePathField("service_account_key_file", "Service Key File", "The full path to the service account key", empty_allowed=False, validate_file_existence=False),
                BooleanField("only_if_changed", "Import file only if changed", "If set to true, then the import will only be done if the Google worksheet was changed.", empty_allowed=True, required_on_create=False, required_on_edit=False),

                DurationField("interval", "Interval", "The interval defining how often to import the file; can include time units (e.g. 15m for 15 minutes, 8h for 8 hours)", empty_allowed=False),
                ]
        
        ModularInput.__init__( self, scheme_args, args, logger_name='google_drive_modular_input' )

    def run(self, stanza, cleaned_params, input_config):
        
        # Make the parameters
        interval = cleaned_params["interval"]
        
        path = cleaned_params.get("path", None)
        service_account_key_file = cleaned_params.get("service_account_key_file", None)
        only_if_changed = cleaned_params.get("only_if_changed", False)
        recurse = cleaned_params.get("recurse", False)
        
        if self.needs_another_run(input_config.checkpoint_dir, stanza, interval):
            
            # Perform the operation accordingly
            # TODO
            self.logger.info("We have run!")

            # Get the time that the input last ran
            # last_ran = self.last_ran(input_config.checkpoint_dir, stanza)
            
            # Save the checkpoint so that we remember when we last 
            # self.save_checkpoint(input_config.checkpoint_dir, stanza, self.get_non_deviated_last_run(last_ran, interval, stanza),  date_worksheet_last_updated)
        
# Try to run the input
if __name__ == '__main__':
    
    try:
        google_drive = GoogleDrive()
        google_drive.execute()
        sys.exit(0)
    except Exception as e:
        
        try:
            # This logs general exceptions that would have been unhandled otherwise (such as coding errors)
            if google_drive is not None:
                google_drive.logger.exception("Unhandled exception was caught, this may be due to a defect in the script")
        except NameError:
            pass # google_drive was not instantiated yet
        
        raise e
