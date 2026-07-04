"use client";

import { useEffect, useState } from "react";
import { 
  api, TravelPreferences, DiagnosticAnswer, DiagnosticQuestion, 
  SessionResponse, ChecklistItem, Activity 
} from "../lib/api";
import { 
  Sparkles, Compass, MapPin, DollarSign, Calendar, ListTodo, 
  HelpCircle, RefreshCw, AlertTriangle, ArrowRight, User, Check, X, ShieldAlert
} from "lucide-react";

export default function HomePage() {
  // Session states
  const [session, setSession] = useState<SessionResponse | null>(null);
  const [loading, setLoading] = useState<boolean>(false);
  const [loadingMessage, setLoadingMessage] = useState<string>("");
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [ariaNotification, setAriaNotification] = useState<string>("");

  // Quiz state
  const [questions, setQuestions] = useState<DiagnosticQuestion[]>([]);
  const [quizAnswers, setQuizAnswers] = useState<Record<string, { answer: string; confidence: number }>>({});
  const [quizStep, setQuizStep] = useState<boolean>(false);

  // Preferences Form state
  const [preferences, setPreferences] = useState<TravelPreferences>({
    destination: "Kyoto",
    travel_style: "Cultural Immersion",
    cultural_interests: ["Traditional Arts", "Gardens & Temples"],
    budget_tier: "Mid-range",
    budget_limit: 800.0,
    duration_days: 3,
    excluded_factors: [],
  });

  const [rawExclusions, setRawExclusions] = useState<string>("");
  const [rawInterests, setRawInterests] = useState<string>("Traditional Arts, Gardens & Temples, Gastronomy");

  // Authentication simulation states
  const [isLoggedIn, setIsLoggedIn] = useState<boolean>(false);
  const [authToken, setAuthToken] = useState<string>("");

  // Substitution state
  const [substitutionModal, setSubstitutionModal] = useState<{
    dayNumber: number;
    activityName: string;
    show: boolean;
  }>({ dayNumber: 1, activityName: "", show: false });
  const [substitutionReason, setSubstitutionReason] = useState<string>("Bad Weather");
  const [customSubReason, setCustomSubReason] = useState<string>("");

  // Active itinerary tab
  const [activeDay, setActiveDay] = useState<number>(1);

  // Initialize: restore simulated authentication & check url session if persisted
  useEffect(() => {
    if (typeof window !== "undefined") {
      const savedToken = localStorage.getItem("tp_token");
      if (savedToken) {
        setAuthToken(savedToken);
        setIsLoggedIn(true);
      }
      
      const savedSessionId = localStorage.getItem("tp_session_id");
      if (savedSessionId) {
        loadSession(savedSessionId);
      }
    }
  }, []);

  const announce = (message: string) => {
    setAriaNotification(message);
    // Auto-clear after speaking
    setTimeout(() => setAriaNotification(""), 3000);
  };

  const handleLoginToggle = () => {
    if (isLoggedIn) {
      localStorage.removeItem("tp_token");
      setAuthToken("");
      setIsLoggedIn(false);
      announce("Switched to Guest session mode.");
    } else {
      const dummyToken = "tp_jwt_secret_verifier_token_example";
      localStorage.setItem("tp_token", dummyToken);
      setAuthToken(dummyToken);
      setIsLoggedIn(true);
      announce("Logged in as simulated registered user.");
    }
  };

  const loadSession = async (id: string) => {
    setLoading(true);
    setLoadingMessage("Retrieving your active travel planner...");
    try {
      const data = await api.getSession(id);
      setSession(data);
      localStorage.setItem("tp_session_id", data.session_id);
      setErrorMessage(null);
      announce(`Travel plan for ${data.preferences.destination} loaded successfully.`);
    } catch (err: any) {
      console.error(err);
      localStorage.removeItem("tp_session_id");
    } finally {
      setLoading(false);
    }
  };

  // Step 1: Preferences Form submit
  const handleStartPlanning = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    setLoadingMessage("Fetching cultural baseline quiz for your destination...");
    
    // Parse interests & exclusions
    const parsedInterests = rawInterests
      .split(",")
      .map(i => i.trim())
      .filter(i => i.length > 0);
    const parsedExclusions = rawExclusions
      .split(",")
      .map(e => e.trim())
      .filter(e => e.length > 0);

    const updatedPrefs = {
      ...preferences,
      cultural_interests: parsedInterests,
      excluded_factors: parsedExclusions,
    };
    
    setPreferences(updatedPrefs);

    try {
      const fetchedQuestions = await api.getDiagnosticQuestions();
      setQuestions(fetchedQuestions);
      
      // Initialize quiz answers structure
      const initialAnswers: Record<string, { answer: string; confidence: number }> = {};
      fetchedQuestions.forEach(q => {
        initialAnswers[q.id] = { answer: q.options[0], confidence: 3 };
      });
      setQuizAnswers(initialAnswers);
      
      setQuizStep(true);
      setErrorMessage(null);
      announce("Diagnostic questions loaded. Please complete the cultural baseline quiz.");
    } catch (err: any) {
      setErrorMessage(err.message || "Failed to load diagnostic questions.");
      announce("Error: " + (err.message || "Failed to load diagnostic questions."));
    } finally {
      setLoading(false);
    }
  };

  // Step 2: Quiz submit
  const handleQuizSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    setLoadingMessage("Generating your adaptive itinerary...");
    
    const formattedAnswers: DiagnosticAnswer[] = Object.keys(quizAnswers).map(qId => ({
      question_id: qId,
      user_answer: quizAnswers[qId].answer,
      confidence: quizAnswers[qId].confidence,
    }));

    try {
      const data = await api.initializeSession(preferences, formattedAnswers);
      setSession(data);
      localStorage.setItem("tp_session_id", data.session_id);
      setQuizStep(false);
      setActiveDay(1);
      setErrorMessage(null);
      announce(`Travel planner initialized successfully for ${data.preferences.destination}.`);
    } catch (err: any) {
      setErrorMessage(err.message || "Failed to initialize travel planner.");
      announce("Error: " + (err.message || "Failed to initialize travel planner."));
    } finally {
      setLoading(false);
    }
  };

  // Toggle checklist task completion status
  const handleToggleTask = async (item: ChecklistItem) => {
    if (!session) return;
    try {
      const updated = await api.toggleChecklistItem(
        session.session_id,
        item.task,
        !item.is_completed
      );
      setSession(updated);
      announce(`Marked task "${item.task}" as ${!item.is_completed ? 'completed' : 'incomplete'}.`);
    } catch (err: any) {
      setErrorMessage(err.message || "Failed to update task status.");
    }
  };

  // Open modal for activity substitution
  const openSubstitution = (dayNum: number, actName: string) => {
    setSubstitutionModal({
      dayNumber: dayNum,
      activityName: actName,
      show: true,
    });
    setSubstitutionReason("Bad Weather");
    setCustomSubReason("");
  };

  // Submit substitution request
  const handleSubstitutionSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!session) return;

    setLoading(true);
    setLoadingMessage("Computing adaptive activity replacement...");
    
    const reason = substitutionReason === "Other" ? customSubReason : substitutionReason;
    
    try {
      const updated = await api.substituteActivity(
        session.session_id,
        substitutionModal.dayNumber,
        substitutionModal.activityName,
        reason
      );
      setSession(updated);
      setSubstitutionModal({ dayNumber: 1, activityName: "", show: false });
      setErrorMessage(null);
      announce(`Activity substituted successfully. Check the updated adaptation reason.`);
    } catch (err: any) {
      setErrorMessage(err.message || "Failed to substitute activity.");
      announce("Error: " + (err.message || "Failed to substitute activity."));
    } finally {
      setLoading(false);
    }
  };

  const handleResetSession = () => {
    localStorage.removeItem("tp_session_id");
    setSession(null);
    setQuizStep(false);
    setErrorMessage(null);
    announce("Session cleared. Started a new travel plan.");
  };

  return (
    <div className="flex-1 flex flex-col px-4 md:px-8 py-6 max-w-7xl mx-auto w-full">
      
      {/* Live region for screen readers */}
      <div className="sr-only" aria-live="polite">
        {ariaNotification}
      </div>

      {/* Header section */}
      <header className="flex flex-col md:flex-row justify-between items-start md:items-center gap-4 mb-8 pb-6 border-b border-white/5">
        <div>
          <div 
            onClick={handleResetSession}
            className="flex items-center gap-2 mb-1 cursor-pointer select-none hover:opacity-80 transition-opacity"
            title="Go to Homepage"
            role="button"
            tabIndex={0}
            onKeyDown={(e) => { if (e.key === 'Enter' || e.key === ' ') handleResetSession(); }}
          >
            <Compass className="w-8 h-8 text-indigo-400 animate-spin-slow" />
            <h1 className="text-3xl font-extrabold tracking-tight text-white">
              Travel<span className="text-gradient">Pilot</span>
            </h1>
          </div>
          <p className="text-sm text-gray-400">
            GenAI-powered Adaptive Travel Discovery & Cultural Experiences
          </p>
        </div>

        {/* Auth Simulation Bar */}
        <div className="flex items-center gap-3 p-3 rounded-xl bg-white/5 border border-white/5 glass-panel text-xs">
          <div className="flex items-center gap-2">
            <User className={`w-4 h-4 ${isLoggedIn ? "text-indigo-400" : "text-gray-400"}`} />
            <div>
              <p className="font-semibold text-white">
                Session Mode: {isLoggedIn ? "Simulated User (Registered)" : "Guest Context"}
              </p>
              <p className="text-gray-500">
                {isLoggedIn ? "Bearer headers sent automatically" : "Standard sandbox limits"}
              </p>
            </div>
          </div>
          <button
            onClick={handleLoginToggle}
            className={`px-3 py-1.5 rounded-lg font-semibold transition-all ${
              isLoggedIn 
                ? "bg-rose-500/10 hover:bg-rose-500/20 text-rose-300 border border-rose-500/20" 
                : "bg-indigo-500/10 hover:bg-indigo-500/20 text-indigo-300 border border-indigo-500/20"
            }`}
          >
            {isLoggedIn ? "Simulate Guest" : "Simulate Login"}
          </button>
        </div>
      </header>

      {/* Global Error Banner */}
      {errorMessage && (
        <div role="alert" className="flex items-start gap-3 p-4 mb-6 rounded-xl bg-rose-500/10 border border-rose-500/20 text-rose-300 text-sm">
          <ShieldAlert className="w-5 h-5 shrink-0 mt-0.5" />
          <div>
            <p className="font-bold">Execution Warning</p>
            <p>{errorMessage}</p>
          </div>
          <button 
            onClick={() => setErrorMessage(null)} 
            className="ml-auto p-1 text-rose-300 hover:text-white"
            aria-label="Dismiss alert"
          >
            <X className="w-4 h-4" />
          </button>
        </div>
      )}

      {/* Main content conditional views */}

      {/* Loading Overlay */}
      {loading && (
        <div className="fixed inset-0 z-50 flex flex-col items-center justify-center bg-bg-primary/80 backdrop-blur-md">
          <div className="p-8 rounded-2xl glass-panel max-w-sm w-full text-center flex flex-col items-center gap-4">
            <div className="relative">
              <Compass className="w-16 h-16 text-indigo-400 animate-spin" />
              <Sparkles className="w-6 h-6 text-purple-400 absolute -top-1 -right-1 animate-pulse" />
            </div>
            <p className="font-bold text-white text-lg">Processing Adaptation</p>
            <p className="text-sm text-gray-400">
              {loadingMessage}
            </p>
            <div className="loading-dots text-indigo-400 text-2xl font-bold">
              <span>.</span><span>.</span><span>.</span>
            </div>
          </div>
        </div>
      )}

      {/* View 1: Preference capture form */}
      {!session && !quizStep && (
        <div className="max-w-2xl mx-auto w-full animate-fadeIn">
          <div className="p-6 md:p-8 rounded-2xl glass-panel">
            <div className="flex items-center gap-2 mb-6">
              <Sparkles className="w-5 h-5 text-purple-400" />
              <h2 className="text-xl font-bold text-white">Capture Travel Style & Preferences</h2>
            </div>

            <form onSubmit={handleStartPlanning} className="space-y-6">
              <fieldset className="grid grid-cols-1 md:grid-cols-2 gap-4 border-none p-0 m-0">
                <legend className="sr-only">Destination and style choices</legend>
                
                <div className="flex flex-col gap-1.5">
                  <label htmlFor="destination" className="text-sm font-semibold text-gray-300">
                    Target Destination
                  </label>
                  <div className="relative">
                    <MapPin className="w-4 h-4 text-gray-500 absolute left-3 top-3.5" />
                    <input
                      type="text"
                      id="destination"
                      value={preferences.destination}
                      onChange={e => setPreferences({ ...preferences, destination: e.target.value })}
                      required
                      className="w-full bg-white/5 border border-white/10 rounded-xl py-3 pl-10 pr-4 text-white placeholder-gray-500 focus:outline-none focus:border-indigo-400 transition"
                      placeholder="e.g. Kyoto, Rome, Paris"
                    />
                  </div>
                </div>

                <div className="flex flex-col gap-1.5">
                  <label htmlFor="travel_style" className="text-sm font-semibold text-gray-300">
                    Travel Style Focus
                  </label>
                  <select
                    id="travel_style"
                    value={preferences.travel_style}
                    onChange={e => setPreferences({ ...preferences, travel_style: e.target.value })}
                    className="w-full bg-[#11131c] border border-white/10 rounded-xl py-3 px-4 text-white focus:outline-none focus:border-indigo-400 transition"
                  >
                    <option className="bg-[#11131c] text-white" value="Cultural Immersion">Cultural Immersion</option>
                    <option className="bg-[#11131c] text-white" value="Historical Exploration">Historical Exploration</option>
                    <option className="bg-[#11131c] text-white" value="Relaxed Sightseeing">Relaxed Sightseeing</option>
                    <option className="bg-[#11131c] text-white" value="Adventurous Exploration">Adventurous Exploration</option>
                  </select>
                </div>
              </fieldset>

              <div className="flex flex-col gap-1.5">
                <label htmlFor="interests" className="text-sm font-semibold text-gray-300">
                  Cultural Interests (comma separated)
                </label>
                <input
                  type="text"
                  id="interests"
                  value={rawInterests}
                  onChange={e => setRawInterests(e.target.value)}
                  className="w-full bg-white/5 border border-white/10 rounded-xl py-3 px-4 text-white placeholder-gray-500 focus:outline-none focus:border-indigo-400 transition"
                  placeholder="e.g. Gastronomy, Local Crafts, Temples, Literature"
                />
              </div>

              <fieldset className="grid grid-cols-1 md:grid-cols-3 gap-4 border-none p-0 m-0">
                <legend className="sr-only">Budget and Duration parameters</legend>

                <div className="flex flex-col gap-1.5">
                  <label htmlFor="budget_tier" className="text-sm font-semibold text-gray-300">
                    Budget Tier
                  </label>
                  <select
                    id="budget_tier"
                    value={preferences.budget_tier}
                    onChange={e => setPreferences({ ...preferences, budget_tier: e.target.value })}
                    className="w-full bg-[#11131c] border border-white/10 rounded-xl py-3 px-4 text-white focus:outline-none focus:border-indigo-400 transition"
                  >
                    <option className="bg-[#11131c] text-white" value="Budget">Budget Friendly</option>
                    <option className="bg-[#11131c] text-white" value="Mid-range">Mid-range Value</option>
                    <option className="bg-[#11131c] text-white" value="Luxury">Luxury Premium</option>
                  </select>
                </div>

                <div className="flex flex-col gap-1.5">
                  <label htmlFor="budget_limit" className="text-sm font-semibold text-gray-300">
                    Budget Limit ($ USD)
                  </label>
                  <div className="relative">
                    <DollarSign className="w-4 h-4 text-gray-500 absolute left-3 top-3.5" />
                    <input
                      type="number"
                      id="budget_limit"
                      value={preferences.budget_limit}
                      onChange={e => setPreferences({ ...preferences, budget_limit: Number(e.target.value) })}
                      min="10"
                      max="100000"
                      required
                      className="w-full bg-white/5 border border-white/10 rounded-xl py-3 pl-10 pr-4 text-white focus:outline-none focus:border-indigo-400 transition"
                    />
                  </div>
                </div>

                <div className="flex flex-col gap-1.5">
                  <label htmlFor="duration_days" className="text-sm font-semibold text-gray-300">
                    Duration ({preferences.duration_days} Days)
                  </label>
                  <div className="relative pt-2">
                    <input
                      type="range"
                      id="duration_days"
                      min="1"
                      max="14"
                      value={preferences.duration_days}
                      onChange={e => setPreferences({ ...preferences, duration_days: Number(e.target.value) })}
                      className="w-full accent-indigo-500"
                    />
                  </div>
                </div>
              </fieldset>

              <div className="flex flex-col gap-1.5">
                <label htmlFor="exclusions" className="text-sm font-semibold text-gray-300">
                  Excluded Factors / Zones (comma separated)
                </label>
                <input
                  type="text"
                  id="exclusions"
                  value={rawExclusions}
                  onChange={e => setRawExclusions(e.target.value)}
                  className="w-full bg-white/5 border border-white/10 rounded-xl py-3 px-4 text-white placeholder-gray-500 focus:outline-none focus:border-indigo-400 transition"
                  placeholder="e.g. hiking, high altitude, heavy walking"
                />
              </div>

              <button type="submit" className="w-full py-4 rounded-xl btn-primary font-bold flex items-center justify-center gap-2">
                Continue to Diagnostic Quiz <ArrowRight className="w-5 h-5" />
              </button>
            </form>
          </div>
        </div>
      )}

      {/* View 2: Diagnostic baseline check */}
      {quizStep && questions.length > 0 && (
        <div className="max-w-2xl mx-auto w-full animate-fadeIn">
          <div className="p-6 md:p-8 rounded-2xl glass-panel">
            <div className="flex items-center gap-2 mb-2">
              <HelpCircle className="w-5 h-5 text-indigo-400" />
              <h2 className="text-xl font-bold text-white">Local Culture & Etiquette Diagnostic</h2>
            </div>
            <p className="text-sm text-gray-400 mb-6">
              To calibrate your guide details and activities, please answer these basic local etiquette scenarios.
            </p>

            <form onSubmit={handleQuizSubmit} className="space-y-6">
              {questions.map((q, idx) => (
                <fieldset key={q.id} className="p-5 rounded-xl bg-white/5 border border-white/5 space-y-4">
                  <legend className="text-base font-bold text-white px-2">
                    {idx + 1}. {q.question}
                  </legend>
                  
                  <div className="space-y-3 pt-2">
                    {q.options.map((opt) => (
                      <label key={opt} className="flex items-start gap-3 p-3 rounded-lg border border-white/5 bg-white/5 hover:bg-white/10 cursor-pointer transition">
                        <input
                          type="radio"
                          name={`question-${q.id}`}
                          value={opt}
                          checked={quizAnswers[q.id]?.answer === opt}
                          onChange={() => setQuizAnswers({
                            ...quizAnswers,
                            [q.id]: { ...quizAnswers[q.id], answer: opt }
                          })}
                          className="mt-1 accent-indigo-500"
                        />
                        <span className="text-sm text-gray-300">{opt}</span>
                      </label>
                    ))}
                  </div>

                  <div className="pt-2 border-t border-white/5">
                    <div className="flex justify-between items-center mb-1">
                      <label htmlFor={`conf-${q.id}`} className="text-xs font-semibold text-gray-400">
                        Self-Assessed Confidence:
                      </label>
                      <span className="text-xs font-bold text-indigo-300">
                        {quizAnswers[q.id]?.confidence} / 5 (
                        {quizAnswers[q.id]?.confidence <= 2 ? "Unsure" : 
                         quizAnswers[q.id]?.confidence <= 4 ? "Confident" : "Very Certain"}
                        )
                      </span>
                    </div>
                    <input
                      type="range"
                      id={`conf-${q.id}`}
                      min="1"
                      max="5"
                      value={quizAnswers[q.id]?.confidence || 3}
                      onChange={e => setQuizAnswers({
                        ...quizAnswers,
                        [q.id]: { ...quizAnswers[q.id], confidence: Number(e.target.value) }
                      })}
                      className="w-full accent-indigo-500"
                    />
                  </div>
                </fieldset>
              ))}

              <div className="flex gap-4">
                <button
                  type="button"
                  onClick={() => setQuizStep(false)}
                  className="w-1/3 py-4 rounded-xl btn-secondary font-bold"
                >
                  Back
                </button>
                <button
                  type="submit"
                  className="w-2/3 py-4 rounded-xl btn-primary font-bold flex items-center justify-center gap-2"
                >
                  Build Travel Guide <Sparkles className="w-5 h-5" />
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* View 3: Trip Dashboard */}
      {session && (
        <div className="grid grid-cols-1 lg:grid-cols-12 gap-8 animate-fadeIn">
          
          {/* Left Column: Diagnostics, feasibility, and packing list */}
          <div className="lg:col-span-5 space-y-6">
            
            {/* Adaptation engine feedback */}
            <div className="p-6 rounded-2xl glass-panel">
              <div className="flex items-center justify-between mb-4">
                <div className="flex items-center gap-2">
                  <Sparkles className="w-5 h-5 text-indigo-400" />
                  <h2 className="text-lg font-bold text-white">Adaptation Scoring</h2>
                </div>
                <span className="px-3 py-1 rounded-full text-xs font-extrabold bg-indigo-500/10 text-indigo-300 border border-indigo-500/20">
                  {session.adaptation.challenge_level} Pathway
                </span>
              </div>
              
              <div className="space-y-3">
                <div className="flex justify-between text-sm">
                  <span className="text-gray-400">Cultural Focus:</span>
                  <span className="font-semibold text-white">{session.adaptation.cultural_focus}</span>
                </div>
                <div className="p-4 rounded-xl bg-indigo-500/5 border border-indigo-500/10 text-xs text-indigo-200 italic leading-relaxed">
                  {session.adaptation.reasoning}
                </div>
              </div>
            </div>

            {/* Budget Feasibility */}
            <div className="p-6 rounded-2xl glass-panel">
              <div className="flex items-center justify-between mb-4">
                <div className="flex items-center gap-2">
                  <DollarSign className="w-5 h-5 text-teal-400" />
                  <h2 className="text-lg font-bold text-white">Budget Verification</h2>
                </div>
                <span className={`px-3 py-1 rounded-full text-xs font-extrabold border ${
                  session.budget_feasibility.is_feasible 
                    ? "bg-teal-500/10 text-teal-300 border-teal-500/20" 
                    : "bg-rose-500/10 text-rose-300 border-rose-500/20 animate-pulse"
                }`}>
                  {session.budget_feasibility.is_feasible ? "Feasible Check" : "Overrun Warning"}
                </span>
              </div>

              <div className="space-y-4">
                <div className="grid grid-cols-2 gap-4 text-center">
                  <div className="p-3 rounded-xl bg-white/5 border border-white/5">
                    <p className="text-xs text-gray-400">Budget Limit</p>
                    <p className="text-lg font-bold text-white">${session.preferences.budget_limit.toFixed(2)}</p>
                  </div>
                  <div className="p-3 rounded-xl bg-white/5 border border-white/5">
                    <p className="text-xs text-gray-400">Estimated Cost</p>
                    <p className="text-lg font-bold text-white">${session.budget_feasibility.estimated_total_cost.toFixed(2)}</p>
                  </div>
                </div>

                <div className={`p-4 rounded-xl text-xs leading-relaxed border ${
                  session.budget_feasibility.is_feasible 
                    ? "bg-teal-500/5 border-teal-500/10 text-teal-200" 
                    : "bg-rose-500/5 border-rose-500/10 text-rose-200"
                }`}>
                  {session.budget_feasibility.analysis_reason}
                </div>

                {session.budget_feasibility.saving_tips.length > 0 && (
                  <div className="space-y-2">
                    <p className="text-xs font-semibold text-gray-400">Destination Saving Tips:</p>
                    <ul className="text-xs text-gray-300 list-disc list-inside space-y-1">
                      {session.budget_feasibility.saving_tips.map((tip, idx) => (
                        <li key={idx}>{tip}</li>
                      ))}
                    </ul>
                  </div>
                )}
              </div>
            </div>

            {/* Travel Action / Etiquette Checklist */}
            <div className="p-6 rounded-2xl glass-panel">
              <div className="flex items-center gap-2 mb-4">
                <ListTodo className="w-5 h-5 text-purple-400" />
                <h2 className="text-lg font-bold text-white">Immersive Travel Checklist</h2>
              </div>

              <div className="space-y-4">
                {["Documents", "Packing", "Etiquette"].map((cat) => {
                  const items = session.checklist.filter(item => item.category === cat);
                  if (items.length === 0) return null;
                  
                  return (
                    <div key={cat} className="space-y-2">
                      <p className="text-xs font-bold uppercase tracking-wider text-purple-400 border-b border-white/5 pb-1">
                        {cat}
                      </p>
                      
                      <div className="space-y-1.5">
                        {items.map((item) => (
                          <label key={item.task} className="flex items-start gap-3 p-2 rounded-lg hover:bg-white/5 cursor-pointer transition">
                            <input
                              type="checkbox"
                              checked={item.is_completed}
                              onChange={() => handleToggleTask(item)}
                              className="custom-checkbox mt-0.5"
                            />
                            <span className={`text-xs ${item.is_completed ? "line-through text-gray-500" : "text-gray-300"}`}>
                              {item.task}
                            </span>
                          </label>
                        ))}
                      </div>
                    </div>
                  );
                })}
              </div>
            </div>

            {/* Reset option */}
            <button
              onClick={handleResetSession}
              className="w-full py-3.5 rounded-xl border border-white/10 hover:border-white/20 bg-white/5 hover:bg-white/10 font-bold text-sm text-gray-300 flex items-center justify-center gap-2 transition"
            >
              <RefreshCw className="w-4 h-4" /> Start New Travel Plan
            </button>
          </div>

          {/* Right Column: Daily Plans & Itinerary details */}
          <div className="lg:col-span-7 space-y-6">
            
            {/* Itinerary Title Card */}
            <div className="p-6 rounded-2xl glass-panel bg-gradient-to-r from-indigo-500/5 to-purple-500/5">
              <div className="flex flex-col md:flex-row justify-between items-start md:items-center gap-4 mb-4">
                <div>
                  <h2 className="text-2xl font-bold text-white">
                    Itinerary for {session.preferences.destination}
                  </h2>
                  <p className="text-xs text-gray-400 mt-1">
                    {session.preferences.duration_days} Days ({session.preferences.travel_style})
                  </p>
                </div>
                
                {/* Day tabs selection */}
                <div className="flex flex-wrap gap-1">
                  {session.itinerary.daily_plans.map((day) => (
                    <button
                      key={day.day_number}
                      onClick={() => setActiveDay(day.day_number)}
                      className={`px-3 py-1.5 rounded-lg text-xs font-bold transition-all ${
                        activeDay === day.day_number
                          ? "bg-indigo-500 text-white"
                          : "bg-white/5 hover:bg-white/10 text-gray-400"
                      }`}
                    >
                      Day {day.day_number}
                    </button>
                  ))}
                </div>
              </div>

              {/* Substitution modification notification */}
              {session.itinerary.adaptation_reasoning && (
                <div className="p-3.5 rounded-xl bg-purple-500/10 border border-purple-500/20 text-xs text-purple-200">
                  <span className="font-bold">Active Adaptation: </span>
                  {session.itinerary.adaptation_reasoning}
                </div>
              )}
            </div>

            {/* Displaying active day itinerary activities */}
            {session.itinerary.daily_plans
              .filter(day => day.day_number === activeDay)
              .map(day => (
                <div key={day.day_number} className="space-y-4 animate-fadeIn">
                  <div className="flex items-center gap-2 px-1">
                    <Calendar className="w-5 h-5 text-indigo-400" />
                    <h3 className="text-base font-bold text-gray-200">
                      Theme: {day.theme}
                    </h3>
                  </div>

                  <div className="space-y-4">
                    {day.activities.map((act) => (
                      <div key={act.name} className="p-5 rounded-2xl glass-panel relative overflow-hidden group">
                        
                        {/* Time slot sticker */}
                        <div className="flex justify-between items-start gap-4 mb-2">
                          <span className="px-2 py-0.5 rounded text-[10px] font-bold uppercase tracking-wider bg-indigo-500/20 text-indigo-300">
                            {act.time_slot}
                          </span>
                          <span className="text-xs font-semibold text-teal-400">
                            Est: ${act.estimated_cost.toFixed(2)}
                          </span>
                        </div>

                        {/* Title & description */}
                        <h4 className="text-base font-bold text-white mb-1.5">{act.name}</h4>
                        <p className="text-xs text-gray-400 leading-relaxed mb-3">{act.description}</p>
                        
                        {/* Cultural Significance */}
                        <div className="p-3 rounded-lg bg-white/5 border border-white/5 text-xs">
                          <p className="font-semibold text-gray-300 mb-0.5">Cultural Significance:</p>
                          <p className="text-gray-400">{act.cultural_significance}</p>
                        </div>

                        {/* Substitute trigger */}
                        <div className="mt-4 pt-3 border-t border-white/5 flex justify-end">
                          <button
                            onClick={() => openSubstitution(day.day_number, act.name)}
                            className="px-3 py-1.5 rounded-lg border border-white/10 hover:border-indigo-500/30 bg-white/5 hover:bg-indigo-500/10 text-xs font-semibold text-gray-300 hover:text-indigo-300 transition-all"
                          >
                            Substitute Activity
                          </button>
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              ))}
          </div>
        </div>
      )}

      {/* Substitution Dialog Overlay */}
      {substitutionModal.show && (
        <div className="fixed inset-0 z-50 flex flex-col items-center justify-center bg-bg-primary/80 backdrop-blur-md">
          <div className="p-6 md:p-8 rounded-2xl glass-panel max-w-md w-full animate-scaleIn">
            <div className="flex justify-between items-center mb-4">
              <h3 className="text-lg font-bold text-white">Adaptation Substitution</h3>
              <button 
                onClick={() => setSubstitutionModal({ dayNumber: 1, activityName: "", show: false })}
                className="p-1 hover:bg-white/10 rounded-lg text-gray-400"
              >
                <X className="w-5 h-5" />
              </button>
            </div>
            
            <p className="text-xs text-gray-400 mb-4 leading-relaxed">
              Substitute activity <span className="text-white font-semibold">"{substitutionModal.activityName}"</span> on Day {substitutionModal.dayNumber} due to constraints.
            </p>

            <form onSubmit={handleSubstitutionSubmit} className="space-y-4">
              <div className="flex flex-col gap-1.5">
                <label htmlFor="sub-reason" className="text-xs font-semibold text-gray-300">
                  Select Constraint/Reason
                </label>
                <select
                  id="sub-reason"
                  value={substitutionReason}
                  onChange={e => setSubstitutionReason(e.target.value)}
                  className="w-full bg-[#11131c] border border-white/10 rounded-xl py-3 px-4 text-white focus:outline-none focus:border-indigo-400 transition"
                >
                  <option className="bg-[#11131c] text-white" value="Bad Weather">Bad Weather (Rain/Storm)</option>
                  <option className="bg-[#11131c] text-white" value="Budget Overrun">Budget Overrun (Too Expensive)</option>
                  <option className="bg-[#11131c] text-white" value="Venue Closure">Venue Closure / Construction</option>
                  <option className="bg-[#11131c] text-white" value="Other">Other Custom Reason</option>
                </select>
              </div>

              {substitutionReason === "Other" && (
                <div className="flex flex-col gap-1.5">
                  <label htmlFor="custom-reason" className="text-xs font-semibold text-gray-300">
                    Describe Custom Reason
                  </label>
                  <input
                    type="text"
                    id="custom-reason"
                    value={customSubReason}
                    onChange={e => setCustomSubReason(e.target.value)}
                    required
                    className="w-full bg-white/5 border border-white/10 rounded-xl py-3 px-4 text-white placeholder-gray-500 focus:outline-none focus:border-indigo-400 transition"
                    placeholder="e.g., fatigue, change of interest"
                  />
                </div>
              )}

              <button type="submit" className="w-full py-3.5 rounded-xl btn-primary font-bold flex items-center justify-center gap-2">
                Apply Adaptations <Sparkles className="w-4 h-4" />
              </button>
            </form>
          </div>
        </div>
      )}

      {/* Footer copyright */}
      <footer className="mt-12 pt-6 border-t border-white/5 text-center text-xs text-gray-600">
        &copy; {new Date().getFullYear()} TravelPilot. Built with Google Gemini 2.5 and Next.js.
      </footer>
    </div>
  );
}
