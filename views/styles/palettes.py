# ─────────────────────────────────────────────────────────────────────────────
# views/styles/palettes.py
#
# All colour tokens for the RetailPOS design system.
# Import individual names or the entire `PALETTE` dict – your choice.
# ─────────────────────────────────────────────────────────────────────────────

# ── Brand ──────────────────────────────────────────────────────────────────
PRIMARY           = "#4f46e5"   # indigo-600
PRIMARY_HOVER     = "#4338ca"   # indigo-700
PRIMARY_ACTIVE    = "#3730a3"   # indigo-800
PRIMARY_LIGHT     = "#ede9fe"   # indigo-100

# ── Semantic ───────────────────────────────────────────────────────────────
SUCCESS           = "#10b981"   # emerald-500
SUCCESS_BG        = "#d1fae5"   # emerald-100
SUCCESS_FG        = "#065f46"   # emerald-900

WARNING           = "#f59e0b"   # amber-400
WARNING_BG        = "#fef3c7"   # amber-100
WARNING_FG        = "#92400e"   # amber-900
WARNING_BORDER    = "#fde68a"   # amber-200

DANGER            = "#ef4444"   # red-500
DANGER_HOVER      = "#dc2626"   # red-600
DANGER_BG         = "#fee2e2"   # red-100
DANGER_FG         = "#991b1b"   # red-800
DANGER_BORDER     = "#fecaca"   # red-200

PINK              = "#ec4899"   # pink-500

# ── Neutral / surface ──────────────────────────────────────────────────────
BG_APP            = "#f8fafc"   # slate-50   – app background
BG_SURFACE        = "#ffffff"   # white       – card / panel
BG_MUTED          = "#f1f5f9"   # slate-100

BORDER            = "#e2e8f0"   # slate-200
BORDER_STRONG     = "#334155"   # slate-700

TEXT_PRIMARY      = "#0f172a"   # slate-950
TEXT_SECONDARY    = "#64748b"   # slate-500
TEXT_TERTIARY     = "#94a3b8"   # slate-400
TEXT_INVERSE      = "#f1f5f9"   # slate-100

# ── Sidebar ────────────────────────────────────────────────────────────────
SIDEBAR_BG        = "#1e293b"   # slate-800
SIDEBAR_HOVER     = "#334155"   # slate-700
SIDEBAR_ACTIVE    = PRIMARY
SIDEBAR_TEXT      = "#94a3b8"   # slate-400
SIDEBAR_TEXT_ACT  = "#ffffff"

# ── Tier colours ───────────────────────────────────────────────────────────
TIER_COLORS = {
    "Platinum": ("#7c3aed", "#ede9fe"),   # (fg, bg)
    "Gold":     ("#b45309", "#fef3c7"),
    "Silver":   ("#475569", "#f1f5f9"),
    "Bronze":   ("#92400e", "#fef3c7"),
}

# ── Scrollbar ──────────────────────────────────────────────────────────────
SCROLLBAR_TRACK  = "#f1f5f9"
SCROLLBAR_THUMB  = "#cbd5e1"

# ── Convenience dict (for any code that iterates tokens) ──────────────────
PALETTE = {
    "primary":        PRIMARY,
    "primary_hover":  PRIMARY_HOVER,
    "primary_active": PRIMARY_ACTIVE,
    "primary_light":  PRIMARY_LIGHT,
    "success":        SUCCESS,
    "success_bg":     SUCCESS_BG,
    "success_fg":     SUCCESS_FG,
    "warning":        WARNING,
    "warning_bg":     WARNING_BG,
    "warning_fg":     WARNING_FG,
    "danger":         DANGER,
    "danger_bg":      DANGER_BG,
    "danger_fg":      DANGER_FG,
    "bg_app":         BG_APP,
    "bg_surface":     BG_SURFACE,
    "bg_muted":       BG_MUTED,
    "border":         BORDER,
    "text_primary":   TEXT_PRIMARY,
    "text_secondary": TEXT_SECONDARY,
    "text_tertiary":  TEXT_TERTIARY,
    "sidebar_bg":     SIDEBAR_BG,
}


def tier_fg(tier: str) -> str:
    """Return foreground colour for a loyalty tier label."""
    return TIER_COLORS.get(tier, (PRIMARY, PRIMARY_LIGHT))[0]


def tier_bg(tier: str) -> str:
    """Return background colour for a loyalty tier label."""
    return TIER_COLORS.get(tier, (PRIMARY, PRIMARY_LIGHT))[1]
