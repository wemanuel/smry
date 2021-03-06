# Copyright 2014 Google Inc. All Rights Reserved.

"""The main command group for genomics.

Everything under here will be the commands in your group.  Each file results in
a command with that name.

This module contains a single class that extends base.Group.  Calliope will
dynamically search for the implementing class and use that as the command group
for this command tree.  You can implement methods in this class to override some
of the default behavior.
"""

from googlecloudapis.genomics import v1beta2 as genomics_v1beta2
from googlecloudapis.genomics.v1beta2 import genomics_v1beta2_messages as v1beta2_messages
from googlecloudsdk.calliope import base
from googlecloudsdk.calliope import exceptions
from googlecloudsdk.core import properties
from googlecloudsdk.core.credentials import store
from googlecloudsdk.genomics import lib


@base.ReleaseTracks(base.ReleaseTrack.ALPHA)
class Genomics(base.Group):
  """Manage Genomics resources using version 1 beta 2 of the API."""

  @staticmethod
  def Args(parser):
    """Args is called by calliope to gather arguments for this command.

    Args:
      parser: An argparse parser that you can use to add arguments that go
          on the command line after this command. Positional arguments are
          allowed.
    """
    pass

  def Filter(self, context, args):
    """Setup the API client within the context for this group's commands.

    Args:
      context: {str:object}, A set of key-value pairs that can be used for
          common initialization among commands.
      args: argparse.Namespace: The same namespace given to the corresponding
          .Run() invocation.

    Returns:
      The updated context.
    """

    # TODO(user): make use of resources.Parse().

    # Apitools client to make API requests.
    context[lib.GENOMICS_APITOOLS_CLIENT_KEY] = (
        genomics_v1beta2.GenomicsV1beta2(
            url=properties.VALUES.api_endpoint_overrides.genomics.Get(),
            get_credentials=False,
            http=self.Http())
    )
    context[lib.GENOMICS_MESSAGES_MODULE_KEY] = v1beta2_messages

    return context
