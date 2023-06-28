#!/usr/bin/env python3

import sys
import subprocess

from snakemake.utils import read_job_properties

from float_config import FloatConfig


class FloatSubmit:
    def __init__(self):
        self._config = FloatConfig()

    def submit_job(self, job_file):
        cfg = self._config
        cmd = 'float submit'

        config_parameters = cfg.parameters()
        for key, value in config_parameters.items():
            if key != cfg.SUBMIT_EXTRA:
                cmd += f" --{key} {value}"

        cmd += f" --job {job_file}"
        cmd += f" {config_parameters.get(cfg.SUBMIT_EXTRA, '')}"

        output = subprocess.check_output(cmd, shell=True).decode()
        jobid = output[len('id: '): output.index('\n')]
        return jobid

    def mount_point(self):
        cfg = self._config
        config_parameters = cfg.parameters()

        dv = config_parameters['dataVolume']
        start = dv.index('//')
        colon = dv.index(':', start)

        if colon == -1:
            raise ValueError('Please specify dataVolume mount point')

        return dv[colon + 1:]


if __name__ == '__main__':
    jobscript = sys.argv[1]
    job_properties = read_job_properties(jobscript)

    float_submit = FloatSubmit()

    with open(jobscript, 'r') as js:
        script_lines = js.readlines()

    with open(jobscript, 'w') as js:
        script_lines.insert(3, f"cd {float_submit.mount_point()}\n")
        js.writelines(script_lines)

    jobid = float_submit.submit_job(jobscript)
    print(jobid)
