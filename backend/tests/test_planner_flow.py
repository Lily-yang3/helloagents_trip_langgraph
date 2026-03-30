"""End-to-end service-level tests for the planner graph."""

from __future__ import annotations

from app.schemas.chat import ChatMessageRequest


def test_planner_full_flow(isolated_runtime):
    container = isolated_runtime

    session = container.session_service.create_session(user_id="test_user")
    response = container.planner_service.process_message(
        ChatMessageRequest(
            session_id=session.session_id,
            user_id="test_user",
            message="我想去杭州玩3天，2026-05-01出发，预算3000元，偏好美食，地铁出行，不喜欢博物馆。",
        )
    )

    assert response.need_clarification is False
    assert response.structured_plan is not None
    assert response.structured_plan.city == "杭州"
    assert len(response.structured_plan.days) == 3
    assert response.structured_plan.budget.total > 0
    assert response.structured_plan.days[0].attractions
    assert response.structured_plan.days[0].attractions[0].image_url

    history = container.memory_tool.list_history(user_id="test_user")
    assert len(history) >= 1


def test_clarification_branch(isolated_runtime):
    container = isolated_runtime

    session = container.session_service.create_session(user_id="clarify_user")
    response = container.planner_service.process_message(
        ChatMessageRequest(
            session_id=session.session_id,
            user_id="clarify_user",
            message="我想旅行一下，喜欢美食。",
        )
    )

    assert response.need_clarification is True
    assert response.structured_plan is None
    assert "还缺少以下信息" in response.assistant_message
