#!/usr/bin/env python3
import asyncio
import datetime
import json
import os
import subprocess

from float_common import Command, async_check_output, logger


class FloatService:
    def __init__(self):
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
        # await server.serve_forever()

    async def handle_request(
        self, reader: asyncio.StreamReader, writer: asyncio.StreamWriter
    ):
        request_bytes = await reader.read()
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
                await self.cancel(request["job_ids"])
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
            response_bytes = json.dumps(response).encode()
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
        Submit the job to the OpCenter.
        """
        pass

    async def status(self, job_id: str) -> str:
        """
        Return the job status from the OpCenter.
        """
        pass

    async def cancel(self, job_ids: str):
        """
        Cancel the jobs.
        """
        pass


if __name__ == "__main__":
    asyncio.run(FloatService().serve())
