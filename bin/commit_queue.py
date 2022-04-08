# Options
#  1. Iterate through queue, if any have the checksum that is in the xml, copy to "real" location and delete from queue
#    pros: should be the fastest since queue should be kept clean.
#    cons: Will not detect any issues in "real" location.
#  2. Iterate through all Papers, check if checksummed file is in queue, copy if there is and remove from queue.
#    pros: will detect if any resources are missing.
#    cons: need to iterate through all papers everytime, will not catch case where extra files were copied.
#  3. Iterate through "real" location and checksum all files, if mismatched with paper, look at queue to copy in new file (e.g. a pdf or an attachment).
#    pros: will detect if there are files in the "real" location that aren't referenced, and any resources that are referenced but have a different checksum (different version).
#    cons: need to iterate through all files in "real" location and do checksum
#  4. Combine both #2 and #3
#    pros: will detect missing resources, extra resources and out dated resources
#    cons: have to iterate all Papers, etc... in xml and checksum all files in the "real" location
# Picking option #1 as default and #4 as a complete check (will implement in future)


from typing import List, Optional
import os
import click
import logging as log
from functools import partial
import subprocess

from anthology import Anthology
from anthology.data import ANTHOLOGY_DATA_DIR, ResourceType
from anthology.utils import SeverityTracker, compute_hash_from_file

# Enable show default by default
click.option = partial(click.option, show_default=True)

# The root directory for files, currently containing pdf/ and attachments/
ANTHOLOGY_FILE_ROOT = "/home/anthologizer/anthology-files"

# The ssh shortcut (in ~/.ssh/config) or full hostname
ANTHOLOGY_HOST = "anth"

# The remote url of the acl anthology git repo
REMOTE_URL = "https://github.com/acl-org/acl-anthology.git"

# The main branch of the acl anthology git repo
REMOTE_MAIN_BRANCH_NAME = "master"


def is_clean_checkout_of_remote_branch(
    repo_dir: str, remote_url: str, remote_main_branch_name: str
) -> bool:
    # Check if repo is clean
    status = (
        subprocess.check_output(["git", "status", "-uall", "--short"])
        .decode('utf-8')
        .strip()
    )
    if status:
        log.debug(
            f"Repo @ {repo_dir!r} is not clean. It has the following changes:\n{status}"
        )
        return False

    # Check tracking url and branch
    current_ref = (
        subprocess.check_output(["git", "symbolic-ref", "-q", "HEAD"])
        .decode('utf-8')
        .strip()
    )
    remote_tracking_branch_ref = subprocess.check_output(
        ["git", "for-each-ref", "--format='%(upstream:short)'", current_ref]
    )

    if "/" not in remote_tracking_branch_ref:
        msg = f"Invalid remote tracking branch ref {remote_tracking_branch_ref}"
        log.error(msg)
        raise Exception(msg)

    tracking_remote_name, remote_tracking_branch = remote_tracking_branch_ref.split(
        '/', 1
    )

    if remote_tracking_branch != remote_main_branch_name:
        log.debug(
            f"Remote tracking branch {remote_tracking_branch!r} is not main remote branch {remote_main_branch_name!r}"
        )
        return False

    tracking_remote_url = (
        subprocess.check_output(["git", "remote", "get-url", tracking_remote_name])
        .decode('utf-8')
        .strip()
    )

    if tracking_remote_url != remote_url:
        log.debug(
            f"Remote tracking url {tracking_remote_url!r} is not the remote url {remote_url!r}"
        )
        return False
    return True


def run_remote_command(cmd):
    return subprocess.check_output(['ssh', 'anth', cmd]).decode('utf-8').strip()


