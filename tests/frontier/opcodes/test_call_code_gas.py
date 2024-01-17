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

"""
PUSH gas cost is 3.
GAS gas cost is 2.
We need 6 PUSH's and one GAS to fill the stack for both CALL & CALLCODE.
"""
PUSH_STACK_GAS = 6 * 3 + 2

"""
CALL gas breakdowns: (https://www.evm.codes/#f1)
memory_exp_cost + code_exec_cost + address_access_cost + positive_value_cost + empty_account_cost
= 0 + 0 + 2600 + 9000 + 25000 = 36600
"""
CALL_GAS = 36600
CALL_SUFFICIENT_GAS = CALL_GAS + PUSH_STACK_GAS

"""
CALLCODE gas breakdowns: (https://www.evm.codes/#f2)
memory_exp_cost + code_exec_cost + address_access_cost + positive_value_cost
= 0 + 0 + 2600 + 9000 = 11600
"""
CALLCODE_GAS = 11600
CALLCODE_SUFFICIENT_GAS = CALLCODE_GAS + PUSH_STACK_GAS


@dataclass(frozen=True)
class Accounts:  # noqa: D101
    caller: int = 0xAAAA
    callee: int = 0xAAAB
    nonexistent_callee: int = 0xAAAC


@pytest.fixture
def caller_code(caller_gas: int) -> bytes:
    """
    Code to call the callee contract:
        PUSH1 0x00 * 5
        PUSH2 Accounts.callee
        PUSH2 caller_gas <- gas limit set for the CALL/CALLCODE execution
        CALL/CALLCODE
        PUSH1 0x00
        SSTORE
    """
    return Op.SSTORE(0, Op.CALL(caller_gas, Accounts.callee, 0, 0, 0, 0, 0))


@pytest.fixture
def callee_code(caller_opcode: Op) -> bytes:
    """
    Code called by the caller contract:
        PUSH1 0x00 * 4
        PUSH1 0x01
        PUSH2 Accounts.nonexistent_callee
        GAS
        CALLCODE
    """
    return caller_opcode(Op.GAS(), Accounts.nonexistent_callee, 1, 0, 0, 0, 0)


@pytest.fixture
def caller_tx() -> Transaction:
    """Transaction that performs the call to the callee contract."""
    return Transaction(
        chain_id=0x01,
        nonce=0,
        to=to_address(Accounts.caller),
        value=1,
        gas_limit=500000,
        gas_price=7,
    )


@pytest.fixture
def pre(callee_code: bytes, caller_code: bytes) -> Dict[str, Account]:  # noqa: D103
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
def post(is_sufficient_gas: bool) -> Dict[str, Account]:  # noqa: D103
    return {
        to_address(Accounts.caller): Account(storage={0x00: 0x01 if is_sufficient_gas else 0x00}),
    }


@pytest.mark.parametrize(
    "caller_opcode, caller_gas, is_sufficient_gas",
    [
        (Op.CALL, CALL_SUFFICIENT_GAS, True),
        (Op.CALL, CALL_SUFFICIENT_GAS - 1, False),
        (Op.CALLCODE, CALLCODE_SUFFICIENT_GAS, True),
        (Op.CALLCODE, CALLCODE_SUFFICIENT_GAS - 1, False),
    ],
)
@pytest.mark.valid_from("London")
@pytest.mark.valid_until("Shanghai")
def test_callcode_gas_value_transfer(
    state_test: StateTestFiller,
    pre: Dict[str, Account],
    caller_tx: Transaction,
    post: Dict[str, Account],
):
    """
    Tests the CALLCODE gas consumption with a CALL/CALLCODE value transfer.
    """
    state_test(env=Environment(), pre=pre, post=post, txs=[caller_tx])
