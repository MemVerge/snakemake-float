#!/usr/bin/env python3
'''
import sys
import subprocess
import yaml

from snakemake.utils import read_job_properties


class FloatSubmitter:
    required_kwargs = ('address', 'username', 'password', 'nfs')

    def __init__(self, **kwargs):
        if all(arg in kwargs for arg in self.required_kwargs):
            self.kwargs = kwargs
        else:
            raise TypeError

    def submit_job(self, job_file):
        cmd = ['float', 'submit']

        for key, value in self.kwargs.items():
            cmd.extend([f'--{key}', value])

        cmd.extend(['--job', job_file])

        subprocess.run(cmd)


if __name__ == '__main__':
    jobscript = sys.argv[-1]
    job_properties = read_job_properties(jobscript)

    config_file = 'snakemake-float.yaml'
    try:
        with open(config_file) as cf:
            float_config = yaml.safe_load(cf)
    except:
        pass

    float_submitter = FloatSubmitter(**float_config)
    float_submitter.submit_job(jobscript)
'''