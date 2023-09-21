import hashlib
import json
import os
import shutil
import subprocess
import tarfile
import tempfile
from dataclasses import dataclass, field
from typing import Generator, List, Optional

from snakemake.remote.S3 import S3Helper
from snakemake_interface_common.exceptions import WorkflowError
from snakemake_interface_executor_plugins.executors.base import SubmittedJobInfo
from snakemake_interface_executor_plugins.executors.remote import RemoteExecutor
from snakemake_interface_executor_plugins.jobs import JobExecutorInterface
from snakemake_interface_executor_plugins.logging import LoggerExecutorInterface
from snakemake_interface_executor_plugins.settings import CommonSettings, ExecutorSettingsBase
from snakemake_interface_executor_plugins.workflow import WorkflowExecutorInterface

from snakemake_executor_plugin_mmcloud.common import Status, async_check_output, status_map


# Define additional settings for executor.
# They will occur in the Snakemake CLI as --<executor-name>-<param-name>.
@dataclass
class ExecutorSettings(ExecutorSettingsBase):
    """
    myparam: Optional[int]=field(
        default=None,
        metadata={
            "help": "Some help text",
            # Optionally request that setting is also available for specification
            # via an environment variable. The variable will be named automatically as
            # SNAKEMAKE_<executor-name>_<param-name>, all upper case.
            # This mechanism should only be used for passwords and usernames.
            # For other items, we rather recommend to let people use a profile
            # for setting defaults
            # (https://snakemake.readthedocs.io/en/stable/executing/cli.html#profiles).
            "env_var": False,
            # Optionally specify that setting is required when the executor is in use.
            "required": True
        }
    )
    """

    mmc_address: Optional[str] = field(
        default=None,
        metadata={
            "help": "MMCloud OpCenter address",
            "env_var": True,
            "required": True,
        },
    )
    mmc_username: Optional[str] = field(
        default=None,
        metadata={
            "help": "MMCloud OpCenter username",
            "env_var": True,
            "required": True,
        },
    )
    mmc_password: Optional[str] = field(
        default=None,
        metadata={
            "help": "MMCloud OpCenter password",
            "env_var": True,
            "required": True,
        },
    )


# Specify common settings shared by various executors.
common_settings = CommonSettings(
    non_local_exec=True,
    implies_no_shared_fs=True,
)


