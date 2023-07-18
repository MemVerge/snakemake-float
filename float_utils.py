#!/usr/bin/env python3

import os

import logging

LOG_FILE = (
    '.snakemake/log/'
    f"{os.environ.get('SNAKEMAKE_CLUSTER_SIDECAR_VARS', 'snakemake')}"
    '.float.log'
)

log_level = logging.INFO

logging.basicConfig(
    filename=LOG_FILE,
    format='[%(asctime)s] [FLOAT] %(levelname)s: %(message)s',
    level=log_level
)

logger = logging.getLogger(__name__)
