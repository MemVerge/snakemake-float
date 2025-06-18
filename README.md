# snakemake-float

[![Python 3.9](https://img.shields.io/badge/python-3.9-blue.svg)](https://www.python.org/downloads/release/python-390/)
[![Snakemake 7](https://img.shields.io/badge/snakemake-7-blue.svg)](https://github.com/snakemake/snakemake/tree/v7.32.4)

Snakemake cluster execution profile plugin to allow executing Snakemake jobs using MemVerge Memory Machine Cloud (float).

## Install profile

First, install [Mamba](https://mamba.readthedocs.io/en/latest/mamba-installation.html#mamba-install) (alternatively, [Conda](https://conda.io/projects/conda/en/latest/user-guide/install/index.html)) and [Snakemake](https://snakemake.readthedocs.io/en/stable/getting_started/installation.html).

Download and extract the profile source code to `~/.config/snakemake/snakemake-float/`.

## Configuration

Set the following environment variables:
* `MMC_ADDRESS`: MMCloud OpCenter address
* `MMC_USERNAME`: MMCloud OpCenter username
* `MMC_PASSWORD`: MMCloud OpCenter password

In the Snakemake working directory, create file `snakemake-float.yaml` based on the template, specifying arguments to pass to  `float` for job submission.

* `work-dir` [required]: specifies the work directory for all worker nodes. This should be the same as `-d` or `--directory` parameter passed to `snakemake`.
* `data-volumes` [optional]: specifies a list of data volumes for all worker nodes.
* `job-prefix` [optional]: specifies a string to prefix job names with. This will also be used as the workflow run name in the MM Cloud OpCentre.
* `base-image` [optional]: specifies a container image to execute jobs with. Must have `snakemake` installed. If left empty, an image with `snakemake` version corresponding to the head node is automatically selected.
* `cpu` [optional]: specifies cpu for all worker nodes. Overrides values inferred from workflow.
* `mem` [optional]: specifies mem for all worker nodes in GBs. Overrides values inferred from workflow.
* `max-cpu-factor` [optional]: a float number. defaults to 4.0. The maximum CPU cores of the instance is set to maxCpuFactor * cpus of the task.
* `max-mem-factor` [optional]: a float number. defaults to 4.0. The maximum memory of the instance is set to maxMemoryFactor * memory of the task.
* `submit-extra` [optional]: specifies arguments, as a string, to append to the [`float submit`](https://docs.memverge.com/MMCloud/latest/User%20Guide/Reference%20Guides/cli_summary/#float-submit) command. Storages registered in the MM Cloud can be mounted on all worker nodes by passing them here with `--storage` parameter.

### Cluster configuration

Default cluster configuration is defined in [config.yaml](./config.yaml). By default, `no-shared-fs` is set to `true`, `rerun-incomplete` to `true` and `retries` to 0. These defaults can be overridden by `snakemake` command line arguments.

## Software dependencies

> [!Warning]
> When using `--conda-create-envs-only`, do not include `--profile snakemake-float` as this causes the pipeline to exit without creating the conda environments.

There are two ways in which dependencies can be managed,

- `A fat container:` Using a single docker container which has all the software dependencies pre-loaded. For example, `quay.io/biocontainers/verkko:2.2.1--h45dadce_0` for the [verkko](https://github.com/marbl/verkko) pipeline. This can be specified against `base-image` in `snakemake-float.yaml`.
- `Conda/Mamba:` Using Conda/Mamba to create all the necessary Conda environments before processing the data. This can be achieved by telling `snakemake` to `--use-conda`, with `--conda-prefix` pointing to a location accessible to all the nodes and telling snakemake to `--conda-create-envs-only`. Once the conda environments have been created, the data can be processed by removing the `--conda-create-envs-only` and resuming the pipeline.

Containers specified by the `singularity` directive in the workflow are not supported.

## Shared working directory

MM Cloud supports a wide range of file systems [Amazon EFS](https://aws.amazon.com/efs/), [Amazon FSx for Lustre](https://www.google.com/search?client=safari&rls=en&q=FSx+for+lustre&ie=UTF-8&oe=UTF-8), [s3fs-fuse](https://github.com/s3fs-fuse/s3fs-fuse), [JuiceFS](https://github.com/juicedata/juicefs) and any other file system which adheres to the Network File System (NFS) protocol. A comparison of these file systems from the perspective of workflow orchestration is available on [docs.memverge.com](https://docs.memverge.com/MMCloud/latest/User%20Guide/Application%20Solution%20Stacks/introduction/#filesystems-for-workdir).

### NFS

For NFS, set up NFS server and add NFS permissions if needed.

Add the following:

`/etc/exports`

```
<SHARED_DIR> <SUBNET>(rw,sync,all_squash,anonuid=<UID>,anongid=<GID>)
```

Where:
* `SHARED_DIR` is the path to the shared working directory.
* `SUBNET` is the subnet mask in CIDR notation.
* `UID` and `GID` are those of the owner of `SHARED_DIR`.

We squash all NFS clients to the `UID` and `GID` of the owner of `SHARED_DIR` so that the user running `snakemake` has access permissions to all files created by worker instances.

Add to the shared working directory the mininum:

`snakemake-float.yaml`
```yaml
work-dir: "<MOUNT_POINT>"
data-volumes:
- "nfs://<NFS_SERVER_ADDRESS>/<SHARED_DIR>:<MOUNT_POINT>"
```

Where:

* `MOUNT_POINT` is the desired mount point of the shared working directory on each worker node.
* `NFS_SERVER_ADDRESS` is the address of the NFS server.
* `SHARED_DIR` is the path to the shared working directory

To execute a workflow, run:

`snakemake --profile snakemake-float --jobs <VALUE>`

`VALUE` can take the value `unlimited`. This value determines the queue size.

## Logging

`cluster-sidecar` is specified in `config.yaml` to set the environment variable `SNAKEMAKE_CLUSTER_SIDECAR_VARS` as the time, which is used in determining the log file name for the user invocation of `snakemake`. Log files are stored in `.snakemake/log/` in the working directory.

Set log level by setting environment variable `SNAKEMAKE_FLOAT_LOG_LEVEL` as one of `CRITICAL`, `ERROR`, `WARNING`, `INFO`, or `DEBUG`. The default log level is `INFO`.

## Tested workflows

The following workflows have been tested and known to be working at some time for some sets of rules and data:
* [verkko](https://github.com/marbl/verkko)
* [rna-seq-star-deseq2](https://github.com/snakemake-workflows/rna-seq-star-deseq2)
* [dna-seq-varlociraptor](https://github.com/snakemake-workflows/dna-seq-gatk-variant-calling)
    - With workarounds: `curl` in rule `get_vep_cache` can break due to instance migration. Either disable instance migration or make offending rules local.
* [StainedGlass](https://github.com/mrvollger/StainedGlass)

## Limitations

- MMCloud jobs that execute rules requiring network usage may fail or hang if migration is enabled.
- In the case of workflows with large fan-out, job submission may take a long time due to a lack of concurrency.