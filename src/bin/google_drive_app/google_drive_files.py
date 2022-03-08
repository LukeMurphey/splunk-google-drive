

import sys, os
sys.path.append( os.path.join("bin", "google_drive_app") )

from PyPDF2 import PdfFileWriter, PdfFileReader

from googleapiclient.discovery import build
#from google_auth_oauthlib.flow import InstalledAppFlow
#from google.auth.transport.requests import Request()

"""
import sys, types, os
has_mfs = sys.version_info > (3, 5)
p = os.path.join(sys._getframe(1).f_locals['sitedir'], *('google',))
importlib = has_mfs and __import__('importlib.util')
has_mfs and __import__('importlib.machinery')


m = has_mfs and sys.modules.setdefault('google', importlib.util.module_from_spec(importlib.machinery.PathFinder.find_spec('google', [os.path.dirname(p)])))
m = m or sys.modules.setdefault('google', types.ModuleType('google'))
mp = (m or []) and m.__dict__.setdefault('__path__',[])
(p not in mp) and mp.append(p)
"""

"""
import sys, os
from splunk.appserver.mrsparkle.lib.util import make_splunkhome_path
# sys.path.insert(0, make_splunkhome_path(["etc", "apps", "google_drive_app", "bin", "lib", "python3.7", "site-packages"]))
sys.path.append( os.path.join("..", "src", "bin") )
sys.path.append( os.path.join("..", "src", "bin", "google_drive_app") )

source = os.path.join(os.path.join("..", "src", "bin", "google_drive_app"))
# p = os.path.join(os.path.join("..", "src", "bin", "google_drive_app", "google"))

from googleapiclient.discovery import build
#from google_auth_oauthlib.flow import InstalledAppFlow
#from google.auth.transport.requests import Request()

"""
# Py 3.5
"""
import importlib.util
sys.modules.setdefault('google', importlib.util.module_from_spec(importlib.machinery.PathFinder.find_spec('google', [os.path.dirname(p)])))
"""

# Not Py 3.5
"""
import types
sys.modules.setdefault('google', types.ModuleType('google'))
m = m or sys.modules.setdefault('google', types.ModuleType('google'))
mp = (m or []) and m.__dict__.setdefault('__path__',[])
(p not in mp) and mp.append(p)
"""


"""
from pydrive.auth import GoogleAuth
from pydrive.drive import GoogleDrive

gauth = GoogleAuth()
gauth.LocalWebserverAuth()
gauth.LoadCredentialsFile()

drive = GoogleDrive(gauth)


# LoadCredentialsFile
"""