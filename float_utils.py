#!/usr/bin/env python3

import os

import logging

LOG_FILE = (
    '.snakemake/log/'
    f"{os.environ.get('SNAKEMAKE_CLUSTER_SIDECAR_VARS', 'snakemake')}"
    '.float.log'
)

log_level = os.environ.get('SNAKEMAKE_FLOAT_LOG_LEVEL', 'INFO')
match log_level:
    case 'CRITICAL':
        log_level = logging.CRITICAL
    case 'ERROR':
        log_level = logging.ERROR
    case 'WARNING':
        log_level = logging.WARNING
    case 'INFO':
        log_level = logging.INFO
    case 'DEBUG':
        log_level = logging.DEBUG
    case _:
        log_level = logging.NOTSET

logging.basicConfig(
    filename=LOG_FILE,
    format='[%(asctime)s] [FLOAT] %(levelname)s: %(message)s',
    level=log_level
)

logger = logging.getLogger(__name__)
