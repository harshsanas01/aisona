from carecall_application.ports.brief_prose_generator import BriefProseGenerator
from carecall_domain import Brief


class MockBriefProseGenerator(BriefProseGenerator):
    """No-op passthrough - the required, always-available default. CI and
    demo mode never touch the LLM-backed prose stage."""

    def polish(self, brief: Brief) -> Brief:
        return brief
