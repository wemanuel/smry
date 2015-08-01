# Copyright 2015 Google Inc. All Rights Reserved.

"""Utility methods to aid in interacting with a GCS results bucket."""

import datetime
import os

from googlecloudapis.apitools.base import py as apitools_base
from googlecloudapis.storage import v1 as storage_v1
from googlecloudsdk.calliope import exceptions
from googlecloudsdk.core import log
from googlecloudsdk.test.lib import util


GCS_PREFIX = 'gs://'
ERROR_NOTFOUND = 404
FORBIDDEN = 403


class ResultsBucketOps(object):
  """A utility class to encapsulate operations on the results bucket."""

  def __init__(self, project, bucket_name,
               tr_client, tr_messages, storage_client,
               clock=datetime.datetime.now):
    """Construct a ResultsBucketOps object to be used with a single matrix run.

    Args:
      project: string containing the Google Developers Console project id.
      bucket_name: string containing the name of the GCS bucket.
      tr_client: ToolResults API client library generated by Apitools.
      tr_messages: ToolResults API messages library generated by Apitools.
      storage_client: Cloud Storage API client library generated by Apitools.
      clock: injected function which will return a datetime object to be used
        as a timestamp for the test's results storage in GCS. We default to
        local time so the timestamp feels 'normal' to the user.
    """
    self._project = project
    self._storage_client = storage_client

    # Get a current timestamp string in the format YYYY-MM-DD_hh:mm:ss.sss
    self._timestamp = clock().isoformat('_')[:-3]
    log.info('Test timestamp is {t}'.format(t=self._timestamp))

    # If the user supplied a results bucket, make sure it exists. Otherwise,
    # call the SettingsService to get the project's existing default bucket.
    if bucket_name:
      self.EnsureBucketExists(bucket_name)
    else:
      bucket_name = self._GetDefaultBucket(tr_client, tr_messages)

    self._results_bucket = bucket_name
    self.gcs_results_root = ('gs://{b}/{t}/'
                             .format(b=bucket_name, t=self._timestamp))
    self._gcs_results_url = (
        'https://console.developers.google.com/storage/browser/{b}/{t}/'
        .format(b=bucket_name, t=self._timestamp))

  def _GetDefaultBucket(self, tr_client, tr_messages):
    """Fetch the project's default GCS bucket name for storing tool results."""
    request = tr_messages.ToolresultsProjectsInitializeSettingsRequest(
        projectId=self._project)
    try:
      response = tr_client.projects.InitializeSettings(request)
      return response.defaultBucket.decode('utf8')
    except apitools_base.HttpError as error:
      code, err_msg = util.GetErrorCodeAndMessage(error)
      if code == FORBIDDEN:
        msg = ('Permission denied while fetching the default results bucket. '
               'Is billing enabled for project: [{0}]?'
               .format(self._project))
      else:
        msg = ('Http error while trying to fetch the default results bucket:\n'
               'ResponseError {0}: {1}'
               .format(code, err_msg))
      raise exceptions.HttpException(msg)

  def EnsureBucketExists(self, bucket_name):
    """Create a GCS bucket if it doesn't already exist.

    Args:
      bucket_name: the name of the GCS bucket to create if it doesn't exist.

    Raises:
      BadFileException if the bucket name is malformed, the user does not
        have access rights to the bucket, or the bucket can't be created.
    """
    if self._storage_client is None:
      return  # Bypass so some tests won't need to mock all the API calls

    get_req = storage_v1.StorageBucketsGetRequest(bucket=bucket_name)
    try:
      self._storage_client.buckets.Get(get_req)
      return  # The bucket exists and the user can access it.
    except apitools_base.HttpError as err:
      code, err_msg = util.GetErrorCodeAndMessage(err)
      if code != ERROR_NOTFOUND:
        raise exceptions.BadFileException(
            'Could not access bucket [{b}]. Response error {c}: {e}. '
            'Please supply a valid bucket name or use the default bucket '
            'provided by Google Cloud Test Lab.'
            .format(b=bucket_name, c=code, e=err_msg))

    # The bucket does not exist in any project, so create it in user's project.
    log.status.Print('Creating results bucket [{g}{b}] in project [{p}].'
                     .format(g=GCS_PREFIX, b=bucket_name, p=self._project))

    bucket_req = storage_v1.StorageBucketsInsertRequest
    acl = bucket_req.PredefinedAclValueValuesEnum.projectPrivate
    objacl = bucket_req.PredefinedDefaultObjectAclValueValuesEnum.projectPrivate

    insert_req = storage_v1.StorageBucketsInsertRequest(
        bucket=storage_v1.Bucket(name=bucket_name),
        predefinedAcl=acl,
        predefinedDefaultObjectAcl=objacl,
        project=self._project)
    try:
      self._storage_client.buckets.Insert(insert_req)
      return
    except apitools_base.HttpError as err:

      code, err_msg = util.GetErrorCodeAndMessage(err)
      if code == FORBIDDEN:
        msg = ('Permission denied while creating bucket [{b}]. '
               'Is billing enabled for project: [{p}]?'
               .format(b=bucket_name, p=self._project))
      else:
        msg = ('Failed to create bucket [{b}] {e}'
               .format(b=bucket_name, e=util.GetError(err)))
      raise exceptions.BadFileException(msg)

  def UploadApkFileToGcs(self, apk):
    """Upload an APK file to the GCS results bucket using the storage API.

    Args:
      apk: str, the absolute or relative path of the APK file to upload. File
        may be in located in GCS or the local filesystem.

    Raises:
      BadFileException if the file upload is not successful.
    """
    log.status.Print('Uploading [{f}] to the Cloud Test Lab...'.format(f=apk))
    try:
      if apk.startswith(GCS_PREFIX):
        # Perform a GCS object to GCS object copy
        apk_bucket, apk_obj = _SplitBucketAndObject(apk)
        copy_req = storage_v1.StorageObjectsCopyRequest(
            sourceBucket=apk_bucket,
            sourceObject=apk_obj,
            destinationBucket=self._results_bucket,
            destinationObject='{t}/{a}'.format(t=self._timestamp,
                                               a=os.path.basename(apk_obj)))
        self._storage_client.objects.Copy(copy_req)
      else:
        # Perform a GCS insert of a local APK file
        try:
          apk_size = os.path.getsize(apk)
          apk_stream = open(apk, 'r')
        except os.error:
          raise exceptions.BadFileException('[{0}] not found or not accessible'
                                            .format(apk))
        src_obj = storage_v1.Object(size=apk_size)
        upload = apitools_base.Upload.FromStream(
            apk_stream,
            mime_type='application/vnd.android.package-archive')
        insert_req = storage_v1.StorageObjectsInsertRequest(
            bucket=self._results_bucket,
            name='{t}/{a}'.format(t=self._timestamp, a=os.path.basename(apk)),
            object=src_obj)
        self._storage_client.objects.Insert(insert_req, upload=upload)
    except apitools_base.HttpError as err:
      raise exceptions.BadFileException(
          'Could not copy [{f}] to [{gcs}] {e}.'
          .format(f=apk, gcs=self.gcs_results_root, e=util.GetError(err)))

  def LogGcsResultsUrl(self):
    log.status.Print('Raw results will be stored in your GCS bucket at [{0}].'
                     .format(self._gcs_results_url))


def _SplitBucketAndObject(gcs_path):
  """Split a GCS path into bucket & object tokens, or raise BadFileException."""
  tokens = gcs_path[len(GCS_PREFIX):].strip('/').split('/', 1)
  if len(tokens) != 2:
    raise exceptions.BadFileException(
        '[{0}] is not a valid Google Cloud Storage path'.format(gcs_path))
  return tokens
