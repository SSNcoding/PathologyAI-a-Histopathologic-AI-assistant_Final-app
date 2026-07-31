"""Shared constants, enums, and design-token palettes."""

from enum import Enum


class AnalysisStatus(str, Enum):
    IDLE = "idle"
    PROCESSING = "processing"
    COMPLETE = "complete"
    ERROR = "error"


class ModelStatus(str, Enum):
    LOADED = "loaded"
    PLACEHOLDER = "placeholder"
    UNAVAILABLE = "unavailable"


class ModelArchitecture(str, Enum):
    """Backbones with real (untrained-by-default) constructors in models/architectures.py."""
    RESNET50 = "ResNet50"
    DENSENET121 = "DenseNet121"
    EFFICIENTNET_B0 = "EfficientNet-B0"
    CONVNEXT_TINY = "ConvNeXt-Tiny"
    VIT_B16 = "ViT-B/16"
    ENSEMBLE = "Ensemble (ResNet50 + EfficientNet-B0 + ViT-B/16)"
    HEURISTIC_CV = "Classical CV Heuristic (no trained weights)"


# ---------------------------------------------------------------------------
# Design tokens — CSS variables are generated from these in ui/theme.py so
# Python and CSS never drift out of sync.
# ---------------------------------------------------------------------------
THEME_DARK = {
    "bg_primary": "#0B1120",
    "bg_surface": "#111827",
    "bg_elevated": "#1E293B",
    "bg_glass": "rgba(30, 41, 59, 0.55)",
    "border": "rgba(148, 163, 184, 0.18)",
    "accent_cyan": "#06B6D4",
    "accent_blue": "#3B82F6",
    "accent_teal": "#14B8A6",
    "accent_purple": "#8B5CF6",
    "success": "#10B981",
    "warning": "#F59E0B",
    "danger": "#EF4444",
    "text_primary": "#F1F5F9",
    "text_muted": "#94A3B8",
    "shadow": "0 8px 32px rgba(0, 0, 0, 0.35)",
}

THEME_LIGHT = {
    "bg_primary": "#F4F8FB",
    "bg_surface": "#FFFFFF",
    "bg_elevated": "#FFFFFF",
    "bg_glass": "rgba(255, 255, 255, 0.55)",
    "border": "rgba(15, 23, 42, 0.10)",
    "accent_cyan": "#0891B2",
    "accent_blue": "#2563EB",
    "accent_teal": "#0D9488",
    "accent_purple": "#7C3AED",
    "success": "#059669",
    "warning": "#D97706",
    "danger": "#DC2626",
    "text_primary": "#0F172A",
    "text_muted": "#475569",
    "shadow": "0 8px 32px rgba(15, 23, 42, 0.08)",
}

# Named background presets, grouped by mode, for the sidebar "Background"
# picker (ui/theme.py: background_picker_control()). Each entry is a full
# palette dict with the same keys as THEME_DARK/THEME_LIGHT so it can drop
# straight into inject_theme_variables(). "Midnight" and "Cloud" are the
# original defaults and are the same dict objects as THEME_DARK/THEME_LIGHT
# (some modules, e.g. ui/charts.py, do an `is THEME_LIGHT` identity check).
THEME_PRESETS = {
    "dark": {
        "Midnight": THEME_DARK,
        "Charcoal": {
            "bg_primary": "#17181C",
            "bg_surface": "#202127",
            "bg_elevated": "#2A2B33",
            "bg_glass": "rgba(42, 43, 51, 0.55)",
            "border": "rgba(210, 210, 220, 0.14)",
            "accent_cyan": "#06B6D4",
            "accent_blue": "#3B82F6",
            "accent_teal": "#14B8A6",
            "accent_purple": "#8B5CF6",
            "success": "#10B981",
            "warning": "#F59E0B",
            "danger": "#EF4444",
            "text_primary": "#F5F5F7",
            "text_muted": "#A1A1AA",
            "shadow": "0 8px 32px rgba(0, 0, 0, 0.4)",
        },
        "Deep Teal": {
            "bg_primary": "#08191A",
            "bg_surface": "#0D2628",
            "bg_elevated": "#123436",
            "bg_glass": "rgba(18, 52, 54, 0.55)",
            "border": "rgba(45, 212, 191, 0.18)",
            "accent_cyan": "#2DD4BF",
            "accent_blue": "#38BDF8",
            "accent_teal": "#14B8A6",
            "accent_purple": "#A78BFA",
            "success": "#10B981",
            "warning": "#F59E0B",
            "danger": "#F87171",
            "text_primary": "#ECFEFF",
            "text_muted": "#8FC7C2",
            "shadow": "0 8px 32px rgba(0, 0, 0, 0.4)",
        },
        "Aubergine": {
            "bg_primary": "#170B23",
            "bg_surface": "#221331",
            "bg_elevated": "#2E1B42",
            "bg_glass": "rgba(46, 27, 66, 0.55)",
            "border": "rgba(196, 163, 255, 0.18)",
            "accent_cyan": "#22D3EE",
            "accent_blue": "#818CF8",
            "accent_teal": "#2DD4BF",
            "accent_purple": "#C084FC",
            "success": "#34D399",
            "warning": "#FBBF24",
            "danger": "#FB7185",
            "text_primary": "#F5F3FF",
            "text_muted": "#B8A9D9",
            "shadow": "0 8px 32px rgba(0, 0, 0, 0.45)",
        },
    },
    "light": {
        "Cloud": THEME_LIGHT,
        "Ivory": {
            "bg_primary": "#FBF7EE",
            "bg_surface": "#FFFFFF",
            "bg_elevated": "#FFFDF8",
            "bg_glass": "rgba(255, 253, 248, 0.6)",
            "border": "rgba(120, 100, 60, 0.12)",
            "accent_cyan": "#0891B2",
            "accent_blue": "#2563EB",
            "accent_teal": "#0D9488",
            "accent_purple": "#7C3AED",
            "success": "#059669",
            "warning": "#B45309",
            "danger": "#DC2626",
            "text_primary": "#2B2416",
            "text_muted": "#78716C",
            "shadow": "0 8px 32px rgba(120, 100, 60, 0.10)",
        },
        "Mint Frost": {
            "bg_primary": "#EFFBF8",
            "bg_surface": "#FFFFFF",
            "bg_elevated": "#F5FEFC",
            "bg_glass": "rgba(245, 254, 252, 0.6)",
            "border": "rgba(13, 148, 136, 0.14)",
            "accent_cyan": "#0891B2",
            "accent_blue": "#2563EB",
            "accent_teal": "#0D9488",
            "accent_purple": "#7C3AED",
            "success": "#059669",
            "warning": "#D97706",
            "danger": "#DC2626",
            "text_primary": "#0F2E2A",
            "text_muted": "#4B7B73",
            "shadow": "0 8px 32px rgba(13, 148, 136, 0.08)",
        },
    },
}

