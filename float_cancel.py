#!/usr/bin/env python3

import asyncio
import json
import os
import sys

from float_common import Command, logger


async def sidecar_cancel(port: str, job_id: str):
    reader, writer = await asyncio.open_connection("localhost", port)
    request = {
        "command": Command.CANCEL,
        "job_id": job_id,
    }
    request_bytes = json.dumps(request).encode()
    writer.write(request_bytes)
    await writer.drain()

    writer.close()
    await writer.wait_closed()


async def cancel_jobs(job_ids: list[str]):
    try:
        sidecar_vars = json.loads(os.environ["SNAKEMAKE_CLUSTER_SIDECAR_VARS"])
        port = sidecar_vars["port"]
    except KeyError:
        logger.exception("Missing sidecar vars")
    except json.JSONDecodeError:
        logger.exception("Failed to decode sidecar vars")

    await asyncio.gather(*[sidecar_cancel(port, job_id) for job_id in job_ids])


if __name__ == "__main__":
    job_ids = sys.argv[1:]
    asyncio.run(cancel_jobs(job_ids))
