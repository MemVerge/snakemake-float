#!/usr/bin/env python3

import asyncio
import json
import sys
from typing import Union

from float_common import Command
from float_logger import logger
from sidecar_vars import SIDECAR_PORT


async def sidecar_submit(port: Union[int, str], job_script: str) -> str:
    reader, writer = await asyncio.open_connection("localhost", SIDECAR_PORT)
    request = {
        "command": Command.SUBMIT,
        "job_id": job_script,
    }
    request_bytes = json.dumps(request).encode()
    writer.write(request_bytes)
    await writer.drain()

    writer.close()
    await writer.wait_closed()

    response_bytes = await reader.read()

    try:
        response = json.loads(response_bytes.decode())
        job_id = response["job_id"]
    except json.JSONDecodeError:
        logger.exception(f"Failed to decode response: {response}")
        raise
    except KeyError:
        logger.exception(f"Missing id in response: {response}")
        raise

    return job_id


if __name__ == "__main__":
    job_script = sys.argv[1]
    job_id = asyncio.run(sidecar_submit(job_script))
    print(job_id)
