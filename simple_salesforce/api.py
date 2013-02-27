import requests
import json
import urllib

from login import login as SalesforceLogin


class SalesforceAPI(object):
    """Salesforce API Instance"""
    def __init__(self, username, password, securitytoken, sandbox=False,
                 sf_version="23.0"):
        self.sessionId, self.sfInstance = SalesforceLogin(username, password,
                                                          securitytoken,
                                                          sandbox,
                                                          sf_version)
        self.sf_version = sf_version
        self.headers = {
            "Content-Type":"application/json",
            "Authorization":"Bearer " + self.sessionId,
            "X-PrettyPrint":"1"
        }
        self.base_url = ('https://{instance}/services/data/v{version}/'
                         .format(instance=self.sfInstance,
                                 version=self.sf_version))

    # SObject Handler
    def __getattr__(self, name):
        return SFType(name, self.sessionId, self.sfInstance, self.sf_version)

    # Search Functions
    def search(self, search):
        url = self.base_url + 'search/'

        # `requests` will correctly encode the query string passed as `params`
        params = { 'q': search }
        result = requests.get(url, headers=self.headers, params=params)
        if result.status_code != 200:
            raise SalesforceGeneralError(result.content)
        json_result = result.json()
        if len(json_result) == 0:
            return None
        else:
            return json_result

    def quick_search(self, search):
        search_string = 'FIND {{{search_string}}}'.format(search_string=search)
        return self.search(search_string)

    # Query Handler
    def query(self, query):
        url = self.base_url + 'query/'
        params = {'q': query}
        # `requests` will correctly encode the query string passed as `params`
        result = requests.get(url, headers=self.headers, params=params)
        if result.status_code != 200:
            raise SalesforceGeneralError(result.content)
        return result.json()

    def query_more(self, nextRecordsIdentifier, identifier_is_url=False):
        if identifier_is_url:
            url = 'https://{instance}{next_record_url}'.format(
                    instance=self.sfInstance,
                    next_record_url=next_records_identifer)
        else:
            url = self.base_url + 'query/{next_record_id}'
            url = url.format(next_record_id=next_records_identifer)
        result = requests.get(url, headers=self.headers)
        if result.status_code != 200:
            raise SalesforceGeneralError(result.content)
        return result.json()


class SFType(object):
    """An interface to a specific type of SObject"""

    def __init__(self, objectName, sessionId, sfInstance, sf_version):
        self.sessionid = sessionId
        self.name = objectName
        self.baseurl = 'https://{instance}/services/data/v{sf_version}/sobjects/{object_name}/'.format(
                instance=sfInstance,
                object_name=objectName,
                sf_version=sf_version)

    def metadata(self):
        result = self._call_salesforce('GET',self.baseurl)
        return result.json()

    def describe(self):
        result = self._call_salesforce('GET',self.baseurl + 'describe')
        return result.json()

    def get(self,recordId):
        result = self._call_salesforce('GET',self.baseurl + recordId)
        return result.json()

    def create(self,data):
        result = self._call_salesforce('POST',self.baseurl, data=json.dumps(data))
        return result.json()

    def upsert(self,recordId,data):
        result = self._call_salesforce('PATCH',self.baseurl + recordId, data=json.dumps(data))
        return result.status_code

    def update(self,recordId,data):
        result = self._call_salesforce('PATCH',self.baseurl + recordId, data=json.dumps(data))
        return result.status_code

    def delete(self, recordId):
        result = self._call_salesforce('DELETE',self.baseurl + recordId)
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
