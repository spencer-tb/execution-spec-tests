"""
Test suite for `ethereum_test_tools.consume.types` module, with a focus on the engine payloads.
"""

import json
import os
from typing import Any

import pytest

from ethereum_test_forks import Cancun, Fork, Merge, Shanghai  # TODO: Replace with Paris
from ethereum_test_tools.common import (
    Account,
    Block,
    Fixture,
    FixtureBlock,
    TestAddress,
    Transaction,
    to_json,
)
from ethereum_test_tools.common.json import load_dataclass_from_json
from ethereum_test_tools.consume.types import EngineCancun, EngineParis, EngineShanghai
from ethereum_test_tools.filling import fill_test
from ethereum_test_tools.spec import BlockchainTest
from evm_transition_tool import GethTransitionTool

common_execution_payload_fields = {
    "coinbase": "0x2adc25665018aa1fe0e6bc666dac8fc2697ff9ba",
    "receipts_root": "0xc598f69a5674cae9337261b669970e24abc0b46e6d284372a239ec8ccbf20b0a",
    "logs_bloom": "0x00000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000",  # noqa: E501
    "prev_randao": "0x0000000000000000000000000000000000000000000000000000000000000000",
    "number": 1,
    "gas_limit": 100000000000000000,
    "gas_used": 43105,
    "timestamp": 12,
    "extra_data": "0x",
    "base_fee_per_gas": 7,
    "transactions": [
        "0xf861800a8405f5e10094100000000000000000000000000000000000000080801ba07e09e26678ed4fac08a249ebe8ed680bf9051a5e14ad223e4b2b9d26e0208f37a05f6e3f188e3e6eab7d7d3b6568f5eac7d687b08d307d3154ccd8c87b4630509b"  # noqa: E501
    ],
}


@pytest.mark.parametrize(
    "fork, expected_json_fixture, expected_engine_new_payload, expected_enp_json",
    [
        (
            Merge,  # TODO: Replace with Paris
            "valid_simple_merge_blockchain.json",
            EngineParis.NewPayloadV1(
                execution_payload=EngineParis.ExecutionPayloadV1(
                    **common_execution_payload_fields,
                    parent_hash=(
                        "0x86c6dc9cb7b8ada9e27b1cf16fd81f366a0ad8127f42ff13d778eb2ddf7eaa90"
                    ),
                    state_root=(
                        "0x19919608275963e6e20a1191996f5b19db8208dd8df54097cfd2b9cb14f682b6"
                    ),
                    block_hash=(
                        "0xe9694e4b99986d312c6891cd7839b73d9e1b451537896818cefeeae97d7e3ea6"
                    ),
                )
            ),
            "valid_simple_merge_enp.json",
        ),
        (
            Shanghai,
            "valid_simple_shanghai_blockchain.json",
            EngineShanghai.NewPayloadV2(
                execution_payload=EngineShanghai.ExecutionPayloadV2(
                    **common_execution_payload_fields,
                    parent_hash=(
                        "0xccb89b5b6043aa73114e6857f0783a02808ea6ff4cabd104a308eb4fe0114a9b"
                    ),
                    state_root=(
                        "0x19919608275963e6e20a1191996f5b19db8208dd8df54097cfd2b9cb14f682b6"
                    ),
                    block_hash=(
                        "0xc970b6bcf304cd5c71d24548a7d65dd907a24a3b66229378e2ac42677c1eec2b"
                    ),
                    withdrawals=[],
                )
            ),
            "valid_simple_shanghai_enp.json",
        ),
        (
            Cancun,
            "valid_simple_cancun_blockchain.json",
            EngineCancun.NewPayloadV3(
                execution_payload=EngineCancun.ExecutionPayloadV3(
                    **common_execution_payload_fields,
                    parent_hash=(
                        "0xda9249b7aff004bcdfadfb5f668899746e36a5eee8197d1589deb4a3842251ce"
                    ),
                    state_root=(
                        "0x3d760432d38fbf795fb9addd6b25a692d82498bd5f7b703a6da6d8647c5b7820"
                    ),
                    block_hash=(
                        "0x546546d8a2d99b3135a47debdfc708e6a2199b8d90e43325d2c0b3adc3613709"
                    ),
                    withdrawals=[],
                    blob_gas_used=0,
                    excess_blob_gas=0,
                ),
                expected_blob_versioned_hashes=[],
                parent_beacon_block_root=(
                    "0x0000000000000000000000000000000000000000000000000000000000000000"
                ),
            ),
            "valid_simple_cancun_enp.json",
        ),
    ],
)
def test_valid_engine_new_payload_fields(
    fork: Fork,
    expected_json_fixture: str,
    expected_engine_new_payload: Any,
    expected_enp_json: str,
):
    """
    Test ...
    """
    blockchain_test = BlockchainTest(
        pre={
            0x1000000000000000000000000000000000000000: Account(code="0x4660015500"),
            TestAddress: Account(balance=1000000000000000000000),
        },
        post={
            "0x1000000000000000000000000000000000000000": Account(
                code="0x4660015500", storage={"0x01": "0x01"}
            ),
        },
        blocks=[
            Block(
                txs=[
                    Transaction(
                        ty=0x0,
                        chain_id=0x0,
                        nonce=0,
                        to="0x1000000000000000000000000000000000000000",
                        gas_limit=100000000,
                        gas_price=10,
                        protected=False,
                    )
                ]
            )
        ],
    )
    # Create a blockchain test fixture
    fixture: Fixture = {
        f"000/valid_blockchain_test/{fork}": fill_test(
            t8n=GethTransitionTool(),
            test_spec=blockchain_test,
            fork=fork,
            spec=None,
        ),
    }
    # Sanity check the fixture is equal to the expected
    with open(
        os.path.join(
            "src",
            "ethereum_test_tools",
            "tests",
            "test_consume",
            "fixtures",
            expected_json_fixture,
        )
    ) as f:
        expected = json.load(f)
    fixture_json = to_json(fixture)
    assert fixture_json == expected

    # Load json fixture into Fixture type
    for _, fixture_data in fixture_json.items():
        fixture = load_dataclass_from_json(Fixture, fixture_data)

    # Get fixture blocks
    fixture_blocks = [
        load_dataclass_from_json(FixtureBlock, block.get("rlp_decoded", block))
        for block in fixture.blocks
    ]

    # Extract the engine payloads from the fixture blocks
    # Ideally we don't know the fork at this point
    for fixture_block in fixture_blocks:
        fork = globals()[fixture.fork]
        version = fork.engine_new_payload_version(
            fixture_block.block_header.number, fixture_block.block_header.timestamp
        )
        if version == 1:
            PayloadClass = EngineParis.NewPayloadV1
        elif version == 2:
            PayloadClass = EngineShanghai.NewPayloadV2
        elif version == 3:
            PayloadClass = EngineCancun.NewPayloadV3
        else:
            ValueError(f"Unexpected payload version: {version}")
            continue

        engine_new_payload = PayloadClass.from_fixture_block(fixture_block)

    # Compare the engine payloads with the expected payloads
    assert engine_new_payload == expected_engine_new_payload

    # Check the json representation of the engine payloads that would be sent over json-rpc
    with open(
        os.path.join(
            "src",
            "ethereum_test_tools",
            "tests",
            "test_consume",
            "engine_json",
            expected_enp_json,
        )
    ) as f:
        expected = json.load(f)

    print(engine_new_payload.to_json_rpc())
    assert engine_new_payload.to_json_rpc() == expected
