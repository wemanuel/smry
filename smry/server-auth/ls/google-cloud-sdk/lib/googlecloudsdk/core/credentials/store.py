# Copyright 2013 Google Inc. All Rights Reserved.

"""One-line documentation for auth module.

A detailed description of auth.
"""

import datetime
import os
import textwrap

from googlecloudsdk.core.util import files
import httplib2
from oauth2client import client
from oauth2client import gce as oauth2client_gce
from oauth2client import multistore_file

from googlecloudsdk.core import config
from googlecloudsdk.core import exceptions
from googlecloudsdk.core import properties
from googlecloudsdk.core.credentials import devshell as c_devshell
from googlecloudsdk.core.credentials import gce as c_gce
from googlecloudsdk.core.credentials import legacy


GOOGLE_OAUTH2_PROVIDER_AUTHORIZATION_URI = (
    'https://accounts.google.com/o/oauth2/auth')
GOOGLE_OAUTH2_PROVIDER_TOKEN_URI = (
    'https://accounts.google.com/o/oauth2/token')


class Error(exceptions.Error):
  """Exceptions for the credentials module."""


class AuthenticationException(Error):
  """Exceptions that tell the users to run auth login."""

  def __init__(self, message):
    super(AuthenticationException, self).__init__(textwrap.dedent("""\
        {message}
        Please run:

          $ gcloud auth login

        to obtain new credentials, or if you have already logged in with a
        different account:

          $ gcloud config set account ACCOUNT

        to select an already authenticated account to use.""".format(
            message=message)))


class NoCredentialsForAccountException(AuthenticationException):
  """Exception for when no credentials are found for an account."""

  def __init__(self, account):
    super(NoCredentialsForAccountException, self).__init__(
        'Your current active account [{account}] does not have any'
        ' valid credentials'.format(account=account))


class NoActiveAccountException(AuthenticationException):
  """Exception for when there are no valid active credentials."""

  def __init__(self):
    super(NoActiveAccountException, self).__init__(
        'You do not currently have an active account selected.')


class FlowError(Error):
  """Exception for when something goes wrong with a web flow."""


class RefreshError(Error):
  """Exception for when there was a problem refreshing."""


class RevokeError(Error):
  """Exception for when there was a problem revoking."""


def _Http(*args, **kwargs):
  no_validate = properties.VALUES.auth.disable_ssl_validation.GetBool()
  kwargs['disable_ssl_certificate_validation'] = no_validate
  return httplib2.Http(*args, **kwargs)


def _GetStorageKeyForAccount(account):
  return {
      'type': 'google-cloud-sdk',
      'account': account,
  }


# TODO(user): use _GetStorageKeyForAccount instead, but in meantime since the
# key format has changed this will not invalidate existing auth credentials and
# will move over existing credentials under new key format.
def _FindStorageKeyForAccount(account):
  """Scans credential file for keys matching given account.

  If such key(s) is found it checks that current set of scopes is a subset of
  scopes associated with the key.

  Args:
    account: str, The account tied to the storage key being fetched.

  Returns:
    dict, key to be used in the credentials store.
  """
  storage_path = config.Paths().credentials_path
  current_scopes = set(config.CLOUDSDK_SCOPES)
  equivalent_keys = [key for key in
                     multistore_file.get_all_credential_keys(
                         filename=storage_path)
                     if (key.get('type') == 'google-cloud-sdk' and
                         key.get('account') == account and (
                             'scope' not in key or
                             set(key.get('scope').split()) >= current_scopes))]

  preferred_key = _GetStorageKeyForAccount(account)
  if preferred_key in equivalent_keys:
    equivalent_keys.remove(preferred_key)
  elif equivalent_keys:  # Migrate credentials over to new key format.
    storage = multistore_file.get_credential_storage_custom_key(
        filename=storage_path,
        key_dict=equivalent_keys[0])
    creds = storage.get()
    storage = multistore_file.get_credential_storage_custom_key(
        filename=storage_path,
        key_dict=preferred_key)
    storage.put(creds)

  # Remove all other entries.
  for key in equivalent_keys:
    storage = multistore_file.get_credential_storage_custom_key(
        filename=storage_path,
        key_dict=key)
    storage.delete()

  return preferred_key


