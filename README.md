# snakemake-float

Snakemake profile for MemVerge Memory Machine Cloud (float).

## Add profile

`git clone https://github.com/edwinyyyu/snakemake-float.git ~/.config/snakemake/snakemake-float/`

## Configuration

Set the following environment variables:
* `MMC_ADDRESS`
* `MMC_USERNAME`
* `MMC_PASSWORD`

In your Snakemake working directory, create file `snakemake-float.yaml` based on the template, specifying arguments to pass to  `float` for job submission.
* `work-dir` [required]: specifies the work directory for all worker nodes.
* `data-volumes` [required]: specifies a list of data volumes for all worker nodes.
* `job-prefix` [optional]: specifies a string to prefix job names with.
* `base-image` [optional]: specifies a string to prefix job names with.
* `cpu` [optional]: specifies cpu for all worker nodes. Overrides inferred values from workflow.
* `mem` [optional]: specifies mem for all worker nodes. Overrides inferred values from workflow.
* `submit-extra` [optional]: specifies a string to append to the `float` command.

## Examples

### NFS shared working directory

`/etc/exports`

```
SHARED_DIR SUBNET(rw,sync,all_squash,anonuid=UID,anongid=GID)
```

We squash all NFS clients to the `UID` and `GID` of the owner of `SHARED_DIR` so that the user running `snakemake` has access permissions to all files created by worker instances.

`snakemake-float.yaml`
```yaml
work-dir: "MOUNT_POINT"
data-volumes:
- "nfs://NFS_SERVER_ADDRESS/SHARED_DIR:MOUNT_POINT"
submit-extra: "--migratePolicy [enable=true]"
```

`snakemake --profile snakemake-float --jobs VALUE`

### S3FS shared working directory

`s3fs BUCKET_NAME SHARED_DIR -o umask=0000 -o disable_noobj_cache`

We set `umask` so that the user running `snakemake` has access to all files created by worker instances. We set `disable_noobj_cache` so that `snakemake` can correctly detect output files.

`snakemake-float.yaml`
```yaml
work-dir: "MOUNT_POINT1"
data-volumes:
- "[mode=rw]s3://BUCKET_NAME1:MOUNT_POINT1"
- "[mode=rw]s3://BUCKET_NAME2:MOUNT_POINT2"
submit-extra: "--migratePolicy [enable=true]"
```

`snakemake --profile snakemake-float --jobs VALUE`

### Package management

Additionally tell `snakemake` to `--use-conda` for workflows requiring packages installable by Conda. When using Conda with S3FS, provide `snakemake` with a `--conda-prefix` that is not within the S3FS shared working directory.

Containers are not supported.

### Logging

`cluster-sidecar` is specified in `config.yaml` to set the environment variable `SNAKEMAKE_CLUSTER_SIDECAR_VARS` as the time, which is used in determining the log file name for the user invocation of `snakemake`. Log files are stored in `.snakemake/log/` in the working directory.

There is currently a minor bug where termination of the sidecar via CTRL-C does not behave as it should. Optionally disable the cluster sidecar by removing it from `cluster.yaml`, which will cause the log file to be named `snakemake.float.log` instead.

Set log level by setting environment variable `SNAKEMAKE_FLOAT_LOG_LEVEL` as one of `CRITICAL`, `ERROR`, `WARNING`, `INFO`, or `DEBUG`. The default is `INFO`.