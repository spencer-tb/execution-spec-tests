"""
State test filler.
"""
from copy import copy
from dataclasses import dataclass
from typing import Callable, Generator, List, Mapping, Optional, Tuple, Type

from ethereum_test_forks import Fork
from evm_transition_tool import TransitionTool

from ..common import (
    Address,
    Alloc,
    Bloom,
    Bytes,
    EmptyTrieRoot,
    Environment,
    Fixture,
    FixtureBlock,
    FixtureEngineNewPayload,
    FixtureHeader,
    Hash,
    HeaderNonce,
    HiveFixture,
    Number,
    Transaction,
    ZeroPaddedHexNumber,
    alloc_to_accounts,
    to_json,
)
from ..common.constants import EmptyOmmersRoot, EngineAPIError
from .base_test import BaseTest, verify_post_alloc, verify_result, verify_transactions
from .debugging import print_traces


@dataclass(kw_only=True)
class StateTest(BaseTest):
    """
    Filler type that tests transactions over the period of a single block.
    """

    env: Environment
    pre: Mapping
    post: Mapping
    txs: List[Transaction]
    engine_api_error_code: Optional[EngineAPIError] = None
    tag: str = ""

    chain_id: int = 1

    @classmethod
    def pytest_parameter_name(cls) -> str:
        """
        Returns the parameter name used to identify this filler in a test.
        """
        return "state_test"

    def make_genesis(
        self,
        t8n: TransitionTool,
        fork: Fork,
    ) -> Tuple[Alloc, Bytes, FixtureHeader]:
        """
        Create a genesis block from the state test definition.
        """
        # The genesis environment is similar to the block 1 environment specified by the test
        # with some slight differences, so make a copy here
        genesis_env = copy(self.env)

        # Modify values to the proper values for the genesis block
        genesis_env.withdrawals = None
        genesis_env.beacon_root = None
        genesis_env.number = Number(genesis_env.number) - 1
        assert (
            genesis_env.number >= 0
        ), "genesis block number cannot be negative, set state test env.number to 1"

        # Set the fork requirements to the genesis environment in-place
        genesis_env.set_fork_requirements(fork, in_place=True)

        pre_alloc = Alloc(
            fork.pre_allocation(
                block_number=genesis_env.number, timestamp=Number(genesis_env.timestamp)
            )
        )

        new_alloc, state_root = t8n.calc_state_root(
            alloc=to_json(Alloc.merge(pre_alloc, Alloc(self.pre))),
            fork=fork,
            debug_output_path=self.get_next_transition_tool_output_path(),
        )
        genesis = FixtureHeader(
            parent_hash=Hash(0),
            ommers_hash=Hash(EmptyOmmersRoot),
            coinbase=Address(0),
            state_root=Hash(state_root),
            transactions_root=Hash(EmptyTrieRoot),
            receipt_root=Hash(EmptyTrieRoot),
            bloom=Bloom(0),
            difficulty=ZeroPaddedHexNumber(
                0x20000 if genesis_env.difficulty is None else genesis_env.difficulty
            ),
            number=ZeroPaddedHexNumber(genesis_env.number),
            gas_limit=ZeroPaddedHexNumber(genesis_env.gas_limit),
            gas_used=0,
            timestamp=0,
            extra_data=Bytes([0]),
            mix_digest=Hash(0),
            nonce=HeaderNonce(0),
            base_fee=ZeroPaddedHexNumber.or_none(genesis_env.base_fee),
            blob_gas_used=ZeroPaddedHexNumber.or_none(genesis_env.blob_gas_used),
            excess_blob_gas=ZeroPaddedHexNumber.or_none(genesis_env.excess_blob_gas),
            withdrawals_root=Hash.or_none(
                EmptyTrieRoot if genesis_env.withdrawals is not None else None
            ),
            beacon_root=Hash.or_none(genesis_env.beacon_root),
        )

        genesis_rlp, genesis.hash = genesis.build(
            txs=[],
            ommers=[],
            withdrawals=genesis_env.withdrawals,
        )

        return Alloc(new_alloc), genesis_rlp, genesis

    def make_fixture(
        self,
        t8n: TransitionTool,
        fork: Fork,
        eips: Optional[List[int]] = None,
    ) -> Fixture:
        """
        Create a block from the state test definition.
        Performs checks against the expected behavior of the test.
        Raises exception on invalid test behavior.
        """
        pre, genesis_rlp, genesis = self.make_genesis(t8n, fork)

        network_info = (
            "+".join([fork.name()] + [str(eip) for eip in eips])
            if eips is not None
            else fork.name()
        )

        env = self.env.apply_new_parent(genesis)
        env = env.set_fork_requirements(fork)

        txs = [tx.with_signature_and_sender() for tx in self.txs] if self.txs is not None else []

        alloc, result = t8n.evaluate(
            alloc=to_json(pre),
            txs=to_json(txs),
            env=to_json(env),
            fork_name=network_info,
            chain_id=self.chain_id,
            reward=fork.get_reward(Number(env.number), Number(env.timestamp)),
            eips=eips,
            debug_output_path=self.get_next_transition_tool_output_path(),
        )

        rejected_txs = verify_transactions(txs, result)
        if len(rejected_txs) > 0:
            raise Exception(
                "one or more transactions in `StateTest` are "
                + "intrinsically invalid, which are not allowed. "
                + "Use `BlockchainTest` to verify rejection of blocks "
                + "that include invalid transactions."
            )

        try:
            verify_post_alloc(self.post, alloc)
            verify_result(result, env)
        except Exception as e:
            print_traces(traces=t8n.get_traces())
            raise e

        env.extra_data = b"\x00"
        header = FixtureHeader.collect(
            fork=fork,
            transition_tool_result=result,
            environment=env,
        )

        block, header.hash = header.build(
            txs=txs,
            ommers=[],
            withdrawals=env.withdrawals,
        )

        fixture = Fixture(
            fork=network_info,
            genesis=genesis,
            genesis_rlp=genesis_rlp,
            blocks=[
                FixtureBlock(
                    rlp=block,
                    block_header=header,
                    txs=txs,
                    ommers=[],
                    withdrawals=env.withdrawals,
                )
            ],
            last_block_hash=header.hash,
            pre_state=pre,
            post_state=alloc_to_accounts(alloc),
        )
        return fixture

    def make_hive_fixture(
        self,
        t8n: TransitionTool,
        fork: Fork,
        eips: Optional[List[int]] = None,
    ) -> HiveFixture:
        """
        Create a block from the state test definition.
        Performs checks against the expected behavior of the test.
        Raises exception on invalid test behavior.
        """
        pre, _, genesis = self.make_genesis(t8n, fork)

        network_info = (
            "+".join([fork.name()] + [str(eip) for eip in eips])
            if eips is not None
            else fork.name()
        )

        env = self.env.apply_new_parent(genesis)
        env = env.set_fork_requirements(fork)

        txs = [tx.with_signature_and_sender() for tx in self.txs] if self.txs is not None else []

        alloc, result = t8n.evaluate(
            alloc=to_json(pre),
            txs=to_json(txs),
            env=to_json(env),
            fork_name=network_info,
            chain_id=self.chain_id,
            reward=fork.get_reward(Number(env.number), Number(env.timestamp)),
            eips=eips,
            debug_output_path=self.get_next_transition_tool_output_path(),
        )

        rejected_txs = verify_transactions(txs, result)
        if len(rejected_txs) > 0:
            raise Exception(
                "one or more transactions in `StateTest` are "
                + "intrinsically invalid, which are not allowed. "
                + "Use `BlockchainTest` to verify rejection of blocks "
                + "that include invalid transactions."
            )

        try:
            verify_post_alloc(self.post, alloc)
            verify_result(result, env)
        except Exception as e:
            print_traces(traces=t8n.get_traces())
            raise e

        env.extra_data = b"\x00"
        header = FixtureHeader.collect(
            fork=fork,
            transition_tool_result=result,
            environment=env,
        )

        _, header.hash = header.build(
            txs=txs,
            ommers=[],
            withdrawals=env.withdrawals,
        )

        fixture_payload = FixtureEngineNewPayload.from_fixture_header(
            fork=fork,
            header=header,
            transactions=txs,
            withdrawals=env.withdrawals,
            valid=True,
            error_code=None,
        )
        fcu_version = fork.engine_forkchoice_updated_version(header.number, header.timestamp)

        hive_fixture = HiveFixture(
            fork=network_info,
            genesis=genesis,
            payloads=[fixture_payload],
            fcu_version=fcu_version,
            pre_state=pre,
            post_state=alloc_to_accounts(alloc),
        )

        return hive_fixture


StateTestSpec = Callable[[str], Generator[StateTest, None, None]]
StateTestFiller = Type[StateTest]
