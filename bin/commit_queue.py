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


from collections import Counter
import itertools
import json
from typing import List, Optional
import os
import click
import asyncio
from tqdm import tqdm
import concurrent.futures
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
        
        if not is_on_server:
            import paramiko
            self.ssh_client = paramiko.SSHClient()
            self.ssh_client.load_system_host_keys()
            self.ssh_client.connect('aclanthology.org', username="anthologizer", key_filename="/Users/xinruyan/.ssh/acl")
            self.sftp = self.ssh_client.open_sftp()

        self.root_dir = ANTHOLOGY_DATA_DIR if is_on_server else ANTHOLOGY_FILE_ROOT
    

    def find(self, resource_type: ResourceType):
        _, stdout, stderr = self.ssh_client.exec_command(f'cd /home/anthologizer/anthology-files; find {resource_type.value}')
        output = stdout.read()
        while not stdout.channel.exit_status_ready():
            output += stdout.read()
        if stdout.channel.recv_exit_status():
            raise Exception(stderr.read().decode('utf-8'))
        return output.decode('utf-8').strip().split('\n')
        # subprocess.check_output(['ssh', 'anth', f'cd ~/anthology-files/pdf; find .']).decode('utf-8').strip().split('\n')

    def listdir(self, relative_path: str) -> List[str]:
        abs_dir = f'{self.root_dir}/{relative_path}'
        if self.is_on_server:
            return os.listdir(abs_dir)
        try:
            return self.sftp.listdir(abs_dir)
        except FileNotFoundError:
            raise FileNotFoundError(f"Directory {abs_dir} not on server")
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
        _, stdout, stderr = self.ssh_client.exec_command(f'crc32 {abs_dir}')
        if stdout.channel.recv_exit_status():
            raise Exception(stderr.read().decode('utf-8'))
        return stdout.read().decode('utf-8').strip()
        # return (
        #     subprocess.check_output(['ssh', self.host, f'crc32 {abs_dir}'])
        #     .decode('utf-8')
        #     .strip()
        # )

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


def get_all_pdf_filepath_to_hash(anth: Anthology):
    filepath_to_hash = {}
    for paper in anth.papers.values():
        if paper.pdf is not None and not paper.is_pdf_remote:
            filepath = paper.relative_pdf_path_to_anthology_files
            filepath_to_hash[filepath] = paper.pdf_hash
    for volume in anth.volumes.values():
        if volume.pdf is not None and not volume.is_pdf_remote:
            filepath = volume.relative_pdf_path_to_anthology_files
            filepath_to_hash[filepath] = volume.pdf_hash

    return filepath_to_hash


def get_all_attachment_filepath_to_hash(anth: Anthology):
    filepath_to_hash = {}
    for _, paper in anth.papers.items():
        for attachment in paper.attachments:
            filepath = f"{ResourceType.ATTACHMENT.value}/{paper.collection_id}/{attachment['filename']}"
            filepath_to_hash[filepath] = attachment['hash']

    return filepath_to_hash


old_venue_names = {
    "A",
    "C",
    "D",
    "E",
    "F",
    "H",
    "I",
    "J",
    "K",
    "L",
    "M",
    "N",
    "O",
    "P",
    "Q",
    "R",
    "S",
    "T",
    "U",
    "W",
    "X",
    "Y",
    "Z",
}

directories_to_ignore = {'.DS_Store', 'favicon.ico', 't', 'README', 'J.bib', '.htaccess'}


def list_venues(fs: FileSystemOps, base_path: str):
    for venue_name in tqdm(fs.listdir(base_path)):
        log.debug(f'Checking venue {venue_name!r}')
        if venue_name not in old_venue_names:
            if venue_name not in directories_to_ignore:
                yield venue_name
            continue
        for sub_venue_name in fs.listdir(os.path.join(base_path, venue_name)):
            if sub_venue_name not in directories_to_ignore:
                yield os.path.join(venue_name, sub_venue_name)


def list_venue_files(fs: FileSystemOps, base_path: str):
    l = []
    for filename in fs.listdir(os.path.join(base_path)):
        l.append(os.path.join(base_path, filename))
    return l