# Backwards-compat alias used by a few existing modules/charts.
COLORS = THEME_DARK

TISSUE_LABELS = [
    "Normal Epithelium",
    "Stroma",
    "Adipose",
    "Necrosis",
    "Inflammatory Infiltrate",
    "Suspected Neoplasia",
]

DIAGNOSIS_SEVERITY = {
    "low": {"color": THEME_DARK["success"], "label": "Low Risk"},
    "moderate": {"color": THEME_DARK["warning"], "label": "Moderate Risk"},
    "high": {"color": THEME_DARK["danger"], "label": "High Risk"},
}

# Primary navigation, grouped the way a hospital-facing product would present it.
# Order here also drives sidebar order in app_create.py; core/permissions.py
# decides which of these a given role actually sees.
NAV_PUBLIC = ["Home", "About", "Contact"]
NAV_AUTH = ["Login", "Register"]
NAV_APP = [
    "Dashboard",
    "Upload",
    "AI Analysis",
    "Results Dashboard",
    "Explainable AI",
    "Tissue Detection",
    "Cell Detection",
    "Statistics",
    "Scan Queue",
    "Slide Inventory",
    "Comparison",
    "Patient Report",
    "ROI Annotation",
    "Audit Log",
    "Profile",
    "Settings",
]

NAV_ICONS = {
    "Home": "house-door",
    "About": "info-circle",
    "Contact": "envelope",
    "Login": "box-arrow-in-right",
    "Register": "person-plus",
    "Dashboard": "speedometer2",
    "Upload": "cloud-upload",
    "AI Analysis": "cpu",
    "Results Dashboard": "clipboard2-pulse",
    "Explainable AI": "search",
    "Tissue Detection": "grid-3x3",
    "Cell Detection": "bullseye",
    "Statistics": "bar-chart-line",
    "Scan Queue": "hdd-network",
    "Slide Inventory": "upc-scan",
    "Comparison": "columns-gap",
    "Patient Report": "file-earmark-medical",
    "ROI Annotation": "bounding-box-circles",
    "Audit Log": "shield-check",
    "Profile": "person-circle",
    "Settings": "gear",
}

# Worklist / case-queue statuses (db/database.py: saved_analyses.status).
WORKLIST_STATUSES = ["pending", "in_review", "complete"]
WORKLIST_STATUS_LABELS = {
    "pending": "Pending Review",
    "in_review": "In Review",
    "complete": "Complete",
}
WORKLIST_STATUS_BADGE_KIND = {
    "pending": "warning",
    "in_review": "info",
    "complete": "success",
}

RESEARCH_ONLY_FEATURES = {
    "Cancer Staging": "Requires clinical/TNM data beyond a single image — shown as research preview only.",
    "Survival Risk Prediction": "Requires longitudinal clinical outcomes data — shown as research preview only.",
    "Biomarker Prediction": "Requires molecular/IHC ground truth for training — shown as research preview only.",
}

# The assistant's mascot identity — an owl, since it's meant to read as a
# knowledgeable second set of eyes rather than a generic chatbot. Used
# wherever the assistant renders a chat bubble (sidebar widget + the
# dedicated Assistant page) so the same "character" shows up consistently
# on every page, not just one tab.
MASCOT_NAME = "Hoot"
MASCOT_AVATAR = "\U0001F989"  # owl emoji
USER_AVATAR = "\U0001F9D1"  # person emoji, for the human side of the chat
