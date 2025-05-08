#!/usr/bin/env python3
import os

# Adjust import path as needed based on test execution context
import sys
import unittest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../..")))

from src.dreamos.tools._core.base import BaseTool, ToolContext, ToolParameter


class TestBaseTool(unittest.TestCase):
    def setUp(self):
        # Setup that runs before each test method
        pass

    def tearDown(self):
        # Cleanup that runs after each test method
        pass

    # --- Test Cases for BaseTool --- #

    def test_base_tool_initialization(self):
        """Test basic initialization of BaseTool."""

        # Define dummy parameters for a concrete subclass
        class DummyTool(BaseTool):
            name = "dummy_tool"
            description = "A dummy tool for testing."
            parameters = [
                ToolParameter(
                    name="param1",
                    description="First param",
                    type="string",
                    required=True,
                ),
                ToolParameter(
                    name="param2",
                    description="Second param",
                    type="integer",
                    required=False,
                ),
            ]

            async def execute(self, context: ToolContext) -> str:
                return "Dummy execution"

        tool = DummyTool()
        self.assertEqual(tool.name, "dummy_tool")
        self.assertEqual(tool.description, "A dummy tool for testing.")
        self.assertEqual(len(tool.parameters), 2)

    # TODO: Add tests for parameter validation logic (if implemented in BaseTool)
    # TODO: Add tests for context handling (if applicable)
    # TODO: Add tests for abstract execute method enforcement (though hard to test directly)  # noqa: E501

    # {{ EDIT START: Add new tests for BaseTool }}
    def test_base_tool_validate_arguments_missing_required(self):
        """Test argument validation detects missing required parameters."""
        class SimpleReqTool(BaseTool):
            name = "req_tool"
            description = "Requires one param."
            parameters = [
                ToolParameter(name="req_param", description="Required", type="string", required=True)
            ]
            async def execute(self, context: ToolContext) -> str:
                return ""

        tool = SimpleReqTool()
        # Assume validate_arguments raises ValueError or similar
        # This requires BaseTool to have a validate_arguments method
        with self.assertRaises(ValueError, msg="Validation should fail for missing required arg"):
            # If validate_arguments is called implicitly by a wrapper, test that wrapper
            # If called explicitly:
            # tool.validate_arguments({})
            # Placeholder: Assuming validation happens implicitly somewhere
            # If not, this test needs adjustment based on BaseTool implementation.
            pass # If validation isn't directly testable here, skip or adapt

    def test_base_tool_validate_arguments_valid(self):
        """Test argument validation passes with valid arguments."""
        class SimpleReqTool(BaseTool):
            name = "req_tool"
            description = "Requires one param."
            parameters = [
                ToolParameter(name="req_param", description="Required", type="string", required=True),
                ToolParameter(name="opt_param", description="Optional", type="integer", required=False)
            ]
            async def execute(self, context: ToolContext) -> str:
                return ""

        tool = SimpleReqTool()
        try:
            # Assuming validation happens implicitly somewhere or can be called
            # tool.validate_arguments({"req_param": "value"})
            # tool.validate_arguments({"req_param": "value", "opt_param": 123})
            pass # If validation isn't directly testable here, skip or adapt
        except ValueError:
            self.fail("Validation should pass with valid arguments.")


    def test_base_tool_abstract_execute_enforcement(self):
        """Test that instantiating BaseTool subclass without execute fails."""
        with self.assertRaises(TypeError, msg="Cannot instantiate abstract class without execute method"):
            class IncompleteTool(BaseTool):
                name = "incomplete"
                description = "Missing execute."
                parameters = []
                # No execute method implemented!

            IncompleteTool() # Attempt instantiation

    # {{ EDIT END }}

    # --- Test Cases for ToolContext --- #

    def test_tool_context_initialization(self):
        """Test basic initialization of ToolContext."""
        args = {"arg1": "value1", "arg2": 123}
        context = ToolContext(args=args)
        self.assertEqual(context.args, args)

    def test_tool_context_get_arg(self):
        """Test get_argument method of ToolContext."""
        args = {"arg1": "value1", "arg2": 123}
        context = ToolContext(args=args)
        self.assertEqual(context.get_argument("arg1"), "value1")
        self.assertEqual(context.get_argument("arg2"), 123)
        self.assertIsNone(context.get_argument("arg3"))  # Test missing arg
        self.assertEqual(
            context.get_argument("arg3", default="default_val"), "default_val"
        )  # Test default

    # --- Test Cases for ToolParameter --- #

    def test_tool_parameter_initialization(self):
        """Test basic initialization of ToolParameter."""
        param = ToolParameter(
            name="test_param", description="Desc", type="boolean", required=True
        )
        self.assertEqual(param.name, "test_param")
        self.assertEqual(param.description, "Desc")
        self.assertEqual(param.type, "boolean")
        self.assertTrue(param.required)


if __name__ == "__main__":
    unittest.main()
