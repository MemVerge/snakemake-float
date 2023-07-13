#!/usr/bin/env python3

import sys
import subprocess

from float_config import FloatConfig


class FloatCancel:
    def __init__(self):
        self._cmd = ['float', 'cancel', '--force']

        self._config = FloatConfig()
        config_parameters = self._config.parameters()

        self._cmd.extend(['-a', config_parameters['address']])
        self._cmd.extend(['-u', config_parameters['username']])
        self._cmd.extend(['-p', config_parameters['password']])

    def cancel_job(self, jobid):
        cmd = self._cmd
        cmd.extend(['--job', jobid])

        subprocess.Popen(cmd)


if __name__ == '__main__':
    jobids = sys.argv[1:]

    float_cancel = FloatCancel()
    for jobid in jobids:
        float_cancel.cancel_job(jobid)
