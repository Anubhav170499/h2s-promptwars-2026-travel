export interface TravelPreferences {
  destination: string;
  travel_style: string;
  cultural_interests: string[];
  budget_tier: string;
  budget_limit: number;
  duration_days: number;
  excluded_factors: string[];
}

export interface DiagnosticAnswer {
  question_id: string;
  user_answer: string;
  confidence: number;
}

export interface DiagnosticQuestion {
  id: string;
  question: string;
  options: string[];
  correct_option: string;
  topic: string;
}

export interface AdaptationResult {
  challenge_level: string;
  cultural_focus: string;
  reasoning: string;
}

export interface Activity {
  name: string;
  description: string;
  time_slot: string;
  estimated_cost: number;
  cultural_significance: string;
}

export interface DailyItinerary {
  day_number: number;
  theme: string;
  activities: Activity[];
}

export interface TripItinerary {
  destination: string;
  adaptation_reasoning: string;
  daily_plans: DailyItinerary[];
}

export interface ChecklistItem {
  task: string;
  category: string;
  is_completed: boolean;
}

export interface BudgetFeasibility {
  is_feasible: boolean;
  estimated_total_cost: number;
  analysis_reason: string;
  saving_tips: string[];
}

export interface SessionResponse {
  session_id: string;
  owner_id: string;
  preferences: TravelPreferences;
  adaptation: AdaptationResult;
  itinerary: TripItinerary;
  checklist: ChecklistItem[];
  budget_feasibility: BudgetFeasibility;
}

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

// Helper to fetch with timeout
async function fetchWithTimeout(
  url: string,
  options: RequestInit = {},
  timeoutMs = 60000
): Promise<Response> {
  const controller = new AbortController();
  const id = setTimeout(() => controller.abort(), timeoutMs);
  
  try {
    const res = await fetch(url, {
      ...options,
      signal: controller.signal,
    });
    return res;
  } finally {
    clearTimeout(id);
  }
}

// Get Auth Token from localStorage if it exists
function getAuthHeaders(): Record<string, string> {
  const headers: Record<string, string> = {
    "Content-Type": "application/json",
  };
  
  if (typeof window !== "undefined") {
    const token = localStorage.getItem("tp_token");
    if (token) {
      headers["Authorization"] = `Bearer ${token}`;
    }
  }
  
  return headers;
}

export const api = {
  async getDiagnosticQuestions(): Promise<DiagnosticQuestion[]> {
    const res = await fetchWithTimeout(`${API_BASE}/api/diagnostic-questions`, {
      method: "GET",
      headers: getAuthHeaders(),
    });
    
    if (!res.ok) {
      throw new Error(`Failed to load diagnostic questions: ${res.statusText}`);
    }
    return res.json();
  },

  async initializeSession(
    preferences: TravelPreferences,
    diagnosticAnswers: DiagnosticAnswer[]
  ): Promise<SessionResponse> {
    const res = await fetchWithTimeout(`${API_BASE}/api/session/init`, {
      method: "POST",
      headers: getAuthHeaders(),
      body: JSON.stringify({
        preferences,
        diagnostic_answers: diagnosticAnswers,
      }),
    });
    
    if (!res.ok) {
      const errDetail = await res.json().catch(() => ({ detail: res.statusText }));
      throw new Error(errDetail.detail || "Failed to initialize travel session");
    }
    return res.json();
  },

  async getSession(sessionId: string): Promise<SessionResponse> {
    const res = await fetchWithTimeout(`${API_BASE}/api/session/${sessionId}`, {
      method: "GET",
      headers: getAuthHeaders(),
    });
    
    if (!res.ok) {
      throw new Error(`Failed to retrieve session: ${res.statusText}`);
    }
    return res.json();
  },

  async substituteActivity(
    sessionId: string,
    dayNumber: number,
    activityName: string,
    reasonForSubstitution: string
  ): Promise<SessionResponse> {
    const res = await fetchWithTimeout(`${API_BASE}/api/session/${sessionId}/substitute`, {
      method: "POST",
      headers: getAuthHeaders(),
      body: JSON.stringify({
        day_number: dayNumber,
        activity_name: activityName,
        reason_for_substitution: reasonForSubstitution,
      }),
    });
    
    if (!res.ok) {
      const errDetail = await res.json().catch(() => ({ detail: res.statusText }));
      throw new Error(errDetail.detail || "Failed to substitute activity");
    }
    return res.json();
  },

  async toggleChecklistItem(
    sessionId: string,
    taskName: string,
    isCompleted: boolean
  ): Promise<SessionResponse> {
    const query = new URLSearchParams({
      task_name: taskName,
      is_completed: String(isCompleted),
    });
    
    const res = await fetchWithTimeout(
      `${API_BASE}/api/session/${sessionId}/checklist/toggle?${query.toString()}`,
      {
        method: "POST",
        headers: getAuthHeaders(),
      }
    );
    
    if (!res.ok) {
      const errDetail = await res.json().catch(() => ({ detail: res.statusText }));
      throw new Error(errDetail.detail || "Failed to update checklist item");
    }
    return res.json();
  },
};
