#!/usr/bin/env python3

import logging
import os

LOG_LEVEL = os.environ.get("SNAKEMAKE_FLOAT_LOG_LEVEL", "INFO").upper()
logging.basicConfig(
    filename=".snakemake/log/snakemake-float.log",
    format="[%(asctime)s] [FLOAT] %(levelname)s: %(message)s",
    level=LOG_LEVEL,
)

logger = logging.getLogger(__name__)
