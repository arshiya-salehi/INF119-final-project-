import pytest
from agents.tracking_agent import TrackingAgent
from agents.parser_agent import ParserAgent
from agents.design_agent import DesignAgent
from agents.code_gen_agent import CodeGenAgent
from agents.test_agent import TestAgent

# TrackingAgent basic test
@pytest.fixture
def tracking_agent():
    return TrackingAgent()

def test_tracking_agent_usage_report(tracking_agent):
    report = tracking_agent.get_usage_report()
    assert isinstance(report, dict)
    assert "total_tokens" in report or "usage" in report

# ParserAgent basic test
@pytest.fixture
def parser_agent(tracking_agent):
    return ParserAgent(tracking_agent)

def test_parser_agent_parse_requirements(parser_agent):
    spec = parser_agent.parse_requirements("English present tense, handle irregular verbs")
    assert hasattr(spec, "languages")
    assert "English" in spec.languages

# DesignAgent basic test
@pytest.fixture
def design_agent(tracking_agent):
    return DesignAgent(tracking_agent)
