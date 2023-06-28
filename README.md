# snakemake-float
Snakemake profile for MemVerge Memory Machine Cloud (float).

## Add profile
`git clone https://github.com/edwinyyyu/snakemake-float.git ~/.config/snakemake/snakemake-float/`

## Configuration
In your Snakemake working directory, create file `snakemake-float.yaml` based on the template, specifying arguments to pass to  `float` for job submission. The `extra` option specifies a string to append to the `float` command.

## Example with working directory in AWS S3 bucket
`snakemake --profile snakemake-float --jobs 100 --default-remote-provider S3 --default-remote-prefix BUCKET_NAME`