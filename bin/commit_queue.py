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


class ServerLocation:
    REMOTE = 'remote'
    LOCAL = 'local'


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
    def __init__(self, remote: bool, host: Optional[str], commit: bool):
        self.remote = remote
        self.host = host
        self.commit = commit
        if remote and not host:
            raise Exception(f"If remote is true host is required but got host: {host!r}")

        self.root_dir = ANTHOLOGY_FILE_ROOT if remote else ANTHOLOGY_DATA_DIR

    def listdir(self, relative_path: str) -> List[str]:
        abs_dir = f'{self.root_dir}/{relative_path}'
        if self.remote:
            return (
                subprocess.check_output(['ssh', self.host, f'ls {abs_dir}'])
                .decode('utf-8')
                .strip()
                .split('\n')
            )
        else:
            return os.listdir(abs_dir)

    def movefile(self, relative_src_path: str, relative_dest_path: str):
        abs_src = f'{self.root_dir}/{relative_src_path}'
        abs_dest = f'{self.root_dir}/{relative_dest_path}'

        if self.remote:
            cmd = ['ssh', self.host, f'mv {abs_src} {abs_dest}']
            if self.commit:
                subprocess.check_call(cmd)
            else:
                log.info(f"Would run: {cmd}")
        else:
            if self.commit:
                os.rename(abs_src, abs_dest)
            else:
                log.info(f"Would move file {abs_src!r} to {abs_dest!r}")

    def hashfile(self, relative_path: str) -> str:
        abs_dir = f'{self.root_dir}/{relative_path}'
        if self.remote:
            return (
                subprocess.check_output(['ssh', self.host, f'crc32 {abs_dir}'])
                .decode('utf-8')
                .strip()
            )
        else:
            return compute_hash_from_file(abs_dir)

    def exists(self, relative_path: str) -> bool:
        abs_dir = f'{self.root_dir}/{relative_path}'
        if self.remote:
            try:
                subprocess.check_output(['ssh', self.host, f'stat {abs_dir}'])
                return True
            except subprocess.CalledProcessError:
                return False
        else:
            return os.path.exists(abs_dir)

    def remove(self, relative_path: str) -> bool:
        abs_dir = f'{self.root_dir}/{relative_path}'
        if self.remote:
            cmd = ['ssh', self.host, f'rm {abs_dir}']
            if self.commit:
                subprocess.check_call(cmd)
            else:
                log.info(f"Would run: {cmd}")
        else:
            if self.commit:
                os.remove(abs_dir)
            else:
                log.info(f"Would remove file {abs_dir!r}")


def process_queue(anth: Anthology, resource_type: ResourceType, fs: FileSystemOps):
    queue_base_path = f'queue/{resource_type.value}'
    for venue_name in fs.listdir(queue_base_path):
        for filename in fs.listdir(os.path.join(queue_base_path, venue_name)):
            base_filename, file_hash = filename.rsplit('.', 1)

            # Get main branch resource hash
            try:
                current_version_hash = anth.get_hash_for_resource(
                    anth, resource_type, base_filename
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


def get_all_pdf_filepath_to_hash(anth: Anthology):
    filepath_to_hash = {}
    for _, paper in anth.papers.items():
        if paper.pdf is not None:
            filepath = (
                f"{ResourceType.PDF.value}/{paper.collection_id}/{paper.full_id}.pdf"
            )
            filepath_to_hash[filepath] = paper.pdf_hash

    return filepath_to_hash


def get_all_attachment_filepath_to_hash(anth: Anthology):
    filepath_to_hash = {}
    for _, paper in anth.papers.items():
        for attachment in paper.attachments:
            filepath = f"{ResourceType.ATTACHMENT.value}/{paper.collection_id}/{attachment['filename']}"
            filepath_to_hash[filepath] = attachment['hash']

    return filepath_to_hash


def complete_check(anth: Anthology, resource_type: ResourceType, fs: FileSystemOps):
    log.error("Complete check isn't implemented yet")
    # get all hashes for files in server "live" directory
    live_filepath_to_hash = {}
    base_path = f'{resource_type.value}'
    for venue_name in fs.listdir(base_path):
        for filename in fs.listdir(os.path.join(base_path, venue_name)):
            filepath = os.path.join(base_path, venue_name, filename)
            live_filepath_to_hash[filepath] = fs.hashfile(filepath)

    expected_filepath_to_hash = {
        ResourceType.ATTACHMENT: get_all_pdf_filepath_to_hash,
        ResourceType.PDF: get_all_attachment_filepath_to_hash,
    }[resource_type](anth)

    missing_files = set(expected_filepath_to_hash.keys() - live_filepath_to_hash.keys())
    extra_files = set(live_filepath_to_hash.keys() - expected_filepath_to_hash.keys())

    out_dated_files = set()
    common_files = set(expected_filepath_to_hash.keys() & live_filepath_to_hash.keys())
    for filepath in common_files:
        if expected_filepath_to_hash[filepath] is None:
            log.error(f'Missing expected_file_hash for {filepath}')
            continue
        if expected_filepath_to_hash[filepath] != live_filepath_to_hash[filepath]:
            out_dated_files.add(filepath)

    files_to_move_in = missing_files | out_dated_files
    for filepath in files_to_move_in:
        expected_file_hash = expected_filepath_to_hash[filepath]
        if expected_file_hash is None:
            log.error(f'Missing expected_file_hash for {filepath}')
            continue
        queue_file_path = f'queue/{filepath}.{expected_file_hash}'
        if fs.exists(queue_file_path):
            fs.movefile(queue_file_path, filepath)
        else:
            log.error(f'Missing file in queue: {queue_file_path}')

    for filepath in extra_files:
        fs.remove(filepath)


@click.command()
@click.option(
    '-i',
    '--importdir',
    type=click.Path(exists=True),
    default=ANTHOLOGY_DATA_DIR,
    help="Directory to import the Anthology XML files data files from.",
)
@click.option(
    '--server-location',
    required=True,
    type=click.Choice(
        [ServerLocation.REMOTE, ServerLocation.LOCAL], case_sensitive=False
    ),
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
    server_location: str,
    remote: bool,
    commit: str,
    complete_check: bool,
    debug: bool,
):
    log_level = log.DEBUG if debug else log.INFO
    log.basicConfig(format="%(levelname)-8s %(message)s", level=log_level)
    tracker = SeverityTracker()
    log.getLogger().addHandler(tracker)

    log.info(f"Remote {remote}")

    if server_location != ServerLocation.REMOTE:
        log.error("Running this script locally on the server isn't supported yet!")
        exit(1)

    # if not is_clean_checkout_of_remote_branch(importdir, REMOTE_URL, REMOTE_MAIN_BRANCH_NAME):
    #   log.error(f"Repo @ {importdir} isn't clean or isn't tracking the master remote branch.")

    log.info("Instantiating the Anthology...")
    anth = Anthology(importdir=importdir)

    fs = FileSystemOps(remote=remote, host=ANTHOLOGY_HOST, commit=commit)

    if complete_check:
        complete_check()
    else:
        process_queue(anth, resource_type=ResourceType.PDF, fs=fs)
        process_queue(anth, resource_type=ResourceType.ATTACHMENT, fs=fs)

    if tracker.highest >= log.ERROR:
        exit(1)


if __name__ == "__main__":
    main()
