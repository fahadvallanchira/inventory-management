---
name: saas-ui-redesign
description: Use when asked to redesign, restyle, or modernize a Vue 3 app's UI into a SaaS-style interface, move a top nav bar to a left vertical sidebar, or make cards, tables, and spacing look consistent and professional
---

# SaaS UI Redesign (Vue 3)

## Overview

Turn a basic top-nav Vue 3 app into a light, neutral SaaS interface: a fixed left sidebar, a soft gray canvas with white cards, one accent color, and spacing from a single scale. Every visual value comes from design tokens defined once.

## Design tokens (define once, in the app shell's global styles)

Put these as CSS variables on `:root` in the global stylesheet (here `client/src/App.vue`). Views and components use `var(--...)`, never hard-coded hex, px spacing, radii or shadows.

```css
:root {
  /* color */
  --bg: #f8fafc;            /* page canvas */
  --surface: #ffffff;       /* cards, sidebar */
  --border: #e2e8f0;
  --text: #0f172a;
  --text-muted: #64748b;
  --accent: #4f46e5;        /* the single accent: active nav, primary buttons, focus ring */
  --accent-soft: #eef2ff;   /* active nav background, hover tint */
  --success: #16a34a; --info: #2563eb; --warning: #d97706; --danger: #dc2626;
  /* spacing: 4px base, use only these */
  --space-1: 4px; --space-2: 8px; --space-3: 12px; --space-4: 16px;
  --space-6: 24px; --space-8: 32px;
  /* shape */
  --radius: 10px; --radius-sm: 6px;
  --shadow-sm: 0 1px 2px rgba(15, 23, 42, 0.06);
  --shadow-md: 0 4px 12px rgba(15, 23, 42, 0.08);
  /* layout */
  --sidebar-width: 240px; --sidebar-width-collapsed: 64px;
}
```

Keep the app's existing status colors (green/blue/yellow/red) by mapping them to the status tokens. Do not invent new colors.

## Layout

| Part | Spec |
|---|---|
| Shell | CSS Grid: `grid-template-columns: var(--sidebar-width) 1fr`; sidebar `position: sticky; top: 0; height: 100vh`; only the content column scrolls |
| Sidebar | `--surface` with a right `--border`. Top: logo/app name. Middle: nav items. Bottom: user/profile and language/settings controls moved out of the old top bar |
| Nav item | Icon (20px) + label, height 40px, `--radius-sm`, `--text-muted`. Hover: `--accent-soft`. Active (`router-link-exact-active` or the existing `$route.path` check): `--accent-soft` background, `--accent` text, 3px left accent bar |
| Content | `--bg` canvas, max-width 1400px, padding `--space-8`, sections spaced by `--space-6` |
| Page header | Title (24px/600) with muted subtitle on the left, page actions and filters on the right |
| Cards | `--surface`, 1px `--border`, `--radius`, `--shadow-sm`, padding `--space-6`; card header has title (16px/600) and optional actions; hover elevation only on clickable cards |
| Stat cards | Muted 13px label, 28px/600 value, status shown by a small colored badge, not a colored card background |
| Tables | No vertical borders; 12px uppercase muted header row on `--bg`; row height 48px; row hover `--accent-soft`; numbers right-aligned |
| Buttons | Primary: `--accent` fill, white text. Secondary: `--surface` with `--border`. Height 36px, `--radius-sm`; visible `:focus-visible` ring in `--accent` |
| Typography | System UI font stack; sizes 12/13/14/16/24 only; weights 400/500/600 |

### Placement and color rules

- **Filters and toolbars:** if views own their page headers, put global filters in a sticky toolbar at the top of the content column rather than editing every header.
- **Footer dropdowns:** profile and language menus in the sidebar footer open upward (or to the right when the sidebar is collapsed) so they are never clipped.
- **Status tints:** add `--success-soft`, `--info-soft`, `--warning-soft`, `--danger-soft` for badge backgrounds.
- **Accent vs data colors:** `--accent` is for UI chrome (active nav, focus rings, primary buttons). The app's existing blue data/chart/interactive colors map to `--info` so charts do not shift.
- **Legacy values:** map existing rem/px spacing and radii to the nearest token (0.25rem=`--space-1`, 0.5rem=`--space-2`, 0.75rem=`--space-3`, 1rem=`--space-4`, 1.5rem=`--space-6`, 2rem=`--space-8`).
- **Modals:** backdrop `rgba(15, 23, 42, 0.45)`, panel uses the card spec with `--shadow-md`, and a z-index above the sidebar.
- **Responsive:** define a collapsed icons-only sidebar rail (`--sidebar-width-collapsed`) for narrow screens; content must scroll inside its containers, never the page horizontally.

## Icons

Use inline SVG, no icon dependency and no emoji. Create one small component (e.g. `components/NavIcon.vue`) that takes a `name` prop and renders a 24x24 viewBox SVG with `fill="none" stroke="currentColor" stroke-width="1.75" stroke-linecap="round" stroke-linejoin="round"`. Keep the path data in one object keyed by name, one icon per nav destination. Color comes from `currentColor` so active/hover states need no extra work.

## Process

1. Read the app shell (`App.vue`), router, and every view's `<style>` block. List hard-coded colors and sizes that the tokens should replace.
2. Add the tokens, then rebuild the shell: replace the top nav with the sidebar, keeping the same routes, labels (through the app's i18n `t()`), and active-state logic.
3. Restyle the shared classes in the global stylesheet first (`.card`, `.stat-card`, `.badge`, `.table-container`, `.page-header`, buttons, inputs) so views inherit the look. Touch a view's scoped CSS only to swap hard-coded values for tokens.
4. Move controls that lived in the top bar (filters, profile, language) to their new home; do not leave an empty header strip.
5. Run the production build and fix errors.

## Common mistakes

| Mistake | Fix |
|---|---|
| Hex values and px spacing sprinkled through views | Replace with tokens; add a token only if the scale truly lacks the value |
| Several accent colors | One `--accent`; status colors are for status only |
| Page scrolls the sidebar away | Sidebar sticky at 100vh, content column scrolls |
| Active nav shown only by color | Add the left accent bar and background tint |
| Icon font or emoji for icons | Inline SVG with `currentColor` |
| Cards with mixed padding and radii | Always `--space-6` and `--radius` |
