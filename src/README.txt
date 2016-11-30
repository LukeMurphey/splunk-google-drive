================================================
Overview
================================================

This app provides a mechanism for importing and exporting data to/from Google drive.



================================================
Configuring Splunk
================================================

----------------------------------------------------------------
Step one: configure the app with a service account
----------------------------------------------------------------

You will need to create an OAuth2 service account key from Google and assign the service account permission to read and/or write to the files accordingly. See the following for specific instructions:

     http://lukemurphey.net/projects/splunk-google-docs/wiki/How_to_setup_app

----------------------------------------------------------------
Step two: give the service account permission to the spreadsheet
----------------------------------------------------------------

You will need to give the service account permission to read and/or write to the spreadsheet. See http://lukemurphey.net/projects/splunk-google-docs/wiki/How_to_setup_app.

----------------------------------------------------------------
Step three: create input
----------------------------------------------------------------

This app exposes a new input type that can be configured in the Splunk Manager. To configure it, create a new input in the Manager under Data inputs » Google Spreadsheet.



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
+---------+------------------------------------------------------------------------------------------------------------------+
