from workflow.state import DebateState


class RoundManager:
    def run(self, state: DebateState) -> DebateState:
        return self.increment_round(state)

    def increment_round(self, state: DebateState) -> DebateState:
        new_state = state.copy()
        new_state["current_round"] = state["current_round"] + 1
        return new_state
