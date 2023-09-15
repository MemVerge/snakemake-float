#!/usr/bin/env python3

import asyncio
import logging
import os
import shlex
import subprocess
from asyncio.subprocess import PIPE
from enum import Enum


class Command(Enum):
    SUBMIT = 1
    STATUS = 2
    CANCEL = 3


LOG_LEVEL = os.environ.get("SNAKEMAKE_FLOAT_LOG_LEVEL", "INFO").upper()
logging.basicConfig(
    level=LOG_LEVEL,
    format="[%(asctime)s] [FLOAT] %(levelname)s: %(message)s",
)
logger = logging.getLogger(__name__)


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
