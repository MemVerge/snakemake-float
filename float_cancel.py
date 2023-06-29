#!/usr/bin/env python3

import sys
import subprocess

from float_config import FloatConfig


class FloatCancel:
    def __init__(self):
        self._config = FloatConfig()

    def cancel_job(self, jobid):
        cmd = ['float', 'cancel', '--force']

        config_parameters = self._config.parameters()
        cmd.extend(['-a', config_parameters['address']])
        cmd.extend(['-u', config_parameters['username']])
        cmd.extend(['-p', config_parameters['password']])

        cmd.extend(['--job', jobid])

        subprocess.check_call(cmd)


if __name__ == '__main__':
    jobids = sys.argv[1:]

    float_cancel = FloatCancel()
    for jobid in jobids:
        float_cancel.cancel_job(jobid)
