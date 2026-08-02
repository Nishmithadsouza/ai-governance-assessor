"""Single source of truth for every structured intake field's allowed values.
Used by the New Assessment form AND must stay in sync with the `condition`
values used in data/criteria.json — the rule engine only ever matches on
these exact strings.

Fields that genuinely differ by industry (what an AI system *does*, what data
it touches, who it can affect) live in INDUSTRY_CONFIG, keyed by industry.
Fields that describe an AI system's build/operation the same way regardless
of domain (autonomy, model type, monitoring, jurisdiction, ...) are shared
globals below — adding a new industry only means adding one INDUSTRY_CONFIG
entry, not rebuilding the whole form."""

# Industries with a full curated corpus: their own real, dated sources and their
# own rule set (see data/criteria.json, data/sources.json). This is the "deep"
# tier.
INDUSTRIES = ["Healthcare & Life Sciences", "HR / Recruitment & Hiring"]

# Convenience presets for common verticals that don't (yet) have a dedicated
# curated corpus. Picking one of these — or typing a brand new name entirely —
# runs the use case through GENERIC_CONFIG's intake vocabulary and the
# "Generic / Cross-Industry Baseline" rule set (data/criteria.json entries
# tagged with that industry), which is itself real and cited (NIST AI RMF,
# ISO/IEC 42001, OECD AI Principles, the UNESCO AI Ethics Recommendation, the
# EU AI Act, and Colorado's AI Act — all written to apply across sectors).
# This is what satisfies "construct a different analysis rather than relying
# entirely on hard-coded data": an industry nobody wrote code for today still
# gets a real, deterministic, cited assessment tonight.
PRESET_INDUSTRIES = [
    "Financial Services / Lending",
    "Insurance",
    "Retail / E-commerce",
    "Education / EdTech",
    "Criminal Justice / Public Safety",
    "Transportation / Autonomous Vehicles",
    "Manufacturing / Industrial",
    "Real Estate / Housing",
    "Media / Content Moderation",
    "Telecommunications",
]

OTHER_INDUSTRY_OPTION = "Other (type your own industry)"

GENERIC_INDUSTRY_KEY = "Generic / Cross-Industry Baseline"

GENERIC_CONFIG = {
    "icon": "🌐",
    "functions": [
        "Automated Decision-Making (Consequential)",
        "Prediction / Risk Scoring",
        "Classification / Categorization",
        "Recommendation / Ranking",
        "Content Generation",
        "Chatbot / Conversational Agent",
        "Process Automation (Non-consequential)",
        "Research / Analytics",
    ],
    "data_types": [
        "Personal/Identifying Data",
        "Sensitive/Special-Category Data (health, biometric, genetic, etc.)",
        "Financial Data",
        "Behavioral/Usage Data",
        "Public/Non-sensitive Data",
        "De-identified Data",
        "Synthetic Data",
    ],
    "vulnerable_groups": [
        "Racial/Ethnic Minorities",
        "Women",
        "Elderly",
        "Children/Minors",
        "Disabled Individuals",
        "Low-Income Individuals",
        "Non-Native Language Speakers",
        "Other Protected Class",
    ],
    "regulated_flag_label": (
        "Deployed in a way that makes or substantially assists a legally 'consequential decision' "
        "about an individual (e.g. access to housing, employment, credit, healthcare, education, "
        "insurance, or government services)"
    ),
}


def get_industry_config(industry):
    """Curated industries get their own INDUSTRY_CONFIG entry; anything else
    (a preset not yet curated, or a freely typed name) gets the generic,
    still-real, still-cited baseline vocabulary."""
    return INDUSTRY_CONFIG.get(industry, GENERIC_CONFIG)


def resolve_rule_profile(industry):
    """Which row of `criteria.industry` to score against. Curated industries
    use their own rules; everything else falls back to the generic baseline —
    this is the one place that decides "deep corpus" vs "constructed on the
    fly" and every caller (scoring, narrative, display) goes through it."""
    return industry if industry in INDUSTRIES else GENERIC_INDUSTRY_KEY


def is_curated(industry):
    return industry in INDUSTRIES


