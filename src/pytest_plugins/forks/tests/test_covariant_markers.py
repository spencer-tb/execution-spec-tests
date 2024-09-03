"""
Test fork covariant markers and their effect on test parametrization.
"""

import pytest


@pytest.mark.parametrize(
    "test_function,outcomes,error_string",
    [
        pytest.param(
            """
            import pytest
            @pytest.mark.with_all_tx_types()
            @pytest.mark.valid_from("Paris")
            @pytest.mark.valid_until("Paris")
            def test_case(state_test_only, tx_type):
                pass
            """,
            dict(passed=3, failed=0, skipped=0, errors=0),
            None,
            id="with_all_tx_types",
        ),
        pytest.param(
            """
            import pytest
            @pytest.mark.with_all_tx_types(selector=lambda tx_type: tx_type != 0)
            @pytest.mark.valid_from("Paris")
            @pytest.mark.valid_until("Paris")
            def test_case(state_test_only, tx_type):
                pass
            """,
            dict(passed=2, failed=0, skipped=0, errors=0),
            None,
            id="with_all_tx_types_with_selector",
        ),
        pytest.param(
            """
            import pytest
            @pytest.mark.with_all_tx_types(
                marks=lambda tx_type: pytest.mark.skip("incompatible") if tx_type == 1 else None,
            )
            @pytest.mark.valid_from("Paris")
            @pytest.mark.valid_until("Paris")
            def test_case(state_test_only, tx_type):
                assert tx_type != 1
            """,
            dict(passed=2, xpassed=0, failed=0, skipped=1, errors=0),
            None,
            id="with_all_tx_types_with_marks_lambda",
        ),
        pytest.param(
            """
            import pytest
            @pytest.mark.with_all_tx_types(marks=pytest.mark.skip("incompatible"))
            @pytest.mark.valid_from("Paris")
            @pytest.mark.valid_until("Paris")
            def test_case(state_test_only, tx_type):
                assert False
            """,
            dict(passed=0, xpassed=0, failed=0, skipped=3, errors=0),
            None,
            id="with_all_tx_types_with_marks_lambda",
        ),
        pytest.param(
            """
            import pytest
            @pytest.mark.with_all_tx_types(marks=[pytest.mark.skip("incompatible")])
            @pytest.mark.valid_from("Paris")
            @pytest.mark.valid_until("Paris")
            def test_case(state_test_only, tx_type):
                assert False
            """,
            dict(passed=0, xpassed=0, failed=0, skipped=3, errors=0),
            None,
            id="with_all_tx_types_with_marks_lambda",
        ),
        pytest.param(
            """
            import pytest
            @pytest.mark.with_all_tx_types(
                marks=(
                    lambda tx_type:
                        [pytest.mark.xfail, pytest.mark.slow]
                        if tx_type == 1 else None
                    ),
            )
            @pytest.mark.valid_from("Paris")
            @pytest.mark.valid_until("Paris")
            def test_case(request, state_test_only, tx_type):
                mark_names = [mark.name for mark in request.node.iter_markers()]

                assert "state_test" in mark_names
                if tx_type == 1:
                    assert "slow" in mark_names
            """,
            dict(passed=2, xpassed=1, failed=0, skipped=0, errors=0),
            None,
            id="with_all_tx_types_with_marks_lambda_multiple_marks",
        ),
        pytest.param(
            """
            import pytest
            @pytest.mark.with_all_contract_creating_tx_types()
            @pytest.mark.valid_from("Paris")
            @pytest.mark.valid_until("Paris")
            def test_case(state_test_only, tx_type):
                pass
            """,
            dict(passed=3, failed=0, skipped=0, errors=0),
            None,
            id="with_all_contract_creating_tx_types",
        ),
        pytest.param(
            """
            import pytest
            @pytest.mark.with_all_contract_creating_tx_types()
            @pytest.mark.valid_from("Cancun")
            @pytest.mark.valid_until("Cancun")
            def test_case(state_test_only, tx_type):
                pass
            """,
            dict(passed=3, failed=0, skipped=0, errors=0),
            None,
            id="with_all_contract_creating_tx_types",
        ),
        pytest.param(
            """
            import pytest
            @pytest.mark.with_all_precompiles()
            @pytest.mark.valid_from("Cancun")
            @pytest.mark.valid_until("Cancun")
            def test_case(state_test_only, precompile):
                pass
            """,
            dict(passed=10, failed=0, skipped=0, errors=0),
            None,
            id="with_all_precompiles",
        ),
        pytest.param(
            """
            import pytest
            @pytest.mark.with_all_evm_code_types()
            @pytest.mark.valid_from("Cancun")
            @pytest.mark.valid_until("Cancun")
            def test_case(state_test_only, evm_code_type):
                pass
            """,
            dict(passed=1, failed=0, skipped=0, errors=0),
            None,
            id="with_all_evm_code_types",
        ),
        pytest.param(
            """
            import pytest
            @pytest.mark.with_all_call_opcodes()
            @pytest.mark.valid_from("Cancun")
            @pytest.mark.valid_until("Cancun")
            def test_case(state_test_only, call_opcode):
                pass
            """,
            dict(passed=4, failed=0, skipped=0, errors=0),
            None,
            id="with_all_call_opcodes",
        ),
        pytest.param(
            """
            import pytest
            from ethereum_test_tools import EVMCodeType
            @pytest.mark.with_all_call_opcodes(
                selector=(lambda _, evm_code_type: evm_code_type == EVMCodeType.LEGACY)
            )
            @pytest.mark.valid_from("Cancun")
            @pytest.mark.valid_until("Cancun")
            def test_case(state_test_only, call_opcode):
                pass
            """,
            dict(passed=4, failed=0, skipped=0, errors=0),
            None,
            id="with_all_call_opcodes_with_selector_for_evm_code_type",
        ),
        pytest.param(
            """
            import pytest
            from ethereum_test_tools import Opcodes as Op
            @pytest.mark.with_all_call_opcodes(selector=lambda call_opcode: call_opcode == Op.CALL)
            @pytest.mark.valid_from("Cancun")
            @pytest.mark.valid_until("Cancun")
            def test_case(state_test_only, call_opcode):
                pass
            """,
            dict(passed=1, failed=0, skipped=0, errors=0),
            None,
            id="with_all_call_opcodes_with_selector",
        ),
        pytest.param(
            """
            import pytest
            @pytest.mark.with_all_create_opcodes()
            @pytest.mark.valid_from("Cancun")
            @pytest.mark.valid_until("Cancun")
            def test_case(state_test_only, create_opcode):
                pass
            """,
            dict(passed=2, failed=0, skipped=0, errors=0),
            None,
            id="with_all_create_opcodes",
        ),
        pytest.param(
            """
            import pytest
            @pytest.mark.with_all_call_opcodes()
            @pytest.mark.with_all_precompiles()
            @pytest.mark.valid_from("Cancun")
            @pytest.mark.valid_until("Cancun")
            def test_case(state_test_only, call_opcode, precompile):
                pass
            """,
            dict(passed=4 * 10, failed=0, skipped=0, errors=0),
            None,
            id="with_all_call_opcodes_and_precompiles",
        ),
        pytest.param(
            """
            import pytest
            @pytest.mark.with_all_call_opcodes()
            @pytest.mark.with_all_create_opcodes()
            @pytest.mark.valid_from("Cancun")
            @pytest.mark.valid_until("Cancun")
            def test_case(state_test_only, call_opcode, create_opcode):
                pass
            """,
            dict(passed=2 * 4, failed=0, skipped=0, errors=0),
            None,
            id="with_all_call_opcodes_and_create_opcodes",
        ),
        pytest.param(
            """
            import pytest
            @pytest.mark.with_all_system_contracts()
            @pytest.mark.valid_from("Cancun")
            @pytest.mark.valid_until("Cancun")
            def test_case(state_test_only, system_contract):
                pass
            """,
            dict(passed=1, failed=0, skipped=0, errors=0),
            None,
            id="with_all_system_contracts",
        ),
        pytest.param(
            """
            import pytest
            @pytest.mark.with_all_tx_types(invalid_parameter="invalid")
            @pytest.mark.valid_from("Paris")
            @pytest.mark.valid_until("Paris")
            def test_case(state_test_only, tx_type):
                pass
            """,
            dict(passed=0, failed=0, skipped=0, errors=1),
            "Unknown arguments to with_all_tx_types",
            id="invalid_covariant_marker_parameter",
        ),
        pytest.param(
            """
            import pytest
            @pytest.mark.with_all_tx_types(selector=None)
            @pytest.mark.valid_from("Paris")
            @pytest.mark.valid_until("Paris")
            def test_case(state_test_only, tx_type):
                pass
            """,
            dict(passed=0, failed=0, skipped=0, errors=1),
            "selector must be a function",
            id="invalid_selector",
        ),
        pytest.param(
            """
            import pytest
            @pytest.mark.with_all_tx_types(lambda tx_type: tx_type != 0)
            @pytest.mark.valid_from("Paris")
            @pytest.mark.valid_until("Paris")
            def test_case(state_test_only, tx_type):
                pass
            """,
            dict(passed=0, failed=0, skipped=0, errors=1),
            "Only keyword arguments are supported",
            id="selector_as_positional_argument",
        ),
    ],
)
def test_fork_covariant_markers(
    pytester, test_function: str, outcomes: dict, error_string: str | None
):
    """
    Test fork covariant markers in an isolated test session, i.e., in
    a `fill` execution.

    In the case of an error, check that the expected error string is in the
    console output.
    """
    pytester.makepyfile(test_function)
    pytester.copy_example(name="pytest.ini")
    result = pytester.runpytest()
    result.assert_outcomes(**outcomes)
    if outcomes["errors"]:
        assert error_string is not None
        assert error_string in "\n".join(result.stdout.lines)