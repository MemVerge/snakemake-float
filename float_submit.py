#!/usr/bin/env python3

import json
import re
import shlex
import sys
import math
import subprocess

from snakemake.utils import read_job_properties

from float_config import FloatConfig
from float_login import FloatLogin
from float_utils import logger


class FloatSubmit:

    def __init__(self):
        self._cmd = ['float', 'submit', '--force', '--format', 'json']

        self._config = FloatConfig()

    def submit_job(self, job_file):
        cmd = self._cmd
        cfg = self._config
        config_parameters = cfg.parameters()

        cmd.extend(['--image', config_parameters['base-image']])

        if 'data-volumes' in config_parameters:
            for data_volume in config_parameters['data-volumes']:
                cmd.extend(['--dataVolume', data_volume])

        job_properties = read_job_properties(jobscript)
        if 'cpu' in config_parameters:
            cpu = int(config_parameters['cpu'])
            max_cpu = math.ceil(self._config.max_cpu_factor() * float(cpu))
            cmd.extend(['--cpu', f"{cpu}:{max_cpu}"])
        else:
            cpu = int(max(job_properties.get('threads'), 2))
            max_cpu = math.ceil(self._config.max_cpu_factor() * float(cpu))
            cmd.extend(['--cpu', f"{cpu}:{max_cpu}"])

        if 'mem' in config_parameters:
            mem = config_parameters['mem']
            max_mem = math.ceil(self._config.max_mem_factor() * float(mem))
            cmd.extend(['--mem', f"{mem}:{max_mem}"])
        else:
            job_resources = job_properties.get('resources', {})
            
            mem_MiB = int(max(
                job_resources.get('mem_mib'),
                4096
            ))

            # Check if mem_gb is specified and pick the greater of the two
            mem_gb_spec = int(job_resources.get('mem_gb', 4))

            mem_GiB = max((mem_MiB + 1023) // 1024, mem_gb_spec)

            # Some pipelines use file size to determine memory which can create problems on
            # AWS as no instance has memory less tha 2x the number of vCPUs
            min_allowed_mem_gb = 2 * cpu
            mem_GiB = max(mem_GiB, min_allowed_mem_gb)

            max_mem = math.ceil(self._config.max_mem_factor() * float(mem_GiB))
            cmd.extend(['--mem', f"{mem_GiB}:{max_mem}"])

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
        cmd.extend(['--name', job_name])

        cmd.extend(['--job', job_file])
        cmd.extend(shlex.split(config_parameters.get('submit-extra', '')))

        rule_name = job_properties.get('rule')
        cmd.extend(['--customTag', f"nextflow-io-run-name:{job_prefix}"])
        cmd.extend(['--customTag', f"nextflow-io-project-name:{job_prefix}"])
        cmd.extend(['--customTag', f"nextflow-io-process-name:{rule_name}"])
        
        logger.info(f"Attempt {attempt} to submit Snakemake job {snakejob}")

        try:
            FloatLogin().login()
            output = subprocess.check_output(cmd)
            output = json.loads(output.decode())
            jobid = output['id']
        except subprocess.CalledProcessError:
            msg = 'Failed to submit job'
            logger.exception(msg)
            raise
        except (UnicodeError, json.JSONDecodeError):
            msg = 'Failed to decode submit response'
            logger.exception(msg)
            raise
        except KeyError:
            msg = 'Failed to obtain float job id'
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
        override = f" --conda-frontend 'mamba' --conda-prefix '{conda_prefix}'"
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
