import os
import logging
import boto3
from botocore.exceptions import ClientError
from odoo import models

_logger = logging.getLogger(__name__)

_S3_ENDPOINT   = os.environ.get('S3_ENDPOINT_URL', '')
_S3_ACCESS_KEY = os.environ.get('S3_ACCESS_KEY_ID', '')
_S3_SECRET_KEY = os.environ.get('S3_SECRET_ACCESS_KEY', '')
_S3_BUCKET     = os.environ.get('S3_BUCKET', 'odoo')
_S3_REGION     = os.environ.get('S3_REGION', 'ap-southeast-1')

# Prefix on store_fname distinguishes S3 keys from local filesystem paths.
_S3_PREFIX = 's3/'


def _s3_client():
    return boto3.client(
        's3',
        endpoint_url=_S3_ENDPOINT,
        aws_access_key_id=_S3_ACCESS_KEY,
        aws_secret_access_key=_S3_SECRET_KEY,
        region_name=_S3_REGION,
    )


class IrAttachment(models.Model):
    _inherit = 'ir.attachment'

    def _file_write(self, bin_data, checksum):
        if not _S3_ENDPOINT:
            return super()._file_write(bin_data, checksum)

        # Mirror Odoo's two-level checksum sharding (e.g. s3/ab/abcdef…)
        key = _S3_PREFIX + checksum[:2] + '/' + checksum
        try:
            _s3_client().put_object(Bucket=_S3_BUCKET, Key=key, Body=bin_data)
            _logger.debug('S3 upload: %s', key)
        except Exception:
            _logger.exception('S3 upload failed (key=%s)', key)
            raise
        return key

    def _file_read(self, fname):
        if not fname.startswith(_S3_PREFIX):
            return super()._file_read(fname)

        try:
            obj = _s3_client().get_object(Bucket=_S3_BUCKET, Key=fname)
            return obj['Body'].read()
        except ClientError:
            _logger.exception('S3 read failed (key=%s)', fname)
            raise

    def _file_delete(self, fname):
        if not fname.startswith(_S3_PREFIX):
            return super()._file_delete(fname)

        try:
            _s3_client().delete_object(Bucket=_S3_BUCKET, Key=fname)
            _logger.debug('S3 delete: %s', fname)
        except Exception:
            _logger.warning('S3 delete failed (key=%s)', fname, exc_info=True)
