# Copyright 2013 Google Inc. All Rights Reserved.

"""Higher level functions to support updater operations at the CLI level."""

import hashlib
import os
import subprocess
import sys
import textwrap

from googlecloudsdk.core.util import files as file_utils
from googlecloudsdk.core.util import platforms

from googlecloudsdk.core import config
from googlecloudsdk.core import exceptions
from googlecloudsdk.core import log
from googlecloudsdk.core import metrics
from googlecloudsdk.core import properties
from googlecloudsdk.core.console import console_io
from googlecloudsdk.core.updater import local_state
from googlecloudsdk.core.updater import schemas
from googlecloudsdk.core.updater import snapshots
from googlecloudsdk.core.util import execution_utils


# These are components that used to exist, but we removed.  In order to prevent
# scripts and installers that use them from getting errors, we will just warn
# and move on.  This can be removed once we think enough time has passed.
_GAE_REDIRECT_MSG = ("""\
The standalone App Engine SDKs are no longer distributed through the Cloud SDK
(however, the appcfg and dev_appserver commands remain the official and
supported way of using App Engine from the command line).  If you want to
continue using these tools, they are available for download from the official
App Engine download page here:
    https://cloud.google.com/appengine/downloads
""")
_IGNORED_MISSING_COMPONENTS = {
    'app-engine-go-linux-x86': None,
    'app-engine-go-linux-x86_64': None,
    'app-engine-go-darwin-x86': None,
    'app-engine-go-darwin-x86_64': None,
    'app-engine-go-windows-x86': None,
    'app-engine-go-windows-x86_64': None,
    'compute': None,
    'dns': None,
    'gae-java': _GAE_REDIRECT_MSG,
    'gae-python': _GAE_REDIRECT_MSG,
    'gae-go': _GAE_REDIRECT_MSG,
    'gae-python-launcher-mac': _GAE_REDIRECT_MSG,
    'gae-python-launcher-win': _GAE_REDIRECT_MSG,
    'pkg-core': None,
    'pkg-java': None,
    'pkg-python': None,
    'pkg-go': None,
    'sql': None,
}

_SHELL_RCFILES = [
    'completion.bash.inc',
    'completion.zsh.inc',
    'path.bash.inc',
    'path.zsh.inc',
    'gcfilesys.bash.inc',
    'gcfilesys.zsh.inc'
]


class Error(exceptions.Error):
  """Base exception for the update_manager module."""
  pass


class InvalidCWDError(Error):
  """Error for when your current working directory prevents an operation."""
  pass


class UpdaterDisableError(Error):
  """Error for when an update is attempted but it is disallowed."""
  pass


class InvalidComponentError(Error):
  """Error for when a given component id is not valid for the operation."""
  pass


class NoBackupError(Error):
  """Error for when you try to restore a backup but one does not exist."""
  pass


class ReinstallationFailedError(Error):
  """Error for when performing a reinstall fails."""
  pass


class MissingRequiredComponentsError(Error):
  """Error for when components are required, but you don't install them."""
  pass


