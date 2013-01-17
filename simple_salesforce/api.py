import requests
import json
import urllib

from login import login as SalesforceLogin


class SalesforceAPI(object):
    """Salesforce API Calls"""
    def __init__(self, username, password, securitytoken, sandbox=False):
        self.sessionId, self.sfInstance = SalesforceLogin(username, password, securitytoken, sandbox)
        self.headers = {
            "Content-Type":"application/json",
            "Authorization":"Bearer " + self.sessionId,
            "X-PrettyPrint":"1"
        }

    # SObject Handler
    def __getattr__(self, name):
        return SObject(name, self.sessionId, self.sfInstance)

    # Search Functions
    def search(self, search):
        search_string = urllib.quote_plus(search)
        return self._raw_search(search_string)

    def quick_search(self, search):
        search_string = urllib.quote_plus('FIND {%s}' % search)
        return self._raw_search(search_string)

    def _raw_search(self, search_string):
        result = requests.get('https://%s/services/data/v26.0/search/?q=%s' % (self.sfInstance, search_string), headers=self.headers)
        if result.status_code != 200:
            raise SalesforceGeneralError(result.content)
        json_result = result.json()
        if len(json_result) == 0:
            return None
        else:
            return json_result

    # Query Handler
    def query(self, query):
        query_string = urllib.quote_plus(query)
        result = requests.get('https://%s/services/data/v20.0/query/?q=%s' % (self.sfInstance, query_string), headers=self.headers)
        if result.status_code != 200:
            raise SalesforceGeneralError(result.content)
        return result.json()

    def query_more(self, nextRecordsId):
        result = requests.get('https://%s/services/data/v20.0/query/%s' % nextRecordsId, headers=self.headers)
        if result.status_code != 200:
            raise SalesforceGeneralError(result.content)
        return result.json()


class SObject(object):
    """A Salesforce.com Object"""

    def __init__(self, objectName, sessionId, sfInstance):
        self.sessionid = sessionId
        self.name = objectName
        self.baseurl = 'https://%s/services/data/v20.0/sobjects/%s/' % (sfInstance, objectName)

    def metadata(self):
        result = self._call_salesforce('GET',self.baseurl)
        return result.json()

    def describe(self):
        result = self._call_salesforce('GET','%sdescribe' % self.baseurl)
        return result.json()

    def get(self,recordId):
        result = self._call_salesforce('GET','%s%s' % (self.baseurl, recordId))
        return result.json()

    def create(self,data):
        result = self._call_salesforce('POST',self.baseurl, data=json.dumps(data))
        return result.json()

    def upsert(self,recordId,data):
        result = self._call_salesforce('PATCH','%s%s' % (self.baseurl, recordId), data=json.dumps(data))
        return result.status_code

    def update(self,recordId,data):
        result = self._call_salesforce('PATCH','%s%s' % (self.baseurl, recordId), data=json.dumps(data))
        return result.status_code

    def delete(self, recordId):
        result = self._call_salesforce('DELETE','%s%s' % (self.baseurl, recordId))
        return result.status_code

    def _call_salesforce(self, method, url, **kwargs):
        headers = {
            "Content-Type":"application/json",
            "Authorization":"Bearer " + self.sessionid,
            "X-PrettyPrint":"1"
        }
        result = requests.request(method, url, headers=headers, **kwargs)

        if result.status_code >= 300:
            if result.status_code == 300:
                raise SalesforceMoreThanOneRecord()
            elif result.status_code == 401:
                raise SalesforceExpiredSession()
            elif result.status_code == 403:
                raise SalesforceRefusedRequest()
            elif result.status_code == 404:
                raise SalesforceResourceNotFound('Resource %s Not Found' % (self.name))
            else:
                raise SalesforceGeneralError('Error Code %s' % result.status_code)

        return result


class SalesforceMoreThanOneRecord(Exception):
    """
    Error Code: 300
    The value returned when an external ID exists in more than one record. The response body contains the list of matching records.
    """
    pass

class SalesforceExpiredSession(Exception):
    """
    Error Code: 401
    The session ID or OAuth token used has expired or is invalid. The response body contains the message and errorCode.
    """

class SalesforceRefusedRequest(Exception):
    """
    Error Code: 403
    The request has been refused. Verify that the logged-in user has appropriate permissions.
    """

class SalesforceResourceNotFound(Exception):
    """
    Error Code: 404
    The requested resource couldn't be found. Check the URI for errors, and verify that there are no sharing issues.
    """
    pass

class SalesforceGeneralError(Exception):
    pass