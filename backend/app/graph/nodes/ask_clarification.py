"""Graph node: ask follow-up questions when key fields are missing."""

from __future__ import annotations

from typing import Callable

from app.graph.state import PlannerState
from app.services.request_parser import RequestParser


def make_ask_clarification_node(parser: RequestParser) -> Callable[[PlannerState], dict]:
    def node(state: PlannerState) -> dict:
        missing_fields = list(state.get("missing_fields") or [])
        labels = parser.build_missing_labels(missing_fields)
        messages = list(state.get("messages") or [])

        question = (
            "为了给你生成个性化行程，我还缺少以下信息："
            f"{', '.join(labels)}。"
            "请用一句话补充，例如：\n"
            "“去杭州，5月1日出发玩3天，预算3000元，偏好美食，地铁出行”。"
        )
        messages.append({"role": "assistant", "content": question})

        return {
            "clarification_question": question,
            "assistant_message": question,
            "messages": messages,
            "structured_plan": None,
            "need_clarification": True,
        }

    return node
