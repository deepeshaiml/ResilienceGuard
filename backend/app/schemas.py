from pydantic import BaseModel, Field


class ActionProposalIn(BaseModel):
    scenario_id: str = Field(min_length=1, max_length=64)
    service_id: str = Field(min_length=1, max_length=64)
    backup_id: str = Field(min_length=1, max_length=96)


class ActionDecisionIn(BaseModel):
    decision: str
    rationale: str = Field(default="", max_length=500)

    def validated_decision(self) -> str:
        value = self.decision.lower().strip()
        if value not in {"approve", "reject"}:
            raise ValueError("decision must be approve or reject")
        return value


class AssistantRequest(BaseModel):
    scenario_id: str
    question: str = Field(default="Summarize recovery readiness and next steps.", max_length=500)
