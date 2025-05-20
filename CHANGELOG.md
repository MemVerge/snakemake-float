# snakemake-float: Changelog

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/)
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## 0.2.0 - [21-May-2025]

### `Added`

1. Added parameters `max-cpu-factor`, `max-mem-factor` to match the user experience provided by [nf-float](https://github.com/MemVerge/nf-float)
2. Added `--customTag` so that the jobs are bundled into a workflow on MM Cloud OpCentre
3. Added `container-init-snakemake-fsx-efs.sh` for container initialization on MM Cloud OpCentre

### `Fixed`

1. Removed a `match` statement from `float_utils.py` to support Python 3.9
2. Fixed an issue where job memory was not correctly assigned if the pipeline specified `mem_gb` instead of `mem_mib`
3. Fixed an issue where job submission failed due to very low memory requirement compared to the number of required vCPUs
4. Fixed an issue where `--conda-prefix` was ignored and `/memverge/.snakemake` was force specified as the prefix

### `Deprecated`

1. `data-volumes` is no longer a required parameter.

### `Dependencies`

1. Snakemake==7.*.*
2. Python>=3.9