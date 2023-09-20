import json
import subprocess
from dataclasses import dataclass, field
from typing import Generator, List, Optional

from snakemake_interface_executor_plugins import CommonSettings, ExecutorSettingsBase
from snakemake_interface_executor_plugins.executors.base import SubmittedJobInfo
from snakemake_interface_executor_plugins.executors.remote import RemoteExecutor
from snakemake_interface_executor_plugins.jobs import JobExecutorInterface
from snakemake_interface_executor_plugins.logging import LoggerExecutorInterface
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
        # access workflow
        self.workflow
        # access executor specific settings
        self.workflow.executor_settings

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
        # Implement here how to run a job.
        # You can access the job's resources, etc.
        # via the job object.
        # After submitting the job, you have to call
        # self.report_job_submission(job_info).
        # with job_info being of type
        # snakemake_interface_executor_plugins.executors.base.SubmittedJobInfo.
        # If required, make sure to pass the job's id to the job_info object, as keyword
        # argument 'external_job_id'.

        ...

    async def check_active_jobs(self, active_jobs: List[SubmittedJobInfo]) -> Generator[SubmittedJobInfo, None, None]:
        # Check the status of active jobs.

        # self.report_job_success(active_job).
        # self.report_job_error(active_job).
        # Jobs that are still running have to be yielded.
        # To modify the time until the next call of this method,
        # you can set self.next_sleep_seconds here.
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
                        status = status_map(show_response["status"])
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

                if status is Status.RUNNING:
                    yield job
                elif status is Status.SUCCESS:
                    self.report_job_success(job)
                elif status is Status.FAILURE:
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
