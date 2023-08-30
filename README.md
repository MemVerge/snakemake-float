# snakemake-float

Snakemake cluster execution profile plugin to allow executing Snakemake jobs using MemVerge Memory Machine Cloud (float).

## Install profile

First, install [Mamba](https://mamba.readthedocs.io/en/latest/mamba-installation.html#mamba-install) (alternatively, [Conda](https://conda.io/projects/conda/en/latest/user-guide/install/index.html)) and [Snakemake](https://snakemake.readthedocs.io/en/stable/getting_started/installation.html).

`git clone https://github.com/edwinyyyu/snakemake-float.git ~/.config/snakemake/snakemake-float/`

## Configuration

Set the following environment variables:
* `MMC_ADDRESS`: MMCloud OpCenter address
* `MMC_USERNAME`: MMCloud OpCenter username
* `MMC_PASSWORD`: MMCloud OpCenter password

In the Snakemake working directory, create file `snakemake-float.yaml` based on the template, specifying arguments to pass to  `float` for job submission.
* `work-dir` [required]: specifies the work directory for all worker nodes.
* `data-volumes` [required]: specifies a list of data volumes for all worker nodes.
* `job-prefix` [optional]: specifies a string to prefix job names with.
* `base-image` [optional]: specifies a container image to execute jobs with. Must have Snakemake installed.
* `cpu` [optional]: specifies cpu for all worker nodes. Overrides inferred values from workflow.
* `mem` [optional]: specifies mem for all worker nodes. Overrides inferred values from workflow.
* `submit-extra` [optional]: specifies arguments, as a string, to append to the `float` command.

## Shared working directory

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

`VALUE` can take the value `unlimited`.

### S3FS

Install [s3fs](https://github.com/s3fs-fuse/s3fs-fuse#installation).

To mount a bucket as a directory, run:

`s3fs <BUCKET_NAME> <SHARED_DIR> -o umask=0000 -o disable_noobj_cache`

Where:
* `BUCKET_NAME` is the S3 bucket name.
* `SHARED_DIR` is the path to the shared working directory.

We set `umask` so that the user running `snakemake` has access to all files created by worker instances. We set `disable_noobj_cache` so that `snakemake` can correctly detect output files.

Add to the shared working directory the mininum:

`snakemake-float.yaml`
```yaml
work-dir: "<MOUNT_POINT>"
data-volumes:
- "[mode=rw]s3://<BUCKET_NAME>:<MOUNT_POINT>"
```

Where:
* `MOUNT_POINT` is the desired mount point of the shared working directory on each worker node.
* `BUCKET_NAME` is the S3 bucket name

To execute a workflow, run:

`snakemake --profile snakemake-float --jobs <VALUE>`

`VALUE` can take the value `unlimited`.

## Package management

Tell `snakemake` to `--use-conda` for workflows requiring packages installable by Conda.

Additionally, when using Conda with S3FS, provide `snakemake` with a `--conda-prefix` that is not within the S3FS shared working directory. Otherwise, package installation can stall workflow execution.

Containers as specified by the `singularity` directive are not supported.

## Logging

`cluster-sidecar` is specified in `config.yaml` to set the environment variable `SNAKEMAKE_CLUSTER_SIDECAR_VARS` as the time, which is used in determining the log file name for the user invocation of `snakemake`. Log files are stored in `.snakemake/log/` in the working directory.

Set log level by setting environment variable `SNAKEMAKE_FLOAT_LOG_LEVEL` as one of `CRITICAL`, `ERROR`, `WARNING`, `INFO`, or `DEBUG`. The default log level is `INFO`.

## Workflows Tested

The following workflows have been tested and known to be working at some time for some sets of rules and data:
* [rna-seq-star-deseq2](https://github.com/snakemake-workflows/rna-seq-star-deseq2)
* [dna-seq-varlociraptor](https://github.com/snakemake-workflows/dna-seq-gatk-variant-calling)
    - With workarounds: `curl` in rule `get_vep_cache` can break due to instance migration. Either disable instance migration or make offending rules local.
* [StainedGlass](https://github.com/mrvollger/StainedGlass)

## Problems and Limitations

MMCloud jobs that execute rules requiring network usage may fail or hang if migration is enabled.
In the case of workflows with large fan-out, job submission may take a long time due to a lack of concurrency.