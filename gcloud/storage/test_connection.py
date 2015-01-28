# Copyright 2014 Google Inc. All rights reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import unittest2


class TestConnection(unittest2.TestCase):

    def _getTargetClass(self):
        from gcloud.storage.connection import Connection
        return Connection

    def _makeOne(self, *args, **kw):
        return self._getTargetClass()(*args, **kw)

    def test_ctor_defaults(self):
        PROJECT = 'project'
        conn = self._makeOne(PROJECT)
        self.assertEqual(conn.project, PROJECT)
        self.assertEqual(conn.credentials, None)

    def test_ctor_explicit(self):
        PROJECT = 'project'
        creds = object()
        conn = self._makeOne(PROJECT, creds)
        self.assertEqual(conn.project, PROJECT)
        self.assertTrue(conn.credentials is creds)

    def test_http_w_existing(self):
        PROJECT = 'project'
        conn = self._makeOne(PROJECT)
        conn._http = http = object()
        self.assertTrue(conn.http is http)

    def test_http_wo_creds(self):
        import httplib2
        PROJECT = 'project'
        conn = self._makeOne(PROJECT)
        self.assertTrue(isinstance(conn.http, httplib2.Http))

    def test_http_w_creds(self):
        import httplib2
        PROJECT = 'project'
        authorized = object()

        class Creds(object):
            def authorize(self, http):
                self._called_with = http
                return authorized
        creds = Creds()
        conn = self._makeOne(PROJECT, creds)
        self.assertTrue(conn.http is authorized)
        self.assertTrue(isinstance(creds._called_with, httplib2.Http))

    def test___iter___empty(self):
        PROJECT = 'project'
        conn = self._makeOne(PROJECT)
        URI = '/'.join([
            conn.API_BASE_URL,
            'storage',
            conn.API_VERSION,
            'b?project=%s' % PROJECT,
        ])
        http = conn._http = Http(
            {'status': '200', 'content-type': 'application/json'},
            '{}',
        )
        blobs = list(conn)
        self.assertEqual(len(blobs), 0)
        self.assertEqual(http._called_with['method'], 'GET')
        self.assertEqual(http._called_with['uri'], URI)

    def test___iter___non_empty(self):
        PROJECT = 'project'
        BLOB_NAME = 'blob-name'
        conn = self._makeOne(PROJECT)
        URI = '/'.join([
            conn.API_BASE_URL,
            'storage',
            conn.API_VERSION,
            'b?project=%s' % PROJECT,
        ])
        http = conn._http = Http(
            {'status': '200', 'content-type': 'application/json'},
            '{"items": [{"name": "%s"}]}' % BLOB_NAME,
        )
        blobs = list(conn)
        self.assertEqual(len(blobs), 1)
        self.assertEqual(blobs[0].name, BLOB_NAME)
        self.assertEqual(http._called_with['method'], 'GET')
        self.assertEqual(http._called_with['uri'], URI)

    def test___contains___miss(self):
        PROJECT = 'project'
        NONESUCH = 'nonesuch'
        conn = self._makeOne(PROJECT)
        URI = '/'.join([
            conn.API_BASE_URL,
            'storage',
            conn.API_VERSION,
            'b',
            'nonesuch?project=%s' % PROJECT,
        ])
        http = conn._http = Http(
            {'status': '404', 'content-type': 'application/json'},
            '{}',
        )
        self.assertFalse(NONESUCH in conn)
        self.assertEqual(http._called_with['method'], 'GET')
        self.assertEqual(http._called_with['uri'], URI)

    def test___contains___hit(self):
        PROJECT = 'project'
        BLOB_NAME = 'blob-name'
        conn = self._makeOne(PROJECT)
        URI = '/'.join([
            conn.API_BASE_URL,
            'storage',
            conn.API_VERSION,
            'b',
            '%s?project=%s' % (BLOB_NAME, PROJECT),
        ])
        http = conn._http = Http(
            {'status': '200', 'content-type': 'application/json'},
            '{"name": "%s"}' % BLOB_NAME,
        )
        self.assertTrue(BLOB_NAME in conn)
        self.assertEqual(http._called_with['method'], 'GET')
        self.assertEqual(http._called_with['uri'], URI)

    def test_build_api_url_no_extra_query_params(self):
        PROJECT = 'project'
        conn = self._makeOne(PROJECT)
        URI = '/'.join([
            conn.API_BASE_URL,
            'storage',
            conn.API_VERSION,
            'foo?project=%s' % PROJECT,
        ])
        self.assertEqual(conn.build_api_url('/foo'), URI)

    def test_build_api_url_w_extra_query_params(self):
        from urlparse import parse_qsl
        from urlparse import urlsplit
        PROJECT = 'project'
        conn = self._makeOne(PROJECT)
        uri = conn.build_api_url('/foo', {'bar': 'baz'})
        scheme, netloc, path, qs, _ = urlsplit(uri)
        self.assertEqual('%s://%s' % (scheme, netloc), conn.API_BASE_URL)
        self.assertEqual(path,
                         '/'.join(['', 'storage', conn.API_VERSION, 'foo']))
        parms = dict(parse_qsl(qs))
        self.assertEqual(parms['project'], PROJECT)
        self.assertEqual(parms['bar'], 'baz')

    def test_build_api_url_w_upload(self):
        PROJECT = 'project'
        conn = self._makeOne(PROJECT)
        URI = '/'.join([
            conn.API_BASE_URL,
            'upload',
            'storage',
            conn.API_VERSION,
            'foo?project=%s' % PROJECT,
        ])
        self.assertEqual(conn.build_api_url('/foo', upload=True), URI)

    def test_make_request_no_data_no_content_type_no_headers(self):
        PROJECT = 'project'
        conn = self._makeOne(PROJECT)
        URI = 'http://example.com/test'
        http = conn._http = Http(
            {'status': '200', 'content-type': 'text/plain'},
            '',
        )
        headers, content = conn.make_request('GET', URI)
        self.assertEqual(headers['status'], '200')
        self.assertEqual(headers['content-type'], 'text/plain')
        self.assertEqual(content, '')
        self.assertEqual(http._called_with['method'], 'GET')
        self.assertEqual(http._called_with['uri'], URI)
        self.assertEqual(http._called_with['body'], None)
        expected_headers = {
            'Accept-Encoding': 'gzip',
            'Content-Length': 0,
            'User-Agent': conn.USER_AGENT,
        }
        self.assertEqual(http._called_with['headers'], expected_headers)

    def test_make_request_w_data_no_extra_headers(self):
        PROJECT = 'project'
        conn = self._makeOne(PROJECT)
        URI = 'http://example.com/test'
        http = conn._http = Http(
            {'status': '200', 'content-type': 'text/plain'},
            '',
        )
        conn.make_request('GET', URI, {}, 'application/json')
        self.assertEqual(http._called_with['method'], 'GET')
        self.assertEqual(http._called_with['uri'], URI)
        self.assertEqual(http._called_with['body'], {})
        expected_headers = {
            'Accept-Encoding': 'gzip',
            'Content-Length': 0,
            'Content-Type': 'application/json',
            'User-Agent': conn.USER_AGENT,
        }
        self.assertEqual(http._called_with['headers'], expected_headers)

    def test_make_request_w_extra_headers(self):
        PROJECT = 'project'
        conn = self._makeOne(PROJECT)
        URI = 'http://example.com/test'
        http = conn._http = Http(
            {'status': '200', 'content-type': 'text/plain'},
            '',
        )
        conn.make_request('GET', URI, headers={'X-Foo': 'foo'})
        self.assertEqual(http._called_with['method'], 'GET')
        self.assertEqual(http._called_with['uri'], URI)
        self.assertEqual(http._called_with['body'], None)
        expected_headers = {
            'Accept-Encoding': 'gzip',
            'Content-Length': 0,
            'X-Foo': 'foo',
            'User-Agent': conn.USER_AGENT,
        }
        self.assertEqual(http._called_with['headers'], expected_headers)

    def test_api_request_defaults(self):
        PROJECT = 'project'
        PATH = '/path/required'
        conn = self._makeOne(PROJECT)
        URI = '/'.join([
            conn.API_BASE_URL,
            'storage',
            '%s%s?project=%s' % (conn.API_VERSION, PATH, PROJECT),
        ])
        http = conn._http = Http(
            {'status': '200', 'content-type': 'application/json'},
            '{}',
        )
        self.assertEqual(conn.api_request('GET', PATH), {})
        self.assertEqual(http._called_with['method'], 'GET')
        self.assertEqual(http._called_with['uri'], URI)
        self.assertEqual(http._called_with['body'], None)
        expected_headers = {
            'Accept-Encoding': 'gzip',
            'Content-Length': 0,
            'User-Agent': conn.USER_AGENT,
        }
        self.assertEqual(http._called_with['headers'], expected_headers)

    def test_api_request_w_non_json_response(self):
        PROJECT = 'project'
        conn = self._makeOne(PROJECT)
        conn._http = Http(
            {'status': '200', 'content-type': 'text/plain'},
            'CONTENT',
        )

        self.assertRaises(TypeError, conn.api_request, 'GET', '/')

    def test_api_request_wo_json_expected(self):
        PROJECT = 'project'
        conn = self._makeOne(PROJECT)
        conn._http = Http(
            {'status': '200', 'content-type': 'text/plain'},
            'CONTENT',
        )
        self.assertEqual(conn.api_request('GET', '/', expect_json=False),
                         'CONTENT')

    def test_api_request_w_query_params(self):
        from urlparse import parse_qsl
        from urlparse import urlsplit
        PROJECT = 'project'
        conn = self._makeOne(PROJECT)
        http = conn._http = Http(
            {'status': '200', 'content-type': 'application/json'},
            '{}',
        )
        self.assertEqual(conn.api_request('GET', '/', {'foo': 'bar'}), {})
        self.assertEqual(http._called_with['method'], 'GET')
        uri = http._called_with['uri']
        scheme, netloc, path, qs, _ = urlsplit(uri)
        self.assertEqual('%s://%s' % (scheme, netloc), conn.API_BASE_URL)
        self.assertEqual(path,
                         '/'.join(['', 'storage', conn.API_VERSION, '']))
        parms = dict(parse_qsl(qs))
        self.assertEqual(parms['project'], PROJECT)
        self.assertEqual(parms['foo'], 'bar')
        self.assertEqual(http._called_with['body'], None)
        expected_headers = {
            'Accept-Encoding': 'gzip',
            'Content-Length': 0,
            'User-Agent': conn.USER_AGENT,
        }
        self.assertEqual(http._called_with['headers'], expected_headers)

    def test_api_request_w_data(self):
        import json
        PROJECT = 'project'
        DATA = {'foo': 'bar'}
        DATAJ = json.dumps(DATA)
        conn = self._makeOne(PROJECT)
        URI = '/'.join([
            conn.API_BASE_URL,
            'storage',
            conn.API_VERSION,
            '?project=%s' % PROJECT,
        ])
        http = conn._http = Http(
            {'status': '200', 'content-type': 'application/json'},
            '{}',
        )
        self.assertEqual(conn.api_request('POST', '/', data=DATA), {})
        self.assertEqual(http._called_with['method'], 'POST')
        self.assertEqual(http._called_with['uri'], URI)
        self.assertEqual(http._called_with['body'], DATAJ)
        expected_headers = {
            'Accept-Encoding': 'gzip',
            'Content-Length': len(DATAJ),
            'Content-Type': 'application/json',
            'User-Agent': conn.USER_AGENT,
        }
        self.assertEqual(http._called_with['headers'], expected_headers)

    def test_api_request_w_404(self):
        from gcloud.exceptions import NotFound
        PROJECT = 'project'
        conn = self._makeOne(PROJECT)
        conn._http = Http(
            {'status': '404', 'content-type': 'text/plain'},
            '{}'
        )
        self.assertRaises(NotFound, conn.api_request, 'GET', '/')

    def test_api_request_w_500(self):
        from gcloud.exceptions import InternalServerError
        PROJECT = 'project'
        conn = self._makeOne(PROJECT)
        conn._http = Http(
            {'status': '500', 'content-type': 'text/plain'},
            '{}',
        )
        self.assertRaises(InternalServerError, conn.api_request, 'GET', '/')

    def test_get_all_buckets_empty(self):
        PROJECT = 'project'
        conn = self._makeOne(PROJECT)
        URI = '/'.join([
            conn.API_BASE_URL,
            'storage',
            conn.API_VERSION,
            'b?project=%s' % PROJECT,
        ])
        http = conn._http = Http(
            {'status': '200', 'content-type': 'application/json'},
            '{}',
        )
        blobs = conn.get_all_buckets()
        self.assertEqual(len(blobs), 0)
        self.assertEqual(http._called_with['method'], 'GET')
        self.assertEqual(http._called_with['uri'], URI)

    def test_get_all_buckets_non_empty(self):
        PROJECT = 'project'
        BLOB_NAME = 'blob-name'
        conn = self._makeOne(PROJECT)
        URI = '/'.join([
            conn.API_BASE_URL,
            'storage',
            conn.API_VERSION,
            'b?project=%s' % PROJECT,
        ])
        http = conn._http = Http(
            {'status': '200', 'content-type': 'application/json'},
            '{"items": [{"name": "%s"}]}' % BLOB_NAME,
        )
        blobs = conn.get_all_buckets()
        self.assertEqual(len(blobs), 1)
        self.assertEqual(blobs[0].name, BLOB_NAME)
        self.assertEqual(http._called_with['method'], 'GET')
        self.assertEqual(http._called_with['uri'], URI)

    def test_get_bucket_miss(self):
        from gcloud.exceptions import NotFound
        PROJECT = 'project'
        NONESUCH = 'nonesuch'
        conn = self._makeOne(PROJECT)
        URI = '/'.join([
            conn.API_BASE_URL,
            'storage',
            conn.API_VERSION,
            'b',
            'nonesuch?project=%s' % PROJECT,
        ])
        http = conn._http = Http(
            {'status': '404', 'content-type': 'application/json'},
            '{}',
        )
        self.assertRaises(NotFound, conn.get_bucket, NONESUCH)
        self.assertEqual(http._called_with['method'], 'GET')
        self.assertEqual(http._called_with['uri'], URI)

    def test_get_bucket_hit(self):
        from gcloud.storage.bucket import Bucket
        PROJECT = 'project'
        BLOB_NAME = 'blob-name'
        conn = self._makeOne(PROJECT)
        URI = '/'.join([
            conn.API_BASE_URL,
            'storage',
            conn.API_VERSION,
            'b',
            '%s?project=%s' % (BLOB_NAME, PROJECT),
        ])
        http = conn._http = Http(
            {'status': '200', 'content-type': 'application/json'},
            '{"name": "%s"}' % BLOB_NAME,
        )
        bucket = conn.get_bucket(BLOB_NAME)
        self.assertTrue(isinstance(bucket, Bucket))
        self.assertTrue(bucket.connection is conn)
        self.assertEqual(bucket.name, BLOB_NAME)
        self.assertEqual(http._called_with['method'], 'GET')
        self.assertEqual(http._called_with['uri'], URI)

    def test_lookup_miss(self):
        PROJECT = 'project'
        NONESUCH = 'nonesuch'
        conn = self._makeOne(PROJECT)
        URI = '/'.join([
            conn.API_BASE_URL,
            'storage',
            conn.API_VERSION,
            'b',
            'nonesuch?project=%s' % PROJECT,
        ])
        http = conn._http = Http(
            {'status': '404', 'content-type': 'application/json'},
            '{}',
        )
        self.assertEqual(conn.lookup(NONESUCH), None)
        self.assertEqual(http._called_with['method'], 'GET')
        self.assertEqual(http._called_with['uri'], URI)

    def test_lookup_hit(self):
        from gcloud.storage.bucket import Bucket
        PROJECT = 'project'
        BLOB_NAME = 'blob-name'
        conn = self._makeOne(PROJECT)
        URI = '/'.join([
            conn.API_BASE_URL,
            'storage',
            conn.API_VERSION,
            'b',
            '%s?project=%s' % (BLOB_NAME, PROJECT),
        ])
        http = conn._http = Http(
            {'status': '200', 'content-type': 'application/json'},
            '{"name": "%s"}' % BLOB_NAME,
        )
        bucket = conn.lookup(BLOB_NAME)
        self.assertTrue(isinstance(bucket, Bucket))
        self.assertTrue(bucket.connection is conn)
        self.assertEqual(bucket.name, BLOB_NAME)
        self.assertEqual(http._called_with['method'], 'GET')
        self.assertEqual(http._called_with['uri'], URI)

    def test_create_bucket_ok(self):
        from gcloud.storage.bucket import Bucket
        PROJECT = 'project'
        BLOB_NAME = 'blob-name'
        conn = self._makeOne(PROJECT)
        URI = '/'.join([
            conn.API_BASE_URL,
            'storage',
            conn.API_VERSION,
            'b?project=%s' % PROJECT,
            ])
        http = conn._http = Http(
            {'status': '200', 'content-type': 'application/json'},
            '{"name": "%s"}' % BLOB_NAME,
        )
        bucket = conn.create_bucket(BLOB_NAME)
        self.assertTrue(isinstance(bucket, Bucket))
        self.assertTrue(bucket.connection is conn)
        self.assertEqual(bucket.name, BLOB_NAME)
        self.assertEqual(http._called_with['method'], 'POST')
        self.assertEqual(http._called_with['uri'], URI)

    def test_delete_bucket_defaults_miss(self):
        _deleted_blobs = []

        class _Bucket(object):

            def __init__(self, name):
                self._name = name
                self.path = '/b/' + name

        PROJECT = 'project'
        BLOB_NAME = 'blob-name'
        conn = self._makeOne(PROJECT)
        URI = '/'.join([
            conn.API_BASE_URL,
            'storage',
            conn.API_VERSION,
            'b',
            '%s?project=%s' % (BLOB_NAME, PROJECT),
        ])
        http = conn._http = Http(
            {'status': '200', 'content-type': 'application/json'},
            '{}',
        )

        def _new_bucket(name):
            return _Bucket(name)

        conn.new_bucket = _new_bucket
        self.assertEqual(conn.delete_bucket(BLOB_NAME), True)
        self.assertEqual(_deleted_blobs, [])
        self.assertEqual(http._called_with['method'], 'DELETE')
        self.assertEqual(http._called_with['uri'], URI)

    def test_delete_bucket_force_True(self):
        _deleted_blobs = []

        class _Blob(object):

            def __init__(self, name):
                self._name = name

            def delete(self):
                _deleted_blobs.append(self._name)

        class _Bucket(object):

            def __init__(self, name):
                self._name = name
                self.path = '/b/' + name

            def __iter__(self):
                return iter([_Blob(x) for x in ('foo', 'bar')])

        PROJECT = 'project'
        BLOB_NAME = 'blob-name'
        conn = self._makeOne(PROJECT)
        URI = '/'.join([
            conn.API_BASE_URL,
            'storage',
            conn.API_VERSION,
            'b',
            '%s?project=%s' % (BLOB_NAME, PROJECT),
        ])
        http = conn._http = Http(
            {'status': '200', 'content-type': 'application/json'},
            '{}',
        )

        def _new_bucket(name):
            return _Bucket(name)

        conn.new_bucket = _new_bucket
        self.assertEqual(conn.delete_bucket(BLOB_NAME, True), True)
        self.assertEqual(_deleted_blobs, ['foo', 'bar'])
        self.assertEqual(http._called_with['method'], 'DELETE')
        self.assertEqual(http._called_with['uri'], URI)

    def test_new_bucket_w_existing(self):
        from gcloud.storage.bucket import Bucket
        PROJECT = 'project'
        BLOB_NAME = 'blob-name'
        conn = self._makeOne(PROJECT)
        existing = Bucket(self, BLOB_NAME)
        self.assertTrue(conn.new_bucket(existing) is existing)

    def test_new_bucket_w_blob(self):
        from gcloud.storage.bucket import Bucket
        PROJECT = 'project'
        BLOB_NAME = 'blob-name'
        conn = self._makeOne(PROJECT)
        bucket = conn.new_bucket(BLOB_NAME)
        self.assertTrue(isinstance(bucket, Bucket))
        self.assertTrue(bucket.connection is conn)
        self.assertEqual(bucket.name, BLOB_NAME)

    def test_new_bucket_w_invalid(self):
        PROJECT = 'project'
        conn = self._makeOne(PROJECT)
        self.assertRaises(TypeError, conn.new_bucket, object())

    def test_generate_signed_url_w_expiration_int(self):
        import base64
        import urlparse
        from gcloud._testing import _Monkey
        from gcloud.test_credentials import _Credentials
        from gcloud.storage import connection as MUT

        ENDPOINT = 'http://api.example.com'
        RESOURCE = '/name/path'
        PROJECT = 'project'
        SIGNED = base64.b64encode('DEADBEEF')
        conn = self._makeOne(PROJECT, _Credentials())
        conn.API_ACCESS_ENDPOINT = ENDPOINT

        def _get_signed_query_params(*args):
            credentials, expiration = args[:2]
            return {
                'GoogleAccessId': credentials.service_account_name,
                'Expires': str(expiration),
                'Signature': SIGNED,
            }

        with _Monkey(MUT, _get_signed_query_params=_get_signed_query_params):
            url = conn.generate_signed_url(RESOURCE, 1000)

        scheme, netloc, path, qs, frag = urlparse.urlsplit(url)
        self.assertEqual(scheme, 'http')
        self.assertEqual(netloc, 'api.example.com')
        self.assertEqual(path, RESOURCE)
        params = urlparse.parse_qs(qs)
        self.assertEqual(len(params), 3)
        self.assertEqual(params['Signature'], [SIGNED])
        self.assertEqual(params['Expires'], ['1000'])
        self.assertEqual(params['GoogleAccessId'],
                         [_Credentials.service_account_name])
        self.assertEqual(frag, '')


