================================================
Overview
================================================

This app provides a mechanism for importing and exporting data to/from Google drive.



================================================
Configuring Splunk
================================================

Step one: generate OAuth2 service account key

1) Head to Google Developers Console (https://console.developers.google.com/project) and create a new project (or select the one you have.)
2) Under “API & auth”, in the API enable “Drive API”.
3) Go to “Credentials” and choose “New Credentials > Service Account Key”. This will generate a JSON key file.

Step two: upload servie account key to Splunk

You will need to perform the app setup in order to define the service account key that you want to use. The app will ask you to set it up the first time you run it. When you come to this page, upload the key to Splunk and press save.

Step three: create input

This app exposes a new input type that can be configured in the Splunk Manager. To configure it, create a new input in the Manager under Data inputs » Google Spreadsheet.



================================================
Getting Support
================================================

Go to the following website if you need support:

     http://splunk-base.splunk.com/apps/2630/answers/

You can access the source-code and get technical details about the app at:

     https://github.com/LukeMurphey/splunk-google-drive



================================================
Change History
================================================

+---------+------------------------------------------------------------------------------------------------------------------+
| Version |  Changes                                                                                                         |
+---------+------------------------------------------------------------------------------------------------------------------+
| 0.5     | Initial release                                                                                                  |
+---------+------------------------------------------------------------------------------------------------------------------+
| 0.6     | Added sourcetyping of the modular input logs                                                                     |
|         | Fixed issue where exporting did not work                                                                         |
+---------+------------------------------------------------------------------------------------------------------------------+
| 1.0     | Added support for oauth2 service account credentials                                                             |
+---------+------------------------------------------------------------------------------------------------------------------+
