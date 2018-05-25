import splunk
import splunk.admin as admin
import splunk.rest
import json
import sys


class GoogleDriveApp(admin.MConfigHandler):

    def logger(message):
        sys.stderr.write(message.strip() + "\n")

    def setup(self):
        if self.requestedAction == admin.ACTION_EDIT:
            for arg in ['keys', 'method']:
                self.supportedArgs.addOptArg(arg)


    def handleList(self, confInfo):

        my_app = "google_drive"

        try:

            sessionKey = self.getSessionKey()
            get_path = '/servicesNS/nobody/google_drive/storage/passwords?output_mode=json'
            serverResponse = splunk.rest.simpleRequest(get_path, sessionKey=sessionKey, method='GET',
                                                           raiseAllErrors=True)
            jsonObj = json.loads(serverResponse[1])

            i = 0

            for realm_key, realm_value in jsonObj.iteritems():
                if realm_key == "entry":
                    while i < len(realm_value):
                        for entry_key, entry_val in realm_value[i].iteritems():
                            if entry_key == "content":
                                app_context = realm_value[i]["acl"]["app"]
                                realm = entry_val['realm']
                                if app_context == my_app:
                                    for k, v in entry_val.iteritems():
                                        if k != "clear_password":
                                            confInfo[realm].append(k, v)
                                i += 1

        except Exception, e:
            raise Exception("Could not GET credentials: %s" % (str(e)))

    def handleEdit(self, confInfo):
        name = self.callerArgs.id
        args = self.callerArgs

        method_obj = json.loads(args['method'][0])
        keys = json.loads(args['keys'][0])
        entity_name = keys['apiKeyName']
        method = method_obj['type']

        if method == 'post':

            entity_value = keys['apiKeyValue']

            try:
                sessionKey = self.getSessionKey()
                post_path = '/servicesNS/nobody/google_drive/storage/passwords?output_mode=json'
                creds = {"name": entity_name, "password": entity_value, "realm": entity_name}
                serverResponse, serverContent = splunk.rest.simpleRequest(post_path, sessionKey=sessionKey, postargs=creds, method='POST',
                                                          raiseAllErrors=True)


            except Exception, e:
                raise Exception("Could not post credentials: %s" % (str(e)))

        elif method == 'delete':

            entity_url_encode = entity_name.replace(" ", "%20")
            entity = entity_url_encode + ":" + entity_url_encode + ":"

            try:
                sessionKey = self.getSessionKey()
                post_path = '/servicesNS/nobody/google_drive/storage/passwords/' + entity
                serverResponse, serverContent = splunk.rest.simpleRequest(post_path, sessionKey=sessionKey, method='DELETE',
                                                          raiseAllErrors=True)
            except Exception, e:
                raise Exception("Could not post credentials: %s" % (str(e)))


# initialize the handler
admin.init(GoogleDriveApp, admin.CONTEXT_NONE)
