# snakemake-float

Snakemake profile for MemVerge Memory Machine Cloud (float).

## Add profile

`git clone https://github.com/edwinyyyu/snakemake-float.git ~/.config/snakemake/snakemake-float/`

## Configuration

In your Snakemake working directory, create file `snakemake-float.yaml` based on the template, specifying arguments to pass to  `float` for job submission. The `extra` option specifies a string to append to the `float` command.

## Examples

### NFS shared working directory

`/etc/exports`

```
SHARED_DIR SUBNET(rw,sync,all_squash,anonuid=UID,anongid=GID)
```

We squash all NFS clients to the `UID` and `GID` of the owner of `SHARED_DIR` so that the user running `snakemake` has access permissions to all files created by worker instances.

`snakemake-float.yaml`
```yaml
address: "OPCENTER_ADDRESS"
username: "admin"
password: "memverge"
dataVolume: "nfs://NFS_SERVER_ADDRESS/SHARED_DIR:MOUNT_POINT"
extra: "--migratePolicy [enable=true]"
```

`snakemake --profile snakemake-float --jobs VALUE`

### S3FS shared working directory

`s3fs BUCKET_NAME SHARED_DIR -o umask=0000`

We set `umask` so that the user running `snakemake` has access to all files created by worker instances.

`snakemake-float.yaml`
```yaml
address: "OPCENTER_ADDRESS"
username: "admin"
password: "memverge"
dataVolume: "[mode=rw]s3://BUCKET_NAME:MOUNT_POINT"
extra: "--migratePolicy [enable=true]"
```

`snakemake --profile snakemake-float --jobs VALUE`

### Package management

Additionally tell `snakemake` to `--use-conda` for workflows requiring packages installable by Conda.
Containers are not supported.

### Logging

`cluster-sidecar` is specified in `config.yaml` to set the environment variable `SNAKEMAKE_CLUSTER_SIDECAR_VARS` as the time, which is used in determining the log file name for the user invocation of `snakemake`. Log files are stored in `.snakemake/log/` in the working directory.

There is currently a minor bug where termination of the sidecar via CTRL-C does not behave as it should. Optionally disable the cluster sidecar by removing it from `cluster.yaml`, which will cause the log file to be named `snakemake.float.log` instead.
