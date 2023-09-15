# snakemake-float

Snakemake cluster execution profile plugin to allow executing Snakemake jobs using MemVerge Memory Machine Cloud (float).

## Install profile

First, install [Mamba](https://mamba.readthedocs.io/en/latest/mamba-installation.html#mamba-install) (alternatively, [Conda](https://conda.io/projects/conda/en/latest/user-guide/install/index.html)) and [Snakemake](https://snakemake.readthedocs.io/en/stable/getting_started/installation.html).

Download and extract the profile source code to `~/.config/snakemake/snakemake-float/`.

## Configuration

Set the following environment variables:
* `MMC_ADDRESS`: MMCloud OpCenter address
* `MMC_USERNAME`: MMCloud OpCenter username
* `MMC_PASSWORD`: MMCloud OpCenter password