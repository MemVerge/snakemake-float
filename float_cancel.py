#!/usr/bin/env python3

import asyncio
import json
import sys
from typing import Union

from float_common import Command
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


if __name__ == "__main__":
    job_ids = sys.argv[1:]
    asyncio.run(asyncio.wait([sidecar_cancel(job_id) for job_id in job_ids]))
