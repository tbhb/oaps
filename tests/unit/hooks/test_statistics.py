from typing import TYPE_CHECKING

from oaps.hooks._statistics import (
    SessionStatistics,
    format_statistics_context,
    gather_session_statistics,
)

if TYPE_CHECKING:
    from collections.abc import Callable

    from oaps.session import Session


class TestSessionStatistics:
    def test_stores_all_fields(
        self, make_session_statistics: Callable[..., SessionStatistics]
    ) -> None:
        stats = make_session_statistics(
            started_at="2025-12-16T10:00:00Z",
            ended_at="2025-12-16T12:00:00Z",
            source="startup",
            prompt_count=15,
            first_prompt_at="2025-12-16T10:00:05Z",
            last_prompt_at="2025-12-16T11:45:30Z",
            total_tool_count=47,
            last_tool="Read",
            last_tool_at="2025-12-16T11:45:28Z",
            tool_counts={"Read": 20, "Write": 8},
            permission_request_count=3,
            last_permission_tool="Bash",
            notification_count=2,
            notification_counts={"permission_prompt": 2},
            stop_count=0,
            compaction_count=2,
            subagent_spawn_count=1,
            subagent_stop_count=1,
        )

        assert stats.started_at == "2025-12-16T10:00:00Z"
        assert stats.source == "startup"
        assert stats.prompt_count == 15
        assert stats.tool_counts == {"Read": 20, "Write": 8}


class TestGatherSessionStatistics:
    def test_returns_empty_stats_for_empty_store(self, session: Session) -> None:
        stats = gather_session_statistics(session)

        assert stats.started_at is None
        assert stats.prompt_count == 0
        assert stats.total_tool_count == 0
        assert stats.tool_counts == {}

    def test_gathers_session_timestamps(self, session: Session) -> None:
        session.set("oaps.session.started_at", "2025-12-16T10:00:00Z")
        session.set("oaps.session.ended_at", "2025-12-16T12:00:00Z")
        session.set("oaps.session.source", "startup")

        stats = gather_session_statistics(session)

        assert stats.started_at == "2025-12-16T10:00:00Z"
        assert stats.ended_at == "2025-12-16T12:00:00Z"
        assert stats.source == "startup"

    def test_gathers_prompt_statistics(self, session: Session) -> None:
        session.set("oaps.prompts.count", 15)
        session.set("oaps.prompts.first_at", "2025-12-16T10:00:05Z")
        session.set("oaps.prompts.last_at", "2025-12-16T11:45:30Z")

        stats = gather_session_statistics(session)

        assert stats.prompt_count == 15
        assert stats.first_prompt_at == "2025-12-16T10:00:05Z"
        assert stats.last_prompt_at == "2025-12-16T11:45:30Z"

    def test_gathers_tool_statistics(self, session: Session) -> None:
        session.set("oaps.tools.total_count", 47)
        session.set("oaps.tools.last_tool", "Read")
        session.set("oaps.tools.last_at", "2025-12-16T11:45:28Z")
        session.set("oaps.tools.Read.count", 20)
        session.set("oaps.tools.Write.count", 8)
        session.set("oaps.tools.Bash.count", 19)

        stats = gather_session_statistics(session)

        assert stats.total_tool_count == 47
        assert stats.last_tool == "Read"
        assert stats.last_tool_at == "2025-12-16T11:45:28Z"
        assert stats.tool_counts == {"Read": 20, "Write": 8, "Bash": 19}

    def test_gathers_permission_statistics(self, session: Session) -> None:
        session.set("oaps.permissions.request_count", 3)
        session.set("oaps.permissions.last_tool", "Bash")

        stats = gather_session_statistics(session)

        assert stats.permission_request_count == 3
        assert stats.last_permission_tool == "Bash"

    def test_gathers_notification_statistics(self, session: Session) -> None:
        session.set("oaps.notifications.count", 5)
        session.set("oaps.notifications.permission_prompt.count", 3)
        session.set("oaps.notifications.error.count", 2)

        stats = gather_session_statistics(session)

        assert stats.notification_count == 5
        assert stats.notification_counts == {"permission_prompt": 3, "error": 2}

    def test_gathers_session_control_statistics(self, session: Session) -> None:
        session.set("oaps.session.stop_count", 1)
        session.set("oaps.session.compaction_count", 3)

        stats = gather_session_statistics(session)

        assert stats.stop_count == 1
        assert stats.compaction_count == 3

    def test_gathers_subagent_statistics(self, session: Session) -> None:
        session.set("oaps.subagents.spawn_count", 5)
        session.set("oaps.subagents.stop_count", 4)

        stats = gather_session_statistics(session)

        assert stats.subagent_spawn_count == 5
        assert stats.subagent_stop_count == 4

    def test_handles_int_stored_as_string(self, session: Session) -> None:
        session.store.set("oaps.prompts.count", "42")

        stats = gather_session_statistics(session)

        assert stats.prompt_count == 42

    def test_handles_int_stored_as_float(self, session: Session) -> None:
        session.store.set("oaps.prompts.count", 42.7)

        stats = gather_session_statistics(session)

        assert stats.prompt_count == 42


