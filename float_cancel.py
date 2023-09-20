#!/usr/bin/env python3

import asyncio
import json
import subprocess
import sys
from typing import List

from float_common import Command, login
from float_logger import logger
from sidecar_vars import SIDECAR_PORT


async def sidecar_cancel(job_id: str):
    """
    Open a connection with sidecar and cancel job.
    """
    reader, writer = await asyncio.open_connection("localhost", SIDECAR_PORT)

    request = {
        "command": Command.CANCEL,
        "job_id": job_id,
    }

    request_bytes = (json.dumps(request) + "\n").encode()
    writer.write(request_bytes)
    await writer.drain()

    writer.close()
    await writer.wait_closed()


async def cancel(job_id):
    """
    Attempt to cancel job.
    """
    cancel_command = ["float", "cancel", "--force", "--job", job_id]

    logger.info(f"Attempting to cancel MMCloud job {job_id}")
    logger.debug(f"With command: {cancel_command}")

    await login()
    subprocess.Popen(cancel_command)

    logger.info(f"Sent request to cancel MMCloud job: {job_id}")


async def cancel_jobs(job_ids: List[str]):
    # This is commented because sidecar shuts down too early when interrupted to cancel using sidecar.
    # await asyncio.gather(*[sidecar_cancel(job_id) for job_id in job_ids])

    await asyncio.gather(*[cancel(job_id) for job_id in job_ids])


if __name__ == "__main__":
    job_ids = sys.argv[1:]
    asyncio.run(cancel_jobs(job_ids))