class FileSystemOps:
    def __init__(self, is_on_server: bool, host: Optional[str], commit: bool):
        self.is_on_server = is_on_server
        self.host = host
        self.commit = commit
        if not is_on_server and not host:
            raise Exception(
                f"If is_on_server is false, host is required but got host: {host!r}"
            )

        self.root_dir = ANTHOLOGY_DATA_DIR if is_on_server else ANTHOLOGY_FILE_ROOT

    def listdir(self, relative_path: str) -> List[str]:
        abs_dir = f'{self.root_dir}/{relative_path}'
        if self.is_on_server:
            return os.listdir(abs_dir)
        return (
            subprocess.check_output(['ssh', self.host, f'ls {abs_dir}'])
            .decode('utf-8')
            .strip()
            .split('\n')
        )

    def movefile(self, relative_src_path: str, relative_dest_path: str):
        abs_src = f'{self.root_dir}/{relative_src_path}'
        abs_dest = f'{self.root_dir}/{relative_dest_path}'
        abs_dest_dir = os.path.dirname(abs_dest)

        if self.is_on_server:
            if self.commit:
                os.makedirs(abs_dest_dir, exist_ok=True)
            else:
                log.info(f"Would super-mkdir {abs_dest_dir!r}")
            if self.commit:
                os.rename(abs_src, abs_dest)
            else:
                log.info(f"Would move file {abs_src!r} to {abs_dest!r}")
            return
        mdkir_cmd = [
            'ssh',
            ANTHOLOGY_HOST,
            f'mkdir -p {abs_dest_dir}',
        ]
        if self.commit:
            subprocess.check_call(mdkir_cmd)
        else:
            log.info(f"Would run: {mdkir_cmd}")

        cmd = ['ssh', self.host, f'mv {abs_src} {abs_dest}']
        if self.commit:
            subprocess.check_call(cmd)
        else:
            log.info(f"Would run: {cmd}")

    def hashfile(self, relative_path: str) -> str:
        abs_dir = f'{self.root_dir}/{relative_path}'
        if self.is_on_server:
            return compute_hash_from_file(abs_dir)
        return (
            subprocess.check_output(['ssh', self.host, f'crc32 {abs_dir}'])
            .decode('utf-8')
            .strip()
        )

    def exists(self, relative_path: str) -> bool:
        abs_dir = f'{self.root_dir}/{relative_path}'
        if self.is_on_server:
            return os.path.exists(abs_dir)
        try:
            subprocess.check_output(['ssh', self.host, f'stat {abs_dir}'])
            return True
        except subprocess.CalledProcessError:
            return False

    def remove(self, relative_path: str):
        abs_dir = f'{self.root_dir}/{relative_path}'
        if self.is_on_server:
            if self.commit:
                os.remove(abs_dir)
            else:
                log.info(f"Would remove file {abs_dir!r}")
            return
        cmd = ['ssh', self.host, f'rm {abs_dir}']
        if self.commit:
            subprocess.check_call(cmd)
        else:
            log.info(f"Would run: {cmd}")


def process_queue(anth: Anthology, resource_type: ResourceType, fs: FileSystemOps):
    log.debug(f'Processing queue for {resource_type}')
    queue_base_path = f'queue/{resource_type.value}'
    if not fs.exists(queue_base_path):
        log.error(f'Missing queue directory: {queue_base_path}.')
        return
    for venue_name in fs.listdir(queue_base_path):
        for filename in fs.listdir(os.path.join(queue_base_path, venue_name)):
            log.debug(f'\tProcessing file {filename!r}')
            base_filename, file_hash = filename.rsplit('.', 1)

            # Get main branch resource hash
            try:
                current_version_hash = anth.get_hash_for_resource(
                    resource_type, base_filename
                )
            except Exception as e:
                log.error(f"{e} (filename: {filename!r})", exc_info=True)
                continue

            if file_hash == current_version_hash:
                log.info(
                    f"Found queued file matching hash: {os.path.join(queue_base_path, venue_name, filename)}"
                )
                fs.movefile(
                    os.path.join(queue_base_path, venue_name, filename),
                    os.path.join(resource_type.value, venue_name, base_filename),
                )


def do_complete_check(anth: Anthology, resource_type: ResourceType, fs: FileSystemOps):
    log.error("Complete check isn't implemented yet")


@click.command()
@click.option(
    '-i',
    '--importdir',
    type=click.Path(exists=True),
    default=ANTHOLOGY_DATA_DIR,
    help="Directory to import the Anthology XML files data files from.",
)
@click.option(
    '--is-on-server',
    is_flag=True,
    help="If this flag is set file system changes will be applied to the local file system, else changes will be made by sshing into the anth server.",
)
@click.option(
    '-c',
    '--commit',
    is_flag=True,
    help="Commit (=write) the changes to the anthology server; will only do a dry run otherwise.",
)
@click.option(
    '--complete-check', is_flag=True, help="Do a complete check of resources on server."
)
@click.option('--debug', is_flag=True, help="Output debug-level log messages.")
def main(
    importdir: str,
    is_on_server: bool,
    commit: str,
    complete_check: bool,
    debug: bool,
):
    log_level = log.DEBUG if debug else log.INFO
    log.basicConfig(format="%(levelname)-8s %(message)s", level=log_level)
    tracker = SeverityTracker()
    log.getLogger().addHandler(tracker)

    log.info(
        'Running as if on server.'
        if is_on_server
        else 'Will ssh to server for file system operations.'
    )

    if not is_clean_checkout_of_remote_branch(
        importdir, REMOTE_URL, REMOTE_MAIN_BRANCH_NAME
    ):
        log.error(
            f"Repo @ {importdir} isn't clean or isn't tracking the master remote branch."
        )

    log.info("Instantiating the Anthology...")
    anth = Anthology(importdir=importdir)

    fs = FileSystemOps(is_on_server=is_on_server, host=ANTHOLOGY_HOST, commit=commit)

    if complete_check:
        do_complete_check(anth, resource_type=ResourceType.PDF, fs=fs)
        do_complete_check(anth, resource_type=ResourceType.ATTACHMENT, fs=fs)
    else:
        process_queue(anth, resource_type=ResourceType.PDF, fs=fs)
        process_queue(anth, resource_type=ResourceType.ATTACHMENT, fs=fs)

    if tracker.highest >= log.ERROR:
        exit(1)


if __name__ == "__main__":
    main()
