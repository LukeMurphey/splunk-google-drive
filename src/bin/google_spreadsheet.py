
from splunk.appserver.mrsparkle.lib.util import make_splunkhome_path
from splunk.models.base import SplunkAppObjModel
from google_drive_app.modular_input import Field, ModularInput, URLField, DurationField
from splunk.models.field import Field as ModelField
from splunk.models.field import IntField as ModelIntField 

import re
import logging
from logging import handlers
import hashlib
import socket
import sys
import time
import splunk
import os

import httplib2
from httplib2 import socks

from google_drive_app import GoogleLookupSync

def setup_logger():
    """
    Setup a logger.
    """
    
    logger = logging.getLogger('google_spreadsheet_modular_input')
    logger.propagate = False # Prevent the log messages from being duplicated in the python.log file
    logger.setLevel(logging.INFO)
    
    file_handler = handlers.RotatingFileHandler(make_splunkhome_path(['var', 'log', 'splunk', 'google_spreadsheet_modular_input.log']), maxBytes=25000000, backupCount=5)
    formatter = logging.Formatter('%(asctime)s %(levelname)s %(message)s')
    file_handler.setFormatter(formatter)
    
    logger.addHandler(file_handler)
    
    return logger

logger = setup_logger()
    
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
    
    def __init__(self, timeout=30):

        scheme_args = {'title': "Google Spreadsheet",
                       'description': "Allows you to import Google spreadsheets into Splunk and use them as lookups",
                       'use_external_validation': "true",
                       'streaming_mode': "xml",
                       'use_single_instance': "true"}
        
        args = [
                Field("spreadsheet", "Spreadsheet Title", "The title of the spreadsheet", empty_allowed=False),
                Field("worksheet", "Worksheet Name", 'The name of the worksheet (e.g. "Sheet1")', empty_allowed=False),
                Field("google_login", "Google Login", 'The login to use when authenticating to Google', empty_allowed=False),
                Field("google_password", "Google Password", 'The password to use when authenticating to Google. You will need to use an app-specific password here if you are using two-factor authentication.', empty_allowed=False),
                
                Field("lookup_name", "Lookup File Name", 'The name of the lookup file to import the content into', empty_allowed=False),
                
                DurationField("interval", "Interval", "The interval defining how often to import the file; can include time units (e.g. 15m for 15 minutes, 8h for 8 hours)", empty_allowed=False)
                ]
        
        ModularInput.__init__( self, scheme_args, args )
        
        if timeout > 0:
            self.timeout = timeout
        else:
            self.timeout = 30
        
    @classmethod
    def resolve_proxy_type(cls, proxy_type):
        
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
            logger.warn("Proxy type is not recognized: %s", proxy_type)
            return None
        
    @classmethod
    def import_file(cls, spreadsheet_title, worksheet_name, lookup_name, google_login=None, google_password=None, oauth2_token=None, proxy_type=None, proxy_server=None, proxy_port=None, proxy_user=None, proxy_password=None, session_key=None):
        """
        Import the given Google Drive Spreadsheet as a file into Splunk as a lookup file.
        
        Argument:
        spreadsheet_title -- 
        worksheet_name -- 
        lookup_name -- 
        google_login
        google_password -- 
        oauth2_token -- 
        proxy_type -- The type of the proxy server (must be one of: socks4, socks5, http)
        proxy_server -- The proxy server to use.
        proxy_port -- The port on the proxy server to use.
        proxy_user -- The proxy server to use.
        proxy_password -- The port on the proxy server to use.
        session_key -- 
        """
        
        #logger.debug('Performing import, url="%s"', url.geturl())
        
        # Determine which type of proxy is to be used (if any)
        resolved_proxy_type = cls.resolve_proxy_type(proxy_type)
        
        # Setup the proxy info if so configured
        if resolved_proxy_type is not None and proxy_server is not None and len(proxy_server.strip()) > 0:
            proxy_info = httplib2.ProxyInfo(resolved_proxy_type, proxy_server, proxy_port, proxy_user=proxy_user, proxy_pass=proxy_password)
        else:
            # No proxy is being used
            proxy_info = None
        
        try:
            
            # Make the HTTP object
            http = httplib2.Http(proxy_info=proxy_info, disable_ssl_certificate_validation=True)
            
            #session_key = splunk.auth.getSessionKey(username='admin', password='changeme')
            
            # Perform the request
            with Timer() as timer:
                google_lookup_sync = GoogleLookupSync(google_login, google_password, logger=logger)
                google_lookup_sync.import_to_lookup_file(lookup_name, None, None, spreadsheet_title, worksheet_name, session_key, create_if_non_existent=False)
                
            logger.info("Import completed, time=%r", timer.msecs)
            
        except socks.GeneralProxyError:
            # This may be thrown if the user configured the proxy settings incorrectly
            logger.exception("An error occurred when attempting to communicate with the proxy")
        
        except Exception:
            logger.exception("A general exception was thrown when executing the import")
    
    @classmethod
    def save_checkpoint(cls, checkpoint_dir, stanza, last_run):
        """
        Save the checkpoint state.
        
        Arguments:
        checkpoint_dir -- The directory where checkpoints ought to be saved
        stanza -- The stanza of the input being used
        last_run -- The time when the analysis was last performed
        """
                
        cls.save_checkpoint_data(checkpoint_dir, stanza, { 'last_run' : last_run })
        
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
            
            logger.debug("Proxy information loaded, stanza=%s", stanza)
            
        except splunk.ResourceNotFound:
            logger.error("Unable to find the proxy configuration for the specified configuration stanza=%s", stanza)
            raise
        
        return web_proxy_config.proxy_type, web_proxy_config.proxy_server, web_proxy_config.proxy_port, web_proxy_config.proxy_user, web_proxy_config.proxy_password
        
    def run(self, stanza, cleaned_params, input_config):
        
        # Make the parameters
        interval                 = cleaned_params["interval"]
        lookup_name              = cleaned_params["lookup_name"]
        
        google_login             = cleaned_params["google_login"]
        google_password          = cleaned_params["google_password"]
        google_spreadsheet       = cleaned_params["spreadsheet"]
        google_worksheet         = cleaned_params["worksheet"]
        
        timeout                  = self.timeout
        sourcetype               = cleaned_params.get("sourcetype", "google_spreadsheet")
        host                     = cleaned_params.get("host", None)
        index                    = cleaned_params.get("index", "default")
        conf_stanza              = cleaned_params.get("configuration", None)
        source                   = stanza
        
        if self.needs_another_run( input_config.checkpoint_dir, stanza, interval ):
            
            # Get the proxy configuration
            proxy_type, proxy_server, proxy_port, proxy_user, proxy_password = None, None, None, None, None
            """
            try:
                proxy_type, proxy_server, proxy_port, proxy_user, proxy_password = self.get_proxy_config(input_config.session_key, conf_stanza)
            except splunk.ResourceNotFound:
                logger.error("The proxy configuration could not be loaded. The execution will be skipped for this input with stanza=%s", stanza)
                return
            """
            
            # Perform the import
            GoogleSpreadsheets.import_file(google_spreadsheet, google_worksheet, lookup_name, google_login=google_login, google_password=google_password, proxy_type=proxy_type, proxy_server=proxy_server, proxy_port=proxy_port, proxy_user=proxy_user, proxy_password=proxy_password, session_key=input_config.session_key)
            
            # Get the time that the input last ran
            last_ran = self.last_ran(input_config.checkpoint_dir, stanza)
            
            # Save the checkpoint so that we remember when we last 
            self.save_checkpoint(input_config.checkpoint_dir, stanza, self.get_non_deviated_last_run(last_ran, interval, stanza) )
        
            
if __name__ == '__main__':
    try:
        google_spreadsheet = GoogleSpreadsheets()
        google_spreadsheet.execute()
        sys.exit(0)
    except Exception as e:
        logger.exception("Unhandled exception was caught, this may be due to a defect in the script") # This logs general exceptions that would have been unhandled otherwise (such as coding errors)
        raise e