#!/usr/bin/env python3

import os
import subprocess

from float_utils import logger


class FloatLogin:
    def __init__(self):
        self._info_cmd = ["float", "login", "--info"]

        try:
            address = os.environ["MMC_ADDRESS"]
            username = os.environ["MMC_USERNAME"]
            password = os.environ["MMC_PASSWORD"]
        except KeyError:
            logger.exception("Missing required OpCenter credential(s)")
            raise

        self._login_cmd = [
            "float",
            "login",
            "--address",
            address,
            "--username",
            username,
            "--password",
            password,
        ]

    def login(self):
        try:
            info_cmd = self._info_cmd
            # Check output because we can't print anything
            subprocess.check_output(info_cmd)
        except subprocess.CalledProcessError:
            logger.info("Attempting to log in to OpCenter")
            try:
                login_cmd = self._login_cmd
                # Check output because we can't print anything
                subprocess.check_output(login_cmd)
            except subprocess.CalledProcessError:
                logger.exception("Failed to log in to OpCenter")
                raise

            logger.info("Logged in to OpCenter")