class Test__BucketIterator(unittest2.TestCase):

    def _getTargetClass(self):
        from gcloud.storage.connection import _BucketIterator
        return _BucketIterator

    def _makeOne(self, *args, **kw):
        return self._getTargetClass()(*args, **kw)

    def test_ctor(self):
        connection = object()
        iterator = self._makeOne(connection)
        self.assertTrue(iterator.connection is connection)
        self.assertEqual(iterator.path, '/b')
        self.assertEqual(iterator.page_number, 0)
        self.assertEqual(iterator.next_page_token, None)

    def test_get_items_from_response_empty(self):
        connection = object()
        iterator = self._makeOne(connection)
        self.assertEqual(list(iterator.get_items_from_response({})), [])

    def test_get_items_from_response_non_empty(self):
        from gcloud.storage.bucket import Bucket
        BLOB_NAME = 'blob-name'
        response = {'items': [{'name': BLOB_NAME}]}
        connection = object()
        iterator = self._makeOne(connection)
        buckets = list(iterator.get_items_from_response(response))
        self.assertEqual(len(buckets), 1)
        bucket = buckets[0]
        self.assertTrue(isinstance(bucket, Bucket))
        self.assertTrue(bucket.connection is connection)
        self.assertEqual(bucket.name, BLOB_NAME)


