#!/usr/bin/env python3

import os
import sys
import subprocess

from float_config import FloatConfig
from float_utils import logger


class FloatStatus:
    _STATUS_MAP = {
        'Submitted': 'running',
        'Initializing': 'running',
        'Starting': 'running',
        'Executing': 'running',
        'Capturing': 'running',
        'Floating': 'running',
        'Suspended': 'running',
        'Suspending': 'running',
        'Resuming': 'running',
        'Completed': 'success',
        'Cancelled': 'failed',
        'Cancelling': 'failed',
        'FailToComplete': 'failed',
        'FailToExecute': 'failed',
        'CheckpointFailed': 'failed',
        'Timedout': 'failed',
        'NoAvailableHost': 'failed',
        'Unknown': 'failed',
        'WaitingForLicense': 'failed'
    }

    def __init__(self):
        self._cmd = ['float', 'show']

        self._config = FloatConfig()
        config_parameters = self._config.parameters()

        self._cmd.extend(['-a', config_parameters['address']])
        self._cmd.extend(['-u', config_parameters['username']])
        self._cmd.extend(['-p', config_parameters['password']])

    def job_status(self, jobid):
        cmd = self._cmd
        cmd.extend(['--job', jobid])

        output = subprocess.check_output(cmd).decode()
        status_part = output.partition('status: ')[2].partition('\n')[0]
        status = self._STATUS_MAP[status_part]

        # There are too many status checks to log for normal use
        logger.debug(f"Submitted float show for job: {jobid}")
        logger.debug(f"With command: {cmd}")
        logger.debug(f"Obtained status: {status_part}")
        logger.debug(f"OpCenter response: {output}")

        return status


if __name__ == '__main__':
    jobid = sys.argv[1]

    float_status = FloatStatus()
    status = float_status.job_status(jobid)

    # S3FS may cache file nonexistence: force cache refresh
    if status == 'success':
        os.listdir()

    print(status)
