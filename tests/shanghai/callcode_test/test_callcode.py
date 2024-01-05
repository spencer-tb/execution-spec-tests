"""
Test CALLCODE gas consumption
"""

import pytest


from ethereum_test_forks import Fork
from ethereum_test_tools import Account, Environment
from ethereum_test_tools import StateTestFiller, Transaction


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
            balance=0xfffffffff,
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
        "0x000000000000000000000000000000000000aaab": Account(
            storage={0x00: 0x01}
        ),
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
            balance=0xfffffffff,
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
        "0x000000000000000000000000000000000000aaab": Account(
            storage={0x00: 0x00}
        ),
    }
    state_test(env=env, pre=pre, post=post, txs=[tx])
