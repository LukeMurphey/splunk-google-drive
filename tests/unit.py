# coding=utf-8
"""
This test case works with a file shared from Google Drive. To use it, you will need to:

1) Create a spreadsheet on Google Drive named "test_case_import" with a sheet named "data"
2) Create another spreadsheet on Google Drive named "test_case_export" with a sheet named "data"
3) Export a service key to an account that has been given read access to the spreadsheet
4) Declare the path to the service key in local.properties like this:
5) Create a lookup named "test_case_import.csv" in the search app (you can use the Lookup Editor to do this)
"""

import unittest
import sys
import os
import time
import re
import json
import splunk.auth

sys.path.append( os.path.join("..", "src", "bin") )
sys.path.append( os.path.join("..", "src", "bin", "google_drive_app") )

from google_drive_app import GoogleLookupSync, SpreadsheetInaccessible, gspread, lookupfiles

class SplunkGoogleDriveTestCase(unittest.TestCase):
    
    def get_property(self, pattern, file_contents, exception_msg):
        
        m = re.search(pattern, file_contents)
        
        if m is None:
            raise Exception(exception_msg)
        else:
            value = m.groups()[0]
            
            return value
    
    def get_credential_file_path(self):
        with open('../local.properties', 'r') as props_fh:
            props = props_fh.read()
            return self.get_property("value[.]test[.]oauth2_credentials[ ]*[=](.*)", props, "Google credentials were not specified")

    def get_credentials(self):
        # Find the path of the key
        credentials_path = self.get_credential_file_path()

        # Load the key file
        json_key = json.load(open(os.path.join("..", credentials_path)))
        
        # Return the credentials
        return json_key['client_email'], json_key['private_key']
    
    def get_google_lookup_sync_instance(self):
        
        key_file = self.get_credential_file_path()
        
        return GoogleLookupSync(key_file)
    
    def setUp(self):
        self.google_lookup_sync = self.get_google_lookup_sync_instance()

class TestLookupExport(SplunkGoogleDriveTestCase):
    
    def test_export_by_full_lookup_path(self):
        
        # Clear the file first
        self.clear_exported_file("test_case_export", "data")
        
        session_key = splunk.auth.getSessionKey(username='admin', password='changeme')
        namespace = "search"
        owner = "nobody"
        lookup_name = "test_case_import.csv"
        
        google_spreadsheet_name = "test_case_export"
        google_worksheet_name = "data"
        
        splunk_lookup_table = lookupfiles.SplunkLookupTableFile.get(lookupfiles.SplunkLookupTableFile.build_id(lookup_name, namespace, owner), sessionKey=session_key)
        lookup_full_path = splunk_lookup_table.path
        
        # Export the file
        self.google_lookup_sync.export_lookup_file_full_path(lookup_full_path, namespace, owner, google_spreadsheet_name, google_worksheet_name, session_key)
        
        # Now check the file
        google_spread_sheet = self.google_lookup_sync.open_google_spreadsheet(google_spreadsheet_name)
        worksheet = google_spread_sheet.worksheet(google_worksheet_name)
        
        # Check the columns
        self.assertEqual(worksheet.acell("A1").value, "name")
        self.assertEqual(worksheet.acell("B1").value, "value")
        
        # Check some of the rows
        self.assertEqual(worksheet.acell("A2").value, "one")
        self.assertEqual(worksheet.acell("B2").value, "1")
        self.assertEqual(worksheet.acell("A6").value, "five")
        self.assertEqual(worksheet.acell("B6").value, "5")
        
    def clear_exported_file(self, google_spreadsheet_name="test_case_export", google_worksheet_name="data"):
        
        google_spreadsheet = self.google_lookup_sync.open_google_spreadsheet(google_spreadsheet_name)
        worksheet = google_spreadsheet.worksheet(google_worksheet_name)
        
        worksheet.clear()
        
    def test_export_by_lookup_name(self):
        
        session_key = splunk.auth.getSessionKey(username='admin', password='changeme')
        lookup_name = "test_case_import.csv"
        namespace = "search"
        owner = "nobody"
        
        self.clear_exported_file("test_case_export", "data")
        
        # Export the file
        self.google_lookup_sync.export_lookup_file(lookup_name, namespace, owner, "test_case_export", "data", session_key)
        
        # Now check the file
        google_spread_sheet = self.google_lookup_sync.open_google_spreadsheet("test_case_export")
        worksheet = google_spread_sheet.worksheet("data")

        # Check the columns
        self.assertEqual(worksheet.acell("A1").value, "name")
        self.assertEqual(worksheet.acell("B1").value, "value")
        
        # Check some of the rows
        self.assertEqual(worksheet.acell("A2").value, "one")
        self.assertEqual(worksheet.acell("B2").value, "1")
        self.assertEqual(worksheet.acell("A6").value, "five")
        self.assertEqual(worksheet.acell("B6").value, "5")
        
