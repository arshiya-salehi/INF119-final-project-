# Test Generation Agent - Generates test cases for the application
# Author: [Your Name] - [Student ID]

from typing import Optional, List
from mcp import MCPClient, AgentRole, RequirementSpec, GeneratedCode, TestCase
from agents.tracking_agent import TrackingAgent
from utils.helpers import clean_code_block, save_to_file
from config.api_config import TESTS_DIR

class TestAgent:
    """
    Agent responsible for generating comprehensive test cases
    """
    
    def __init__(self, tracking_agent: TrackingAgent, mcp_client: Optional[MCPClient] = None):
        """Initialize test generation agent"""
        self.tracking_agent = tracking_agent
        self.mcp_client = mcp_client
    
    def generate_tests(self, spec: RequirementSpec, generated_code: List[GeneratedCode]) -> str:
        """
        Generate test cases for the application

        Args:
            spec: Requirement specification
            generated_code: List of generated code files

        Returns:
            Test file content as string
        """
        if self.mcp_client:
            self.mcp_client.notify({"event": "test_generation_started"})

        # Get the main conjugator code (not used directly here, but kept for context)
        conjugator_code = next((gc for gc in generated_code if "conjugator" in gc.filename), None)

        prompt = f"""
You are writing pytest tests for verb_conjugator.py.

The module under test provides this public API:

    from verb_conjugator import conjugate_verb, ConjugationError

- conjugate_verb(language: str, verb: str, tense: str) -> dict
- The dict returned for English must have exactly these keys:
    "I", "You", "He/She/It", "We", "They"
- The function raises ConjugationError on invalid input or unsupported options.

Write a single test file named test_conjugator.py that:

1. Imports exactly:
       import pytest
       from verb_conjugator import conjugate_verb, ConjugationError

2. Contains at least 12 test functions that:

   Regular and irregular verbs:
   - Test a regular English verb in present tense (for example "walk").
   - Test a regular English verb in past tense (for example "play").
   - Test a verb ending in "e" in present and past.
   - Test a few irregular verbs in present and past, such as "go", "be", "have", "eat".
   - Check that the returned dict has the expected pronoun keys and plausible values.

   Robust input handling:
   - Test that leading and trailing spaces around the verb are handled correctly.
   - Test that mixed case verbs like "RuN" work.
   - Test that mixed case tenses like "PaSt" work.

   Error handling:
   - Test that an unsupported language code "fr" raises ConjugationError with message:
         "Unsupported language: fr"
   - Test that an unsupported tense "future" raises ConjugationError with message:
         "Unsupported tense: future"
   - Test that an empty verb string raises ConjugationError with message:
         "Verb cannot be empty"
   - Test that a non string verb raises ConjugationError with message:
         "Verb must be a string"
   - Test that a non string tense raises ConjugationError with message:
         "Tense must be a string"
   - Test that an obviously fake verb such as "nonexistentverb" in English present tense
     raises ConjugationError with message:
         "Verb 'nonexistentverb' not found or unsupported for English in present tense."

3. Assume that English is always available and that at least these tenses exist:
   {', '.join(spec.tenses)}

4. Keep the tests deterministic.
   Do not use randomness or network calls.
   Only call conjugate_verb and assert on its return value or raised ConjugationError.

Return ONLY the full Python source code for test_conjugator.py, with no surrounding backticks.
"""

        test_code = self.tracking_agent.generate_content(prompt)
        test_code = clean_code_block(test_code)

        # Ensure proper imports
        if "import pytest" not in test_code:
            test_code = "import pytest\n" + test_code

        # Save test file
        test_filepath = f"{TESTS_DIR}/test_conjugator.py"
        save_to_file(test_code, test_filepath)

        if self.mcp_client:
            self.mcp_client.notify({
                "event": "test_generation_completed",
                "test_file": test_filepath
            })

        return test_code
