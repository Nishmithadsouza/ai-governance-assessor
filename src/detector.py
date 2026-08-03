"""Deterministic, keyword-based auto-fill for the New Assessment "quick start"
flow — a fresher (or a live evaluator) can type one plain-English sentence
instead of cold-filling ~12 fields, and every other field gets a sensible
starting value they can still edit.

This is intake convenience, not risk scoring: nothing here decides a score or
a citation — it only pre-populates the exact same structured fields a person
would otherwise pick from dropdowns, and `scoring_engine.evaluate()` runs
identically afterward regardless of whether a value came from detection or
from the user typing/clicking it themselves.

Every detected field is labeled one of three confidence tiers so nothing is
silently guessed and hidden:
  - CONFIDENT  — the description said this fairly explicitly
  - ASSUMED    — nothing said this; a defensible default was used
  - UNRESOLVED — nothing said this and no safe default exists; needs input
"""

import re

from src.options import (
    AUTONOMY_OPTIONS, EXPLAINABILITY_OPTIONS, GENERIC_CONFIG, INDUSTRIES,
    INDUSTRY_CONFIG, JURISDICTIONS, MODEL_TYPES, MONITORING_OPTIONS,
    PRESET_INDUSTRIES, THIRD_PARTY_OPTIONS, get_industry_config,
)

CONFIDENT = "confident"
ASSUMED = "assumed"
UNRESOLVED = "unresolved"

ICON = {CONFIDENT: "✅", ASSUMED: "🟡", UNRESOLVED: "❓"}


def _norm(text):
    return f" {re.sub(r'[^a-z0-9 ]', ' ', text.lower())} "


def _any_in(text, keywords):
    return any(kw in text for kw in keywords)


INDUSTRY_KEYWORDS = {
    "Healthcare & Life Sciences": [
        "patient", "clinical", "diagnos", "medical", "health", "hospital", "drug",
        "treatment", "triage", "radiolog", "clinician", "surgical", "nurse",
        "physician", "disease", "symptom", "phi", "ehr",
    ],
    "HR / Recruitment & Hiring": [
        "resume", "cv ", "candidate", "hiring", "recruit", "employee", "interview",
        "applicant", "workforce", "layoff", "promotion", "job seeker", "termination",
        "onboarding", "talent",
    ],
    "Financial Services / Lending": [
        "loan", "lending", "mortgage", "borrower", "underwriting", "credit score",
        "credit application",
    ],
    "Insurance": ["insurance", "insurer", "policyholder", "premium", "claim payout"],
    "Retail / E-commerce": ["retail", "e-commerce", "ecommerce", "shopping", "product recommendation", "shopper"],
    "Education / EdTech": ["student", "school", "classroom", "exam", "plagiarism", "teacher", "grading"],
    "Criminal Justice / Public Safety": ["recidivism", "parole", "sentencing", "policing", "criminal justice", "law enforcement"],
    "Transportation / Autonomous Vehicles": ["vehicle", "driving", "traffic", "drone", "autonomous car", "self-driving"],
    "Manufacturing / Industrial": ["factory", "assembly line", "manufactur", "industrial robot", "production line"],
    "Real Estate / Housing": ["tenant", "landlord", "rental application", "housing application"],
    "Media / Content Moderation": ["content moderation", "social media post", "flagged content", "user-generated content"],
    "Telecommunications": ["telecom", "network outage", "call center", "customer churn"],
}

MODEL_KEYWORDS = {
    "Generative AI / LLM": ["generative ai", "gpt", "large language model", " llm", "chatbot", "language model", "genai", "gemini", "claude"],
    "Deep Learning (black-box)": ["deep learning", "neural network", "computer vision", "image recognition", "nlp", "natural language processing", "black box", "black-box", "convolutional"],
    "Rule-based / Expert System": ["rule-based", "rule based", "if-then", "expert system", "scorecard"],
    "Traditional ML / Statistical Model": ["machine learning", "statistical model", "regression", "predictive model", "classifier", "gradient boost"],
}

# When the text gives no explicit model-type signal, fall back to the
# conventional model family for that function (ASSUMED, not CONFIDENT) —
# e.g. resume screening / imaging analysis / chatbots are conventionally
# NLP or vision deep-learning systems even when the text doesn't say so.
FUNCTION_MODEL_PRIORS = {
    "Resume Screening / Candidate Ranking": "Deep Learning (black-box)",
    "Video Interview Analysis": "Deep Learning (black-box)",
    "Medical Imaging Analysis": "Deep Learning (black-box)",
    "Patient-Facing Chatbot / Virtual Assistant": "Generative AI / LLM",
    "Chatbot / Conversational Agent": "Generative AI / LLM",
    "Content Generation": "Generative AI / LLM",
    "Drug Discovery / Research": "Deep Learning (black-box)",
    "Diagnosis / Clinical Decision Support": "Deep Learning (black-box)",
}

