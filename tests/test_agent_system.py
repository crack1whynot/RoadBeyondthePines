import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from backend.agent_system.agent import BaseAgent
from backend.agent_system.agent_capability import AgentCapability
from backend.agent_system.agent_context import AgentContext
from backend.agent_system.agent_factory import AgentFactory
from backend.agent_system.agent_manager import AgentManager
from backend.agent_system.agent_metadata import AgentMetadata
from backend.agent_system.agent_registry import AgentRegistry
from backend.agent_system.agent_result import AgentResult
from backend.agent_system.agent_status import AgentStatus
from backend.agent_system.agent_task import AgentTask
from backend.agent_system.default_agents import WorldAgent
from backend.core.execution import ExecutionStatus


class DummyAgent(BaseAgent):
    def __init__(self) -> None:
        super().__init__(name="DummyAgent", capabilities=[AgentCapability(name="Testing")], metadata=AgentMetadata(name="DummyAgent"))

    def execute(self, task: AgentTask, context: AgentContext) -> AgentResult:
        return AgentResult.succeeded(
            task_id=task.task_id,
            agent_id=self.name,
            output={"message": "ok"},
        )


def test_registry_registers_and_finds_agents() -> None:
    registry = AgentRegistry()
    agent = DummyAgent()
    registry.register(agent)
    assert registry.find(agent.name) is agent
    assert registry.find_by_capability("Testing")[0] is agent
    assert registry.list_agents() == [agent]


def test_manager_dispatches_task() -> None:
    registry = AgentRegistry()
    agent = DummyAgent()
    registry.register(agent)
    manager = AgentManager(registry=registry)
    task = AgentTask(task_id="task-1", description="Run tests", required_capabilities=["Testing"])
    ctx = AgentContext(task=task)
    result = manager.dispatch_task(task, ctx)
    assert result.status is ExecutionStatus.SUCCEEDED
    assert result.success is True
    assert result.task_id == task.task_id
    assert result.agent_id == agent.name
    assert result.output == {"message": "ok"}


def test_factory_creates_supported_agent() -> None:
    registry = AgentRegistry()
    factory = AgentFactory(registry=registry)
    agent = factory.create_agent("world")
    assert isinstance(agent, WorldAgent)
    assert registry.find(agent.name) is agent


def test_base_agent_lifecycle_helpers() -> None:
    agent = DummyAgent()
    agent.initialize()
    agent.start()
    agent.pause()
    agent.resume()
    agent.stop()
    assert agent.health_check() is False
