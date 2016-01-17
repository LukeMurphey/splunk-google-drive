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
* The file name of the service account key to use when authenticating to Google
* The file must exist in the "service_account_keys" directory of the app (e.g. "/etc/apps/google_drive/service_account_keys")
* See the following for information on how to generate a service account key: http://gspread.readthedocs.org/en/latest/oauth2.html

interval = <value>
* Indicates how often to perform the import

only_if_changed = <value>
* If true, then the import will only happen if the Google Worksheet has changed since it was last imported
* Valid values are: 0, 1, false, true
* Defaults to true