AUTONOMY_KEYWORDS = [
    ("Fully autonomous - no human review", [
        "without human review", "no human review", "fully automated", "fully autonomous",
        "automatically decides", "no human intervention", "without a human", "no clinician review",
    ]),
    ("Human-in-the-loop (advisory, human must act)", [
        "flags for review", "alerts a human", "escalates to", "advisory only", "for human review",
    ]),
    ("Human-on-the-loop (human can override)", [
        "human can override", "with override", "subject to override",
    ]),
    ("Human makes final decision, AI is one input", [
        "recommends", "suggests", "assists", "supports the decision", "one input", "helps decide", "advises",
    ]),
]

JURISDICTION_KEYWORDS = {
    "European Union": ["europe", "eu ", "gdpr", "european union"],
    "United States - Colorado": ["colorado"],
    "United States - New York City": ["new york city", "nyc"],
    "United States - Illinois": ["illinois"],
    "United States - Federal": ["united states", "u.s.", "usa", "america", "federal"],
}

VULNERABLE_KEYWORDS = [
    "minorit", "race", "ethnic", "women", "female", "elderly", "senior citizen",
    "child", "minor", "disab", "low-income", "low income", "uninsured",
    "non-native", "veteran", "protected class", "underserved",
]

THIRD_PARTY_KEYWORDS = {
    "Licensed third-party/vendor product": ["vendor", "licensed", "third-party", "third party", "off-the-shelf", "purchased from"],
    "Hybrid (vendor model, in-house integration)": ["vendor model", "integrated with our"],
    "Built in-house": ["in-house", "internally built", "our own model", "developed internally", "built by our team"],
}

DATA_TYPE_KEYWORDS = {
    "PHI/ePHI": ["patient data", "phi", "medical record", "health record", "clinical data", "ehr", "patient", "medical imaging", "imaging data"],
    "Genomic Data": ["genom", "dna", "genetic"],
    "Biometric Data": ["biometric", "facial recognition", "fingerprint", "voice print"],
    "Claims/Billing Data": ["claims data", "billing", "insurance claim"],
    "Resume/CV Data": ["resume", "cv ", "cover letter"],
    "Video/Audio Interview Data": ["video interview", "recorded interview", "audio interview"],
    "Biometric Data (facial/voice analysis)": ["facial analysis", "voice analysis", "biometric"],
    "Demographic/EEO Data": ["demographic", "eeo", "race and gender", "protected characteristic"],
    "Performance Review Data": ["performance review", "performance data"],
    "Personal/Identifying Data": ["personal data", "pii", "customer data", "name and address"],
    "Sensitive/Special-Category Data (health, biometric, genetic, etc.)": ["special category", "sensitive data", "health data"],
    "Financial Data": [
        "financial data", "credit history", "bank account", "transaction data", "income data",
        "loan application", "loan applications", "insurance claim", "premium", "credit application", "borrower",
    ],
    "Behavioral/Usage Data": ["usage data", "behavioral data", "clickstream", "browsing history"],
    "De-identified Data": ["de-identified", "de identified", "anonymized", "anonymised"],
    "Synthetic Data": ["synthetic data"],
}


