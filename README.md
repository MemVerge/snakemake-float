# snakemake-float
Snakemake profile for MemVerge Memory Machine Cloud (float).

## Add profile
`git clone https://github.com/edwinyyyu/snakemake-float.git ~/.config/snakemake/snakemake-float/`

## Configuration
In your Snakemake working directory, create file `snakemake-float.yaml` based on the template, specifying arguments to pass to  `float` for job submission. The `extra` option specifies a string to append to the `float` command.

## Examples

### NFS shared working directory
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
s3fs BUCKET_NAME SHARED_DIR -o umask=0000

`snakemake-float.yaml`
```yaml
address: "OPCENTER_ADDRESS"
username: "admin"
password: "memverge"
dataVolume: "[mode=rw]s3://BUCKET_NAME:MOUNT_POINT"
extra: "--migratePolicy [enable=true]"
```

`snakemake --profile snakemake-float --jobs VALUE`

## Known issues
NFS: Permission denied recording Snakemake metadata after job completion: Current workaround by setting `drop-metadata: true` in profile `config.yaml`.

S3FS: Permission denied accessing Snakemake metadata if umask not set. Possibly related to above.

S3FS: Snakemake will not detect output files by itself. Running `ls` will trigger it to do so for some reason. Maybe run a script that runs `ls` at some interval.