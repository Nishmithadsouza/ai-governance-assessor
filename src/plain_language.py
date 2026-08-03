"""Plain-English translations for display only. The actual field values used
for scoring never change — this module only controls what a non-technical
person reads on screen."""

DIMENSION_PLAIN = {
    "Data Privacy": ("🔒", "Keeping Data Safe"),
    "Bias/Fairness": ("⚖️", "Fairness"),
    "Human Oversight": ("👀", "Human Checks"),
    "Explainability": ("💡", "Clear Reasoning"),
    "Security": ("🛡️", "Security"),
    "Decision Impact": ("🎯", "Impact on People"),
    "Regulatory Exposure": ("📜", "Legal Risk"),
    "Model Risk": ("🤖", "AI Reliability"),
    "Monitoring": ("📈", "Ongoing Checks"),
}

LEVEL_PLAIN = {
    "Low": ("Good", "🟢"),
    "Medium": ("Watch", "🟡"),
    "High": ("Risk", "🟠"),
    "Critical": ("Critical", "🔴"),
}

FUNCTION_PLAIN = {
    "Diagnosis / Clinical Decision Support": "Helps diagnose patients",
    "Treatment Recommendation": "Recommends medical treatment",
    "Patient Triage": "Decides how urgently a patient needs care",
    "Risk Scoring / Population Health Prediction": "Predicts health risk for people",
    "Medical Imaging Analysis": "Reads medical scans/images",
    "Patient-Facing Chatbot / Virtual Assistant": "Chats directly with patients",
    "Claims / Prior-Authorization Decisioning": "Approves or denies insurance claims",
    "Administrative Scheduling / Staffing": "Handles scheduling/staffing",
    "Drug Discovery / Research": "Helps research new drugs",
    "Resume Screening / Candidate Ranking": "Screens resumes and ranks candidates",
    "Video Interview Analysis": "Analyzes recorded job interviews",
    "Candidate Sourcing / Outreach": "Finds and contacts job candidates",
    "Skills Assessment / Testing": "Tests candidate skills",
    "Interview Scheduling (Administrative)": "Schedules interviews",
    "Promotion / Performance-Based Decisioning": "Decides on promotions",
    "Termination / Layoff Risk Scoring": "Scores layoff/termination risk",
    "Automated Decision-Making (Consequential)": "Makes a decision that affects someone's life",
    "Prediction / Risk Scoring": "Predicts a risk score about someone",
    "Classification / Categorization": "Sorts people/things into categories",
    "Recommendation / Ranking": "Recommends or ranks options",
    "Content Generation": "Generates text/content",
    "Chatbot / Conversational Agent": "Chats with users",
    "Process Automation (Non-consequential)": "Automates routine back-office work",
    "Research / Analytics": "Used for research/analysis only",
}

MODEL_PLAIN = {
    "Traditional ML / Statistical Model": "Standard predictive statistics",
    "Deep Learning (black-box)": "Advanced AI pattern-recognition",
    "Generative AI / LLM": "Generative AI (like ChatGPT-style models)",
    "Rule-based / Expert System": "Fixed rules, not learning AI",
}

AUTONOMY_PLAIN = {
    "Fully autonomous - no human review": "AI decides entirely on its own",
    "Human-in-the-loop (advisory, human must act)": "AI flags things for a person to act on",
    "Human-on-the-loop (human can override)": "AI decides, but a person can step in",
    "Human makes final decision, AI is one input": "A person makes the final call; AI just advises",
}

MONITORING_PLAIN = {
    "No post-deployment monitoring": "Not being actively checked after launch",
    "Periodic manual audit": "Checked occasionally by a person",
    "Continuous automated monitoring": "Checked continuously",
}

EXPLAINABILITY_PLAIN = {
    "None available": "Can't explain its own decisions",
    "Global feature importance only": "Gives a general sense of what matters, not per-case",
    "Case-level explanation (e.g., SHAP/LIME)": "Can explain each individual decision",
    "Fully interpretable model (e.g., rules/scorecard)": "Fully transparent — no black box",
}


def plain_level(level):
    word, icon = LEVEL_PLAIN.get(level, (level, "⚪"))
    return f"{icon} {word}"


def plain_dimension(dimension):
    icon, label = DIMENSION_PLAIN.get(dimension, ("⚪", dimension))
    return icon, label
