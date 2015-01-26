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

google_login = <value>
* The login to use when authenticating to Google

google_password = <value>
* The password to use when authenticating to Google

interval = <value>
* Indicates how often to perform the import

only_if_changed = <value>
* If true, then the import will only happen if the Google Worksheet has changed since it was last imported
* Valid values are: 0, 1, false, true
* Defaults to true