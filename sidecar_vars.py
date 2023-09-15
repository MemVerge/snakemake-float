#!/usr/bin/env python3

import json
import os

SIDECAR_VARS = json.loads(os.environ["SNAKEMAKE_CLUSTER_SIDECAR_VARS"])
SIDECAR_PORT = SIDECAR_VARS["port"]
SIDECAR_TIME = SIDECAR_VARS["time"]
