# Copyright 2023-2024 Marcel Bollmann <marcel@bollmann.me>
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from git.repo import Repo
from git import RemoteProgress
from os import PathLike
from pathlib import Path
from rich.progress import Progress
from typing import Optional

from .logging import get_logger


log = get_logger()


def clone_or_pull_from_repo(
    repo_url: str, local_path: PathLike[str], verbose: bool
) -> None:
    """Clones a Git repository, or pulls from remote if it already exists.

    Arguments:
        repo_url: The URL of a Git repo.
        local_path: The local path containing the repo.  If it doesn't exist, we will attempt to clone the repo into it; if it exists, we assume it already contains the repo and will attempt to pull from 'origin'.
        verbose: If True, will show a progress display.
    """
    path = Path(local_path)
    progress = RichRemoteProgress() if verbose else None
    log.debug(f"Using local repository folder: {path}")
    if path.exists():
        repo = Repo(path)
        if repo.remote().url != repo_url:
            log.error(
                (
                    "Repository folder exists, but doesn't match the given URL:\n",
                    f"   {repo.remote().url} != {repo_url}",
                )
            )
        log.info(f"Fetching updates from: {repo_url}")
        repo.remote().pull(force=True, progress=progress)
    else:
        log.info(f"Cloning repository: {repo_url}")
        repo = Repo.clone_from(
            repo_url, path, progress=progress, single_branch=True, depth=1  # type: ignore[arg-type]
        )
        # ^-- It seems that Repo.clone_from() has an incorrect type signature
        # for its progress argument...
    if progress is not None:
        progress.progress.update(progress.task, completed=210.0)
        progress.progress.stop()


# This is a bit hacky, mainly to provide a "smoother" user experience, but
# could probably be simplified.
class RichRemoteProgress(RemoteProgress):
    def __init__(self) -> None:
        super().__init__()
        self.progress = Progress()
        self.task = self.progress.add_task(
            "Fetching Anthology data...", start=False, visible=False, total=210.0
        )

    def update(
        self,
        op_code: int,
        cur_count: str | float,
        max_count: Optional[str | float] = None,
        message: str = "",
    ) -> None:
        operation = op_code & self.OP_MASK

        # Satisfying the type checker, even though this _should_ always be float ...
        if isinstance(cur_count, str):
            try:
                cur_count = float(cur_count)
            except ValueError:
                cur_count = 0.0
        if isinstance(max_count, str):
            try:
                max_count = float(max_count)
            except ValueError:
                max_count = 100.0
        elif max_count is None:
            max_count = 100.0

        if operation == self.COUNTING:
            if op_code & self.BEGIN:
                self.progress.start()
                self.progress.start_task(self.task)
                self.progress.update(self.task, visible=True)
            if op_code & self.END:
                value = 9.0
                self.progress.update(self.task, completed=value)
        elif operation == self.COMPRESSING:
            value = 9.0 + 100.0 * (cur_count / max_count)
            self.progress.update(self.task, completed=value)
        elif operation == self.RECEIVING:
            value = 109.0 + 100.0 * (cur_count / max_count)
            self.progress.update(self.task, completed=value)
        elif (op_code & self.END) and (operation == self.RESOLVING):
            self.progress.update(self.task, completed=210.0)
            self.progress.stop()
