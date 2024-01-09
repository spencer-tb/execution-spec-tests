"""
abstract: Tests the CALLCODE gas consumption with a CALL/CALLCODE value transfer.

    Tests an EthereumJS bug where the CALLCODE gas was incorrectly calculated from a
    CALL value transfer: https://github.com/ethereumjs/ethereumjs-monorepo/issues/3194

    Test setup: 2 smart contract accounts exist where AAAB CALL/CALLCODEs AAAA, which then
    CALLCODEs a non-existent contract AAAC. The result of AAAA's CALL/CALLCODE is stored in AAAB's
    storage slot 0.
"""

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


@pytest.fixture
def caller_code(caller_gas, caller_type):
    """
    Code to call the callee contract:
        PUSH1 0x00
        DUP1 * 4
        PUSH2 0xAAAA
        PUSH2 call_gas
        CALL/CALLCODE
        PUSH1 0x00
        SSTORE
    """
    return Op.SSTORE(0, caller_type(caller_gas, 0xAAAA, 0, 0, 0, 0, 0))


@pytest.fixture
def callee_code():
    """
    Code called by the caller contract:
        PUSH1 0x00 * 4
        PUSH1 0x00
        PUSH1 0x00
        PUSH2 0xAACC
        PUSH2 0x1a90
        CALLCODE
    """
    return Op.CALLCODE(0x1A90, 0xAACC, 1, 0, 0, 0, 0)


@pytest.fixture
def caller_tx() -> Transaction:
    """
    Transaction that calls the callee contract.
    """
    return Transaction(
        chain_id=0x01,
        nonce=0,
        to=to_address(0xAAAB),
        value=1,
        gas_limit=500000,
        gas_price=7,
    )


@pytest.fixture
def pre(callee_code, caller_code) -> Dict[str, Account]:  # noqa: D103
    return {
        to_address(0xAAAA): Account(
            balance=0x03,
            code=callee_code,
            nonce=1,
        ),
        to_address(0xAAAB): Account(
            balance=0x03,
            code=caller_code,
            nonce=1,
        ),
        TestAddress: Account(
            balance=0x0BA1A5CE,
        ),
    }


@pytest.fixture
def post(caller_gas) -> Dict[str, Account]:  # noqa: D103
    return {
        to_address(0xAAAB): Account(storage={0x00: (0x01 if caller_gas >= 0x3D50 else 0x00)}),
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
