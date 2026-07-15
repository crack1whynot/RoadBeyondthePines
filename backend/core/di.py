from dataclasses import dataclass

from backend.agent_system.agent_factory import AgentFactory
from backend.agent_system.agent_loader import AgentLoader
from backend.agent_system.agent_manager import AgentManager
from backend.agent_system.agent_registry import AgentRegistry
from backend.brain.brain import Brain
from backend.brain.context_builder import ContextBuilder
from backend.brain.decision_engine import DecisionEngine
from backend.core.config import settings
from backend.memory.memory import InMemoryStore, ProjectMemory
from backend.orchestrator.agent_registry import AgentRegistry as OrchestratorAgentRegistry
from backend.orchestrator.capability_registry import CapabilityRegistry
from backend.orchestrator.orchestrator import Orchestrator, OrchestratorContext
from backend.orchestrator.planner import Planner, PlannerDependencies
from backend.orchestrator.progress_tracker import ProgressTracker
from backend.orchestrator.result_collector import ResultCollector
from backend.orchestrator.scheduler import Scheduler, SchedulerDependencies
from backend.providers.factory import ProviderFactory
from backend.providers.manager import ProviderManager
from backend.providers.mock_provider import MockProvider
from backend.providers.registry import ProviderRegistry
from backend.runtime.runtime import Runtime


@dataclass
class AppContainer:
    """Application service container for dependency injection."""

    runtime: Runtime | None = None
    orchestrator: Orchestrator | None = None
    planner: Planner | None = None
    scheduler: Scheduler | None = None
    progress_tracker: ProgressTracker | None = None
    result_collector: ResultCollector | None = None
    agent_registry: AgentRegistry | None = None
    capability_registry: CapabilityRegistry | None = None
    brain: Brain | None = None
    memory: ProjectMemory | None = None
    agent_manager: AgentManager | None = None
    agent_loader: AgentLoader | None = None
    agent_factory: AgentFactory | None = None
    provider_registry: ProviderRegistry | None = None
    provider_factory: ProviderFactory | None = None
    provider_manager: ProviderManager | None = None


def create_app_container() -> AppContainer:
    """Create and wire application dependencies."""
    runtime = Runtime()
    runtime.initialize()

    planner = Planner(PlannerDependencies())
    scheduler = Scheduler(SchedulerDependencies(runtime=runtime))
    progress_tracker = ProgressTracker()
    result_collector = ResultCollector()
    agent_registry = AgentRegistry()
    capability_registry = CapabilityRegistry()

    orchestrator = Orchestrator(
        OrchestratorContext(
            runtime=runtime,
            planner=planner,
            scheduler=scheduler,
            progress_tracker=progress_tracker,
            result_collector=result_collector,
        )
    )
    brain = Brain(
        context_builder=ContextBuilder(),
        decision_engine=DecisionEngine(),
    )
    memory = ProjectMemory(
        store=InMemoryStore(),
        storage_path="data/memory.json",
    )
    agent_registry = AgentRegistry()
    agent_factory = AgentFactory(registry=agent_registry)
    agent_loader = AgentLoader(registry=agent_registry, factory=agent_factory)
    agent_manager = AgentManager(registry=agent_registry, runtime=runtime)
    agent_loader.load_all()

    provider_registry = ProviderRegistry()
    provider_factory = ProviderFactory(registry=provider_registry)
    provider_factory.register_builder("mock", MockProvider)
    provider_factory.register_builder("placeholder", MockProvider)
    active_provider = provider_factory.create_provider(settings.ai_provider)
    provider_manager = ProviderManager(registry=provider_registry)
    provider_manager.set_active_provider(active_provider.name)

    return AppContainer(
        runtime=runtime,
        orchestrator=orchestrator,
        planner=planner,
        scheduler=scheduler,
        progress_tracker=progress_tracker,
        result_collector=result_collector,
        agent_registry=agent_registry,
        capability_registry=capability_registry,
        brain=brain,
        memory=memory,
        agent_manager=agent_manager,
        agent_loader=agent_loader,
        agent_factory=agent_factory,
        provider_registry=provider_registry,
        provider_factory=provider_factory,
        provider_manager=provider_manager,
    )
