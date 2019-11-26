# This file is retained because older versions of the app need a valid Python file in order for upgrades to not break.
# This is due to the fact that Splunk 8.0+ requires that Python files be valid Python 3.7 code. Splunk doesn't remove
# old files when apps get upgraded. Thus, an old version of the controller code file will be retained when users upgrade
# to a newer version of the app that no longer uses the controller. This would cause an old Python 2 compatible file to
# be left around which would cause newer versions of Splunk to choke on the file.