INDUSTRY_CONFIG = {
    "Healthcare & Life Sciences": {
        "icon": "🩺",
        "functions": [
            "Diagnosis / Clinical Decision Support",
            "Treatment Recommendation",
            "Patient Triage",
            "Risk Scoring / Population Health Prediction",
            "Medical Imaging Analysis",
            "Patient-Facing Chatbot / Virtual Assistant",
            "Claims / Prior-Authorization Decisioning",
            "Administrative Scheduling / Staffing",
            "Drug Discovery / Research",
        ],
        "data_types": [
            "PHI/ePHI",
            "Genomic Data",
            "Biometric Data",
            "Claims/Billing Data",
            "De-identified Data",
            "Synthetic Data",
            "Operational/Non-clinical Data",
        ],
        "vulnerable_groups": [
            "Racial/Ethnic Minorities",
            "Elderly",
            "Children",
            "Low-Income/Uninsured",
            "Disabled Patients",
            "Non-English Speakers",
        ],
        "regulated_flag_label": "Regulated as a medical device (SaMD) — e.g. FDA-cleared / CE-marked",
    },
    "HR / Recruitment & Hiring": {
        "icon": "🧑‍💼",
        "functions": [
            "Resume Screening / Candidate Ranking",
            "Video Interview Analysis",
            "Candidate Sourcing / Outreach",
            "Skills Assessment / Testing",
            "Interview Scheduling (Administrative)",
            "Promotion / Performance-Based Decisioning",
            "Termination / Layoff Risk Scoring",
        ],
        "data_types": [
            "Resume/CV Data",
            "Video/Audio Interview Data",
            "Biometric Data (facial/voice analysis)",
            "Demographic/EEO Data",
            "Performance Review Data",
            "Operational/Administrative Data",
            "De-identified Data",
            "Synthetic Data",
        ],
        "vulnerable_groups": [
            "Racial/Ethnic Minorities",
            "Women",
            "Older Workers (40+)",
            "Disabled Candidates",
            "Non-Native English Speakers",
            "Veterans",
        ],
        "regulated_flag_label": "Legally classified as an Automated Employment Decision Tool (AEDT) subject to a mandatory bias audit — e.g. NYC Local Law 144",
    },
}

# Shared across every industry — how a system is built and operated doesn't
# depend on what domain it's deployed in.
AUTONOMY_OPTIONS = [
    "Fully autonomous - no human review",
    "Human-in-the-loop (advisory, human must act)",
    "Human-on-the-loop (human can override)",
    "Human makes final decision, AI is one input",
]

JURISDICTIONS = [
    "European Union",
    "United States - Federal",
    "United States - Colorado",
    "United States - New York City",
    "United States - Illinois",
    "United States - Other State",
    "Global/Unspecified",
]

MODEL_TYPES = [
    "Traditional ML / Statistical Model",
    "Deep Learning (black-box)",
    "Generative AI / LLM",
    "Rule-based / Expert System",
]

THIRD_PARTY_OPTIONS = [
    "Built in-house",
    "Licensed third-party/vendor product",
    "Hybrid (vendor model, in-house integration)",
]

MONITORING_OPTIONS = [
    "No post-deployment monitoring",
    "Periodic manual audit",
    "Continuous automated monitoring",
]

EXPLAINABILITY_OPTIONS = [
    "None available",
    "Global feature importance only",
    "Case-level explanation (e.g., SHAP/LIME)",
    "Fully interpretable model (e.g., rules/scorecard)",
]

SOURCE_TYPES = [
    "Law/Regulation",
    "Regulatory Guidance",
    "Industry Standard",
    "Research",
    "Vendor Information",
    "General Web Content",
]

# Fixed categorical order (never cycled/reassigned) — one slot per required
# source type, taken from the validated 8-hue categorical palette.
SOURCE_TYPE_COLORS = {
    "Law/Regulation": "#2a78d6",
    "Regulatory Guidance": "#eb6834",
    "Industry Standard": "#1baf7a",
    "Research": "#eda100",
    "Vendor Information": "#e87ba4",
    "General Web Content": "#008300",
}

# Fixed status palette (never themed) — same hex in light and dark, both clear
# 3:1 against their respective chart surfaces. Never shown as color alone —
# always paired with the icon + level word.
LEVEL_COLORS = {
    "Low": "#0ca30c",
    "Medium": "#fab219",
    "High": "#ec835a",
    "Critical": "#d03b3b",
}

LEVEL_ICONS = {
    "Low": "🟢",
    "Medium": "🟡",
    "High": "🟠",
    "Critical": "🔴",
}


def level_badge(level):
    return f"{LEVEL_ICONS.get(level, '⚪')} {level}"
