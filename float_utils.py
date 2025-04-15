#!/usr/bin/env python3

import os

import logging

LOG_LEVEL_MAP = {
    'CRITICAL': logging.CRITICAL,
    'ERROR': logging.ERROR,
    'WARNING': logging.WARNING,
    'INFO': logging.INFO,
    'DEBUG': logging.DEBUG
}

LOG_FILE = (
    '.snakemake/log/'
    f"{os.environ.get('SNAKEMAKE_CLUSTER_SIDECAR_VARS', 'snakemake')}"
    '.float.log'
)

log_level = os.environ.get('SNAKEMAKE_FLOAT_LOG_LEVEL', 'INFO')
log_level = LOG_LEVEL_MAP.get(log_level, logging.NOTSET)

logging.basicConfig(
    filename=LOG_FILE,
    format='[%(asctime)s] [FLOAT] %(levelname)s: %(message)s',
    level=log_level
)

logger = logging.getLogger(__name__)
