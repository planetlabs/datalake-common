import pytest
import random
import string
from datetime import datetime, timedelta

try:
    from moto import mock_s3
    import boto.s3
    from boto.s3.key import Key
    from urlparse import urlparse
    import simplejson as json
except ImportError:
    # if developers use s3-test features without having installed s3 stuff,
    # things will fail. So it goes.
    pass

@pytest.fixture
def basic_metadata():

    return {
        'version': 0,
        'start': 1426809600000,
        'end': 1426895999999,
        'where': 'nebraska',
        'what': 'apache',
        'hash': '12345'
    }

def random_word(length):
    return ''.join(random.choice(string.lowercase) for i in xrange(length))

def random_hex(length):
    return ('%0' + str(length) + 'x') % random.randrange(16**length)

def random_interval():
    year_2010 = 1262304000000
    five_years = 5 * 365 * 24 * 60 * 60 * 1000
    three_days = 3 * 24 * 60 * 60 * 1000
    start = year_2010 + random.randint(0, five_years)
    end = start + random.randint(0, three_days)
    return start, end

def random_work_id():
    if random.randint(0, 1):
        return None
    return '{}-{}'.format(random_word(5), random.randint(0,2**15))

@pytest.fixture
def random_metadata():
    start, end = random_interval()
    return {
        'version': 0,
        'start': start,
        'end': end,
        'work_id': random_work_id(),
        'where': random_word(10),
        'what': random_word(10),
        'id': random_hex(40),
        'hash': random_hex(40),
    }

@pytest.fixture
def tmpfile(tmpdir):
    name = random_word(10)
    def get_tmpfile(content):
        f = tmpdir.join(name)
        f.write(content)
        return str(f)

    return get_tmpfile


@pytest.fixture
def aws_connector(request):

    def create_connection(mocker, connector):
        mock = mocker()
        mock.start()

        def tear_down():
            mock.stop()
        request.addfinalizer(tear_down)

        return connector()

    return create_connection


@pytest.fixture
def s3_connection(aws_connector):
    return aws_connector(mock_s3, boto.connect_s3)


@pytest.fixture
def s3_bucket_maker(s3_connection):

    def maker(bucket_name):
        return s3_connection.create_bucket(bucket_name)

    return maker


@pytest.fixture
def s3_file_maker(s3_bucket_maker):

    def maker(bucket, key, content, metadata):
        b = s3_bucket_maker(bucket)
        k = Key(b)
        k.key = key
        if metadata:
            k.set_metadata('datalake', json.dumps(metadata))
        k.set_contents_from_string(content)

    return maker


@pytest.fixture
def s3_file_from_metadata(s3_file_maker):

    def maker(url, metadata):
        url = urlparse(url)
        assert url.scheme == 's3'
        s3_file_maker(url.netloc, url.path, '', metadata)

    return maker
