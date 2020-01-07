"""
This script provides a search command that allows you to input a Google sheet into Splunk search results.
"""

import os
import sys
import base64

from splunk.util import normalizeBoolean

from google_drive_app.search_command import SearchCommand
from google_drive_app import GoogleLookupSync

path_to_mod_input_lib = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'modular_input.zip')
if path_to_mod_input_lib not in sys.path:
    sys.path.insert(0, path_to_mod_input_lib)

from modular_input.secure_password import get_secure_password
from google_drive_app import GoogleLookupSync, SpreadsheetInaccessible, SERVICE_KEY_REALM, SERVICE_KEY_USERNAME

class InputGoogleSheetSearchCommand(SearchCommand):
    """
    The search command takes the arguments provided by the command-line and sends it to the
    modular input functions so that you could you run the input manually.
    """

    def __init__(self, spreadsheet=None, worksheet=None):

        # Note: output_matches_as_mv and include_raw_content are supported for legacy purposes

        # Make sure the required arguments are provided
        if spreadsheet is None:
            raise ValueError("spreadsheet argument must be provided")

        if worksheet is None:
            raise ValueError("worksheet argument must be provided")

        # Save the parameters
        self.spreadsheet = spreadsheet
        self.worksheet = worksheet

        SearchCommand.__init__(self, run_in_preview=True, logger_name="input_google_sheet_search_command")

    def handle_results(self, results, session_key, in_preview):

        # FYI: we ignore results since this is a generating command

        # Setup the proxy info if so configured
        """
        if resolved_proxy_type is not None and proxy_server is not None and len(proxy_server.strip()) > 0:
            proxy_info = httplib2.ProxyInfo(resolved_proxy_type, proxy_server, proxy_port, proxy_user=proxy_user, proxy_pass=proxy_password)
        else:
            # No proxy is being used
            proxy_info = None
        """

        # Get the stored password
        key_file_encoded = get_secure_password(realm=SERVICE_KEY_REALM,
                                               username=SERVICE_KEY_USERNAME,
                                               session_key=session_key)

        # We store this in base64, decode it
        key_file_str = None
        if key_file_encoded is not None:
            key_file_str = base64.b64decode(key_file_encoded['content']['clear_password'])
            key_file_str = key_file_str.decode('utf-8')

        # Stop if we didn't get a key
        if key_file_str is None:
            raise Exception("Key is not available")

        # Make the lookup sync class
        google_lookup_sync = GoogleLookupSync.from_service_key_string(key_file_str, logger=self.logger)

        # Open the spreadsheet
        google_spread_sheet = google_lookup_sync.open_google_spreadsheet(self.spreadsheet)
        
        # Open or make the worksheet
        google_work_sheet = google_lookup_sync.get_or_make_sheet_if_necessary(google_spread_sheet, self.worksheet)
        
        # Get the contents of spreadsheet
        list_of_lists = google_work_sheet.get_all_values()

        # Convert the results to a dictionary
        results = google_lookup_sync.convert_to_dict(list_of_lists)

        # Output the results
        self.output_results(results)

if __name__ == '__main__':
    InputGoogleSheetSearchCommand.execute()
