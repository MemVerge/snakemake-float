#!/usr/bin/env python3

import os
import sys
import time
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
        self._cmd.extend(['-u', "config_parameters['username']"])
        self._cmd.extend(['-p', config_parameters['password']])

    def job_status(self, jobid):
        cmd = self._cmd
        cmd.extend(['--job', jobid])

        try:
            output = subprocess.check_output(cmd).decode()
        except subprocess.CalledProcessError:
            logger.exception(f"Failed to obtain status for job: {jobid}")
            raise

        status_part = output.partition('status: ')[2].partition('\n')[0]
        status = self._STATUS_MAP[status_part]

        # There are too many status checks to log for normal use
        logger.debug(f"Submitted float show for job: {jobid}")
        logger.debug(f"With command: {cmd}")
        logger.debug(f"Obtained status: {status_part}")
        logger.debug(f"OpCenter response:\n{output}")

        return status


if __name__ == '__main__':
    jobid = sys.argv[1]

    float_status = FloatStatus()
    status = None

    retry_int = 5
    num_retries = 4  # num_attempts - 1
    for attempt in range(num_retries + 1):
        try:
            status = float_status.job_status(jobid)
        except subprocess.CalledProcessError:
            if attempt < num_retries:
                logger.info(
                    f"Retrying status check for job {jobid}"
                    f" in {retry_int} seconds"
                )
                time.sleep(retry_int)
            continue
        break

    if status is None:
        logger.info(f"Failed to obtain status: marking job {jobid} as failed")
        status = 'failed'

    # S3FS may cache file nonexistence: force cache refresh
    if status == 'success':
        os.listdir()

    print(status)