def _StorageForAccount(account):
  """Get the oauth2client.multistore_file storage.

  Args:
    account: str, The account tied to the storage being fetched.

  Returns:
    oauth2client.client.Storage, A credentials store.
  """
  storage_path = config.Paths().credentials_path
  parent_dir, unused_name = os.path.split(storage_path)
  files.MakeDir(parent_dir)

  storage = multistore_file.get_credential_storage_custom_key(
      filename=storage_path,
      key_dict=_FindStorageKeyForAccount(account))
  return storage


def AvailableAccounts():
  """Get all accounts that have credentials stored for the CloudSDK.

  This function will also ping the GCE metadata server to see if GCE credentials
  are available.

  Returns:
    [str], List of the accounts.

  """
  all_keys = multistore_file.get_all_credential_keys(
      filename=config.Paths().credentials_path)

  accounts = [key['account'] for key in all_keys
              if key.get('type') == 'google-cloud-sdk']

  accounts.extend(c_gce.Metadata().Accounts())

  devshell_creds = c_devshell.LoadDevshellCredentials()
  if devshell_creds:
    accounts.append(devshell_creds.devshell_response.user_email)

  accounts.sort()

  return accounts


def LoadIfValid(account=None):
  """Gets the credentials associated with the provided account if valid.

  Args:
    account: str, The account address for the credentials being fetched. If
        None, the account stored in the core.account property is used.

  Returns:
    oauth2client.client.Credentials, The credentials if they were found and
    valid, or None otherwise.
  """
  try:
    return Load(account=account)
  except Error:
    return None


def Load(account=None):
  """Get the credentials associated with the provided account.

  Args:
    account: str, The account address for the credentials being fetched. If
        None, the account stored in the core.account property is used.

  Returns:
    oauth2client.client.Credentials, The specified credentials.

  Raises:
    NoActiveAccountException: If account is not provided and there is no
        active account.
    NoCredentialsForAccountException: If there are no valid credentials
        available for the provided or active account.
    c_gce.CannotConnectToMetadataServerException: If the metadata server cannot
        be reached.
    RefreshError: If the credentials fail to refresh.
  """
  if not account:
    account = properties.VALUES.core.account.Get()

  if not account:
    raise NoActiveAccountException()

  devshell_creds = c_devshell.LoadDevshellCredentials()
  if devshell_creds and (
      devshell_creds.devshell_response.user_email == account):
    return devshell_creds

  if account in c_gce.Metadata().Accounts():
    return AcquireFromGCE(account)

  store = _StorageForAccount(account)
  if not store:
    raise NoCredentialsForAccountException(account)
  cred = store.get()
  if not cred:
    raise NoCredentialsForAccountException(account)

  # cred.token_expiry is in UTC time.
  if not cred.token_expiry or cred.token_expiry < cred.token_expiry.utcnow():
    Refresh(cred)

  return cred


def Refresh(creds, http=None):
  """Refresh credentials.

  Calls creds.refresh(), unless they're SignedJwtAssertionCredentials.

  Args:
    creds: oauth2client.client.Credentials, The credentials to refresh.
    http: httplib2.Http, The http transport to refresh with.

  Raises:
    RefreshError: If the credentials fail to refresh.
  """
  try:
    creds.refresh(http or _Http())
  except (client.AccessTokenRefreshError, httplib2.ServerNotFoundError) as e:
    raise RefreshError(e)


def Store(creds, account=None):
  """Store credentials according for an account address.

  Args:
    creds: oauth2client.client.Credentials, The credentials to be stored.
    account: str, The account address of the account they're being stored for.
        If None, the account stored in the core.account property is used.

  Raises:
    NoActiveAccountException: If account is not provided and there is no
        active account.
  """

  # We never serialize devshell credentials.
  if isinstance(creds, c_devshell.DevshellCredentials):
    return

  if not account:
    account = properties.VALUES.core.account.Get()
  if not account:
    raise NoActiveAccountException()

  store = _StorageForAccount(account)
  store.put(creds)
  creds.set_store(store)
  _GetLegacyGen(account, creds).WriteTemplate()


def _GetLegacyGen(account, creds):
  return legacy.LegacyGenerator(
      multistore_path=config.Paths().LegacyCredentialsMultistorePath(account),
      json_path=config.Paths().LegacyCredentialsJSONPath(account),
      gae_java_path=config.Paths().LegacyCredentialsGAEJavaPath(account),
      gsutil_path=config.Paths().LegacyCredentialsGSUtilPath(account),
      key_path=config.Paths().LegacyCredentialsKeyPath(account),
      json_key_path=config.Paths().LegacyCredentialsJSONKeyPath(account),
      credentials=creds, scopes=config.CLOUDSDK_SCOPES)


