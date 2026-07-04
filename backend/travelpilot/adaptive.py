from typing import List, Optional
from travelpilot.models import (
    DiagnosticAnswer,
    DiagnosticQuestion,
    AdaptationResult,
    TravelPreferences,
    BudgetFeasibility,
    Activity,
    SubstitutionResponse,
)

# Default template diagnostic questions (used as fallback when no destination-specific questions are available)
DEFAULT_DIAGNOSTIC_QUESTIONS: List[DiagnosticQuestion] = [
    DiagnosticQuestion(
        id="q1",
        question="What is the traditional and polite greeting when meeting someone for the first time in this destination?",
        options=[
            "A loud high-five and calling them by their first name",
            "A gentle bow or polite handshake, avoiding prolonged intense eye contact",
            "Direct physical contact like a hug or kiss on both cheeks immediately",
        ],
        correct_option="A gentle bow or polite handshake, avoiding prolonged intense eye contact",
        topic="Greeting Etiquette",
    ),
    DiagnosticQuestion(
        id="q2",
        question="When dining at a local restaurant, which table behavior is considered disrespectful or taboos?",
        options=[
            "Leaving a small portion of food on the plate to indicate the host provided plenty",
            "Sticking your chopsticks vertically into a bowl of rice",
            "Asking the waiter for recommendations on local specialties",
        ],
        correct_option="Sticking your chopsticks vertically into a bowl of rice",
        topic="Dining Customs",
    ),
    DiagnosticQuestion(
        id="q3",
        question="What is the expected dress code when visiting religious, historical temples, or sacred spaces?",
        options=[
            "Shoulders and knees must be fully covered, and shoes removed before entering",
            "Standard tourist beachwear is perfectly acceptable",
            "Formal business suit is mandatory for entry",
        ],
        correct_option="Shoulders and knees must be fully covered, and shoes removed before entering",
        topic="Sacred Sites",
    ),
]


def score_diagnostic(
    answers: List[DiagnosticAnswer],
    questions: Optional[List[DiagnosticQuestion]] = None,
) -> AdaptationResult:
    """Score diagnostic answers against questions.

    Args:
        answers: User's submitted answers with confidence levels.
        questions: Optional custom questions list (e.g., Gemini-generated).
                   Falls back to DEFAULT_DIAGNOSTIC_QUESTIONS if not provided.
    """
    source_questions = questions if questions else DEFAULT_DIAGNOSTIC_QUESTIONS
    # Build maps of questions — strip any group prefix from answer IDs for matching
    q_map = {q.id: q for q in source_questions}

    correct_count = 0
    incorrect_high_confidence = 0
    incorrect_low_confidence = 0
    correct_high_confidence = 0
    correct_low_confidence = 0

    for ans in answers:
        q = q_map.get(ans.question_id)
        if not q:
            continue

        is_correct = ans.user_answer.strip() == q.correct_option.strip()
        confidence = ans.confidence  # 1 to 5

        if is_correct:
            correct_count += 1
            if confidence >= 4:
                correct_high_confidence += 1
            else:
                correct_low_confidence += 1
        else:
            if confidence >= 4:
                incorrect_high_confidence += 1
            else:
                incorrect_low_confidence += 1

    # Apply adaptation pathways:
    # 1. Incorrect + high confidence -> Misconception risk! Focus on warnings & safety.
    if incorrect_high_confidence > 0:
        challenge_level = "Intermediate"
        cultural_focus = "Safety Orientation & Common Pitfalls"
        reasoning = (
            "Why this step: System added active cultural warnings, dining taboos, and safety tips because "
            "you missed critical cultural scenario questions despite reporting high confidence."
        )
    # 2. Incorrect + low confidence -> Beginner orientation.
    elif incorrect_low_confidence > 0 or correct_count == 0:
        challenge_level = "Beginner"
        cultural_focus = "Basic Cultural Orientation"
        reasoning = (
            "Why this step: System selected basic cultural guidelines, language starter tips, and "
            "guided sightseeing because you missed baseline cultural etiquette questions with low confidence."
        )
    # 3. Correct + high confidence -> Deep local immersion.
    elif correct_high_confidence >= 2:
        challenge_level = "Advanced"
        cultural_focus = "Deep Local Cultural Immersion"
        reasoning = (
            "Why this step: System unlocked advanced independent exploration, local craft workshops, "
            "and off-the-beaten-path historic routes since you proved high cultural literacy and confidence."
        )
    # 4. Correct + low confidence -> Guided immersion.
    else:
        challenge_level = "Intermediate"
        cultural_focus = "Guided Cultural Immersion"
        reasoning = (
            "Why this step: System selected interactive guided tours to build your confidence, since you "
            "answered the cultural questions correctly but indicated unsure confidence."
        )

    return AdaptationResult(
        challenge_level=challenge_level,
        cultural_focus=cultural_focus,
        reasoning=reasoning,
    )


