#!/usr/bin/env python3

import json
import re
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
        config_parameters = cfg.parameters()

        cmd = 'float submit --force --format json'

        cmd += f" -a {config_parameters['address']}"
        cmd += f" -u {config_parameters['username']}"
        cmd += f" -p {config_parameters['password']}"

        cmd += f" --image {config_parameters['base-image']}"

        for data_volume in config_parameters['data-volumes']:
            cmd += f" --dataVolume {data_volume}"

        job_properties = read_job_properties(jobscript)
        if 'cpu' in config_parameters:
            cmd += f" --cpu {config_parameters['cpu']}"
        else:
            cpu = max(job_properties.get('threads'), 2)
            cmd += f" --cpu {cpu}:{self._AWS_CPU_UPPER_BOUND}"

        if 'mem' in config_parameters:
            cmd += f" --mem {config_parameters['mem']}"
        else:
            mem_MiB = max(
                job_properties.get('resources', {}).get('mem_mib'),
                4096
            )
            mem_GiB = (mem_MiB + 1023) // 1024
            cmd += f" --mem {mem_GiB}:{self._AWS_MEM_UPPER_BOUND}"

        try:
            with open(job_file, 'r') as jf:
                script_lines = jf.readlines()
                logger.debug('Opened job file for reading')
        except OSError:
            logger.exception('Cannot open job file for reading')
            raise

        exec_job_cmd = script_lines[-1]
        attempt = exec_job_cmd.partition(' --attempt ')[2].partition(' ')[0]

        snakejob = job_properties.get('jobid', 'N/A')

        job_prefix = config_parameters.get('job-prefix', 'snakemake')
        job_name = f"{job_prefix}-job_{snakejob}-attempt_{attempt}"
        cmd += f" --name {job_name}"

        cmd += f" --job {job_file}"
        cmd += f" {config_parameters.get('submit-extra', '')}"

        logger.info(f"Attempt {attempt} to submit Snakemake job {snakejob}")
        try:
            output = subprocess.check_output(cmd, shell=True).decode()
        except subprocess.CalledProcessError:
            logger.exception('Failed to submit job')
            raise

        try:
            output = subprocess.check_output(cmd, shell=True)
            output = json.loads(output.decode())
            jobid = output["id"]
        except subprocess.CalledProcessError:
            msg = "Failed to submit job"
            logger.exception(msg)
            raise
        except (UnicodeError, json.JSONDecodeError):
            msg = "Failed to decode submit response"
            logger.exception(msg)
            raise
        except KeyError:
            msg = "Failed to obtain float job id"
            logger.exception(msg)
            raise

        logger.info(
            f"Submitted Snakemake job {snakejob}"
            f" as float job {jobid} with name {job_name}"
        )
        logger.debug(f"With command: {cmd}")
        logger.debug(f"OpCenter response:\n{output}")

        return jobid

    def work_dir(self):
        return self._config.parameters()['work-dir']


if __name__ == '__main__':
    jobscript = sys.argv[1]

    float_submit = FloatSubmit()

    try:
        with open(jobscript, 'r') as js:
            script_lines = js.readlines()
            logger.debug('Opened jobscript for reading')
    except OSError:
        logger.exception('Cannot open jobscript for reading')
        raise

    script_lines.insert(3, f"cd {float_submit.work_dir()}\n")

    # Hack to allow --use-conda
    exec_job_cmd = script_lines[-1]
    if '--use-conda' in exec_job_cmd:
        logger.debug('Prefixing jobscript to allow --use-conda')
        conda_prefix = '/memverge/.snakemake'
        script_lines[3: 3] = [
            f"mkdir -p {conda_prefix}/conda\n",
            f"mkdir -p {conda_prefix}/conda-archive\n"
        ]

        # Replace conda-frontend and conda-prefix in jobscript
        exec_job_cmd = re.sub(r" --conda-frontend '.+'", '', exec_job_cmd)
        exec_job_cmd = re.sub(r" --conda-prefix '.+'", '', exec_job_cmd)

        conda_part = list(exec_job_cmd.partition(' --use-conda'))
        override = f" --conda-frontend 'conda' --conda-prefix '{conda_prefix}'"
        conda_part[1] += override
        script_lines[-1] = ''.join(conda_part)

    try:
        with open(jobscript, 'w') as js:
            js.writelines(script_lines)
            logger.debug('Wrote modifications to jobscript ')
    except OSError:
        logger.exception('Cannot open jobscript for writing')
        raise

    jobid = float_submit.submit_job(jobscript)
    print(jobid)