def Revoke(account=None):
  """Revoke credentials and clean up related files.

  Args:
    account: str, The account address for the credentials to be revoked. If
        None, the currently active account is used.

  Raises:
    NoCredentialsForAccountException: If the provided account is not tied to any
        known credentials.
    RevokeError: If there was a more general problem revoking the account.
  """
  if not account:
    account = properties.VALUES.core.account.Get()

  if account in c_gce.Metadata().Accounts():
    raise RevokeError('Cannot revoke GCE-provided credentials.')

  creds = Load(account)
  if not creds:
    raise NoCredentialsForAccountException(account)

  # TODO(user): Remove this condition when oauth2client does not crash while
  # revoking SignedJwtAssertionCredentials.
  if creds and (not client.HAS_CRYPTO or
                type(creds) != client.SignedJwtAssertionCredentials):
    creds.revoke(_Http())
  store = _StorageForAccount(account)
  if store:
    store.delete()

  _GetLegacyGen(account, creds).Clean()
  files.RmTree(config.Paths().LegacyCredentialsDir(account))


def AcquireFromWebFlow(launch_browser=True,
                       auth_uri=None,
                       token_uri=None):
  """Get credentials via a web flow.

  Args:
    launch_browser: bool, Open a new web browser window for authorization.
    auth_uri: str, URI to open for authorization.
    token_uri: str, URI to use for refreshing.

  Returns:
    client.Credentials, Newly acquired credentials from the web flow.

  Raises:
    FlowError: If there is a problem with the web flow.
  """
  if auth_uri is None:
    auth_uri = properties.VALUES.auth.auth_host.Get(required=True)
  if token_uri is None:
    token_uri = properties.VALUES.auth.token_host.Get(required=True)

  webflow = client.OAuth2WebServerFlow(
      client_id=properties.VALUES.auth.client_id.Get(required=True),
      client_secret=properties.VALUES.auth.client_secret.Get(required=True),
      scope=config.CLOUDSDK_SCOPES,
      user_agent=config.CLOUDSDK_USER_AGENT,
      auth_uri=auth_uri,
      token_uri=token_uri,
      prompt='select_account')

  # pylint:disable=g-import-not-at-top, This is imported on demand for
  # performance reasons.
  from googlecloudsdk.core.credentials import flow

  try:
    cred = flow.Run(
        webflow, launch_browser=launch_browser,
        http=_Http())
  except flow.Error as e:
    raise FlowError(e)
  return cred


def AcquireFromToken(refresh_token,
                     token_uri=GOOGLE_OAUTH2_PROVIDER_TOKEN_URI):
  """Get credentials from an already-valid refresh token.

  Args:
    refresh_token: An oauth2 refresh token.
    token_uri: str, URI to use for refreshing.

  Returns:
    client.Credentials, Credentials made from the refresh token.
  """
  cred = client.OAuth2Credentials(
      access_token=None,
      client_id=properties.VALUES.auth.client_id.Get(required=True),
      client_secret=properties.VALUES.auth.client_secret.Get(required=True),
      refresh_token=refresh_token,
      # always start expired
      token_expiry=datetime.datetime.utcnow(),
      token_uri=token_uri,
      user_agent=config.CLOUDSDK_USER_AGENT)
  return cred


def AcquireFromGCE(account=None):
  """Get credentials from a GCE metadata server.

  Args:
    account: str, The account name to use. If none, the default is used.

  Returns:
    client.Credentials, Credentials taken from the metadata server.

  Raises:
    c_gce.CannotConnectToMetadataServerException: If the metadata server cannot
      be reached.
    RefreshError: If the credentials fail to refresh.
    Error: If a non-default service account is used.
  """
  default_account = c_gce.Metadata().DefaultAccount()
  if account is None:
    account = default_account
  if account != default_account:
    raise Error('Unable to use non-default GCE service accounts.')
  # TODO(user): Update oauth2client to fetch alternate credentials. This
  # inability is not currently a problem, because the metadata server does not
  # yet provide multiple service accounts.

  creds = oauth2client_gce.AppAssertionCredentials(config.CLOUDSDK_SCOPES)
  Refresh(creds)
  return creds