class Test__get_expiration_seconds(unittest2.TestCase):

    def _callFUT(self, expiration):
        from gcloud.storage.connection import _get_expiration_seconds

        return _get_expiration_seconds(expiration)

    def _utc_seconds(self, when):
        import calendar

        return int(calendar.timegm(when.timetuple()))

    def test__get_expiration_seconds_w_invalid(self):
        self.assertRaises(TypeError, self._callFUT, object())
        self.assertRaises(TypeError, self._callFUT, None)

    def test__get_expiration_seconds_w_int(self):
        self.assertEqual(self._callFUT(123), 123)

    def test__get_expiration_seconds_w_long(self):
        try:
            long
        except NameError:  # pragma: NO COVER Py3K
            pass
        else:
            self.assertEqual(self._callFUT(long(123)), 123)

    def test__get_expiration_w_naive_datetime(self):
        import datetime

        expiration_no_tz = datetime.datetime(2004, 8, 19, 0, 0, 0, 0)
        utc_seconds = self._utc_seconds(expiration_no_tz)
        self.assertEqual(self._callFUT(expiration_no_tz), utc_seconds)

    def test__get_expiration_w_utc_datetime(self):
        import datetime
        import pytz

        expiration_utc = datetime.datetime(2004, 8, 19, 0, 0, 0, 0, pytz.utc)
        utc_seconds = self._utc_seconds(expiration_utc)
        self.assertEqual(self._callFUT(expiration_utc), utc_seconds)

    def test__get_expiration_w_other_zone_datetime(self):
        import datetime
        import pytz

        zone = pytz.timezone('CET')
        expiration_other = datetime.datetime(2004, 8, 19, 0, 0, 0, 0, zone)
        utc_seconds = self._utc_seconds(expiration_other)
        cet_seconds = utc_seconds - (60 * 60)  # CET one hour earlier than UTC
        self.assertEqual(self._callFUT(expiration_other), cet_seconds)

    def test__get_expiration_seconds_w_timedelta_seconds(self):
        import datetime
        from gcloud.storage import connection
        from gcloud._testing import _Monkey

        dummy_utcnow = datetime.datetime(2004, 8, 19, 0, 0, 0, 0)
        utc_seconds = self._utc_seconds(dummy_utcnow)
        expiration_as_delta = datetime.timedelta(seconds=10)

        with _Monkey(connection, _utcnow=lambda: dummy_utcnow):
            result = self._callFUT(expiration_as_delta)

        self.assertEqual(result, utc_seconds + 10)

    def test__get_expiration_seconds_w_timedelta_days(self):
        import datetime
        from gcloud.storage import connection
        from gcloud._testing import _Monkey

        dummy_utcnow = datetime.datetime(2004, 8, 19, 0, 0, 0, 0)
        utc_seconds = self._utc_seconds(dummy_utcnow)
        expiration_as_delta = datetime.timedelta(days=1)

        with _Monkey(connection, _utcnow=lambda: dummy_utcnow):
            result = self._callFUT(expiration_as_delta)

        self.assertEqual(result, utc_seconds + 86400)