def detect(description):
    """Returns {field_name: (value_or_values, confidence)}. Values always come
    from the same option lists the manual form uses, so whatever this returns
    can be fed straight into a widget's default."""
    text = _norm(description)
    out = {}

    # --- Industry ---
    industry_value, industry_conf = None, UNRESOLVED
    for industry, keywords in INDUSTRY_KEYWORDS.items():
        if _any_in(text, keywords):
            industry_value, industry_conf = industry, CONFIDENT
            break
    out["industry"] = (industry_value, industry_conf)

    cfg = get_industry_config(industry_value) if industry_value else GENERIC_CONFIG

    # --- Function --- (substring match against the function's own significant words)
    function_value, function_conf = None, UNRESOLVED
    for fn in cfg["functions"]:
        words = [w for w in re.sub(r"[/()]", " ", fn.lower()).split() if len(w) > 3]
        if any(f" {w} " in text for w in words):
            function_value, function_conf = fn, CONFIDENT
            break
    if not function_value:
        function_value, function_conf = cfg["functions"][0], ASSUMED
    out["function"] = (function_value, function_conf)

    # --- Data types ---
    matched_types = [dt for dt in cfg["data_types"] if dt in DATA_TYPE_KEYWORDS and _any_in(text, DATA_TYPE_KEYWORDS[dt])]
    out["data_types"] = (matched_types, CONFIDENT if matched_types else UNRESOLVED)

    # --- Model type ---
    model_value, model_conf = None, None
    for mt in MODEL_TYPES:
        if mt in MODEL_KEYWORDS and _any_in(text, MODEL_KEYWORDS[mt]):
            model_value, model_conf = mt, CONFIDENT
            break
    if not model_value:
        prior = FUNCTION_MODEL_PRIORS.get(function_value)
        if prior:
            model_value, model_conf = prior, ASSUMED
        else:
            model_value, model_conf = "Traditional ML / Statistical Model", ASSUMED
    out["model_type"] = (model_value, model_conf)

    # --- Autonomy ---
    autonomy_value, autonomy_conf = None, None
    for value, keywords in AUTONOMY_KEYWORDS:
        if _any_in(text, keywords):
            autonomy_value, autonomy_conf = value, CONFIDENT
            break
    if not autonomy_value:
        autonomy_value, autonomy_conf = "Human makes final decision, AI is one input", ASSUMED
    out["autonomy"] = (autonomy_value, autonomy_conf)

    # --- Jurisdictions (multi) ---
    matched_jurisdictions = [j for j, kws in JURISDICTION_KEYWORDS.items() if _any_in(text, kws)]
    if matched_jurisdictions:
        out["jurisdictions"] = (matched_jurisdictions, CONFIDENT)
    else:
        out["jurisdictions"] = (["Global/Unspecified"], ASSUMED)

    # --- Vulnerable population ---
    affects_vulnerable = _any_in(text, VULNERABLE_KEYWORDS)
    out["affects_vulnerable"] = (affects_vulnerable, CONFIDENT if affects_vulnerable else ASSUMED)
    if affects_vulnerable:
        groups = [g for g in cfg["vulnerable_groups"] if any(w.lower() in text for w in g.replace("/", " ").replace("(", " ").replace(")", " ").split() if len(w) > 3)]
        out["vulnerable_groups"] = (groups, CONFIDENT if groups else ASSUMED)
    else:
        out["vulnerable_groups"] = ([], ASSUMED)

    # --- Build ownership ---
    third_party_value, third_party_conf = None, None
    for value, keywords in THIRD_PARTY_KEYWORDS.items():
        if _any_in(text, keywords):
            third_party_value, third_party_conf = value, CONFIDENT
            break
    if not third_party_value:
        third_party_value, third_party_conf = "Built in-house", ASSUMED
    out["third_party"] = (third_party_value, third_party_conf)

    # --- Governance posture: conservative ("not yet in place") until the text
    # says otherwise, since that's the honest default for an unreviewed system
    # and it's what real due-diligence assumes absent evidence. ---
    if _any_in(text, ["continuous monitoring", "real-time monitoring", "ongoing monitoring"]):
        out["monitoring"] = ("Continuous automated monitoring", CONFIDENT)
    elif _any_in(text, ["periodic review", "regular audit", "manual audit"]):
        out["monitoring"] = ("Periodic manual audit", CONFIDENT)
    else:
        out["monitoring"] = ("No post-deployment monitoring", ASSUMED)

    if _any_in(text, ["shap", "lime", "case-level explanation", "explains each"]):
        out["explainability_method"] = ("Case-level explanation (e.g., SHAP/LIME)", CONFIDENT)
    elif _any_in(text, ["interpretable", "scorecard", "transparent model", "rules-based"]):
        out["explainability_method"] = ("Fully interpretable model (e.g., rules/scorecard)", CONFIDENT)
    elif _any_in(text, ["feature importance"]):
        out["explainability_method"] = ("Global feature importance only", CONFIDENT)
    else:
        out["explainability_method"] = ("None available", ASSUMED)

    # --- Regulated/consequential-decision flag: never auto-checked — this is
    # a legal-status question, only ever CONFIDENT if the user says so themselves. ---
    is_samd = _any_in(text, ["fda-cleared", "fda cleared", "ce-marked", "ce marked", "medical device", "aedt", "bias audit"])
    out["is_samd"] = (is_samd, CONFIDENT if is_samd else ASSUMED)

    return out


def summarize(detected):
    """Turns the raw detect() dict into the short, plain-English lines the
    'What we understood' panel shows — five essentials, not all twelve raw
    fields, and in everyday words rather than the form's own option text."""
    from src.plain_language import AUTONOMY_PLAIN, FUNCTION_PLAIN, MONITORING_PLAIN

    industry_value, industry_conf = detected["industry"]
    lines = []

    lines.append(("Industry", industry_value or "Not detected — please pick one below", industry_conf))

    function_value, function_conf = detected["function"]
    lines.append(("What it does", FUNCTION_PLAIN.get(function_value, function_value), function_conf))

    dtypes, dtypes_conf = detected["data_types"]
    lines.append(("Data it uses", ", ".join(dtypes) if dtypes else "Not detected — please select at least one", dtypes_conf))

    autonomy_value, autonomy_conf = detected["autonomy"]
    lines.append(("Who's in control", AUTONOMY_PLAIN.get(autonomy_value, autonomy_value), autonomy_conf))

    monitoring_value, monitoring_conf = detected["monitoring"]
    lines.append(("Ongoing checks", MONITORING_PLAIN.get(monitoring_value, monitoring_value), monitoring_conf))

    return lines
