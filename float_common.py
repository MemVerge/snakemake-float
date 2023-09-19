#!/usr/bin/env python3

import asyncio
import shlex
import subprocess
from asyncio.subprocess import PIPE
from enum import StrEnum

class Command(StrEnum):
    SUBMIT = "SUBMIT"
    STATUS = "STATUS"
    CANCEL = "CANCEL"

FLOAT_TO_SNAKEMAKE_STATUS = {
    "Submitted": "running",
    "Initializing": "running",
    "Starting": "running",
    "Executing": "running",
    "Capturing": "running",
    "Floating": "running",
    "Suspended": "running",
    "Suspending": "running",
    "Resuming": "running",
    "Completed": "success",
    "Cancelled": "failed",
    "Cancelling": "failed",
    "FailToComplete": "failed",
    "FailToExecute": "failed",
    "CheckpointFailed": "failed",
    "Timedout": "failed",
    "NoAvailableHost": "failed",
    "Unknown": "failed",
    "WaitingForLicense": "failed",
}


def float_to_snakemake_status(job_status: str) -> str:
    """
    Map float status to Snakemake status.
    """
    return FLOAT_TO_SNAKEMAKE_STATUS[job_status]


async def async_check_output(*args, **kwargs):
    """
    This behaves similarly to subprocess.check_output().
    """
    process = await asyncio.create_subprocess_exec(
        *args, stdout=PIPE, stderr=PIPE, **kwargs
    )
    stdout, stderr = await process.communicate()
    returncode = process.returncode
    if returncode != 0:
        raise subprocess.CalledProcessError(
            returncode, shlex.join(args), output=stdout, stderr=stderr
        )
    return stdout
