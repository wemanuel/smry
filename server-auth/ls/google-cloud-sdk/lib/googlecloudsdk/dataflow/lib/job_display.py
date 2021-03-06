# Copyright 2015 Google Inc. All Rights Reserved.

"""Facility for displaying information about a Job message to a user.
"""

from googlecloudsdk.dataflow.lib import time_util


class DisplayInfo(object):
  """Information about a job displayed in command output.

  Fields:
    job_id: the job ID
    job_name: the job name
    job_type: one of 'batch', 'streaming'
    status: string representing the current job status
    creation_time: in the form yyyy-mm-dd hh:mm:ss
    status_time: in the form yyyy-mm-dd hh:mm:ss
  """

  def __init__(self, job, dataflow_messages):
    self.job_id = job.id
    self.job_name = job.name
    self.job_type = DisplayInfo._JobTypeForJob(job.type, dataflow_messages)
    self.status = DisplayInfo._StatusForJob(job.currentState, dataflow_messages)
    self.status_time = time_util.FormatTimestamp(job.currentStateTime)
    self.creation_time = time_util.FormatTimestamp(job.createTime)

  @staticmethod
  def _JobTypeForJob(job_type, dataflow_messages):
    """Return a string describing the job type.

    Args:
      job_type: The job type enum
      dataflow_messages: dataflow_messages package
    Returns:
      string describing the job type
    """
    type_value_enum = dataflow_messages.Job.TypeValueValuesEnum
    value_map = {
        type_value_enum.JOB_TYPE_BATCH: 'Batch',
        type_value_enum.JOB_TYPE_STREAMING: 'Streaming',
    }
    return value_map.get(job_type, 'Unknown')

  @staticmethod
  def _StatusForJob(job_state, dataflow_messages):
    """Return a string describing the job state.

    Args:
      job_state: The job state enum
      dataflow_messages: dataflow_messages package
    Returns:
      string describing the job state
    """
    state_value_enum = dataflow_messages.Job.CurrentStateValueValuesEnum
    value_map = {
        state_value_enum.JOB_STATE_CANCELLED: 'Cancelled',
        state_value_enum.JOB_STATE_DONE: 'Done',
        state_value_enum.JOB_STATE_FAILED: 'Failed',
        state_value_enum.JOB_STATE_RUNNING: 'Running',
        state_value_enum.JOB_STATE_STOPPED: 'Stopped',
    }
    return value_map.get(job_state, 'Unknown')
