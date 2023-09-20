#!/usr/bin/env python3

import asyncio
import os
import shlex
import subprocess
from asyncio.subprocess import PIPE
from enum import StrEnum

from float_logger import logger


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


async def login():
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
