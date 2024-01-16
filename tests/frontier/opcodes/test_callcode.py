"""
abstract: Tests the CALLCODE gas consumption with a CALL/CALLCODE value transfer.

    Tests an EthereumJS bug where the CALLCODE gas was incorrectly calculated from a
    CALL value transfer: https://github.com/ethereumjs/ethereumjs-monorepo/issues/3194

    Test setup: Given two smart contract accounts, AAAA and AAAB:
    - AAAA CALL/CALLCODEs AAAB which then CALLCODEs a non-existent contract AAAC.
    - The result of AAAB's CALL/CALLCODE is stored in AAAA's storage slot 0.
"""

from dataclasses import dataclass
from typing import Dict

import pytest

from ethereum_test_tools import (
    Account,
    Environment,
    StateTestFiller,
    TestAddress,
    Transaction,
    to_address,
)
from ethereum_test_tools.vm.opcode import Opcodes as Op


@dataclass(frozen=True)
class Accounts:  # noqa: D101
    caller: int = 0xAAAA
    callee: int = 0xAAAB
    nonexistent_callee: int = 0xAAAC


@pytest.fixture
def caller_code(caller_gas, caller_type):
    """
    Code to call the callee contract:
        PUSH1 0x00
        DUP1 * 4
        PUSH2 Accounts.callee
        PUSH2 call_gas
        CALL/CALLCODE
        PUSH1 0x00
        SSTORE
    """
    return Op.SSTORE(0, caller_type(caller_gas, Accounts.callee, 0, 0, 0, 0, 0))


@pytest.fixture
def callee_code():
    """
    Code called by the caller contract:
        PUSH1 0x00 * 4
        PUSH1 0x00
        PUSH1 0x00
        PUSH2 Accounts.nonexistent_callee
        PUSH2 0x1a90
        CALLCODE
    """
    return Op.CALLCODE(0x1A90, Accounts.nonexistent_callee, 1, 0, 0, 0, 0)


@pytest.fixture
def caller_tx() -> Transaction:
    """
    Transaction that calls the callee contract.
    """
    return Transaction(
        chain_id=0x01,
        nonce=0,
        to=to_address(Accounts.caller),
        value=1,
        gas_limit=500000,
        gas_price=7,
    )


@pytest.fixture
def pre(callee_code, caller_code) -> Dict[str, Account]:  # noqa: D103
    return {
        to_address(Accounts.callee): Account(
            balance=0x03,
            code=callee_code,
            nonce=1,
        ),
        to_address(Accounts.caller): Account(
            balance=0x03,
            code=caller_code,
            nonce=1,
        ),
        TestAddress: Account(
            balance=0x0BA1A9CE,
        ),
    }


@pytest.fixture
def post(caller_gas) -> Dict[str, Account]:  # noqa: D103
    return {
        to_address(Accounts.caller): Account(
            storage={0x00: (0x01 if caller_gas >= 0x3D50 else 0x00)}
        ),
    }


@pytest.mark.parametrize(
    "caller_gas",
    [0x2D5F, 0x3D50],
    ids=["insufficient", "sufficient"],
)
@pytest.mark.parametrize(
    "caller_type",
    [Op.CALL, Op.CALLCODE],
)
@pytest.mark.valid_from("London")
@pytest.mark.valid_until("Shanghai")
def test_callcode_gas_with_call(
    state_test: StateTestFiller,
    pre: Dict[str, Account],
    caller_tx: Transaction,
    post: Dict[str, Account],
):
    """
    Tests the CALLCODE gas consumption with a CALL/CALLCODE value transfer.
    """
    state_test(env=Environment(), pre=pre, post=post, txs=[caller_tx])
