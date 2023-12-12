"""
Ethereum `engine_X` JSON-RPC Engine API methods used within EEST based hive simulators.
"""
from typing import Dict, List, Optional

from ..common import Hash
from .base_rpc import BaseRPC

# TODO: define the executionPayload and forkchoiceState types etc
ExecutionPayload = Dict
ForkchoiceStateV1 = Dict
PayloadAttributes = Dict


class EngineRPC(BaseRPC):
    """
    Represents an Engine API RPC class for every Engine API method used within EEST based hive
    simulators.
    """

    def new_payload(
        self,
        execution_payload: ExecutionPayload,
        version: int = 1,
        blob_versioned_hashes: Optional[List[Hash]] = None,
        parent_beacon_block_root: Optional[Hash] = None,
    ):
        """
        `engine_newPayloadVX`: Attempts to execute the given payload on an execution client.

        Params:
            1) execution_payload: execution payload of the block to be executed.
            2) blob_versioned_hashes: blob hashes within the block for execution (required only
            for version >= 3).
            3) parent_beacon_block_root: parent beacon block root of the block for execution
            (required only for version >= 3).
            2) version: engine api version of the method to be used (default: 1).
        """
        payload_params = [execution_payload]
        if version >= 3:
            if blob_versioned_hashes is None or parent_beacon_block_root is None:
                raise ValueError(
                    """blob_versioned_hashes and parent_beacon_block_root are
                     required for version >= 3"""
                )
            payload_params.append(blob_versioned_hashes)
            payload_params.append(parent_beacon_block_root)
        else:
            if blob_versioned_hashes is not None or parent_beacon_block_root is not None:
                raise ValueError(
                    """cannot use blob_versioned_hashes or parent_beacon_block_root for
                    version < 3"""
                )
        return self.post_request(f"engine_newPayloadV{version}", payload_params)

    def forkchoice_updated(
        self,
        forkchoice_state: ForkchoiceStateV1,
        payload_attributes: PayloadAttributes,
        version: int = 1,
    ):
        """
        `engine_forkchoiceUpdatedVX`: Updates the forkchoice state of the execution client.

        Params:
            1) forkchoice_state: forkchoice state of the execution client.
            2) payload_attributes: payload attributes to update the canonical chain with.
            3) version: engine api version of the method to be used (default: 1).
        """
        payload_params = [forkchoice_state, payload_attributes]
        return self.post_request(f"engine_forkchoiceUpdatedV{version}", payload_params)
