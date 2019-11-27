
from splunk.clilib.bundle_paths import make_splunkhome_path
from splunk.models.base import SplunkAppObjModel
from splunk.models.field import Field as ModelField
from splunk.models.field import IntField as ModelIntField 

import sys
import time
import splunk
import json
import os

import httplib2
from httplib2 import socks

path_to_mod_input_lib = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'modular_input.zip')
sys.path.insert(0, path_to_mod_input_lib)
from modular_input import Field, ModularInput, DurationField, BooleanField, DeprecatedField

from google_drive_app import GoogleLookupSync, SpreadsheetInaccessible
    
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

class WebProxyConfig(SplunkAppObjModel):
    
    resource       = '/admin/web_proxy'
    proxy_server   = ModelField()
    proxy_port     = ModelIntField()
    proxy_type     = ModelField()
    proxy_user     = ModelField()
    proxy_password = ModelField()

class GoogleSpreadsheets(ModularInput):
    """
    The Google Spreadsheet input facilitates import of Google spreadsheets into Splunk as lookups.
    """
    
    def __init__(self):

        scheme_args = {'title': "Google Spreadsheet",
                       'description': "Allows you to import/export Splunk lookups to/from Google spreadsheets",
                       'use_external_validation': "true",
                       'streaming_mode': "xml",
                       'use_single_instance': "true"}
        
        args = [
                Field("spreadsheet", "Spreadsheet Title", "The title of the spreadsheet", empty_allowed=False),
                Field("worksheet", "Worksheet Name", 'The name of the worksheet (e.g. "Sheet1")', empty_allowed=False),
                Field("service_account_key_file", "OAuth2 Service Account Key File", 'The service account key with the credentials necessary for authenticating to Google', empty_allowed=False, required_on_create=False, required_on_edit=False),
                
                BooleanField("only_if_changed", "Import file only if changed", "If set to true, then the import will only be done if the Google worksheet was changed.", empty_allowed=False),
                
                Field("operation", "Operation", "The operation to perform (import into Splunk or export to Google Drive)", empty_allowed=False),
                Field("lookup_name", "Lookup File Name", 'The name of the lookup file to import the content into', empty_allowed=False),
                
                DurationField("interval", "Interval", "The interval defining how often to import the file; can include time units (e.g. 15m for 15 minutes, 8h for 8 hours)", empty_allowed=False),
                
                DeprecatedField("google_login", "Google Login", 'The login to use when authenticating to Google'),
                DeprecatedField("google_password", "Google Password", 'The password to use when authenticating to Google. You will need to use an app-specific password here if you are using two-factor authentication.')
                ]
        
        ModularInput.__init__( self, scheme_args, args, logger_name='google_spreadsheet_modular_input' )
    
    def resolve_proxy_type(self, proxy_type):
        """
        Resolve the proxy type to use from the given string.
        
        Argument:
        proxy_type -- A string description of the proxy type to use
        """
        
        # Make sure the proxy string is not none
        if proxy_type is None:
            return None
        
        # Prepare the string so that the proxy type can be matched more reliably
        t = proxy_type.strip().lower()
        
        if t == "socks4":
            return socks.PROXY_TYPE_SOCKS4
        elif t == "socks5":
            return socks.PROXY_TYPE_SOCKS5
        elif t == "http":
            return socks.PROXY_TYPE_HTTP
        elif t == "":
            return None
        else:
            self.logger.warn("Proxy type is not recognized: %s", proxy_type)
            return None
        
    def export_file(self, spreadsheet_title, worksheet_name, lookup_name, key_file=None, proxy_type=None, proxy_server=None, proxy_port=None, proxy_user=None, proxy_password=None, session_key=None):
        """
        Export the lookup from Splunk into a Google Drive Spreadsheet.
        
        Argument:
        spreadsheet_title -- The title of the spreadsheet to export
        worksheet_name -- The name of the worksheet within the spreadsheet to export
        lookup_name -- The name of the lookup file to export
        key_file -- The private key file
        proxy_type -- The type of the proxy server (must be one of: socks4, socks5, http)
        proxy_server -- The proxy server to use.
        proxy_port -- The port on the proxy server to use.
        proxy_user -- The proxy server to use.
        proxy_password -- The port on the proxy server to use.
        session_key -- A session key to Splunkd
        """
        
        #self.logger.debug('Performing import, url="%s"', url.geturl())
        
        # Determine which type of proxy is to be used (if any)
        resolved_proxy_type = self.resolve_proxy_type(proxy_type)
        
        # Setup the proxy info if so configured
        if resolved_proxy_type is not None and proxy_server is not None and len(proxy_server.strip()) > 0:
            proxy_info = httplib2.ProxyInfo(resolved_proxy_type, proxy_server, proxy_port, proxy_user=proxy_user, proxy_pass=proxy_password)
        else:
            # No proxy is being used
            proxy_info = None
        
        try:
            
            # Make the HTTP object
            http = httplib2.Http(proxy_info=proxy_info, disable_ssl_certificate_validation=True)
            
            last_updated = None
            
            # Perform the request
            with Timer() as timer:
                google_lookup_sync = GoogleLookupSync(key_file, logger=self.logger)
                last_updated = google_lookup_sync.export_lookup_file(lookup_name, None, None, spreadsheet_title, worksheet_name, session_key)
                
            self.logger.info("Export completed, time=%r", timer.msecs)
            
            # Return the date the spreadsheet was last updated
            return last_updated
            
        except socks.GeneralProxyError:
            # This may be thrown if the user configured the proxy settings incorrectly
            self.logger.exception("An error occurred when attempting to communicate with the proxy")
            
        except SpreadsheetInaccessible:
            self.logger.warning("Unable to access the spreadsheet, make sure the service account has been granted access to this file; spreadsheet_title=%s, help_url=%s", spreadsheet_title, "http://lukemurphey.net/projects/splunk-google-docs/wiki/How_to_setup_app")
        
        except Exception:
            self.logger.exception("A general exception was thrown when executing the export")
    
    def import_file(self, spreadsheet_title, worksheet_name, lookup_name, key_file=None, proxy_type=None, proxy_server=None, proxy_port=None, proxy_user=None, proxy_password=None, session_key=None, spreadsheet_date_of_last_import=None, only_import_if_changed=False):
        """
        Import the given Google Drive Spreadsheet as a file into Splunk as a lookup file.
        
        Argument:
        spreadsheet_title -- The title of the spreadsheet to import
        worksheet_name -- The name of the worksheet within the spreadsheet to import
        lookup_name -- The name of the lookup file to export
        key_file -- The key file to use for authentication
        proxy_type -- The type of the proxy server (must be one of: socks4, socks5, http)
        proxy_server -- The proxy server to use.
        proxy_port -- The port on the proxy server to use.
        proxy_user -- The proxy server to use.
        proxy_password -- The port on the proxy server to use.
        session_key -- A session key to Splunkd
        spreadsheet_date_of_last_import -- Updated date of the last spreadsheet that was successfully imported.
        only_import_if_changed -- Only perform the import if the lookup file was changed since the last time it was imported.
        """
        
        #self.logger.debug('Performing import, url="%s"', url.geturl())
        
        # Determine which type of proxy is to be used (if any)
        resolved_proxy_type = self.resolve_proxy_type(proxy_type)
        
        # Setup the proxy info if so configured
        if resolved_proxy_type is not None and proxy_server is not None and len(proxy_server.strip()) > 0:
            proxy_info = httplib2.ProxyInfo(resolved_proxy_type, proxy_server, proxy_port, proxy_user=proxy_user, proxy_pass=proxy_password)
        else:
            # No proxy is being used
            proxy_info = None
        
        try:
            
            # Make the HTTP object
            http = httplib2.Http(proxy_info=proxy_info, disable_ssl_certificate_validation=True)
            
            last_updated = None
            
            # Perform the request
            with Timer() as timer:
                google_lookup_sync = GoogleLookupSync(key_file, logger=self.logger)
                
                # Make sure that the worksheet changed. If it hasn't don't don't bother importing.
                if only_import_if_changed and spreadsheet_date_of_last_import is not None:
                    last_updated = google_lookup_sync.get_worksheet_updated_date(spreadsheet_title, worksheet_name)
                    
                    if last_updated == spreadsheet_date_of_last_import:
                        self.logger.info('Worksheet has not changed since last import, no action necessary, last_updated=%s, spreadsheet="%s", worksheet="%s"', last_updated, spreadsheet_title, worksheet_name)
                        return last_updated
                
                last_updated = google_lookup_sync.import_to_lookup_file(lookup_name, None, None, spreadsheet_title, worksheet_name, session_key, create_if_non_existent=False)
                
            self.logger.info("Import completed, time=%r", timer.msecs)
            
            # Return the date the spreadsheet was last updated
            return last_updated
            
        except socks.GeneralProxyError:
            # This may be thrown if the user configured the proxy settings incorrectly
            self.logger.exception("An error occurred when attempting to communicate with the proxy")
        
        except SpreadsheetInaccessible:
            self.logger.warning("Unable to access the spreadsheet, make sure the service account has been granted access to this file; spreadsheet_title=%s, help_url=%s", spreadsheet_title, "http://lukemurphey.net/projects/splunk-google-docs/wiki/How_to_setup_app")
        
        except Exception:
            self.logger.exception("A general exception was thrown when executing the import")
    
    def save_checkpoint(self, checkpoint_dir, stanza, last_run, google_worksheet_updated):
        """
        Save the checkpoint state.
        
        Arguments:
        checkpoint_dir -- The directory where checkpoints ought to be saved
        stanza -- The stanza of the input being used
        last_run -- The time when the analysis was last performed
        google_worksheet_updated -- The date that the worksheet was updated
        """
                
        self.save_checkpoint_data(checkpoint_dir, stanza, { 'last_run' : last_run,
                                                           'google_worksheet_updated' : google_worksheet_updated
                                                           })
        
    def get_proxy_config(self, session_key, stanza="default"):
        """
        Get the proxy configuration
        
        Arguments:
        session_key -- The session key to use when connecting to the REST API
        stanza -- The stanza to get the proxy information from (defaults to "default")
        """
        
        # If the stanza is empty, then just use the default
        if stanza is None or stanza.strip() == "":
            stanza = "default"
        
        # Get the proxy configuration
        try:
            web_proxy_config = WebProxyConfig.get( WebProxyConfig.build_id( stanza, "default", "nobody"), sessionKey=session_key )
            
            self.logger.debug("Proxy information loaded, stanza=%s", stanza)
            
        except splunk.ResourceNotFound:
            self.logger.error("Unable to find the proxy configuration for the specified configuration stanza=%s", stanza)
            raise
        
        return web_proxy_config.proxy_type, web_proxy_config.proxy_server, web_proxy_config.proxy_port, web_proxy_config.proxy_user, web_proxy_config.proxy_password
        
    def get_date_last_imported(self, checkpoint_dir, stanza):
        """
        Get the date that the worksheet was last updated.
        
        Arguments:
        checkpoint_dir -- The directory where checkpoints ought to be saved and stored
        stanza -- The stanza of the input being used
        """
        
        data = self.get_checkpoint_data(checkpoint_dir, stanza)
        
        if data is not None:
            return data.get('google_worksheet_updated', None)
        
    def resolve_credential_file(self, service_account_key_file):
        return make_splunkhome_path(['etc', 'apps', 'google_drive', 'service_account_keys', os.path.basename(service_account_key_file)])
        
    def run(self, stanza, cleaned_params, input_config):
        
        # Make the parameters
        interval                 = cleaned_params["interval"]
        lookup_name              = cleaned_params["lookup_name"]
        
        service_account_key_file = cleaned_params.get("service_account_key_file", None)
        google_spreadsheet       = cleaned_params["spreadsheet"]
        google_worksheet         = cleaned_params["worksheet"]
        only_if_changed          = cleaned_params.get("only_if_changed", False)
        
        operation                = cleaned_params.get("operation", None)

        # Stop if the service account key was not provided
        if service_account_key_file is None:
            self.logger.warning("The service account key was not provided. Please run setup and provide the service account key to run this input")
            return
        
        if self.needs_another_run(input_config.checkpoint_dir, stanza, interval):
            
            # Get the proxy configuration
            proxy_type, proxy_server, proxy_port, proxy_user, proxy_password = None, None, None, None, None
            """
            try:
                proxy_type, proxy_server, proxy_port, proxy_user, proxy_password = self.get_proxy_config(input_config.session_key, conf_stanza)
            except splunk.ResourceNotFound:
                self.logger.error("The proxy configuration could not be loaded. The execution will be skipped for this input with stanza=%s", stanza)
                return
            """
            
            date_worksheet_last_updated = self.get_date_last_imported(input_config.checkpoint_dir, stanza)
            
            # Perform the operation accordingly
            if operation is not None and operation.lower() == GoogleLookupSync.Operation.IMPORT:
                
                # Perform the import
                date_worksheet_last_updated = self.import_file(google_spreadsheet, google_worksheet, lookup_name, key_file=self.resolve_credential_file(service_account_key_file), proxy_type=proxy_type, proxy_server=proxy_server, proxy_port=proxy_port, proxy_user=proxy_user, proxy_password=proxy_password, session_key=input_config.session_key, only_import_if_changed=only_if_changed, spreadsheet_date_of_last_import=date_worksheet_last_updated)
            
            elif operation is not None and operation.lower() == GoogleLookupSync.Operation.EXPORT:
                
                # Perform the export
                date_worksheet_last_updated = self.export_file(google_spreadsheet, google_worksheet, lookup_name, key_file=self.resolve_credential_file(service_account_key_file), proxy_type=proxy_type, proxy_server=proxy_server, proxy_port=proxy_port, proxy_user=proxy_user, proxy_password=proxy_password, session_key=input_config.session_key)
            
            else:
                self.logger.warning("No valid operation specified for the stanza=%s", stanza)
                
            # Get the time that the input last ran
            last_ran = self.last_ran(input_config.checkpoint_dir, stanza)
            
            # Save the checkpoint so that we remember when we last 
            self.save_checkpoint(input_config.checkpoint_dir, stanza, self.get_non_deviated_last_run(last_ran, interval, stanza),  date_worksheet_last_updated)
        
# Try to run the input
if __name__ == '__main__':
    
    try:
        google_spreadsheet = GoogleSpreadsheets()
        google_spreadsheet.execute()
        sys.exit(0)
    except Exception as e:
        
        try:
            # This logs general exceptions that would have been unhandled otherwise (such as coding errors)
            if google_spreadsheet is not None:
                google_spreadsheet.logger.exception("Unhandled exception was caught, this may be due to a defect in the script")
        except NameError:
            pass # google_spreadsheet was not instantiated yet
        
        raise e