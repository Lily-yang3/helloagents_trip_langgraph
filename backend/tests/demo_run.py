"""Demo script for local manual run (service-level)."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.core.config import get_settings
from app.schemas.chat import ChatMessageRequest
from app.services.dependencies import get_container


def main() -> None:
    settings = get_settings()
    settings.mock_mode = True
    settings.checkpointer_mode = "memory"

    container = get_container()

    session = container.session_service.create_session(user_id="demo_user")
    print(f"session_id={session.session_id} thread_id={session.thread_id}")

    msg1 = ChatMessageRequest(
        session_id=session.session_id,
        user_id="demo_user",
        message="我想去杭州玩，偏好美食。",
    )
    res1 = container.planner_service.process_message(msg1)
    print("\n[Round1]")
    print(res1.assistant_message)

    msg2 = ChatMessageRequest(
        session_id=session.session_id,
        user_id="demo_user",
        message="2026-05-01出发玩3天，预算3000元，地铁出行，不喜欢博物馆。",
    )
    res2 = container.planner_service.process_message(msg2)
    print("\n[Round2]")
    print(res2.assistant_message)
    if res2.structured_plan:
        print(f"city={res2.structured_plan.city}, days={len(res2.structured_plan.days)}, total={res2.structured_plan.budget.total}")


if __name__ == "__main__":
    main()
