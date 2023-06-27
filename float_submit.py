#!/usr/bin/env python3

import sys
import subprocess

from snakemake.utils import read_job_properties

from float_config import FloatConfig


class FloatSubmit:
    def __init__(self):
        self._config = FloatConfig()

    def submit_job(self, job_file):
        cmd = ['float', 'submit']

        for key, value in self._config.parameters().items():
            if key != 'common-extra':
                cmd.extend([f'--{key}', value])

        cmd.extend(['--job', job_file])

        output = subprocess.check_output(cmd).decode()
        jobid = output[len('id: '): output.index('\n')]
        return jobid


if __name__ == '__main__':
    jobscript = sys.argv[1]
    job_properties = read_job_properties(jobscript)

    float_submit = FloatSubmit()
    jobid = float_submit.submit_job(jobscript)
    print(jobid)
