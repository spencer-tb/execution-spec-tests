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
            code="0x6000600060006000600130611a90f2",
            nonce=1,
        ),
        "0xa94f5374fce5edbc8e2a8697c15331677e6ebf0b": Account(
            balance=0x300000,
            nonce=0,
        ),
    }

    tx = Transaction(
        ty=1,
        chain_id=0x01,
        nonce=0,
        to="0x000000000000000000000000000000000000aaaa",
        value=1,
        gas_limit=50000,
        gas_price=7,
        secret_key="0x45a915e4d060149eb4365960e6a7a45f334393093061116b197e3240065ff2d8",
        protected=True,
    )

    post = {
        "0x000000000000000000000000000000000000aaaa": Account(
            code="0x6000600060006000600130611a90f2",
            balance=4,
            nonce=1,
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
            code="0x6000600060006000600130611a90f2",
            nonce=1,
        ),
        "0xa94f5374fce5edbc8e2a8697c15331677e6ebf0b": Account(
            balance=0x300000,
            nonce=0,
        ),
    }

    tx = Transaction(
        ty=0,
        chain_id=0x01,
        nonce=0,
        to="0x000000000000000000000000000000000000aaaa",
        value=1,
        gas_limit=25000,
        gas_price=7,
        secret_key="0x45a915e4d060149eb4365960e6a7a45f334393093061116b197e3240065ff2d8",
        protected=True,
    )

    post = {
        "0x000000000000000000000000000000000000aaaa": Account(
            code="0x6000600060006000600130611a90f2",
            balance=3,
            nonce=1,
        ),
    }
    state_test(env=env, pre=pre, post=post, txs=[tx])