class Executor(RemoteExecutor):
    def __init__(
        self,
        workflow: WorkflowExecutorInterface,
        logger: LoggerExecutorInterface,
    ):
        super().__init__(
            workflow,
            logger,
            # whether arguments for setting the remote provider shall  be passed to jobs
            pass_default_remote_provider_args=True,
            # whether arguments for setting default resources shall be passed to jobs
            pass_default_resources_args=True,
            # whether environment variables shall be passed to jobs
            pass_envvar_declarations_to_cmd=True,
            # specify initial amount of seconds to sleep before checking for job status
            init_sleep_seconds=0,
        )

        self.s3_helper = S3Helper()
        self._response_format = ["--format", "json"]

        # access workflow
        self.workflow

        # IMPORTANT: in your plugin, only access methods and properties of
        # Snakemake objects (like Workflow, Persistence, etc.) that are
        # defined in the interfaces found in the
        # snakemake-interface-executor-plugins and the
        # snakemake-interface-common package.
        # Other parts of those objects are NOT guaranteed to remain
        # stable across new releases.

        # To ensure that the used interfaces are not changing, you should
        # depend on these packages as >=a.b.c,<d with d=a+1 (i.e. pin the
        # dependency on this package to be at least the version at time
        # of development and less than the next major version which would
        # introduce breaking changes).

        # In case of errors outside of jobs, please raise a WorkflowError

    def run_job(self, job: JobExecutorInterface):
        # job.name
        # job.jobid
        # job.logfile_suggestion
        # job.is_group
        # job.log_info
        # job.log_error
        # job.remote_existing_output
        # job.download_remote_input
        # job.properties
        # job.resources
        # job.check_protected_output
        # job.is_local
        # job.is_branched
        # job.is_updated
        # job.output
        # job.register
        # job.postprocess
        # job.get_target_spec
        # job.rules
        # job.attempt
        # job.input
        # job.threads
        # job.log
        # job.cleanup
        # job.get_wait_for_files
        # job.format_wildcards
        # job.is_containerized

        job_info = SubmittedJobInfo(job=job, external_jobid=jobid)
        self.report_job_submission(job_info)

    async def check_active_jobs(self, active_jobs: List[SubmittedJobInfo]) -> Generator[SubmittedJobInfo, None, None]:
        # Check the status of active jobs.
        show_command = [
            "float",
            "show",
            *self._response_format,
        ]

        try:
            self.login()
            for job in active_jobs:
                jobid = job.external_jobid
                async with self.status_rate_limiter:
                    try:
                        show_response = await async_check_output(*(show_command + ["--job", jobid]))
                        show_response = json.loads(show_response.decode())
                        job_status = status_map(show_response["status"])
                    except subprocess.CalledProcessError as e:
                        self.logger.exception(
                            f"Failed to get show response for MMCloud job: {jobid}\n"
                            f"[stdout] {e.stdout.decode()}\n"
                            f"[stderr] {e.stderr.decode()}\n"
                        )
                        raise
                    except (UnicodeError, json.JSONDecodeError):
                        self.logger.exception(f"Failed to decode show response for MMCloud job: {jobid}")
                        raise
                    except KeyError:
                        self.logger.exception(f"Failed to obtain status for MMCloud job: {jobid}")
                        raise

                if job_status is Status.RUNNING:
                    yield job
                elif job_status is Status.SUCCESS:
                    self.report_job_success(job)
                elif job_status is Status.FAILURE:
                    self.report_job_error(job)
        except subprocess.CalledProcessError:
            self.logger.exception("Failed to obtain check active MMCloud jobs")

    def cancel_jobs(self, active_jobs: List[SubmittedJobInfo]):
        # Cancel all active jobs.
        # This method is called when Snakemake is interrupted.
        cancel_command = ["float", "cancel", "--force"]
        try:
            self.login()
            for job in active_jobs:
                jobid = job.external_jobid
                subprocess.check_call(cancel_command + ["--job", jobid])
                self.logger.debug(f"Submitted request to cancel MMCloud job: {jobid}")
        except subprocess.CalledProcessError:
            self.logger.exception("Failed to cancel MMCloud jobs")
            raise

    def login(self):
        try:
            # If already logged in, this will reset the session timer
            login_info_command = ["float", "login", "--info"]
            subprocess.check_call(login_info_command)
        except subprocess.CalledProcessError:
            self.logger.info("Attempting to log in to OpCenter")
            try:
                login_command = [
                    "float",
                    "login",
                    "--address",
                    self.workflow.executor_settings.mmc_address,
                    "--username",
                    self.workflow.executor_settings.mmc_username,
                    "--password",
                    self.workflow.executor_settings.mmc_password,
                ]
                subprocess.check_call(login_command)
            except subprocess.CalledProcessError:
                self.logger.exception("Failed to log in to OpCenter")
                raise

            self.logger.info("Logged in to OpCenter")

    # from snakemake_executor_plugin_google_lifesciences
    def _set_workflow_sources(self):
        """
        We only add files from the working directory that are config related
        (e.g., the Snakefile or a config.yml equivalent), or checked into git.
        """
        self.workflow_sources = []

        for wfs in self.dag.get_sources():
            if os.path.isdir(wfs):
                for dirpath, dirnames, filenames in os.walk(wfs):
                    self.workflow_sources.extend([self.check_source_size(os.path.join(dirpath, f)) for f in filenames])
            else:
                self.workflow_sources.append(self.check_source_size(os.path.abspath(wfs)))

    # from snakemake_executor_plugin_google_lifesciences
    def _generate_build_source_package(self):
        """
        In order for the instance to access the working directory in storage,
        we need to upload it. This file is cleaned up at the end of the run.
        We do this, and then obtain from the instance and extract.
        """
        # Workflow sources for cloud executor must all be under same workdir root
        for filename in self.workflow_sources:
            if self.workdir not in os.path.realpath(filename):
                raise WorkflowError(
                    "All source files must be present in the working directory, "
                    "{workdir} to be uploaded to a build package that respects "
                    "relative paths, but {filename} was found outside of this "
                    "directory. Please set your working directory accordingly, "
                    "and the path of your Snakefile to be relative to it.".format(
                        workdir=self.workdir, filename=filename
                    )
                )

        # We will generate a tar.gz package, renamed by hash
        tmpname = next(tempfile._get_candidate_names())
        targz = os.path.join(tempfile.gettempdir(), "snakemake-%s.tar.gz" % tmpname)
        tar = tarfile.open(targz, "w:gz")

        # Add all workflow_sources files
        for filename in self.workflow_sources:
            arcname = filename.replace(self.workdir + os.path.sep, "")
            tar.add(filename, arcname=arcname)

        tar.close()

        # Rename based on hash, in case user wants to save cache
        hasher = hashlib.sha256()
        hasher.update(open(targz, "rb").read())
        sha256 = hasher.hexdigest()
        hash_tar = os.path.join(self.workflow.persistence.aux_path, f"workdir-{sha256}.tar.gz")

        # Only copy if we don't have it yet, clean up if we do
        if not os.path.exists(hash_tar):
            shutil.move(targz, hash_tar)
        else:
            os.remove(targz)

        # We will clean these all up at shutdown
        self._build_packages.add(hash_tar)

        return hash_tar
