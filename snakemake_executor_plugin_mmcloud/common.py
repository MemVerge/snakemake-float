import asyncio
import shlex
import subprocess
from asyncio.subprocess import PIPE
from enum import StrEnum


class Status(StrEnum):
    RUNNING = "RUNNING"
    SUCCESS = "SUCCESS"
    FAILURE = "FAILURE"


STATUS_MAP = {
    "Submitted": Status.RUNNING,
    "Initializing": Status.RUNNING,
    "Starting": Status.RUNNING,
    "Executing": Status.RUNNING,
    "Capturing": Status.RUNNING,
    "Floating": Status.RUNNING,
    "Suspended": Status.RUNNING,
    "Suspending": Status.RUNNING,
    "Resuming": Status.RUNNING,
    "Completed": Status.SUCCESS,
    "Cancelled": Status.FAILURE,
    "Cancelling": Status.FAILURE,
    "FailToComplete": Status.FAILURE,
    "FailToExecute": Status.FAILURE,
    "CheckpointFailed": Status.FAILURE,
    "Timedout": Status.FAILURE,
    "NoAvailableHost": Status.FAILURE,
    "Unknown": Status.FAILURE,
    "WaitingForLicense": Status.FAILURE,
}


def status_map(status: str) -> Status:
    return STATUS_MAP[status]


async def async_check_output(*args, **kwargs):
    """
    This behaves similarly to subprocess.check_output().
    """
    process = await asyncio.create_subprocess_exec(*args, stdout=PIPE, stderr=PIPE, **kwargs)
    stdout, stderr = await process.communicate()
    returncode = process.returncode
    if returncode != 0:
        raise subprocess.CalledProcessError(returncode, shlex.join(args), output=stdout, stderr=stderr)
    return stdout