def do_complete_check(anth: Anthology, resource_type: ResourceType, fs: FileSystemOps):
    # get all hashes for files in server "live" directory
    # filepaths = []
    # base_path = f'{resource_type.value}'
    # venues = list(list_venues(fs=fs, base_path=base_path))
    # # with concurrent.futures.ThreadPoolExecutor() as executor:
    # for venue_name in tqdm(venues):
    #     # results = list(tqdm(executor.map(partial(list_venue_files, fs), venues), total=len(venues)))
    #     # filepaths = list(itertools.chain(results))
    #     for filename in fs.listdir(os.path.join(base_path, venue_name)):
    #         filepath = os.path.join(base_path, venue_name, filename)
    #         if os.path.splitext(filepath)[1] == ".pdf":
    #             filepaths.append(filepath)

    # log.info(f'Found {len(filepaths)} files')

    fs = FileSystemOps(is_on_server=False, host=ANTHOLOGY_HOST, commit=False)
    o = fs.find(ResourceType.PDF)
    # print(len(o), o[:10])
    pdfs = []
    for x in o:
        path = Path(x)
        if path.suffix == ".pdf":
            pdfs.append(path)
    s = Counter(len(x.parts) for x in pdfs)
    # print(s)
    # print({x for x in pdfs if len(x.parts) == 5})
    filepaths = []
    for pdf_path in pdfs:
        parts = pdf_path.parts
        if len(parts) in {3, 4}:
            filepaths.append(str(pdf_path))

    log.info(f'Found {len(filepaths)} files')

    # import threading
    # mydata = threading.local()
    # def do_work(filepath):
    #     if 'fs' not in mydata.__dict__:
    #         mydata.fs = FileSystemOps(is_on_server=fs.is_on_server, host=fs.host, commit=fs.commit)
    #     return filepath, mydata.fs.hashfile(filepath)

    # # live_filepath_to_hash = {}
    # # filepaths = list(sorted(filepaths))[:200]
    # with concurrent.futures.ThreadPoolExecutor(max_workers=8) as executor:
    #     live_filepath_to_hash = dict(tqdm(executor.map(do_work, filepaths), total=len(filepaths)))
    # # with click.progressbar(filepaths) as bar:
    #     # for filepath in bar:
    #         # live_filepath_to_hash[filepath] = fs.hashfile(filepath)

    # # return

    with open(f'live_{resource_type.value}.json', 'r') as fp:
        live_filepath_to_hash = json.load(fp)
    #     json.dump(live_filepath_to_hash, fp)

    log.info("Will get hashes from Anthology database")
    expected_filepath_to_hash = {
        ResourceType.ATTACHMENT: get_all_attachment_filepath_to_hash,
        ResourceType.PDF: get_all_pdf_filepath_to_hash,
    }[resource_type](anth)
    log.info("Done getting hashes")

    log.info(f'Expected: {list(sorted(expected_filepath_to_hash.keys()))[:10]}')
    log.info(f'Live: {list(sorted(live_filepath_to_hash.keys()))[:10]}')

    missing_files = set(expected_filepath_to_hash.keys() - live_filepath_to_hash.keys())
    extra_files = set(live_filepath_to_hash.keys() - expected_filepath_to_hash.keys())
    log.info(f'Missing Files len: {len(missing_files)}')
    log.info(f'Extra Files len: {len(extra_files)}')


    with open(f'missing_{resource_type.value}.json', 'w') as fp:
        json.dump(list(missing_files), fp)
    with open(f'extra_{resource_type.value}.json', 'w') as fp:
        json.dump(list(extra_files), fp)

    out_dated_files = set()
    common_files = set(expected_filepath_to_hash.keys() & live_filepath_to_hash.keys())
    log.info(f'Common Files len: {len(common_files)}')
    for filepath in common_files:
        if expected_filepath_to_hash[filepath] is None:
            log.error(f'Missing expected_file_hash for {filepath}. Since hash wasn\'t found will assume it is up to date!')
            continue
        if expected_filepath_to_hash[filepath] != live_filepath_to_hash[filepath]:
            log.debug(f'Out Data File {filepath!r} (live hash: {live_filepath_to_hash[filepath]}, expected hash: {expected_filepath_to_hash[filepath]})')
            out_dated_files.add(filepath)

    log.info(f'Out Dated Files len: {len(out_dated_files)}')

    return

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
    # anth = None

    fs = FileSystemOps(is_on_server=is_on_server, host=ANTHOLOGY_HOST, commit=commit)

    if complete_check:
        do_complete_check(anth, resource_type=ResourceType.PDF, fs=fs)
        # do_complete_check(anth, resource_type=ResourceType.ATTACHMENT, fs=fs)
    else:
        process_queue(anth, resource_type=ResourceType.PDF, fs=fs)
        process_queue(anth, resource_type=ResourceType.ATTACHMENT, fs=fs)

    if tracker.highest >= log.ERROR:
        exit(1)

from pathlib import Path

# def test():


if __name__ == "__main__":
    # test()
    main()
