"""
CLI entry point for the `execute` pytest-based command.
"""

import sys
from typing import Tuple

import click
import pytest

from .common import common_click_options, handle_help_flags


@click.option(
    "--hive-mode",
    "hive_mode_flag",
    is_flag=True,
    default=False,
    expose_value=True,
    help="Whether to run in hive mode, which spawns a devnet with the required genesis.",
)
@click.command(context_settings=dict(ignore_unknown_options=True))
@common_click_options
def execute(
    pytest_args: Tuple[str, ...],
    hive_mode_flag: bool,
    **kwargs,
) -> None:
    """
    Entry point for the execute command.
    """
    pytest_type = "execute-hive" if hive_mode_flag else "execute"
    args = handle_help_flags(list(pytest_args), pytest_type=pytest_type)
    ini_file = "pytest-execute-hive.ini" if hive_mode_flag else "pytest-execute.ini"
    args = ["-c", ini_file] + args
    result = pytest.main(args)
    sys.exit(result)
