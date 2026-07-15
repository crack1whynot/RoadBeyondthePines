"""Single composition root for application-owned services."""

from __future__ import annotations

from dataclasses import dataclass

from backend.agent_system.agent_factory import AgentFactory
from backend.agent_system.agent_loader import AgentLoader
from backend.agent_system.agent_manager import AgentManager
from backend.agent_system.agent_registry import AgentRegistry
from backend.brain.brain import Brain
from backend.brain.context_builder import ContextBuilder
from backend.brain.decision_engine import DecisionEngine
from backend.core.config import Settings, settings
from backend.memory.memory import InMemoryStore, ProjectMemory
from backend.mcp.factory import create_unreal_mcp_manager, create_unreal_transport_registry
from backend.mcp.manager import UnrealMCPManager
from backend.mcp.registry import UnrealTransportRegistry
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
from backend.services.agent_service import AgentService
from backend.services.asset_service import AssetService
from backend.services.build_service import BuildService
from backend.services.development_request_service import DevelopmentRequestService
from backend.services.documentation_service import DocumentationService
from backend.services.git_service import GitService
from backend.services.memory_service import MemoryService
from backend.services.plugin_service import PluginService
from backend.services.task_service import TaskService
from backend.services.unreal_service import UnrealService


@dataclass(slots=True)
class AppContainer:
    """One application-scoped object graph, built without starting workers."""

    settings: Settings
    runtime: Runtime
    orchestrator: Orchestrator
    planner: Planner
    scheduler: Scheduler
    progress_tracker: ProgressTracker
    result_collector: ResultCollector
    agent_registry: AgentRegistry
    brain: Brain
    memory: ProjectMemory
    agent_manager: AgentManager
    agent_loader: AgentLoader
    agent_factory: AgentFactory
    provider_registry: ProviderRegistry
    provider_factory: ProviderFactory
    provider_manager: ProviderManager
    unreal_transport_registry: UnrealTransportRegistry
    unreal_mcp_manager: UnrealMCPManager
    development_request_service: DevelopmentRequestService
    agent_service: AgentService
    asset_service: AssetService
    build_service: BuildService
    documentation_service: DocumentationService
    git_service: GitService
    memory_service: MemoryService
    plugin_service: PluginService
    task_service: TaskService
    unreal_service: UnrealService


def create_app_container(app_settings: Settings | None = None) -> AppContainer:
    """Create all singletons for one application lifespan.

    This function deliberately performs no Runtime start, network connection,
    or worker creation.  ``backend.app.main.application_lifespan`` owns those
    lifecycle transitions.
    """

    active_settings = app_settings or settings
    runtime = Runtime()

    provider_registry = ProviderRegistry()
    provider_factory = ProviderFactory(registry=provider_registry)
    provider_factory.register_builder("mock", MockProvider)
    # Retain the documented compatibility alias without adding a real remote
    # provider to this diagnostic-only milestone.
    provider_factory.register_builder("placeholder", MockProvider)
    active_provider = provider_factory.create_provider(active_settings.ai_provider)
    provider_manager = ProviderManager(registry=provider_registry)
    provider_manager.set_active_provider(active_provider.name)

    unreal_transport_registry = create_unreal_transport_registry()
    unreal_mcp_manager = create_unreal_mcp_manager(active_settings, unreal_transport_registry)

    agent_registry = AgentRegistry()
    agent_factory = AgentFactory(
        registry=agent_registry,
        unreal_mcp_manager=unreal_mcp_manager,
    )
    agent_loader = AgentLoader(registry=agent_registry, factory=agent_factory)
    agent_loader.load_all()
    agent_manager = AgentManager(registry=agent_registry, runtime=runtime)

    planner = Planner(PlannerDependencies(provider_manager=provider_manager))
    scheduler = Scheduler(SchedulerDependencies(runtime=runtime))
    progress_tracker = ProgressTracker()
    result_collector = ResultCollector()
    orchestrator = Orchestrator(
        OrchestratorContext(
            runtime=runtime,
            planner=planner,
            scheduler=scheduler,
            progress_tracker=progress_tracker,
            result_collector=result_collector,
            agent_manager=agent_manager,
        )
    )
    brain = Brain(
        context_builder=ContextBuilder(app_settings=active_settings),
        decision_engine=DecisionEngine(),
    )
    memory = ProjectMemory(store=InMemoryStore(), storage_path="data/memory.json")
    development_request_service = DevelopmentRequestService(
        brain=brain,
        orchestrator=orchestrator,
        memory=memory,
    )

    # These legacy management services remain placeholders, but they are now
    # application-scoped dependencies rather than new objects per HTTP call.
    agent_service = AgentService()
    asset_service = AssetService()
    build_service = BuildService()
    documentation_service = DocumentationService()
    git_service = GitService()
    memory_service = MemoryService()
    plugin_service = PluginService()
    task_service = TaskService()
    unreal_service = UnrealService(unreal_mcp_manager)

    # Runtime's string registry is retained only for backwards-compatible
    # runtime lookups.  The container remains the composition source of truth.
    runtime.register_service("orchestrator", orchestrator)
    runtime.register_service("ai_provider_manager", provider_manager)
    runtime.register_service("unreal_mcp_manager", unreal_mcp_manager)

    return AppContainer(
        settings=active_settings,
        runtime=runtime,
        orchestrator=orchestrator,
        planner=planner,
        scheduler=scheduler,
        progress_tracker=progress_tracker,
        result_collector=result_collector,
        agent_registry=agent_registry,
        brain=brain,
        memory=memory,
        agent_manager=agent_manager,
        agent_loader=agent_loader,
        agent_factory=agent_factory,
        provider_registry=provider_registry,
        provider_factory=provider_factory,
        provider_manager=provider_manager,
        unreal_transport_registry=unreal_transport_registry,
        unreal_mcp_manager=unreal_mcp_manager,
        development_request_service=development_request_service,
        agent_service=agent_service,
        asset_service=asset_service,
        build_service=build_service,
        documentation_service=documentation_service,
        git_service=git_service,
        memory_service=memory_service,
        plugin_service=plugin_service,
        task_service=task_service,
        unreal_service=unreal_service,
    )
