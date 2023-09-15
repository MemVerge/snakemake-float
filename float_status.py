#!/usr/bin/env python3

import asyncio
import json
import sys
from typing import Union

from float_common import Command
from float_logger import logger
from sidecar_vars import SIDECAR_PORT


async def sidecar_status(port: Union[int, str], job_id: str) -> str:
    reader, writer = await asyncio.open_connection("localhost", SIDECAR_PORT)
    request = {
        "command": Command.STATUS,
        "job_id": job_id,
    }
    request_bytes = json.dumps(request).encode()
    writer.write(request_bytes)
    await writer.drain()

    writer.close()
    await writer.wait_closed()

    response_bytes = await reader.read()

    try:
        response = json.loads(response_bytes.decode())
        job_status = response["job_status"]
    except json.JSONDecodeError:
        logger.exception(f"Failed to decode response: {response}")
        raise
    except KeyError:
        logger.exception(f"Missing status in response: {response}")
        raise

    return job_status


if __name__ == "__main__":
    job_id = sys.argv[1]
    job_status = asyncio.run(sidecar_status(job_id))
    print(job_status)