class TestGoogleSync(SplunkGoogleDriveTestCase):
    
    def test_get_worksheet_updated_date(self):
        self.google_lookup_sync.get_worksheet_updated_date("test_case_import", "data")
        
    def test_no_auth_creds(self):
        
        def make_client_no_creds():
            GoogleLookupSync()
        
        self.assertRaises(ValueError, make_client_no_creds)

    def test_open_google_spreadsheet_no_title_no_key(self):
        self.assertRaises(ValueError, self.google_lookup_sync.open_google_spreadsheet)
    
    def test_open_google_spreadsheet_by_title(self):
        self.google_lookup_sync.open_google_spreadsheet(title="test_case_import")
        
    def test_open_google_spreadsheet_by_key(self):
        self.google_lookup_sync.open_google_spreadsheet(key="12lGRqELJlj9osKD08ASKO9B6A2G2SqOtrvHh4OR4-sA")
        
    def test_open_google_spreadsheet_doesnt_exist(self):
        self.assertRaises( SpreadsheetInaccessible, lambda: self.google_lookup_sync.open_google_spreadsheet(title="this_doesnt_exist") )

    def test_construct_with_json(self):

        key_string = None

        path = self.get_credential_file_path()

        if path is not None:
            with open(path, 'r') as json_file:
                key_string = json_file.read()

            google_sync = GoogleLookupSync.from_service_key_string(key_string)

            self.assertIsNotNone(google_sync)

    def test_get_or_make_sheet_if_necessary(self):
        
        google_spread_sheet = self.google_lookup_sync.open_google_spreadsheet(title="test_case_make_worksheet")
        worksheet_name = "created_by_unit_test"
        
        # Try to get the worksheet and delete it if it already exists
        try:
            worksheet = google_spread_sheet.worksheet(worksheet_name)
            google_spread_sheet.del_worksheet(worksheet)
        except gspread.WorksheetNotFound:
            pass
        
        # Make it
        self.google_lookup_sync.get_or_make_sheet_if_necessary(google_spread_sheet, worksheet_name)
    
        # Confirm that the sheet exists (if this throws an exception, then the test failed)
        worksheet = google_spread_sheet.worksheet(worksheet_name)
        
        # Now delete it for future tests
        google_spread_sheet.del_worksheet(worksheet)
    
    def test_get_lookup_stats(self):
        col_count, row_count = self.google_lookup_sync.get_lookup_stats("files/test.csv")

        self.assertEqual(col_count, 4)
        self.assertEqual(row_count, 12)
        
class TestLookupImport(SplunkGoogleDriveTestCase):
        
    def test_import_by_full_lookup_path(self):
        
        session_key = splunk.auth.getSessionKey(username='admin', password='changeme')
        namespace = "search"
        owner = "nobody"
        created_file_path = None
        
        with lookupfiles.get_temporary_lookup_file() as temp_file:
            
            created_file_path = temp_file.name
            
            # Import the file
            self.google_lookup_sync.import_to_lookup_file_full_path(created_file_path, namespace, owner, "test_case_import", "data", session_key, create_if_non_existent=True)
        
        # Check the results
        self.assertTrue(os.path.exists(created_file_path), "Lookup file did not get created")
        #print 'File imported successfully, size=%r, path=%r' % (os.path.getsize(created_file_path), created_file_path)
        self.assertGreaterEqual(os.path.getsize(created_file_path), 40, "Lookup file was not populated correctly (is %i bytes)" % (os.path.getsize(created_file_path)))
        
    def test_import_by_lookup_name(self):
        session_key = splunk.auth.getSessionKey(username='admin', password='changeme')
        lookup_name = "test_case_import.csv"
        namespace = "search"
        owner = "nobody"
        
        # Import the file
        self.google_lookup_sync.import_to_lookup_file(lookup_name, namespace, owner, "test_case_import", "data", session_key, create_if_non_existent=False)
        
        # Check the file
        destination_full_path = lookupfiles.SplunkLookupTableFile.get(lookupfiles.SplunkLookupTableFile.build_id(lookup_name, namespace, owner), sessionKey=session_key).path
        
        self.assertTrue(os.path.exists(destination_full_path), "File to import was not created properly")
        
if __name__ == "__main__":
    unittest.main()
