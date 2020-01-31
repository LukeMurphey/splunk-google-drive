================================================
Overview
================================================

This app provides a mechanism for importing and exporting data to/from Google drive.



================================================
Configuring Splunk
================================================


Step one: install the app into Splunk
----------------------------------------------------------------

Install this app into Splunk by doing the following:

  1. Log in to Splunk Web and navigate to "Apps » Manage Apps" via the app dropdown at the top left of Splunk's user interface
  2. Click the "install app from file" button
  3. Upload the file by clicking "Choose file" and selecting the app
  4. Click upload
  5. Restart Splunk if a dialog asks you to


Step two: configure the app with a service account
----------------------------------------------------------------

You will need to create an OAuth2 service account key from Google and assign the service account permission to read and/or write to the files accordingly. See the following for specific instructions:

     http://lukemurphey.net/projects/splunk-google-docs/wiki/How_to_setup_app



================================================
Adding a new input/output
================================================

Once the app is installed, you can use the app by configuring a new input:
  1. Navigate to "Settings » Data Inputs" at the menu at the top of Splunk's user interface.
  2. Click "Google Spreadsheet"
  3. Click "New" to make a new instance of an input



================================================
Getting Support
================================================

Go to the following website if you need support:

     http://splunk-base.splunk.com/apps/2630/answers/

You can access the source-code and get technical details about the app at:

     https://github.com/LukeMurphey/splunk-google-drive




================================================
Known Issues
================================================

* This app cannot be installed with the RADIUS Authentication app (https://splunkbase.splunk.com/app/981/) due to an incompatibility with the six library. If this is an issue, report it and I'll implement a workaround.
* If you change the service account key, existing inputs will not recognize the new key until they are restarted. You can either disable and then re-enable each input or restart Splunk.



================================================
Change History
================================================

+---------+------------------------------------------------------------------------------------------------------------------+
| Version |  Changes                                                                                                         |
+---------+------------------------------------------------------------------------------------------------------------------+
| 0.5     | Initial release                                                                                                  |
|---------|------------------------------------------------------------------------------------------------------------------|
| 0.6     | Added sourcetyping of the modular input logs                                                                     |
|         | Fixed issue where exporting did not work                                                                         |
|---------|------------------------------------------------------------------------------------------------------------------|
| 1.0     | Added support for oauth2 service account credentials                                                             |
|---------|------------------------------------------------------------------------------------------------------------------|
| 1.0.1   | Fixed incompatibility with GoogleAppsForSplunk                                                                   |
|---------|------------------------------------------------------------------------------------------------------------------|
| 1.0.2   | Fixed error on setup page that occurred when no key was defined                                                  |
|---------|------------------------------------------------------------------------------------------------------------------|
| 1.0.3   | Fixed issue preventing the app from working on Splunk 8.0.0                                                      |
|---------|------------------------------------------------------------------------------------------------------------------|
| 2.0     | Updating to the newer version of the Google API                                                                  |
|         | Added improved messaging when uploading a key fails                                                              |
|         | Added support for Python 3                                                                                       |
|         | Added the view "google_drive_logs" to aid in troubleshooting                                                     |
|         | Improved messaging when the user configures an input without providing the service account key                   |
|         | Google Drive updates are now done in batch in order to reduce API usage and improve performance                  |
|         | Service account key is now stored in Splunk's secure password storage system                                     |
|         | Added button on setup screen that will migrate the service account key to secure storage                         |
|---------|------------------------------------------------------------------------------------------------------------------|
| 2.0.1   | Specifying inputs.conf attributes that are not longer supported or deprecated                                    |
|         | Fixing incorrect entry in props.conf                                                                             |
|         | Improving app certification                                                                                      |
|---------|------------------------------------------------------------------------------------------------------------------|
| 2.0.2   | Fixing issue where app would sometimes fail due to an older version of the requests library                      |
|---------|------------------------------------------------------------------------------------------------------------------|
| 2.0.3   | Fixing issue where app would fail when checking for SHC support                                                  |
|---------|------------------------------------------------------------------------------------------------------------------|
| 2.0.4   | Fixing issue where app would fail when it a file-system key didn't exist                                         |
+---------+------------------------------------------------------------------------------------------------------------------+
