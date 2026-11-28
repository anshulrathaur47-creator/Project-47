import itertools
import shutil
from typing import List

from facefusion import metadata
from facefusion.types import Command


def run(commands : List[Command]) -> List[Command]:
	user_agent = metadata.get('name') + '/' + metadata.get('version')

	return [ shutil.which('curl'), '--user-agent', user_agent, '--location', '--silent', '--fail', '--ssl-no-revoke' ] + commands


def chain(*commands : List[Command]) -> List[Command]:
	return list(itertools.chain(*commands))


def ping(url : str) -> List[Command]:
	# Project-47 patch: a HEAD on the bare github.com root gets HTTP 400 through this sandbox's proxy, so ping a real release asset
	return [ '-I', url.rstrip('/') + '/facefusion/facefusion-assets/releases/download/models-3.3.0/nsfw_1.hash' if url.rstrip('/') == 'https://github.com' else url ]


def download(url : str, download_file_path : str) -> List[Command]:
	return [ '--create-dirs', '--continue-at', '-', '--output', download_file_path, url ]


def set_timeout(timeout : int) -> List[Command]:
	return [ '--connect-timeout', str(timeout) ]


def set_retry(retry : int) -> List[Command]:
	return [ '--retry', str(retry) ]
