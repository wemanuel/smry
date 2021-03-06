# Copyright 2015 Google Inc. All Rights Reserved.

"""Implementation of gcloud genomics datasets create.
"""

from googlecloudsdk.calliope import base
from googlecloudsdk.core import log
from googlecloudsdk.genomics import lib
from googlecloudsdk.genomics.lib import genomics_util


class DatasetsCreate(base.Command):
  """Creates a dataset with a specified name.

  A dataset is a collection of genomics objects such as reads and variants.
  """

  @staticmethod
  def Args(parser):
    """Register flags for this command."""
    # TODO(user): when b/20336579 is resolved, this parameter goes away
    parser.add_argument('--project-number',
                        type=int,
                        help='The project number to list datasets for.',
                        required=True)
    parser.add_argument(
        'name', help='The name of the dataset being created.')

  @genomics_util.ReraiseHttpException
  def Run(self, args):
    """This is what gets called when the user runs this command.

    Args:
      args: an argparse namespace, All the arguments that were provided to this
        command invocation.

    Raises:
      HttpException: An http error response was received while executing api
          request.
    Returns:
      None
    """
    apitools_client = self.context[lib.GENOMICS_APITOOLS_CLIENT_KEY]
    genomics_messages = self.context[lib.GENOMICS_MESSAGES_MODULE_KEY]

    dataset = genomics_messages.Dataset(
        name=args.name,
        projectNumber=args.project_number,
    )

    return apitools_client.datasets.Create(dataset)

  def Display(self, args_unused, dataset):
    """This method is called to print the result of the Run() method.

    Args:
      args_unused: The arguments that command was run with.
      dataset: The value returned from the Run() method.
    """
    log.Print('Created dataset {0}, id: {1}'.format(dataset.name, dataset.id))