class Test__get_pem_key(unittest2.TestCase):

    def _callFUT(self, credentials):
        from gcloud.storage.connection import _get_pem_key
        return _get_pem_key(credentials)

    def test_bad_argument(self):
        self.assertRaises(TypeError, self._callFUT, None)

    def test_signed_jwt_for_p12(self):
        import base64
        from oauth2client import client
        from gcloud._testing import _Monkey
        from gcloud.storage import connection as MUT

        scopes = []
        PRIVATE_KEY = 'dummy_private_key_text'
        credentials = client.SignedJwtAssertionCredentials(
            'dummy_service_account_name', PRIVATE_KEY, scopes)
        crypt = _Crypt()
        rsa = _RSA()
        with _Monkey(MUT, crypt=crypt, RSA=rsa):
            result = self._callFUT(credentials)

        self.assertEqual(crypt._private_key_text,
                         base64.b64encode(PRIVATE_KEY))
        self.assertEqual(crypt._private_key_password, 'notasecret')
        self.assertEqual(result, 'imported:__PEM__')

    def test_service_account_via_json_key(self):
        from oauth2client import service_account
        from gcloud._testing import _Monkey
        from gcloud.storage import connection as MUT

        scopes = []

        PRIVATE_TEXT = 'dummy_private_key_pkcs8_text'

        def _get_private_key(private_key_pkcs8_text):
            return private_key_pkcs8_text

        with _Monkey(service_account, _get_private_key=_get_private_key):
            credentials = service_account._ServiceAccountCredentials(
                'dummy_service_account_id', 'dummy_service_account_email',
                'dummy_private_key_id', PRIVATE_TEXT, scopes)

        rsa = _RSA()
        with _Monkey(MUT, RSA=rsa):
            result = self._callFUT(credentials)

        expected = 'imported:%s' % (PRIVATE_TEXT,)
        self.assertEqual(result, expected)


