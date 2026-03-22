# UI Design System & Coherence Verification

## Design Tokens

| Token | Value | Usage |
|-------|-------|-------|
| `bg` | #f5f6f8 | Page background |
| `surface` | #ffffff | Card/panel background |
| `accent` | #0d9488 | Primary accent (teal), buttons, selected tab |
| `border` | #e2e8f0 | Dividers, card outlines |
| `alert_bg` | #fef3c7 | Alerts tab (amber tint) |
| `success` | #10b981 | Positive feedback |
| `error` | #ef4444 | Error feedback |
| `text` | #1e293b | Primary text |
| `PAD_SM/MD/LG/XL` | 4/8/12/16px | Consistent spacing |
| `FONT_FAMILY` | Helvetica | Typography |
| `FONT_SIZE` | 11 | Base size |

## Coherence Verification Checklist

| Criterion | Summary Tab | Add Tab | Transactions Tab | Alerts Tab | Portfolio Tab | Status |
|-----------|-------------|---------|------------------|------------|---------------|--------|
| Card-style container with border | Yes | Yes | Yes (filter + tree) | Yes | Yes (inputs + output) | Pass |
| Same padding (PAD_LG) on frame | Yes | Yes | Yes | Yes | Yes | Pass |
| Same accent color on buttons | Yes | Yes | Yes | Yes | Yes | Pass |
| Same surface/bg hierarchy | Yes | Yes | Yes | Yes | Yes | Pass |
| ttk.Separator between sections | Yes | Yes | Yes | Yes | Yes | Pass |
| Font consistency (FONT_FAMILY, FONT_SIZE) | Yes | Yes | Yes | Yes | Yes | Pass |
| highlightbackground=COLORS["border"] on cards | Yes | Yes | Yes | Yes | Yes | Pass |

## Semantic Variations (Intentional)

- **Alerts tab**: Uses `alert_bg` (#fef3c7) instead of `surface` to signal attention/warning context.
- **Header**: Accent bar (4px) for brand/primary action emphasis.
- **Tab selection**: Selected tab uses accent foreground for consistency.

## Verification Result

All tabs use the same design tokens (COLORS, PAD_*, FONT_*), card pattern (tk.Frame with highlightbackground, surface bg), and separator pattern. Buttons share the accent style. The Alerts tab intentionally uses a softer background for semantic distinction while remaining within the palette. **Design coherence: verified.**
