#!/usr/bin/env python3

import asyncio
import datetime
import json
import os
import subprocess
from typing import Any, Dict, Tuple

from snakemake.common import get_container_image
from snakemake.utils import read_job_properties

from float_common import Command, async_check_output, float_to_snakemake_status
from float_logger import logger


class FloatService:
    def __init__(self):
        self._response_format = ["--format", "json"]

    def _get_compute_resources(job_properties: Dict[str, Any]) -> Tuple[int, int, int, int]:
        resources = job_properties.get("resources", {})

        float_cpu = resources.get("float_cpu")
        float_mem = resources.get("float_mem")

        if isinstance(float_cpu, int):
            min_cpu = float_cpu
            max_cpu = None
        elif isinstance(float_cpu, str):
            min_cpu, max_cpu = [int(cpu_resource) for cpu_resource in float_cpu.split(":")]
        else:
            threads = job_properties.get("threads", 1)
            min_cpu = threads
            max_cpu = threads

        if isinstance(float_mem, int):
            min_mem = float_mem
            max_mem = None
        elif isinstance(float_mem, str):
            min_mem, max_mem = [int(mem_resource) for mem_resource in float_mem.split(":")]
        else:
            mem_mib = resources.get("mem_mib", 1024)
            mem_gib = (mem_mib + 1023) // 1024
            min_mem = mem_gib
            max_mem = mem_gib

        return min_cpu, min_mem, max_cpu, max_mem

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

    async def login(self):
        """
        Log in to Memory Machine Cloud OpCenter.
        """
        try:
            # If already logged in, this will reset the session timer
            login_info_command = ["float", "login", "--info"]
            await async_check_output(*login_info_command)
        except subprocess.CalledProcessError:
            logger.info("Attempting to log in to OpCenter")
            try:
                login_command = [
                    "float",
                    "login",
                    "--address",
                    os.environ.get("MMC_ADDRESS"),
                    "--username",
                    os.environ.get("MMC_USERNAME"),
                    "--password",
                    os.environ.get("MMC_PASSWORD"),
                ]
                await async_check_output(*login_command)
            except subprocess.CalledProcessError:
                logger.exception("Failed to log in to OpCenter")
                raise

            logger.info("Logged in to OpCenter")

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
        submit_command.extend(["--cpu", f"{min_cpu}:{max_cpu}"] if max_cpu else ["--cpu", f"{min_cpu}"])
        submit_command.extend(["--mem", f"{min_mem}:{max_mem}"] if max_mem else ["--mem", f"{min_mem}"])

        resources = job_properties.get("resources", {})

        container_image = resources.get("float_image", get_container_image())
        submit_command.extend("--image", container_image)

        # TODO: Implement

        return "FILLER_JOB_ID"

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
            await self.login()
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
            logger.exception(f"Failed to decode show response for MMCloud job: {job_id}")
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
            await self.login()
            await async_check_output(*cancel_command)
        except subprocess.CalledProcessError as e:
            logger.exception(
                f"Failed to cancel MMCloud job: {job_id}\n[stdout] {e.stdout.decode()}\n[stderr] {e.stderr.decode()}\n"
            )
            raise

        logger.info(f"Submitted cancel request for MMCloud job: {job_id}")

if __name__ == "__main__":
    asyncio.run(FloatService().serve())