class UpdateManager(object):
  """Main class for performing updates for the Cloud SDK."""

  UPDATE_CHECK_FREQUENCY_IN_SECONDS = 86400  # once a day.
  UPDATE_CHECK_NAG_FREQUENCY_IN_SECONDS = 86400  # once a day.
  BIN_DIR_NAME = 'bin'
  VERSIONED_SNAPSHOT_FORMAT = 'components-v{0}.json'

  def HashRcfiles(self, shell_rc_files):
    """Creates the md5 checksums of files.

    Args:
      shell_rc_files: list, A list of files to get the md5 checksums.
    Returns:
      md5dict, dictionary of m5 file sums.
    """

    md5dict = {}
    for name in shell_rc_files:
      try:
        fpath = os.path.join(self.__sdk_root, name)
        if not os.path.exists(fpath):
          continue
        with open(fpath, 'rb') as f:
          md5 = hashlib.md5(f.read()).hexdigest()
          md5dict[name] = md5
      except OSError:
        md5dict[name] = 0
        continue
    return md5dict

  @staticmethod
  def GetAdditionalRepositories():
    """Gets the currently registered repositories as a list.

    Returns:
      [str], The list of registered repos or [] if there are none.
    """
    repos = properties.VALUES.component_manager.additional_repositories.Get()
    if repos:
      return repos.split(',')
    return []

  @staticmethod
  def EnsureInstalledAndRestart(components, msg=None):
    """Installs the given components if necessary and then restarts gcloud.

    Args:
      components: [str], The components that must be installed.
      msg: str, A custom message to print.

    Returns:
      bool, True if the components were already installed.  If installation must
      occur, this method never returns because gcloud is reinvoked after the
      update is done.

    Raises:
      MissingRequiredComponentsError: If the components are not installed and
      the user chooses not to install them.
    """
    platform = platforms.Platform.Current()
    manager = UpdateManager(platform_filter=platform, warn=False)
    # pylint: disable=protected-access
    return manager._EnsureInstalledAndRestart(components, msg)

  @staticmethod
  def PerformUpdateCheck(force=False):
    """Checks to see if a new snapshot has been released periodically.

    This method can be called as often as you'd like.  It will only actually
    check the server for updates if a certain amount of time has elapsed since
    the last check (or if force is True).  If updates are available, to any
    installed components, it will print a notification message.

    Args:
      force: bool, True to force a server check for updates, False to check only
        if the update frequency has expired.

    Returns:
      bool, True if updates are available, False otherwise.
    """
    platform = platforms.Platform.Current()
    manager = UpdateManager(platform_filter=platform, warn=False)
    # pylint: disable=protected-access
    return manager._PerformUpdateCheck(force=force)

  def __init__(self, sdk_root=None, url=None, platform_filter=None, warn=True):
    """Creates a new UpdateManager.

    Args:
      sdk_root: str, The path to the root directory of the Cloud SDK is
        installation.  If None, the updater will search for the install
        directory based on the current directory.
      url: str, The URL to get the latest component snapshot from.  If None,
        the default will be used.
      platform_filter: platforms.Platform, A platform that components must match
        in order to be considered for any operations.  If None, only components
        without OS or architecture filters will match.
      warn: bool, True to warn about overridden configuration like an alternate
        snapshot file, fixed SDK version, or additional repo.  Should be set
        to False when using this class for background operations like checking
        for updates so the user only sees the warnings when they are actually
        dealing directly with the component manager.

    Raises:
      local_state.InvalidSDKRootError: If the Cloud SDK root cannot be found.
    """

    if not url:
      url = properties.VALUES.component_manager.snapshot_url.Get()
    if url:
      if warn:
        log.warning('You are using an overridden snapshot URL: [%s]', url)
    else:
      url = config.INSTALLATION_CONFIG.snapshot_url

    # Change the snapshot URL to point to a fixed SDK version if specified.
    fixed_version = properties.VALUES.component_manager.fixed_sdk_version.Get()
    if fixed_version:
      urls = url.split(',')
      urls[0] = (os.path.dirname(urls[0]) + '/' +
                 UpdateManager.VERSIONED_SNAPSHOT_FORMAT.format(fixed_version))
      if warn:
        log.warning('You have configured your Cloud SDK installation to be '
                    'fixed to version [{0}].'.format(fixed_version))
      url = ','.join(urls)

    # Add in any additional repositories that have been registered.
    repos = properties.VALUES.component_manager.additional_repositories.Get()
    if repos:
      if warn:
        for repo in repos.split(','):
          log.warning('You are using additional component repository: [%s]',
                      repo)
      url = ','.join([url, repos])

    self.__sdk_root = sdk_root
    if not self.__sdk_root:
      self.__sdk_root = config.Paths().sdk_root
    if not self.__sdk_root:
      raise local_state.InvalidSDKRootError()
    self.__sdk_root = os.path.realpath(self.__sdk_root)
    self.__url = url
    self.__platform_filter = platform_filter
    self.__text_wrapper = textwrap.TextWrapper(replace_whitespace=False,
                                               drop_whitespace=False)
    self.__warn = warn

  def __Write(self, stream, msg='', word_wrap=False):
    """Writes the given message to the out stream with a new line.

    Args:
      stream:  The output stream to write to.
      msg: str, The message to write.
      word_wrap: bool, True to enable nicer word wrapper, False to just print
        the string as is.
    """
    if word_wrap:
      msg = self.__text_wrapper.fill(msg)
    stream.write(msg + '\n')
    stream.flush()

  def _ShouldDoFastUpdate(self, allow_no_backup=False,
                          fast_mode_impossible=False):
    """Determine whether we should do an in-place fast update or make a backup.

    This method also ensures the CWD is valid for the mode we are going to use.

    Args:
      allow_no_backup: bool, True if we want to allow the updater to run
        without creating a backup.  This lets us be in the root directory of the
        SDK and still do an update.  It is more fragile if there is a failure,
        so we only do it if necessary.
      fast_mode_impossible: bool, True if we can't do a fast update for this
        particular operation (overrides forced fast mode).

    Returns:
      bool, True if allow_no_backup was True and we are under the SDK root (so
        we should do a no backup update).

    Raises:
      InvalidCWDError: If the command is run from a directory within the SDK
        root.
    """
    force_fast = properties.VALUES.experimental.fast_component_update.GetBool()
    if fast_mode_impossible:
      force_fast = False

    cwd = os.path.realpath(os.getcwd())
    if not cwd.startswith(self.__sdk_root):
      # Outside of the root entirely, this is always fine.
      return force_fast

    # We are somewhere under the install root.
    if ((allow_no_backup or force_fast) and
        (self.__sdk_root == cwd or self.__sdk_root == os.path.dirname(cwd))):
      # Backups are disabled and we are in the root itself, or in a top level
      # directory.  This is OK since these directories won't ever be deleted.
      return True

    raise InvalidCWDError(
        'Your current working directory is inside the Cloud SDK install root:'
        ' {root}.  In order to perform this update, run the command from '
        'outside of this directory.'.format(root=self.__sdk_root))

  def _GetDontCancelMessage(self, disable_backup):
    """Get the message to print before udpates.

    Args:
      disable_backup: bool, True if we are doing an in place udpate.

    Returns:
      str, The message to print, or None.
    """
    if disable_backup:
      return ('Once started, canceling this operation may leave your SDK '
              'installation in an inconsistent state.')
    else:
      return None

  def _EnsureNotDisabled(self):
    """Prints an error and raises an Exception if the updater is disabled.

    The updater is disabled for installations that come from other package
    managers like apt-get or if the current user does not have permission
    to create or delete files in the SDK root directory.

    Raises:
      UpdaterDisableError: If the updater is disabled.
      exceptions.RequiresAdminRightsError: If the caller has insufficient
        privilege.
    """
    if config.INSTALLATION_CONFIG.disable_updater:
      message = (
          'You cannot perform this action because this Cloud SDK installation '
          'is managed by an external package manager.  If you would like to get'
          ' the latest version, please see our main download page at:\n  '
          + config.INSTALLATION_CONFIG.documentation_url + '\n')
      self.__Write(log.err, message, word_wrap=True)
      raise UpdaterDisableError(
          'The component manager is disabled for this installation')
    config.EnsureSDKWriteAccess(self.__sdk_root)

  def _GetInstallState(self):
    return local_state.InstallationState(self.__sdk_root)

  def _GetLatestSnapshot(self):
    return snapshots.ComponentSnapshot.FromURLs(*self.__url.split(','))

  def _GetStateAndDiff(self):
    install_state = self._GetInstallState()
    latest_snapshot = self._GetLatestSnapshot()
    diff = install_state.DiffCurrentState(
        latest_snapshot, platform_filter=self.__platform_filter)
    return install_state, diff

  def GetCurrentVersionsInformation(self):
    """Get the current version for every installed component.

    Returns:
      {str:str}, A mapping from component id to version string.
    """
    current_state = self._GetInstallState()
    versions = {}
    installed_components = current_state.InstalledComponents()
    for component_id, component in installed_components.iteritems():
      if component.ComponentDefinition().is_configuration:
        continue
      versions[component_id] = component.VersionString()
    return versions

  def _PerformUpdateCheck(self, force=False):
    """Checks to see if a new snapshot has been released periodically.

    This method can be called as often as you'd like.  It will only actually
    check the server for updates if a certain amount of time has elapsed since
    the last check (or if force is True).  If updates are available, to any
    installed components, it will print a notification message.

    Args:
      force: bool, True to force a server check for updates, False to check only
        if the update frequency has expired.

    Returns:
      bool, True if updates are available, False otherwise.
    """
    def PrintUpdates(last_update_check):
      """Print the update message but only if it's time to nag again."""
      log.debug('Updates are available.')
      if (log.out.isatty() and
          last_update_check.SecondsSinceLastNag()
          >= UpdateManager.UPDATE_CHECK_NAG_FREQUENCY_IN_SECONDS):
        self.__Write(
            log.status,
            '\nUpdates are available for some Cloud SDK components.  To '
            'install them, please run:', word_wrap=True)
        self.__Write(
            log.status, ' $ gcloud components update\n', word_wrap=False)
        last_update_check.SetNagged()
      return True

    if (config.INSTALLATION_CONFIG.disable_updater or
        properties.VALUES.component_manager.disable_update_check.GetBool()):
      return False

    install_state = self._GetInstallState()

    with install_state.LastUpdateCheck() as last_update_check:
      # We already know there are updates, no need to check again.
      if last_update_check.UpdatesAvailable():
        return PrintUpdates(last_update_check)

      # Not time to check again
      if not force and (last_update_check.SecondsSinceLastUpdateCheck()
                        < UpdateManager.UPDATE_CHECK_FREQUENCY_IN_SECONDS):
        return False

      # Check for updates.
      try:
        latest_snapshot = self._GetLatestSnapshot()
      except snapshots.IncompatibleSchemaVersionError:
        # The schema version of the snapshot is newer than what we know about,
        # it is definitely a newer version.
        last_update_check.SetFromIncompatibleSchema()
        return PrintUpdates(last_update_check)
      updates_available = last_update_check.SetFromSnapshot(
          latest_snapshot, platform_filter=self.__platform_filter)
      if not updates_available:
        return False
      return PrintUpdates(last_update_check)

  def List(self, show_versions=False):
    """Lists all of the components and their current state.

    This pretty prints the list of components along with whether they are up
    to date, require an update, etc.

    Args:
      show_versions: bool, True to print versions in the table.  Defaults to
        False.

    Returns:
      The list of snapshots.ComponentDiffs for all components.
    """
    try:
      _, diff = self._GetStateAndDiff()
    except snapshots.IncompatibleSchemaVersionError as e:
      return self._ReinstallOnError(e)

    to_print = [diff.AvailableUpdates(), diff.Removed(),
                diff.AvailableToInstall(), diff.UpToDate()]

    self._PrintTable('Packages', show_versions=False, to_print=to_print,
                     func=lambda x: x.is_configuration, ignore_if_empty=True)
    self._PrintTable('Components', show_versions=show_versions,
                     to_print=to_print, func=lambda x: not x.is_configuration,
                     ignore_if_empty=False)

    self.__Write(log.status,
                 'To install new components or update existing ones, run:',
                 word_wrap=True)
    self.__Write(log.status, ' $ gcloud components update COMPONENT_ID')
    return diff.AllDiffs()

  def _PrintTable(self, title, show_versions, to_print, func, ignore_if_empty):
    """Prints a table of updatable components.

    Args:
      title: str, The title for the table.
      show_versions: bool, True to print versions in the table.
      to_print: list(list(snapshots.ComponentDiff)), The available components
        divided by state.
      func: func(snapshots.ComponentDiff) -> bool, Decides whether the component
        should be printed.
      ignore_if_empty: bool, True to not show the table at all if there are no
        matching components.
    """
    printer = snapshots.ComponentDiff.TablePrinter(show_versions=show_versions)
    printer.SetTitle(title)
    rows = []
    for components in to_print:
      rows.extend([c.AsTableRow(show_versions=show_versions)
                   for c in components
                   if not c.is_hidden and func(c)])
    if not rows and ignore_if_empty:
      return
    printer.Print(rows, output_stream=log.out)
    self.__Write(log.out, '\n')

  def _PrintPendingAction(self, components, action):
    """Prints info about components we are going to install or remove.

    Args:
      components: list(schemas.Component), The components that are going to be
        acted on.
      action: str, The verb to print for this set of components.
    """
    if not components:
      return

    header_string = 'The following components will be {action}:'.format(
        action=action)
    self.__Write(log.status, header_string)

    printer = schemas.Component.TablePrinter()
    rows = [c.AsTableRow() for c in components]
    printer.Print(rows, output_stream=log.status, indent=4)

  def _UpdateWithProgressBar(self, components, action, action_func):
    """Performs an update on a component while using a progress bar.

    Args:
      components: [schemas.Component], The components that are going to be acted
        on.
      action: str, The action that is printed for this update.
      action_func: func, The function to call to actually do the update.  It
        takes a single argument which is the component id.
    """
    for component in components:
      label = '{action}: {name}'.format(action=action,
                                        name=component.details.display_name)
      with console_io.ProgressBar(label=label, stream=log.status) as pb:
        action_func(component.id, progress_callback=pb.SetProgress)

  def _InstallFunction(self, install_state, diff):
    def Inner(component_id, progress_callback):
      return install_state.Install(diff.latest, component_id,
                                   progress_callback=progress_callback)
    return Inner

  def Update(self, update_seed=None, allow_no_backup=False,
             throw_if_unattended=False):
    """Performs an update of the given components.

    If no components are provided, it will attempt to update everything you have
    installed.

    Args:
      update_seed: list of str, A list of component ids to update.
      allow_no_backup: bool, True if we want to allow the updater to run
        without creating a backup.  This lets us be in the root directory of the
        SDK and still do an update.  It is more fragile if there is a failure,
        so we only do it if necessary.
      throw_if_unattended: bool, True to throw an exception on prompts when
        not running in interactive mode.

    Returns:
      bool, True if the update succeeded (or there was nothing to do, False if
      if was cancelled by the user.

    Raises:
      InvalidComponentError: If any of the given component ids do not exist.
    """
    md5dict1 = self.HashRcfiles(_SHELL_RCFILES)
    self._EnsureNotDisabled()
    try:
      install_state, diff = self._GetStateAndDiff()
    except snapshots.IncompatibleSchemaVersionError as e:
      return self._ReinstallOnError(e)

    if update_seed:
      invalid_seeds = diff.InvalidUpdateSeeds(update_seed)
      if invalid_seeds:
        if os.environ.get('CLOUDSDK_REINSTALL_COMPONENTS'):
          # We are doing a reinstall.  Ignore any components that no longer
          # exist.
          update_seed = set(update_seed) - invalid_seeds
        else:
          ignored = set(_IGNORED_MISSING_COMPONENTS)
          deprecated = invalid_seeds & ignored
          for item in deprecated:
            log.warning('Component [%s] no longer exists.', item)
            additional_msg = _IGNORED_MISSING_COMPONENTS.get(item)
            if additional_msg:
              log.warning(additional_msg)
          invalid_seeds -= ignored
          if invalid_seeds:
            raise InvalidComponentError(
                'The following components are unknown [{invalid_seeds}]'
                .format(invalid_seeds=', '.join(invalid_seeds)))
          update_seed = set(update_seed) - deprecated
    else:
      update_seed = diff.current.components.keys()

    to_remove = diff.ToRemove(update_seed)
    to_install = diff.ToInstall(update_seed)

    self.__Write(log.status)
    if not to_remove and not to_install:
      self.__Write(log.status, 'All components are up to date.')
      with install_state.LastUpdateCheck() as update_check:
        update_check.SetFromSnapshot(diff.latest, force=True,
                                     platform_filter=self.__platform_filter)
      return True

    disable_backup = self._ShouldDoFastUpdate(allow_no_backup=allow_no_backup)
    self._PrintPendingAction(diff.DetailsForCurrent(to_remove - to_install),
                             'removed')
    self._PrintPendingAction(diff.DetailsForLatest(to_remove & to_install),
                             'updated')
    self._PrintPendingAction(diff.DetailsForLatest(to_install - to_remove),
                             'installed')
    self.__Write(log.status)

    if diff.latest.sdk_definition.release_notes_url:
      self.__Write(log.status,
                   'For the latest release notes, please visit:\n  {0}'
                   .format(diff.latest.sdk_definition.release_notes_url))

    message = self._GetDontCancelMessage(disable_backup)
    if not console_io.PromptContinue(
        message=message, throw_if_unattended=throw_if_unattended):
      return False

    components_to_install = diff.DetailsForLatest(to_install)
    components_to_remove = diff.DetailsForCurrent(to_remove)

    for c in components_to_install:
      metrics.Installs(c.id, c.version.version_string)

    if disable_backup:
      with execution_utils.UninterruptibleSection():
        self.__Write(log.status, 'Performing in place update...\n')
        self._UpdateWithProgressBar(components_to_remove, 'Uninstalling',
                                    install_state.Uninstall)
        self._UpdateWithProgressBar(components_to_install, 'Installing',
                                    self._InstallFunction(install_state, diff))
    else:
      with console_io.ProgressBar(
          label='Creating update staging area', stream=log.status) as pb:
        staging_state = install_state.CloneToStaging(pb.SetProgress)
      self.__Write(log.status)
      self._UpdateWithProgressBar(components_to_remove, 'Uninstalling',
                                  staging_state.Uninstall)
      self._UpdateWithProgressBar(components_to_install, 'Installing',
                                  self._InstallFunction(staging_state, diff))
      self.__Write(log.status)
      self.__Write(log.status,
                   'Creating backup and activating new installation...')
      install_state.ReplaceWith(staging_state)

    with install_state.LastUpdateCheck() as update_check:
      update_check.SetFromSnapshot(diff.latest, force=True,
                                   platform_filter=self.__platform_filter)
    md5dict2 = self.HashRcfiles(_SHELL_RCFILES)
    if md5dict1 != md5dict2:
      self.__Write(log.status,
                   '\nStart a new shell for the changes to take effect.\n')
    self.__Write(log.status, '\nUpdate done!\n')

    if self.__warn:
      bad_commands = self.FindAllOldToolsOnPath()
      if bad_commands and not os.environ.get('CLOUDSDK_REINSTALL_COMPONENTS'):
        log.warning("""\
There are older versions of Google Cloud Platform tools on your system PATH.
Please remove the following to avoid accidentally invoking these old tools:

{0}

""".format('\n'.join(bad_commands)))
    return True

  def FindAllOldToolsOnPath(self, path=None):
    """Searches the PATH for any old Cloud SDK tools.

    Args:
      path: str, A path to use instead of the PATH environment variable.

    Returns:
      {str}, The old executable paths.
    """
    bin_dir = os.path.realpath(
        os.path.join(self.__sdk_root, UpdateManager.BIN_DIR_NAME))
    bad_commands = set()
    if not os.path.exists(bin_dir):
      return bad_commands

    commands = [f for f in os.listdir(bin_dir)
                if os.path.isfile(os.path.join(bin_dir, f)) and
                not f.startswith('.')]

    for command in commands:
      existing_paths = file_utils.SearchForExecutableOnPath(command, path=path)
      if existing_paths:
        this_tool = os.path.join(bin_dir, command)
        bad_commands.update(
            set(os.path.realpath(f) for f in existing_paths)
            - set([this_tool]))
    return bad_commands

  def Remove(self, ids, allow_no_backup=False):
    """Uninstalls the given components.

    Args:
      ids: list of str, The component ids to uninstall.
      allow_no_backup: bool, True if we want to allow the updater to run
        without creating a backup.  This lets us be in the root directory of the
        SDK and still do an update.  It is more fragile if there is a failure,
        so we only do it if necessary.

    Raises:
      InvalidComponentError: If any of the given component ids are not
        installed or cannot be removed.
    """
    self._EnsureNotDisabled()
    if not ids:
      return

    install_state = self._GetInstallState()
    snapshot = install_state.Snapshot()
    id_set = set(ids)
    not_installed = id_set - set(snapshot.components.keys())
    if not_installed:
      raise InvalidComponentError(
          'The following components are not currently installed [{components}]'
          .format(components=', '.join(not_installed)))

    required_components = set(
        c_id for c_id, component in snapshot.components.iteritems()
        if c_id in id_set and component.is_required)
    if required_components:
      raise InvalidComponentError(
          ('The following components are required and cannot be removed '
           '[{components}]')
          .format(components=', '.join(required_components)))

    to_remove = snapshot.ConsumerClosureForComponents(ids)
    if not to_remove:
      self.__Write(log.status, 'No components to remove.\n')
      return

    disable_backup = self._ShouldDoFastUpdate(allow_no_backup=allow_no_backup)
    components_to_remove = sorted(snapshot.ComponentsFromIds(to_remove),
                                  key=lambda c: c.details.display_name)
    self._PrintPendingAction(components_to_remove, 'removed')
    self.__Write(log.status)

    message = self._GetDontCancelMessage(disable_backup)
    if not console_io.PromptContinue(message):
      return

    if disable_backup:
      with execution_utils.UninterruptibleSection():
        self.__Write(log.status, 'Performing in place update...\n')
        self._UpdateWithProgressBar(components_to_remove, 'Uninstalling',
                                    install_state.Uninstall)
    else:
      with console_io.ProgressBar(
          label='Creating update staging area', stream=log.status) as pb:
        staging_state = install_state.CloneToStaging(pb.SetProgress)
      self.__Write(log.status)
      self._UpdateWithProgressBar(components_to_remove, 'Uninstalling',
                                  staging_state.Uninstall)
      self.__Write(log.status)
      self.__Write(log.status,
                   'Creating backup and activating new installation...')
      install_state.ReplaceWith(staging_state)

    self.__Write(log.status, '\nUninstall done!\n')

  def Restore(self):
    """Restores the latest backup installation of the Cloud SDK.

    Raises:
      NoBackupError: If there is no valid backup to restore.
    """
    self._EnsureNotDisabled()
    install_state = self._GetInstallState()
    if not install_state.HasBackup():
      raise NoBackupError('There is currently no backup to restore.')

    self._ShouldDoFastUpdate(allow_no_backup=False, fast_mode_impossible=True)

    if not console_io.PromptContinue(
        message='Your Cloud SDK installation will be restored to its previous '
        'state.'):
      return

    self.__Write(log.status, 'Restoring backup...')
    install_state.RestoreBackup()

    self.__Write(log.status, 'Restoration done!\n')

  def Reinstall(self):
    """Do a reinstall of what we have based on a fresh download of the SDK.

    Returns:
      bool, True if the update succeeded, False if it was cancelled.
    """
    snapshot = self._GetLatestSnapshot()
    schema_version = snapshot.sdk_definition.schema_version
    return self._DoFreshInstall(schema_version.message,
                                schema_version.no_update,
                                schema_version.url)

  def _ReinstallOnError(self, e):
    """Do a reinstall of what we have based on a fresh download of the SDK.

    Args:
      e: snapshots.IncompatibleSchemaVersionError, The exception we got with
        information about the new schema version.

    Returns:
      bool, True if the update succeeded, False if it was cancelled.
    """
    return self._DoFreshInstall(e.schema_version.message,
                                e.schema_version.no_update,
                                e.schema_version.url)

  def _DoFreshInstall(self, message, no_update, download_url):
    """Do a reinstall of what we have based on a fresh download of the SDK.

    Args:
      message: str, A message to show to the user before the re-installation.
      no_update: bool, True to show the message and tell the user they must
        re-download manually.
      download_url: The URL the Cloud SDK can be downloaded from.

    Returns:
      bool, True if the update succeeded, False if it was cancelled.
    """
    self._EnsureNotDisabled()
    if os.environ.get('CLOUDSDK_REINSTALL_COMPONENTS'):
      # We are already reinstalling but got here somehow.  Something is very
      # wrong and we want to avoid the infinite loop.
      self._RaiseReinstallationFailedError()

    # Print out an arbitrary message that we wanted to show users for this
    # update.
    if message:
      self.__Write(log.status, msg=message, word_wrap=True)

    # We can decide that for some reason we just never want to update past this
    # version of the schema.
    if no_update:
      return False

    answer = console_io.PromptContinue(
        message='\nThe component manager must perform a self update before you '
        'can continue.  It and all components will be updated to their '
        'latest versions.')
    if not answer:
      return False

    self._ShouldDoFastUpdate(allow_no_backup=False, fast_mode_impossible=True)
    install_state = self._GetInstallState()

    try:
      with console_io.ProgressBar(
          label='Downloading and extracting updated components',
          stream=log.status) as pb:
        staging_state = install_state.CreateStagingFromDownload(
            download_url, progress_callback=pb.SetProgress)
    except local_state.Error:
      log.error('An updated Cloud SDK failed to download')
      log.debug('Handling re-installation error', exc_info=True)
      self._RaiseReinstallationFailedError()

    # shell out to install script
    installed_component_ids = sorted(install_state.InstalledComponents().keys())
    env = dict(os.environ)
    env['CLOUDSDK_REINSTALL_COMPONENTS'] = ','.join(
        installed_component_ids)
    installer_path = os.path.join(staging_state.sdk_root,
                                  'bin', 'bootstrapping', 'install.py')
    p = subprocess.Popen([sys.executable, '-S', installer_path], env=env)
    ret_val = p.wait()
    if ret_val:
      self._RaiseReinstallationFailedError()

    self.__Write(log.status,
                 'Creating backup and activating new installation...')
    install_state.ReplaceWith(staging_state)

    self.__Write(log.status, '\nComponents updated!\n')
    return True

  def _RaiseReinstallationFailedError(self):
    raise ReinstallationFailedError(
        'An error occurred while reinstalling the Cloud SDK.  Please download'
        ' a new copy from: {url}'.format(
            url=config.INSTALLATION_CONFIG.documentation_url))

  def _EnsureInstalledAndRestart(self, components, msg=None):
    """Installs the given components if necessary and then restarts gcloud.

    Args:
      components: [str], The components that must be installed.
      msg: str, A custom message to print.

    Returns:
      bool, True if the components were already installed.  If installation must
      occur, this method never returns because gcloud is reinvoked after the
      update is done.

    Raises:
      MissingRequiredComponentsError: If the components are not installed and
      the user chooses not to install them.
    """
    current_state = self._GetInstallState()
    missing_components = (set(components) -
                          set(current_state.InstalledComponents()))
    if not missing_components:
      # Already installed, just move on.
      return True

    missing_components_list_str = ', '.join(missing_components)
    if not msg:
      msg = ('This action requires the installation of components: '
             '[{components}]'.format(components=missing_components_list_str))
    self.__Write(log.status, msg, word_wrap=True)

    # Need to install the component.
    if not self.Update(components, throw_if_unattended=True):
      raise MissingRequiredComponentsError("""\
The following components are required to run this command, but are not
currently installed:
  [{components_list}]

To install them, re-run the command and choose 'yes' at the installation
prompt, or run:
  $ gcloud components update {components}

""".format(components_list=missing_components_list_str,
           components=' '.join(missing_components)))

    # Restart the original command.
    execution_utils.RestartGcloud()