class TestFormatStatisticsContext:
    def test_formats_empty_stats(
        self, make_session_statistics: Callable[..., SessionStatistics]
    ) -> None:
        stats = make_session_statistics()

        output = format_statistics_context(stats)

        assert "=== OAPS Session Statistics ===" in output
        assert "Prompts:" in output
        assert "Total: 0" in output

    def test_formats_session_section(
        self, make_session_statistics: Callable[..., SessionStatistics]
    ) -> None:
        stats = make_session_statistics(
            started_at="2025-12-16T10:00:00Z",
            source="startup",
            compaction_count=2,
        )

        output = format_statistics_context(stats)

        assert "Session:" in output
        assert "Started: 2025-12-16T10:00:00Z" in output
        assert "Source: startup" in output
        assert "Compactions: 2" in output
        assert "Stops: 0" in output

    def test_formats_prompts_section(
        self, make_session_statistics: Callable[..., SessionStatistics]
    ) -> None:
        stats = make_session_statistics(
            prompt_count=15,
            first_prompt_at="2025-12-16T10:00:05Z",
            last_prompt_at="2025-12-16T11:45:30Z",
        )

        output = format_statistics_context(stats)

        assert "Prompts:" in output
        assert "Total: 15" in output
        assert "First: 2025-12-16T10:00:05Z" in output
        assert "Last: 2025-12-16T11:45:30Z" in output

    def test_formats_tools_section(
        self, make_session_statistics: Callable[..., SessionStatistics]
    ) -> None:
        stats = make_session_statistics(
            total_tool_count=47,
            last_tool="Read",
            last_tool_at="2025-12-16T11:45:28Z",
            tool_counts={"Read": 20, "Write": 8},
        )

        output = format_statistics_context(stats)

        assert "Tools:" in output
        assert "Total invocations: 47" in output
        assert "Last tool: Read (2025-12-16T11:45:28Z)" in output
        assert "By tool:" in output
        assert "Read: 20" in output
        assert "Write: 8" in output

    def test_formats_tools_sorted_by_count_descending(
        self, make_session_statistics: Callable[..., SessionStatistics]
    ) -> None:
        stats = make_session_statistics(
            total_tool_count=100,
            tool_counts={"Write": 5, "Read": 50, "Bash": 25},
        )

        output = format_statistics_context(stats)

        # Find the positions of each tool in the output
        read_pos = output.find("Read: 50")
        bash_pos = output.find("Bash: 25")
        write_pos = output.find("Write: 5")

        assert read_pos < bash_pos < write_pos

    def test_formats_permissions_section(
        self, make_session_statistics: Callable[..., SessionStatistics]
    ) -> None:
        stats = make_session_statistics(
            permission_request_count=3,
            last_permission_tool="Bash",
        )

        output = format_statistics_context(stats)

        assert "Permissions:" in output
        assert "Total requests: 3" in output
        assert "Last tool: Bash" in output

    def test_formats_notifications_section(
        self, make_session_statistics: Callable[..., SessionStatistics]
    ) -> None:
        stats = make_session_statistics(
            notification_count=5,
            notification_counts={"permission_prompt": 3, "error": 2},
        )

        output = format_statistics_context(stats)

        assert "Notifications:" in output
        assert "Total: 5" in output
        assert "By type:" in output
        assert "permission_prompt: 3" in output
        assert "error: 2" in output

    def test_formats_subagents_section(
        self, make_session_statistics: Callable[..., SessionStatistics]
    ) -> None:
        stats = make_session_statistics(
            subagent_spawn_count=5,
            subagent_stop_count=4,
        )

        output = format_statistics_context(stats)

        assert "Subagents:" in output
        assert "Spawned: 5" in output
        assert "Stopped: 4" in output

    def test_full_formatted_output(
        self, make_session_statistics: Callable[..., SessionStatistics]
    ) -> None:
        stats = make_session_statistics(
            started_at="2025-12-16T10:30:00Z",
            source="startup",
            prompt_count=15,
            first_prompt_at="2025-12-16T10:30:05Z",
            last_prompt_at="2025-12-16T11:45:30Z",
            total_tool_count=47,
            last_tool="Read",
            last_tool_at="2025-12-16T11:45:28Z",
            tool_counts={"Read": 20, "Write": 8},
            permission_request_count=3,
            last_permission_tool="Bash",
            notification_count=2,
            notification_counts={"permission_prompt": 2},
            compaction_count=2,
            subagent_spawn_count=1,
            subagent_stop_count=1,
        )

        output = format_statistics_context(stats)

        expected_sections = [
            "=== OAPS Session Statistics ===",
            "Session:",
            "Prompts:",
            "Tools:",
            "Permissions:",
            "Notifications:",
            "Subagents:",
        ]

        for section in expected_sections:
            assert section in output
