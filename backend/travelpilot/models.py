from pydantic import BaseModel, Field, StringConstraints
from typing import List, Annotated

# Session ID pattern: ^tp_[a-f0-9]{14}$
SessionIdStr = Annotated[str, StringConstraints(pattern=r"^tp_[a-f0-9]{14}$")]


class TravelPreferences(BaseModel):
    destination: str = Field(
        ..., min_length=2, max_length=100, description="Target travel destination"
    )
    travel_style: str = Field(
        ...,
        min_length=3,
        max_length=50,
        description="e.g., Adventurous, Relaxing, Historical, Cultural",
    )
    cultural_interests: List[str] = Field(
        ..., min_length=1, description="List of cultural interests"
    )
    budget_tier: str = Field(
        ..., min_length=3, max_length=20, description="e.g., Budget, Mid-range, Luxury"
    )
    budget_limit: float = Field(
        ..., ge=10.0, le=100000.0, description="Maximum total budget in USD"
    )
    duration_days: int = Field(
        ..., ge=1, le=14, description="Duration of the trip in days"
    )
    excluded_factors: List[str] = Field(
        default_factory=list,
        description="Things to avoid, e.g. hiking, high altitude, certain foods",
    )


class DiagnosticAnswer(BaseModel):
    question_id: str = Field(..., min_length=1, max_length=50)
    user_answer: str = Field(..., min_length=1, max_length=200)
    confidence: int = Field(
        ..., ge=1, le=5, description="Confidence level from 1 (unsure) to 5 (certain)"
    )


class DiagnosticRequest(BaseModel):
    answers: List[DiagnosticAnswer] = Field(..., min_length=1)


class DiagnosticQuestion(BaseModel):
    id: str
    question: str
    options: List[str]
    correct_option: str
    topic: str


class AdaptationResult(BaseModel):
    challenge_level: str = Field(
        ..., description="e.g. beginner, intermediate, advanced"
    )
    cultural_focus: str = Field(
        ...,
        description="e.g. basic orientation, safety orientation, deep local immersion",
    )
    reasoning: str = Field(
        ...,
        min_length=5,
        max_length=500,
        description="Explains why this adaptation path was chosen",
    )


class Activity(BaseModel):
    name: str = Field(..., min_length=2, max_length=100)
    description: str = Field(..., min_length=10, max_length=500)
    time_slot: str = Field(
        ..., min_length=2, max_length=50, description="e.g. Morning, Afternoon, Evening"
    )
    estimated_cost: float = Field(..., ge=0.0)
    cultural_significance: str = Field(..., min_length=5, max_length=1000)


class DailyItinerary(BaseModel):
    day_number: int = Field(..., ge=1)
    theme: str = Field(..., min_length=3, max_length=100)
    activities: List[Activity] = Field(..., min_length=1)


class TripItinerary(BaseModel):
    destination: str
    adaptation_reasoning: str
    daily_plans: List[DailyItinerary]


class ChecklistItem(BaseModel):
    task: str = Field(..., min_length=3, max_length=150)
    category: str = Field(
        ...,
        min_length=3,
        max_length=50,
        description="e.g. Packing, Etiquette, Documents",
    )
    is_completed: bool = False


class BudgetFeasibility(BaseModel):
    is_feasible: bool
    estimated_total_cost: float
    analysis_reason: str = Field(..., min_length=5, max_length=1000)
    saving_tips: List[str] = Field(default_factory=list)


class SessionInitRequest(BaseModel):
    preferences: TravelPreferences
    diagnostic_answers: List[DiagnosticAnswer]


class SessionResponse(BaseModel):
    session_id: str
    owner_id: str
    preferences: TravelPreferences
    adaptation: AdaptationResult
    itinerary: TripItinerary
    checklist: List[ChecklistItem]
    budget_feasibility: BudgetFeasibility


class SubstitutionRequest(BaseModel):
    day_number: int = Field(..., ge=1)
    activity_name: str = Field(..., min_length=2, max_length=100)
    reason_for_substitution: str = Field(
        ...,
        min_length=5,
        max_length=200,
        description="e.g. weather, budget overrun, venue closure",
    )


class SubstitutionResponse(BaseModel):
    day_number: int
    original_activity_name: str
    new_activity: Activity
    adaptation_reasoning: str
