"""Long-term memory update tests."""

from __future__ import annotations

from app.schemas.chat import ChatMessageRequest


def test_feedback_updates_profile(isolated_runtime):
    container = isolated_runtime

    session = container.session_service.create_session(user_id="feedback_user")
    container.planner_service.process_message(
        ChatMessageRequest(
            session_id=session.session_id,
            user_id="feedback_user",
            message="去成都玩2天，2026-06-01出发，预算2500元，偏好美食。",
        )
    )

    patch = container.summarizer.from_feedback("行程太赶了，不喜欢早起和博物馆", rating=2)
    profile = container.memory_tool.update_profile("feedback_user", patch)

    assert profile.pace_preference == "relaxed"
    assert any("早起" in item or "博物馆" in item for item in profile.avoid_tags)
