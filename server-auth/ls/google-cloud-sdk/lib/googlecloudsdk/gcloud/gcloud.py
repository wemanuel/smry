# Copyright 2013 Google Inc. All Rights Reserved.

"""gcloud command line tool."""

import time
START_TIME = time.time()

# pylint:disable=g-bad-import-order
# pylint:disable=g-import-not-at-top, We want to get the start time first.
import os
import signal
import sys
import traceback


# Disable stack traces when people kill a command.
def CTRLCHandler(unused_signal, unused_frame):
  """Custom SIGNINT handler.

  Signal handler that doesn't print the stack trace when a command is
  killed by keyboard interupt.
  """
  try:
    log.err.Print('\n\nCommand killed by keyboard interrupt\n')
  except NameError:
    sys.stderr.write('\n\nCommand killed by keyboard interrupt\n')
  # Kill ourselves with SIGINT so our parent can detect that we exited because
  # of a signal. SIG_DFL disables further KeyboardInterrupt exceptions.
  signal.signal(signal.SIGINT, signal.SIG_DFL)
  os.kill(os.getpid(), signal.SIGINT)
  # Just in case the kill failed ...
  sys.exit(1)
signal.signal(signal.SIGINT, CTRLCHandler)


# Enable normal UNIX handling of SIGPIPE to play nice with grep -q, head, etc.
# See https://mail.python.org/pipermail/python-list/2004-June/273297.html and
# http://utcc.utoronto.ca/~cks/space/blog/python/SignalExceptionSurprise
# for more details.
if hasattr(signal, 'SIGPIPE'):
  signal.signal(signal.SIGPIPE, signal.SIG_DFL)


def _SetPriorityCloudSDKPath():
  """Put google-cloud-sdk/lib at the beginning of sys.path.

  Modifying sys.path in this way allows us to always use our bundled versions
  of libraries, even when other versions have been installed. It also allows the
  user to install extra libraries that we cannot bundle (ie PyOpenSSL), and
  gcloud commands can use those libraries.
  """

  def _GetRootContainingGoogle():
    path = __file__
    while True:
      parent, here = os.path.split(path)
      if not here:
        break
      if here == 'googlecloudsdk':
        return parent
      path = parent

  module_root = _GetRootContainingGoogle()

  # check if we're already set
  if (not module_root) or (sys.path and module_root == sys.path[0]):
    return
  sys.path.insert(0, module_root)


def _DoStartupChecks():
  from googlecloudsdk.core.util import platforms
  if not platforms.PythonVersion().IsSupported():
    sys.exit(1)
  if not platforms.Platform.Current().IsSupported():
    sys.exit(1)


_SetPriorityCloudSDKPath()
_DoStartupChecks()


# pylint:disable=g-import-not-at-top, We want the _SetPriorityCloudSDKPath()
# function to be called before we try to import any CloudSDK modules.
from googlecloudsdk.calliope import base
from googlecloudsdk.calliope import cli
from googlecloudsdk.core import config
from googlecloudsdk.core import log
from googlecloudsdk.core import metrics
from googlecloudsdk.core import properties
from googlecloudsdk.core.updater import local_state
from googlecloudsdk.core.updater import update_manager


if not config.Paths().sdk_root:
  # Don't do update checks if there is no install root.
  properties.VALUES.component_manager.disable_update_check.Set(True)


def UpdateCheck():
  try:
    update_manager.UpdateManager.PerformUpdateCheck()
  # pylint:disable=broad-except, We never want this to escape, ever. Only
  # messages printed should reach the user.
  except Exception:
    pass


def VersionFunc():
  _cli.Execute(['version'])


