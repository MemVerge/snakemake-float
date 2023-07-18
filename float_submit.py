#!/usr/bin/env python3

import sys
import subprocess

from snakemake.utils import read_job_properties

from float_config import FloatConfig
from float_utils import logger


class FloatSubmit:
    _AWS_CPU_UPPER_BOUND = 192
    _AWS_MEM_UPPER_BOUND = 1024

    def __init__(self):
        self._config = FloatConfig()

    def submit_job(self, job_file):
        cfg = self._config
        cmd = 'float submit'

        config_parameters = cfg.parameters()
        for key, value in config_parameters.items():
            if key != cfg.SUBMIT_EXTRA:
                cmd += f" --{key} {value}"

        job_properties = read_job_properties(jobscript)
        if 'cpu' not in config_parameters:
            cpu = max(job_properties.get('threads'), 2)
            cmd += f" --cpu {cpu}:{self._AWS_CPU_UPPER_BOUND}"

        if 'mem' not in config_parameters:
            mem_MiB = max(
                job_properties.get('resources', {}).get('mem_mib'),
                4096
            )
            mem_GiB = (mem_MiB + 1023) // 1024
            cmd += f" --mem {mem_GiB}:{self._AWS_MEM_UPPER_BOUND}"

        cmd += f" --job {job_file}"
        cmd += f" {config_parameters.get(cfg.SUBMIT_EXTRA, '')}"

        output = subprocess.check_output(cmd, shell=True).decode()
        jobid = output.partition('id: ')[2].partition('\n')[0]

        logger.info(f"Submitted float job with id: {jobid}")
        logger.debug(f"With command: {cmd}")
        logger.debug(f"OpCenter response: {output}")

        return jobid

    def mount_point(self):
        cfg = self._config
        config_parameters = cfg.parameters()

        dv = config_parameters['dataVolume']
        start = dv.index('//')
        colon = dv.index(':', start)

        if colon == -1:
            logger.error('dataVolume mount point not specified')
            raise ValueError('Please specify dataVolume mount point')

        return dv[colon + 1:]


if __name__ == '__main__':
    jobscript = sys.argv[1]

    float_submit = FloatSubmit()

    try:
        with open(jobscript, 'r') as js:
            script_lines = js.readlines()
    except OSError:
        logger.error(f"Cannot open jobscript for reading: {jobscript}")
        raise

    script_lines.insert(3, f"cd {float_submit.mount_point()}\n")

    # Hack to allow --use-conda
    exec_job_cmd = script_lines[-1]
    if '--use-conda' in exec_job_cmd:
        logger.debug('Prefixing jobscript to allow --use-conda')
        conda_prefix = '/memverge/.snakemake'
        script_lines[3: 3] = [
            f"mkdir -p {conda_prefix}/conda\n",
            f"mkdir -p {conda_prefix}/conda-archive\n"
        ]

        part = list(exec_job_cmd.partition(' --use-conda'))
        part[1] += f" --conda-prefix '{conda_prefix}'"
        script_lines[-1] = ''.join(part)

    try:
        with open(jobscript, 'w') as js:
            js.writelines(script_lines)
    except OSError:
        logger.error(f"Cannot open jobscript for writing: {jobscript}")
        raise

    jobid = float_submit.submit_job(jobscript)
    print(jobid)
