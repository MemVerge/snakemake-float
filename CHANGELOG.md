# snakemake-float: Changelog

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/)
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## 0.2.0dev - [15-April-2025]

### `Added`

1. Added parameters `max-cpu-factor`, `max-mem-factor` to match the user experience provided by [nf-float](https://github.com/MemVerge/nf-float)
2. Added `--customTag` so that the jobs are bundled into a workflow on MM Cloud OpCentre

### `Fixed`

1. Removed a `match` statement from `float_utils.py` to support Python 3.9

### `Dependencies`

1. Snakemake==7
2. Python>=3.9