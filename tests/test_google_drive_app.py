# coding=utf-8
import unittest
import sys
import os
import time
import re
import splunk.auth

sys.path.append( os.path.join("..", "src", "bin") )
sys.path.append( os.path.join("..", "src", "bin", "google_drive_app") )

from google_drive_app import GoogleLookupSync, gspread, lookupfiles

class SplunkGoogleDriveTestCase(unittest.TestCase):
    
    def get_property(self, pattern, file_contents, exception_msg):
        
        m = re.search(pattern, file_contents)
        
        if m is None:
            raise Exeption(exception_msg)
        else:
            value = m.groups()[0]
            
            return value
    
    def get_login_and_password(self):
        
        login = None
        password = None
        
        props_fh = open('../local.properties', 'r')
        
        props = props_fh.read()
        #props_fh.readlines()
        
        # Find the login and password entries
        login = self.get_property("value[.]test[.]google_login[ ]*[=](.*)", props, "Google login was not specified")
        password = self.get_property("value[.]test[.]google_password[ ]*[=](.*)", props, "Google password was not specified")
        
        return login, password
    
    def get_google_lookup_sync_instance(self):
        
        login, password = self.get_login_and_password()
        
        return GoogleLookupSync(login, password)
    
    def setUp(self):
        self.google_lookup_sync = self.get_google_lookup_sync_instance()

class TestLookupImport(SplunkGoogleDriveTestCase):

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
        self.assertEquals(os.path.getsize(created_file_path), 72, "Lookup file was not populated correctly")
        
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
    loader = unittest.TestLoader()
    suites = []
    suites.append(loader.loadTestsFromTestCase(TestLookupImport))
    
    unittest.TextTestRunner(verbosity=2).run(unittest.TestSuite(suites))