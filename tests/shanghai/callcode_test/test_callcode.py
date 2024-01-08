"""
abstract: Test CALLCODE gas consumption with value transfer
Tests for an EthereumJS bug where CALLCODE gas was incorrectly calculated when a call had
value transfer
https://github.com/ethereumjs/ethereumjs-monorepo/issues/3194

Test setup is 2 contracts where AAAB CALLs AAAA which then CALLCODEs a non-existent contract
AAAC. The CALLCODE result is stored in AAAB's slot 0.

Bytecode for AAAB contract (used to call contract AAAA and stores result of call execution)
```
PUSH1 0x00
DUP1
DUP1
DUP1
DUP1
PUSH2 0xAAAA
PUSH2 0x12D5 <- This is the gas limit set for the CALL/CODE execution when insufficient for
CALLCODE execution
CALL
PUSH1 0x00
SSTORE
```

Bytecode for AAAA contract (used to check CALL/CALLCODE execution when gas is less
than/sufficient for execution)
```
PUSH1 0x00
PUSH1 0x00
PUSH1 0x00
PUSH1 0x00
PUSH1 0x01
PUSH2 0xAACC
PUSH2 0x1a90
CALLCODE/CALL
```
"""

import pytest

from ethereum_test_forks import Fork
from ethereum_test_tools import Account, Environment, StateTestFiller, Transaction


@pytest.mark.valid_from("London")
@pytest.mark.valid_until("Shanghai")
def test_callcode_with_gas(state_test: StateTestFiller, fork: Fork):
    """
    Test CALLCODE gas consumption case with sufficient gas
    """
    env = Environment()

    pre = {
        "0x000000000000000000000000000000000000aaaa": Account(
            balance=0x03,
            code="0x6000600060006000600161AACC611A90F2",
            nonce=1,
        ),
        "0x000000000000000000000000000000000000aaab": Account(
            balance=0x03,
            code="0x60008080808061AAAA613d50f1600055",
            nonce=1,
        ),
        "0xa94f5374fce5edbc8e2a8697c15331677e6ebf0b": Account(
            balance=0xFFFFFFFFF,
            nonce=0,
        ),
    }

    tx = Transaction(
        ty=1,
        chain_id=0x01,
        nonce=0,
        to="0x000000000000000000000000000000000000aaab",
        value=1,
        gas_limit=500000,
        gas_price=7,
        secret_key="0x45a915e4d060149eb4365960e6a7a45f334393093061116b197e3240065ff2d8",
        protected=True,
    )

    post = {
        "0x000000000000000000000000000000000000aaab": Account(storage={0x00: 0x01}),
    }
    state_test(env=env, pre=pre, post=post, txs=[tx])


@pytest.mark.valid_from("London")
@pytest.mark.valid_until("Shanghai")
def test_callcode_without_gas(state_test: StateTestFiller, fork: Fork):
    """
    Test CALLCODE gas consumption without sufficient gas
    """
    env = Environment()

    pre = {
        "0x000000000000000000000000000000000000aaaa": Account(
            balance=0x03,
            code="0x6000600060006000600161AACC611A90F2",
            nonce=1,
        ),
        "0x000000000000000000000000000000000000aaab": Account(
            balance=0x03,
            code="0x60008080808061AAAA612d5ff1600055",
            nonce=1,
        ),
        "0xa94f5374fce5edbc8e2a8697c15331677e6ebf0b": Account(
            balance=0xFFFFFFFFF,
            nonce=0,
        ),
    }

    tx = Transaction(
        ty=0,
        chain_id=0x01,
        nonce=0,
        to="0x000000000000000000000000000000000000aaab",
        value=1,
        gas_limit=2500000,
        gas_price=7,
        secret_key="0x45a915e4d060149eb4365960e6a7a45f334393093061116b197e3240065ff2d8",
        protected=True,
    )

    post = {
        "0x000000000000000000000000000000000000aaab": Account(storage={0x00: 0x00}),
    }
    state_test(env=env, pre=pre, post=post, txs=[tx])
