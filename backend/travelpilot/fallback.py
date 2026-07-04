from typing import List
from travelpilot.models import (
    TravelPreferences,
    AdaptationResult,
    TripItinerary,
    DailyItinerary,
    Activity,
    ChecklistItem,
)


def generate_fallback_itinerary(
    preferences: TravelPreferences, adaptation: AdaptationResult
) -> TripItinerary:
    dest = preferences.destination
    challenge = adaptation.challenge_level

    # Custom theme/activities based on challenge level
    if challenge == "Beginner":
        activities_day_1 = [
            Activity(
                name=f"Guided {dest} Orientation & City Walk",
                description="Join an experienced local guide to explore the historic core. Learn basic navigation, greeting etiquette, and safety guidelines for the area.",
                time_slot="Morning",
                estimated_cost=20.0,
                cultural_significance="Offers primary cultural orientation and standard greetings practice under safe instruction.",
            ),
            Activity(
                name="Central Heritage Museum",
                description="Explore chronological displays detailing historical dynasties, colonial impact, and the evolution of local traditions.",
                time_slot="Afternoon",
                estimated_cost=15.0,
                cultural_significance="Essential historical context to help beginners appreciate regional cultural elements.",
            ),
        ]
        activities_day_2 = [
            Activity(
                name="Traditional Introduction Dining Experience",
                description="A guided lunch where staff explain the cultural significance of table rules, chopsticks handling, and regional dishes.",
                time_slot="Afternoon",
                estimated_cost=30.0,
                cultural_significance="Hands-on practice of basic dining customs in a supportive environment.",
            ),
            Activity(
                name="Scenic Botanical Gardens Stroll",
                description="Walk through curated gardens featuring native flora, traditional ponds, and peaceful architectural structures.",
                time_slot="Evening",
                estimated_cost=10.0,
                cultural_significance="Relaxing nature walk demonstrating traditional landscape styling.",
            ),
        ]
    elif challenge == "Intermediate":
        activities_day_1 = [
            Activity(
                name=f"Historic {dest} Temple Exploration",
                description="Visit major architectural wonders. Observe active rituals, incense ceremonies, and traditional carving techniques.",
                time_slot="Morning",
                estimated_cost=25.0,
                cultural_significance="Deeper exploration of spiritual architecture and etiquette requirements.",
            ),
            Activity(
                name="Local Neighborhood Tea House Session",
                description="Participate in a guided tea preparation ceremony, observing proper posture and cup handling rules.",
                time_slot="Afternoon",
                estimated_cost=35.0,
                cultural_significance="A traditional custom focusing on mindfulness and social greeting norms.",
            ),
        ]
        activities_day_2 = [
            Activity(
                name="Local Craft Artisan District Walk",
                description="Meet master craftsmen specialized in wood carving, silk weaving, or pottery. Watch demonstrations and ask questions.",
                time_slot="Morning",
                estimated_cost=15.0,
                cultural_significance="Direct contact with active heritage preservation efforts.",
            ),
            Activity(
                name="Regional Specialty Cooking Masterclass",
                description="Learn to cook authentic street food under the guidance of a local family, learning about spices and history.",
                time_slot="Evening",
                estimated_cost=55.0,
                cultural_significance="Engaging directly with culinary traditions and culinary family heritage.",
            ),
        ]
    else:  # Advanced
        activities_day_1 = [
            Activity(
                name="Off-the-beaten-path Mountain Heritage Hike",
                description="A scenic trail through traditional farming villages. Meet residents, witness ancient agricultural styles, and enjoy rural meals.",
                time_slot="Morning",
                estimated_cost=40.0,
                cultural_significance="Unfiltered, independent immersion into local agricultural lifestyle and dialects.",
            ),
            Activity(
                name="Ancient Manuscript Archives Tour",
                description="A specialized visit to the private library to inspect old scrolls and historical records with a preservationist.",
                time_slot="Afternoon",
                estimated_cost=30.0,
                cultural_significance="Advanced historical research highlighting written heritage.",
            ),
        ]
        activities_day_2 = [
            Activity(
                name="Traditional Musical Instrument Apprenticeship",
                description="A hands-on trial of local traditional instruments guided by a classical musician in their private studio.",
                time_slot="Afternoon",
                estimated_cost=60.0,
                cultural_significance="Complex cultural art form highlighting acoustic heritage.",
            ),
            Activity(
                name="Community Festival Volunteering Activity",
                description="Assist in constructing festival ornaments or preparing community meals alongside local neighborhood residents.",
                time_slot="Evening",
                estimated_cost=10.0,
                cultural_significance="Ultimate social immersion, requiring respect for local cooperation norms.",
            ),
        ]

    # Handle requested duration
    days = []
    day_count = preferences.duration_days

    # Day 1
    days.append(
        DailyItinerary(
            day_number=1,
            theme="Cultural Orientation & Primary Heritage",
            activities=activities_day_1,
        )
    )

    # Day 2+ (duplicate/adapt if duration is longer)
    for d in range(2, day_count + 1):
        if d == 2:
            days.append(
                DailyItinerary(
                    day_number=2,
                    theme="Local Immersion & Craft Traditions",
                    activities=activities_day_2,
                )
            )
        else:
            # Generic days
            days.append(
                DailyItinerary(
                    day_number=d,
                    theme=f"Day {d} Exploration & Discovery",
                    activities=[
                        Activity(
                            name="Historic District Walk & Local Eateries",
                            description=f"Explore secondary heritage zones in {dest}, focusing on regional street vendors and historic buildings.",
                            time_slot="Afternoon",
                            estimated_cost=20.0,
                            cultural_significance="Daily life observation and authentic regional gastronomy.",
                        )
                    ],
                )
            )

    return TripItinerary(
        destination=dest, adaptation_reasoning=adaptation.reasoning, daily_plans=days
    )