class Test__get_signed_query_params(unittest2.TestCase):

    def _callFUT(self, credentials, expiration, signature_string):
        from gcloud.storage.connection import _get_signed_query_params
        return _get_signed_query_params(credentials, expiration,
                                        signature_string)

    def test_wrong_type(self):
        from gcloud._testing import _Monkey
        from gcloud.storage import connection as MUT

        pkcs_v1_5 = _PKCS1_v1_5()
        rsa = _RSA()
        sha256 = _SHA256()

        def _get_pem_key(credentials):
            return credentials

        BAD_CREDENTIALS = None
        EXPIRATION = '100'
        SIGNATURE_STRING = 'dummy_signature'
        with _Monkey(MUT, RSA=rsa, PKCS1_v1_5=pkcs_v1_5,
                     SHA256=sha256, _get_pem_key=_get_pem_key):
            self.assertRaises(NameError, self._callFUT,
                              BAD_CREDENTIALS, EXPIRATION, SIGNATURE_STRING)

    def _run_test_with_credentials(self, credentials, account_name):
        import base64
        from gcloud._testing import _Monkey
        from gcloud.storage import connection as MUT

        crypt = _Crypt()
        pkcs_v1_5 = _PKCS1_v1_5()
        rsa = _RSA()
        sha256 = _SHA256()

        EXPIRATION = '100'
        SIGNATURE_STRING = 'dummy_signature'
        with _Monkey(MUT, crypt=crypt, RSA=rsa, PKCS1_v1_5=pkcs_v1_5,
                     SHA256=sha256):
            result = self._callFUT(credentials, EXPIRATION, SIGNATURE_STRING)

        if crypt._pkcs12_key_as_pem_called:
            self.assertEqual(crypt._private_key_text,
                             base64.b64encode('dummy_private_key_text'))
            self.assertEqual(crypt._private_key_password, 'notasecret')
        self.assertEqual(sha256._signature_string, SIGNATURE_STRING)
        SIGNED = base64.b64encode('DEADBEEF')
        expected_query = {
            'Expires': EXPIRATION,
            'GoogleAccessId': account_name,
            'Signature': SIGNED,
        }
        self.assertEqual(result, expected_query)

    def test_signed_jwt_for_p12(self):
        from oauth2client import client

        scopes = []
        ACCOUNT_NAME = 'dummy_service_account_name'
        credentials = client.SignedJwtAssertionCredentials(
            ACCOUNT_NAME, 'dummy_private_key_text', scopes)
        self._run_test_with_credentials(credentials, ACCOUNT_NAME)

    def test_service_account_via_json_key(self):
        from oauth2client import service_account
        from gcloud._testing import _Monkey

        scopes = []

        PRIVATE_TEXT = 'dummy_private_key_pkcs8_text'

        def _get_private_key(private_key_pkcs8_text):
            return private_key_pkcs8_text

        ACCOUNT_NAME = 'dummy_service_account_email'
        with _Monkey(service_account, _get_private_key=_get_private_key):
            credentials = service_account._ServiceAccountCredentials(
                'dummy_service_account_id', ACCOUNT_NAME,
                'dummy_private_key_id', PRIVATE_TEXT, scopes)

        self._run_test_with_credentials(credentials, ACCOUNT_NAME)


class Http(object):

    _called_with = None

    def __init__(self, headers, content):
        from httplib2 import Response
        self._response = Response(headers)
        self._content = content

    def request(self, **kw):
        self._called_with = kw
        return self._response, self._content


class _Crypt(object):

    _pkcs12_key_as_pem_called = False

    def pkcs12_key_as_pem(self, private_key_text, private_key_password):
        self._pkcs12_key_as_pem_called = True
        self._private_key_text = private_key_text
        self._private_key_password = private_key_password
        return '__PEM__'


class _RSA(object):

    _imported = None

    def importKey(self, pem):
        self._imported = pem
        return 'imported:%s' % pem


class _PKCS1_v1_5(object):

    _pem_key = _signature_hash = None

    def new(self, pem_key):
        self._pem_key = pem_key
        return self

    def sign(self, signature_hash):
        self._signature_hash = signature_hash
        return 'DEADBEEF'


class _SHA256(object):

    _signature_string = None

    def new(self, signature_string):
        self._signature_string = signature_string
        return self
