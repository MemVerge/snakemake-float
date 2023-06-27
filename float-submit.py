#!/usr/bin/env python3
import sys
import subprocess
import re
import yaml

from snakemake.utils import read_job_properties

CONFIG_FILE = 'snakemake-float.yaml'


class FloatSubmitter:
    required_kwargs = ('address', 'username', 'password', 'dataVolume')

    def __init__(self, **kwargs):
        for kwarg in self.required_kwargs:
            if kwarg not in kwargs:
                raise TypeError(f"{CONFIG_FILE} missing required: '{kwarg}'")

        self.kwargs = kwargs

    def submit_job(self, job_file):
        cmd = ['float', 'submit']

        for key, value in self.kwargs.items():
            if key != 'common-extra':
                cmd.extend([f'--{key}', value])

        cmd.extend(['--image', 'cactus'])
        cmd.extend(['--cpu', '2'])
        cmd.extend(['--mem', '4'])
        cmd.extend(['--job', job_file])

        output = subprocess.check_output(cmd).decode()
        jobid = output[len('id: '): output.index('\n')]
        return jobid


if __name__ == '__main__':
    jobscript = sys.argv[-1]
    job_properties = read_job_properties(jobscript)

    with open(CONFIG_FILE) as cf:
        float_config = yaml.safe_load(cf)

    float_submitter = FloatSubmitter(**float_config)
    jobid = float_submitter.submit_job(jobscript)
    print(jobid)
