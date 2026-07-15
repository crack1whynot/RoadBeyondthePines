"""Legacy agent API retained only for backwards-compatible imports.

New execution code must use :mod:`backend.agent_system`.  The classes in
this package expose the older ``run()`` contract and are deliberately not
registered in the Phase 0 Runtime, AgentRegistry, or AgentManager.
"""
