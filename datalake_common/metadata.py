from copy import deepcopy
from dateutil.parser import parse as dateparse
from datetime import datetime
from pytz import utc
from uuid import uuid4
import re


class InvalidDatalakeMetadata(Exception):
    pass


class UnsupportedDatalakeMetadataVersion(Exception):
    pass

_EPOCH = datetime.fromtimestamp(0, utc)

class Metadata(dict):

    _VERSION = 0

    def __init__(self, *args, **kwargs):
        '''prepare compliant, normalized metadata from inputs

        Args:

            kwargs: key-value pairs for metadata fields.

        Raises:

            InvalidDatalakeMetadata if required fields are missing and cannot
            be inferred.
        '''
        # we want to own all of our bits so we can normalize them without
        # altering the caller's data unexpectedly. So deepcopy.
        args = deepcopy(args)
        kwargs = deepcopy(kwargs)
        super(Metadata, self).__init__(*args, **kwargs)
        self._ensure_id()
        self._ensure_version()
        self._ensure_work_id()
        self._validate()
        self._normalize_dates()

    def _ensure_id(self):
        if 'id' not in self:
            self['id'] = uuid4().hex

    def _ensure_version(self):
        if 'version' not in self:
            self['version'] = self._VERSION

    def _ensure_work_id(self):
        if 'work_id' not in self:
            self['work_id'] = None

    def _validate(self):
        self._validate_required_fields()
        self._validate_version()
        self._validate_slug_fields()
        self._validate_work_id()

    _REQUIRED_METADATA_FIELDS = ['version', 'start', 'where', 'what', 'id',
                                 'hash']

    def _validate_required_fields(self):
        for f in self._REQUIRED_METADATA_FIELDS:
            if self.get(f) is None:
                msg = '"{}" is a required field'.format(f)
                raise InvalidDatalakeMetadata(msg)

    def _validate_version(self):
        v = self['version']
        if v != self._VERSION:
            msg = ('Found version {}. '
                   'Only {} is supported').format(v, self._VERSION)
            raise UnsupportedDatalakeMetadataVersion(msg)

    _SLUG_FIELDS = ['where', 'what']

    def _validate_slug_fields(self):
        [self._validate_slug_field(f) for f in self._SLUG_FIELDS]

    def _validate_slug_field(self, f):
        if not re.match(r'^[a-z0-9_-]+$', self[f]):
            msg = ('Invalid value "{}" for "{}". Only lower-case letters, '
                   '_ and - are allowed.').format(self[f], f)
            raise InvalidDatalakeMetadata(msg)

    def _validate_work_id(self):
        if self['work_id'] is None:
            return
        self._validate_slug_field('work_id')
        if self['work_id'] == 'null':
            msg = '"work_id" cannot be the string "null"'
            raise InvalidDatalakeMetadata(msg)

    def _normalize_dates(self):
        self['start'] = self._normalize_date(self['start'])
        self._normalize_end()

    def _normalize_end(self):
        if 'end' not in self:
            return
        if self['end'] is not None:
            self['end'] = self._normalize_date(self['end'])

    @staticmethod
    def _normalize_date(date):
        if type(date) is int:
            return date
        elif type(date) is float:
            return int(date * 1000.0)
        else:
            return Metadata._normalize_date_from_string(date)

    @staticmethod
    def _normalize_date_from_string(date):
        try:
            d = dateparse(date)
            if not d.tzinfo:
                d = d.replace(tzinfo=utc)
            return Metadata._datetime_to_milliseconds(d)
        except ValueError:
            msg = 'could not parse a date from {}'.format(date)
            raise InvalidDatalakeMetadata(msg)

    @staticmethod
    def _datetime_to_milliseconds(d):
        delta = d - _EPOCH
        return int(delta.total_seconds()*1000.0)