def generate_fallback_checklist(
    preferences: TravelPreferences, adaptation: AdaptationResult
) -> List[ChecklistItem]:
    dest = preferences.destination
    focus = adaptation.cultural_focus
    challenge = adaptation.challenge_level

    items = [
        ChecklistItem(
            task="Verify passport validity (minimum 6 months remaining)",
            category="Documents",
        ),
        ChecklistItem(
            task=f"Check local entry requirements and visa regulations for {dest}",
            category="Documents",
        ),
        ChecklistItem(
            task="Pack adapters compatible with local power outlets", category="Packing"
        ),
        ChecklistItem(
            task="Acquire small bills in local currency for markets and tipping",
            category="Finance",
        ),
    ]

    # Adapt packing/etiquette list to diagnostic results
    if challenge == "Beginner":
        items.extend(
            [
                ChecklistItem(
                    task="Carry a printed basic greeting cheat sheet",
                    category="Etiquette",
                ),
                ChecklistItem(
                    task="Confirm shoulders and knees are covered for temple visits",
                    category="Packing",
                ),
                ChecklistItem(
                    task="Download local offline maps and translation apps",
                    category="Packing",
                ),
            ]
        )
    elif challenge == "Intermediate":
        if "Safety" in focus:
            items.extend(
                [
                    ChecklistItem(
                        task="Review common dining faux-pas (e.g. chopstick positioning rules)",
                        category="Etiquette",
                    ),
                    ChecklistItem(
                        task="Watch video on avoiding common tourist scams/overcharging zones",
                        category="Etiquette",
                    ),
                    ChecklistItem(
                        task="Bring slip-on shoes for frequent shoe removal requirements",
                        category="Packing",
                    ),
                ]
            )
        else:
            items.extend(
                [
                    ChecklistItem(
                        task="Learn basic polite dining phrases ('Thank you for the food')",
                        category="Etiquette",
                    ),
                    ChecklistItem(
                        task="Bring slip-on shoes for temple and home entrances",
                        category="Packing",
                    ),
                ]
            )
    else:  # Advanced
        items.extend(
            [
                ChecklistItem(
                    task="Memorize advanced local social gestures and greetings",
                    category="Etiquette",
                ),
                ChecklistItem(
                    task="Bring a small traditional gift (Omiyage/present) from home if meeting local hosts",
                    category="Packing",
                ),
                ChecklistItem(
                    task="Read brief guide on regional dialects or local folklore",
                    category="Etiquette",
                ),
            ]
        )

    return items


def generate_fallback_questions(destination: str):
    """Generate universally appropriate fallback diagnostic questions.

    These questions are worded to be culturally relevant for any destination
    worldwide, avoiding region-specific assumptions (e.g., chopstick rules).
    The destination name is woven into the question text for personalization.
    """
    from travelpilot.models import DiagnosticQuestion

    return [
        DiagnosticQuestion(
            id="q1",
            question=f"When meeting a local person for the first time in {destination}, what is generally the most respectful approach?",
            options=[
                "Observe and mirror the local greeting style, whether it is a handshake, bow, or verbal greeting",
                "Immediately use casual first-name greetings and physical contact like back-slapping",
                "Avoid all eye contact and communication until the other person speaks first",
            ],
            correct_option="Observe and mirror the local greeting style, whether it is a handshake, bow, or verbal greeting",
            topic="Greeting & Social Etiquette",
        ),
        DiagnosticQuestion(
            id="q2",
            question=f"When invited to dine at a local home or traditional restaurant in {destination}, which behavior is most likely to be considered disrespectful?",
            options=[
                "Complimenting the host on the food and asking about local ingredients",
                "Starting to eat before the host or eldest person at the table has begun",
                "Accepting a second serving when offered by the host",
            ],
            correct_option="Starting to eat before the host or eldest person at the table has begun",
            topic="Dining & Food Customs",
        ),
        DiagnosticQuestion(
            id="q3",
            question=f"What is the most appropriate way to prepare for visiting a sacred or historically significant site in {destination}?",
            options=[
                "Research and follow the specific dress code and behavioral rules of the site before visiting",
                "Wear comfortable beachwear since tourist sites are always casual",
                "Bring a professional camera crew to document everything freely",
            ],
            correct_option="Research and follow the specific dress code and behavioral rules of the site before visiting",
            topic="Sacred Sites & Dress Code",
        ),
    ]

