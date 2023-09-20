#!/usr/bin/env python3

import asyncio
import datetime
import json
import re
import shlex
import subprocess
from typing import Any, Dict, Tuple

import yaml
from snakemake.common import get_container_image
from snakemake.utils import read_job_properties

from float_common import Command, async_check_output, float_to_snakemake_status, login
from float_logger import logger


class FloatConfig:
    def __init__(self):
        CONFIG_FILE = "snakemake-float.yaml"
        with open(CONFIG_FILE) as config_file:
            config = yaml.safe_load(config_file)
            self.work_dir = config.get("work-dir")
            self.data_volumes = config.get("data-volumes")

        if not self.work_dir:
            raise TypeError("The MMCloud working directory must be specified")
        if not self.data_volumes:
            raise TypeError("At least one data volume must be specified")


class FloatService:
    _CONFIG_FILE = "snakemake-float.yaml"

    def __init__(self):
        self.config = FloatConfig()
        self._response_format = ["--format", "json"]

    async def serve(self):
        """
        Start serving requests from Snakemake executor.
        """
        server = await asyncio.start_server(
            client_connected_cb=self.handle_request,
            host="localhost",
        )

        sidecar_vars = {
            "port": server.sockets[0].getsockname()[1],
            "time": datetime.datetime.now().isoformat().replace(":", ""),
        }

        print(json.dumps(sidecar_vars), flush=True)
        await server.serve_forever()

    async def handle_request(
        self, reader: asyncio.StreamReader, writer: asyncio.StreamWriter
    ):
        """
        Handle submit, status, and cancel requests.
        """
        request_bytes = await reader.readline()
        try:
            request = json.loads(request_bytes.decode())
            command = request["command"]

            if command == Command.SUBMIT:
                job_id = await self.submit(request["job_script"])
                response = {"job_id": job_id}
            elif command == Command.STATUS:
                job_status = await self.status(request["job_id"])
                response = {"job_status": job_status}
            elif command == Command.CANCEL:
                await self.cancel(request["job_id"])
                response = None
            else:
                logger.exception(f"Invalid command in request: {command}")
                raise ValueError

        except json.JSONDecodeError:
            logger.exception(f"Failed to decode request: {request}")
            raise
        except KeyError:
            logger.exception("Request is missing key")
            raise

        if response is not None:
            response_bytes = (json.dumps(response) + "\n").encode()
            writer.write(response_bytes)
            await writer.drain()

        writer.close()
        await writer.wait_closed()

    async def submit(self, job_script: str) -> str:
        """
        Submit the job to the OpCenter and return job id.
        """
        submit_command = [
            "float",
            "submit",
            "--force",
            *self._response_format,
        ]

        job_properties = read_job_properties(job_script)

        min_cpu, min_mem, max_cpu, max_mem = self._get_compute_resources(job_properties)
        submit_command.extend(
            ["--cpu", f"{min_cpu}:{max_cpu}"] if max_cpu else ["--cpu", f"{min_cpu}"]
        )
        submit_command.extend(
            ["--mem", f"{min_mem}:{max_mem}"] if max_mem else ["--mem", f"{min_mem}"]
        )

        resources = job_properties.get("resources", {})

        container_image = resources.get("float_image", get_container_image())
        submit_command.extend(["--image", container_image])

        for data_volume in self.config.data_volumes:
            submit_command.extend(["--dataVolume", data_volume])

        submit_extra = resources.get("float_submit_extra", "")
        submit_command.extend(shlex.split(submit_extra))

        try:
            with open(job_script, "r") as job_file:
                script_lines = job_file.readlines()
                logger.debug("Read job script")
        except OSError:
            logger.exception("Failed to read job script")
            raise

        script_lines.insert(3, f"cd {self.config.work_dir}\n")

        # Hack to allow --use-conda
        exec_job_command = script_lines[-1]
        if "--use-conda" in exec_job_command:
            logger.debug("Prefixing jobscript to allow --use-conda")
            conda_prefix = "/memverge/.snakemake"
            script_lines[3:3] = [
                f"mkdir -p {conda_prefix}/conda\n",
                f"mkdir -p {conda_prefix}/conda-archive\n",
            ]

            # Replace conda-frontend and conda-prefix in jobscript
            exec_job_command = re.sub(r" --conda-frontend '.+'", "", exec_job_command)
            exec_job_command = re.sub(r" --conda-prefix '.+'", "", exec_job_command)

            conda_part = list(exec_job_command.partition(" --use-conda"))
            override = f" --conda-frontend 'mamba' --conda-prefix '{conda_prefix}'"
            conda_part[1] += override
            script_lines[-1] = "".join(conda_part)

        try:
            with open(job_script, "w") as job_file:
                job_file.writelines(script_lines)
                logger.debug("Wrote job script")
        except OSError:
            logger.exception("Failed to write job script")
            raise

        snakemake_job_id = job_properties.get("jobid", "N/A")
        attempt = exec_job_command.partition(" --attempt ")[2].partition(" ")[0]

        job_name = f"snakemake-job_{snakemake_job_id}-attempt_{attempt}"
        submit_command.extend(["--name", job_name])

        submit_command.extend(["--job", job_script])

        logger.info(
            f"Attempt {attempt} to submit Snakemake job {snakemake_job_id} as MMCloud job"
        )
        logger.debug(f"With command: {submit_command}")
        try:
            await login()
            submit_response = await async_check_output(*submit_command)
            submit_response = json.loads(submit_response.decode())
            job_id = submit_response["id"]
        except subprocess.CalledProcessError as e:
            logger.exception(
                f"Failed to submit Snakemake job {snakemake_job_id} as MMCloud job\n"
                f"[stdout] {e.stdout.decode()}\n"
                f"[stderr] {e.stderr.decode()}\n"
            )
            raise
        except (UnicodeError, json.JSONDecodeError):
            logger.exception(
                f"Failed to decode submit response for Snakemake job: {snakemake_job_id}"
            )
            raise
        except KeyError:
            logger.exception(
                f"Failed to obtain MMCloud job id for Snakemake job: {snakemake_job_id}"
            )
            raise

        logger.info(
            f"Submitted Snakemake job {snakemake_job_id} as MMCloud job {job_id}"
        )
        logger.debug(f"OpCenter response: {submit_response}")

        return job_id

    async def status(self, job_id: str) -> str:
        """
        Return the job status from the OpCenter.
        """
        show_command = [
            "float",
            "show",
            *self._response_format,
            "--job",
            job_id,
        ]

        logger.info(f"Attempting to obtain status for MMCloud job {job_id}")
        logger.debug(f"With command: {show_command}")
        try:
            await login()
            show_response = await async_check_output(*show_command)
            show_response = json.loads(show_response.decode())
            job_status = show_response["status"]
        except subprocess.CalledProcessError as e:
            logger.exception(
                f"Failed to get show response for MMCloud job: {job_id}\n"
                f"[stdout] {e.stdout.decode()}\n"
                f"[stderr] {e.stderr.decode()}\n"
            )
            raise
        except (UnicodeError, json.JSONDecodeError):
            logger.exception(
                f"Failed to decode show response for MMCloud job: {job_id}"
            )
            raise
        except KeyError:
            logger.exception(f"Failed to obtain status for MMCloud job: {job_id}")
            raise

        job_status = float_to_snakemake_status(job_status)
        return job_status

    async def cancel(self, job_id: str):
        """
        Cancel the job.
        """
        cancel_command = [
            "float",
            "cancel",
            "--force",
            "--job",
            job_id,
        ]

        logger.info(f"Attempting to cancel MMCloud job {job_id}")
        logger.debug(f"With command: {cancel_command}")
        try:
            await login()
            await async_check_output(*cancel_command)
        except subprocess.CalledProcessError as e:
            logger.exception(
                f"Failed to cancel MMCloud job: {job_id}\n[stdout] {e.stdout.decode()}\n[stderr] {e.stderr.decode()}\n"
            )
            raise

        logger.info(f"Submitted cancel request for MMCloud job: {job_id}")

    def _get_compute_resources(
        self, job_properties: Dict[str, Any]
    ) -> Tuple[int, int, int, int]:
        """
        Get compute resources from job properties.
        """
        resources = job_properties.get("resources", {})

        float_cpu = resources.get("float_cpu")
        float_mem = resources.get("float_mem")

        if isinstance(float_cpu, int):
            min_cpu = float_cpu
            max_cpu = None
        elif isinstance(float_cpu, str):
            min_cpu, max_cpu = [
                int(cpu_resource) for cpu_resource in float_cpu.split(":")
            ]
        else:
            min_cpu = job_properties.get("threads", 1)
            max_cpu = None

        if isinstance(float_mem, int):
            min_mem = float_mem
            max_mem = None
        elif isinstance(float_mem, str):
            min_mem, max_mem = [
                int(mem_resource) for mem_resource in float_mem.split(":")
            ]
        else:
            mem_mib = resources.get("mem_mib", 1024)
            min_mem = (mem_mib + 1023) // 1024
            max_mem = None

        return min_cpu, min_mem, max_cpu, max_mem


if __name__ == "__main__":
    asyncio.run(FloatService().serve())
