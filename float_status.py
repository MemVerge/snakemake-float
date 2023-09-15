#!/usr/bin/env python3

import asyncio
import json
import os
import sys

from float_common import Command, logger


async def sidecar_status(port: str, job_id: str) -> str:
    reader, writer = await asyncio.open_connection("localhost", port)
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


async def get_job_status(job_id: str):
    try:
        sidecar_vars = json.loads(os.environ["SNAKEMAKE_CLUSTER_SIDECAR_VARS"])
        port = sidecar_vars["port"]
    except KeyError:
        logger.exception("Missing sidecar vars")
    except json.JSONDecodeError:
        logger.exception("Failed to decode sidecar vars")

    job_status = await sidecar_status(port, job_id)
    return job_status


if __name__ == "__main__":
    job_id = sys.argv[1]
    job_status = asyncio.run(get_job_status(job_id))
    print(job_status)
