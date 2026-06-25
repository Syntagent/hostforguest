"""Agent registry for HostForGuest A2A orchestrator."""

from __future__ import annotations

from typing import Dict, List, Optional, TYPE_CHECKING

from app.services.a2a.agent_card import AgentCard, HFG_AGENT_CARDS

if TYPE_CHECKING:
    from app.services.a2a.agent_wrappers import BaseHFGAgent


class AgentRegistry:
    """Registers agent cards and live agent instances."""

    def __init__(self) -> None:
        self._cards: Dict[str, AgentCard] = dict(HFG_AGENT_CARDS)
        self._agents: Dict[str, "BaseHFGAgent"] = {}

    def register_agent(self, agent: "BaseHFGAgent") -> None:
        card = self._cards.get(agent.agent_id)
        if not card:
            raise ValueError(f"Unknown agent id: {agent.agent_id}")
        self._agents[agent.agent_id] = agent

    def get_card(self, agent_id: str) -> Optional[AgentCard]:
        return self._cards.get(agent_id)

    def list_cards(self) -> List[AgentCard]:
        return list(self._cards.values())

    def get_agent(self, agent_id: str) -> Optional["BaseHFGAgent"]:
        return self._agents.get(agent_id)

    def agent_ids(self) -> List[str]:
        return list(self._cards.keys())