def check_budget_feasibility(
    preferences: TravelPreferences, estimated_cost: float
) -> BudgetFeasibility:
    limit = preferences.budget_limit
    difference = estimated_cost - limit
    is_feasible = estimated_cost <= limit

    if is_feasible:
        # Check if they have a healthy buffer
        buffer_percent = ((limit - estimated_cost) / limit) * 100
        if buffer_percent >= 20:
            analysis_reason = (
                f"Your estimated trip cost of ${estimated_cost:.2f} is well within your budget limit of "
                f"${limit:.2f} (leaving a comfortable {buffer_percent:.1f}% safety margin)."
            )
        else:
            analysis_reason = (
                f"Your estimated trip cost of ${estimated_cost:.2f} is feasible, but close to your budget limit of "
                f"${limit:.2f}. We recommend keeping track of incidental expenses."
            )
        saving_tips = [
            "Walk or use public transit for local travel to save on taxi fares.",
            "Try street food or visit local supermarkets for lunch options.",
        ]
    else:
        overrun_percent = (difference / limit) * 100
        analysis_reason = (
            f"ALERT: Estimated cost of ${estimated_cost:.2f} exceeds your budget limit of ${limit:.2f} by "
            f"${difference:.2f} ({overrun_percent:.1f}% overrun). The system has flagged budget-friendly substitutions."
        )
        saving_tips = [
            "Use our 'Budget Substitution' tool to swap high-cost attractions for free local cultural venues.",
            "Consider shared group walking tours instead of booking private history guides.",
            "Focus on visiting public temples, parks, and free museum days.",
        ]

    return BudgetFeasibility(
        is_feasible=is_feasible,
        estimated_total_cost=estimated_cost,
        analysis_reason=analysis_reason,
        saving_tips=saving_tips,
    )


def adapt_activity_substitution(
    day_number: int, activity_name: str, reason: str, challenge_level: str
) -> SubstitutionResponse:
    # Based on the substitution trigger, choose a deterministic or dynamic replacement
    reason_lower = reason.lower()

    if "weather" in reason_lower:
        new_act = Activity(
            name="Indoor Cultural Heritage Museum & Tea Tasting",
            description="Take refuge indoors at the national cultural heritage center. Features high-quality artifacts, interactive video exhibits, and a supervised traditional tea tasting ceremony.",
            time_slot="Afternoon",
            estimated_cost=25.0,
            cultural_significance="Offers deep understanding of historical dynasties, shelter from inclement weather, and hands-on etiquette guidelines.",
        )
        adaptation_reasoning = (
            f"Why this changed: System swapped '{activity_name}' for an indoor museum and tea tasting because of "
            f"rain/weather constraints, maintaining a comfortable pace."
        )
    elif (
        "budget" in reason_lower or "cost" in reason_lower or "overrun" in reason_lower
    ):
        new_act = Activity(
            name="Local Public Cultural Artisan Market Tour",
            description="A vibrant stroll through the historic artisan quarter. Watch craftsmen work with wood, silk, and ceramics. Free entrance, with optional cheap snacks.",
            time_slot="Morning",
            estimated_cost=5.0,
            cultural_significance="Allows direct interaction with local sellers, showcasing daily commerce customs and authentic local crafts at minimal cost.",
        )
        adaptation_reasoning = (
            "Why this changed: System substituted a premium activity with a free, public artisan market tour to address your "
            "budget overrun constraint while preserving cultural immersion."
        )
    else:
        # Closure or general reason
        new_act = Activity(
            name="Historic Heritage Temple Walk & Garden Tour",
            description="Explore the grounds of a highly revered historical temple nearby, featuring ancient stone carvings and serene landscape architecture.",
            time_slot="Afternoon",
            estimated_cost=10.0,
            cultural_significance="A primary local architectural landmark demonstrating spiritual traditions and garden design history.",
        )
        adaptation_reasoning = (
            f"Why this changed: System adapted '{activity_name}' to a historic temple walk to accommodate venue closures or "
            f"schedule adjustments."
        )

    return SubstitutionResponse(
        day_number=day_number,
        original_activity_name=activity_name,
        new_activity=new_act,
        adaptation_reasoning=adaptation_reasoning,
    )
