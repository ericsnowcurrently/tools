import logging
from typing import Any, Optional, Type

from . import _utils, _common, requests, JobsConfig


logger = logging.getLogger(__name__)


class WorkerConfig(_utils.Config):

    FIELDS = ['user', 'ssh_host', 'ssh_port']

    def __init__(self,
                 user: str,
                 ssh_host: str,
                 ssh_port: int,
                 **ignored
                 ):
        if not user:
            raise ValueError('missing user')
        ssh = _utils.SSHConnectionConfig(user, ssh_host, ssh_port)
        super().__init__(
            user=user,
            ssh=ssh,
        )

    def as_jsonable(self) -> Any:  # type: ignore
        return {
            'user': self.user,
            'ssh_host': self.ssh.host,
            'ssh_port': self.ssh.port,
        }


class WorkerJobFS(_common.JobFS):
    """The file structure of a job's data on a worker."""

    context = 'job-worker'


class WorkerJobsFS(_common.JobsFS):
    """The file structure of the jobs data on a worker."""

    context = 'job-worker'

    JOBFS = WorkerJobFS

    def __init__(self, root=None):
        super().__init__(root)

        # the local git repositories used by the job
        self.repos = _utils.FSTree(f'{self}/repositories')
        self.repos.cpython = f'{self.repos}/cpython'
        self.repos.pyperformance = f'{self.repos}/pyperformance'
        self.repos.pyston_benchmarks = f'{self.repos}/pyston-benchmarks'


class JobWorker:
    """A worker assigned to run a requested job."""

    def __init__(self, worker: "Worker", fs: WorkerJobFS):
        self._worker = worker
        self._fs = fs

    def __repr__(self):
        args = (f'{n}={getattr(self, "_"+n)!r}'
                for n in 'worker fs'.split())
        return f'{type(self).__name__}({"".join(args)})'

    def __eq__(self, other):
        raise NotImplementedError

    @property
    def fs(self) -> WorkerJobFS:
        return self._fs

    @property
    def topfs(self) -> WorkerJobsFS:
        return self._worker.fs

    @property
    def ssh(self) -> _utils.SSHClient:
        return self._worker.ssh


class Worker:
    """A single configured worker."""

    @classmethod
    def from_config(
            cls,
            cfg: WorkerConfig,
            JobsFS: Type[WorkerJobsFS] = WorkerJobsFS
    ) -> "Worker":
        fs = JobsFS.from_user(cfg.user)
        ssh = _utils.SSHClient.from_config(cfg.ssh)
        return cls(fs, ssh)

    def __init__(self, fs, ssh):
        self._fs = fs
        self._ssh = ssh

    def __repr__(self):
        args = (f'{n}={getattr(self, "_"+n)!r}'
                for n in 'fs ssh'.split())
        return f'{type(self).__name__}({"".join(args)})'

    def __eq__(self, other):
        raise NotImplementedError

    @property
    def fs(self) -> WorkerJobsFS:
        return self._fs

    @property
    def ssh(self) -> _utils.SSHClient:
        return self._ssh

    def resolve_job(
            self,
            reqid: requests.ToRequestIDType
    ) -> JobWorker:
        fs = self._fs.resolve_request(reqid)
        return JobWorker(self, fs)


class Workers:
    """The set of configured workers."""

    @classmethod
    def from_config(
            cls,
            cfg: JobsConfig,
            JobsFS: Type[WorkerJobsFS] = WorkerJobsFS
    ) -> "Workers":
        worker = Worker.from_config(cfg.worker, JobsFS)
        return cls(worker)

    def __init__(self, worker):
        self._worker = worker

    def __repr__(self):
        args = (f'{n}={getattr(self, "_"+n)!r}'
                for n in 'worker'.split())
        return f'{type(self).__name__}({"".join(args)})'

    def __eq__(self, other):
        raise NotImplementedError

    def resolve_job(
            self,
            reqid: requests.ToRequestIDType
    ) -> JobWorker:
        return self._worker.resolve_job(reqid)
