[google_spreadsheet://default]
* Configure an input for importing Google spreadsheets

spreadsheet = <value>
* The title of the spreadsheet

operation = <value>
* The operation to perform (should be either "import" or "export")
* Valid values are: import, export

worksheet = <value>
* The worksheet to import the data from

lookup_name = <value>
* The name of the lookup to export the data to

service_account_key_file = <value>
# DEPRECATED: the password ought to be stored in secure storage. Open the setup page to put the service account key into secure storage.
* The file name of the service account key to use when authenticating to Google
* The file must exist in the "service_account_keys" directory of the app (e.g. "/etc/apps/google_drive/service_account_keys")
* See the following for information on how to generate a service account key: http://gspread.readthedocs.org/en/latest/oauth2.html

interval = <value>
* Indicates how often to perform the import

only_if_changed = <value>
# NO LONGER USED: this is no longer supported since Google API v4 doesn't support it
* If true, then the import will only happen if the Google Worksheet has changed since it was last imported
* Valid values are: 0, 1, false, true
* Defaults to true

# The following are deprecated (use the service account key from now on)
google_login = <value>
* NO LONGER USED: do not use this since it is no longer supported and is ignored

google_password = <value>
* NO LONGER USED: do not use this since it is no longer supported and is ignored

[google_drive://default]
* Configure an input for importing data from Google Drive

service_account_key_file = <value>
* The file name of the service account key to use when authenticating to Google

interval = <value>
* Indicates how often to perform the import

only_if_changed = <value>
* If true, then the import will only happen if the Google Worksheet has changed since it was last imported
* Valid values are: 0, 1, false, true
* Defaults to true

path = <value>
* The file or directory in Google Drive to monitor

recurse = <value>
* If true, the input will go down the paths