def CreateCLI():
  """Generates the gcloud CLI."""
  pkg_root = config.GoogleCloudSDKPackageRoot()
  loader = cli.CLILoader(
      name='gcloud',
      command_root_directory=os.path.join(
          pkg_root, 'gcloud', 'sdktools', 'root'),
      allow_non_existing_modules=True,
      version_func=VersionFunc)

  loader.AddReleaseTrack(base.ReleaseTrack.ALPHA,
                         os.path.join(pkg_root, 'gcloud', 'sdktools', 'alpha'),
                         component='alpha')
  loader.AddReleaseTrack(base.ReleaseTrack.BETA,
                         os.path.join(pkg_root, 'gcloud', 'sdktools', 'beta'),
                         component='beta')

  loader.AddModule('auth', os.path.join(pkg_root, 'gcloud', 'sdktools', 'auth'))
  loader.AddModule('bigquery', os.path.join(pkg_root, 'bigquery', 'commands'))
  loader.AddModule('bigtable', os.path.join(pkg_root, 'bigtable', 'commands'))
  loader.AddModule('components',
                   os.path.join(pkg_root, 'gcloud', 'sdktools', 'components'))
  loader.AddModule('compute', os.path.join(pkg_root, 'compute', 'subcommands'))
  loader.AddModule('config',
                   os.path.join(pkg_root, 'gcloud', 'sdktools', 'config'))
  loader.AddModule('container',
                   os.path.join(pkg_root, 'container', 'commands'))
  loader.AddModule('dataflow',
                   os.path.join(pkg_root, 'dataflow', 'commands'))
  loader.AddModule('deployment_manager',
                   os.path.join(pkg_root, 'deployment_manager', 'commands'))
  loader.AddModule('dns', os.path.join(pkg_root, 'dns', 'commands'))
  loader.AddModule('endpoints', os.path.join(pkg_root, 'endpoints', 'commands'))
  loader.AddModule('internal',
                   os.path.join(pkg_root, 'internal', 'commands'))
  loader.AddModule('meta', os.path.join(pkg_root, 'gcloud', 'sdktools', 'meta'))
  loader.AddModule('preview', os.path.join(pkg_root, 'preview', 'commands'),
                   component='preview')
  # Put app and datastore under preview for now.
  loader.AddModule('preview.analysis',
                   os.path.join(pkg_root, 'analysis', 'commands'))
  loader.AddModule('preview.app',
                   os.path.join(pkg_root, 'appengine', 'app_commands'),
                   component='app')
  loader.AddModule('preview.datastore',
                   os.path.join(pkg_root, 'appengine', 'datastore_commands'),
                   component='app')
  loader.AddModule('genomics',
                   os.path.join(pkg_root, 'genomics', 'commands'))
  # TODO(user): Put logging in preview for now.
  loader.AddModule('preview.logging',
                   os.path.join(pkg_root, 'logging', 'commands'))
  loader.AddModule('preview.rolling_updates',
                   os.path.join(
                       pkg_root, 'updater', 'commands', 'rolling_updates'))
  loader.AddModule('projects',
                   os.path.join(pkg_root, 'projects', 'commands'))
  loader.AddModule('pubsub',
                   os.path.join(pkg_root, 'pubsub', 'commands'))
  loader.AddModule('services',
                   os.path.join(pkg_root, 'service_management', 'subcommands'))
  loader.AddModule('source',
                   os.path.join(pkg_root, 'source', 'commands'))
  loader.AddModule('sql', os.path.join(pkg_root, 'sql', 'tools'))
  loader.AddModule('test', os.path.join(pkg_root, 'test', 'commands'))

  # Check for updates on shutdown but not for any of the updater commands.
  loader.RegisterPostRunHook(UpdateCheck,
                             exclude_commands=r'gcloud\.components\..*')
  return loader.Generate()

_cli = CreateCLI()


def main():
  metrics.Started(START_TIME)
  # TODO(user): Put a real version number here
  metrics.Executions(
      'gcloud',
      local_state.InstallationState.VersionForInstalledComponent('core'))
  try:
    _cli.Execute()
  except Exception as err:  # pylint:disable=broad-except
    if isinstance(err, KeyboardInterrupt):
      raise
    traceback.print_exc()
    sys.exit(1)

if __name__ == '__main__':
  try:
    main()
  except KeyboardInterrupt:
    CTRLCHandler(None, None)
