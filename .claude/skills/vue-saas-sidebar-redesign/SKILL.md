---
name: vue-saas-sidebar-redesign
description: Redesign a Vue 3 application's top navigation bar into a modern SaaS-style vertical sidebar, with a collapsible icons-only mode for smaller screens. Use this skill when asked to modernize navigation, switch from a top nav to a sidebar layout, or make the app "feel like a professional SaaS product."
---

# Vue 3 SaaS Sidebar Redesign

This skill converts a Vue 3 app's horizontal top navigation into a vertical left sidebar with a polished, professional SaaS look, and makes that sidebar collapsible to an icons-only rail on smaller screens. It's written against this codebase's conventions but the underlying approach (layout shell change, no new dependencies, CSS-variable-driven collapse) generalizes to any Vue 3 app using a single top-level layout component.

**This is a layout/shell change, not a per-page change.** Only the top-level layout component (in this app, `client/src/App.vue`) needs restructuring — individual views (`client/src/views/*.vue`) are unaffected, since they render into the same `<router-view>` slot either way.

## When NOT to reach for this skill

- The app already has a sidebar — this skill is for a top-nav → sidebar conversion, not sidebar tweaks.
- The ask is about a single page's internal layout (that's ordinary Vue work, delegate directly to the project's frontend agent, e.g. `vue-expert` — not this skill).
- Adding a new nav *item* to an existing top nav — that's a one-line addition, not a redesign.

## Prerequisites to check before starting

1. **Confirm this is a Composition API codebase** (`export default { setup() {...} }`), not `<script setup>` or Options API. Match whatever pattern the existing layout component already uses — don't introduce a second style.
2. **Read the full existing layout component** (`App.vue` or equivalent) before changing anything: nav item list, any slot-based children (modals, filter bars, profile menus), and the full global `<style>` block, since a nav restructure often touches global layout CSS (`.app`, `.main-content`, etc.) that every page indirectly depends on.
3. **Identify the routing source of truth** (`main.js` route table, or a router file) so the sidebar's nav item list can be cross-checked against actual registered routes — a common bug is a sidebar item that doesn't match any route, or a route with no sidebar entry.
4. **Check i18n conventions** — nav labels almost always come from a translation function (`t('nav.x')` in this codebase); never hardcode nav item text even temporarily, and never introduce a new nav item without translation keys in *every* locale file.
5. **Check for a design system / token file or convention doc** (e.g. this project's `CLAUDE.md` "Design System" section) — reuse existing colors, spacing scale, and border-radius values. A sidebar redesign should look like it always belonged to the app, not like a new theme was dropped on top.

## Design decisions this skill makes

These are deliberate, opinionated defaults — deviate only if the user asks for something different:

- **Sidebar, not overlay drawer.** The sidebar occupies permanent horizontal space in the layout (a CSS grid/flex column) rather than floating over content, on viewports wide enough to afford it. This matches how most professional SaaS products (Linear, Vercel, Stripe dashboard, etc.) lay out primary nav.
- **Icons required for every nav item.** A collapsible icons-only mode is meaningless if items don't have distinct icons. If the app doesn't already have an icon set, use simple inline SVGs (no new npm dependency) — one per nav item, sized consistently (typically 20×20 or 24×24).
- **Collapse is user-toggleable, not purely viewport-driven.** Provide an explicit collapse/expand toggle button (usually pinned at the sidebar's top or bottom) so a user on a wide screen can still choose the compact rail if they prefer more content width. Additionally auto-collapse below a sensible breakpoint (see Responsive Behavior) as a sensible default, but let the manual toggle override that default per-session.
- **Persist the collapsed/expanded preference** across page navigations (module-level ref or `localStorage`, matching how this app already persists locale in `useI18n.js` / filters in `useFilters.js` — follow that same singleton-composable pattern, don't introduce Pinia/Vuex for one boolean).
- **No new npm dependencies.** No icon library, no UI kit, no CSS framework. Plain SVG icons, plain CSS (flexbox/grid + transitions), matching this app's existing "custom SVG, CSS Grid" convention.

## Implementation Steps

### 1. Extract nav items into a data structure

Before touching markup, turn the flat list of hardcoded `<router-link>` elements into an array of `{ path, labelKey, icon }` objects (a plain array literal or a small `computed()` if any item's visibility is conditional). This is what makes both the expanded and collapsed rendering share one `v-for` instead of duplicating markup, and makes it trivial to verify every item still matches a real route.

### 2. Restructure the layout shell

Change the top-level layout from:
```
header (top nav, full width)
main-content (below it)
```
to:
```
flex/grid row:
  aside (sidebar, fixed width, full viewport height, sticky/fixed position)
  column:
    header (slim top bar: page context, language switcher, profile menu — whatever
            lived in the old top nav besides the nav links themselves)
    main-content
```

Anything that lived in the old header *besides* the nav links (logo, language switcher, profile menu, notification bell, etc.) needs a new home: logo usually moves to the sidebar's top; user/profile/language controls usually move to a slim top bar that remains, or to the bottom of the sidebar. Decide based on what's already there — don't invent new chrome that wasn't in the original design.

### 3. Build the sidebar component

Prefer extracting the sidebar into its own component (e.g. `Sidebar.vue`) rather than inlining it in the layout file, if the layout file is already large — this keeps the collapse logic and nav-item rendering testable in isolation. Inline is fine if the layout file is small and this is the only structural element in it.

Sidebar must render:
- Logo/brand (full at expanded width, icon-only mark when collapsed — reuse existing brand assets, don't invent a new mark)
- Nav items as icon + label, from the array built in step 1 — label hidden (not just visually clipped, actually not rendered or `display:none`'d) when collapsed, so screen readers and hover states behave correctly
- Active-route highlighting equivalent to whatever the old top nav used (background tint, left accent bar, etc. — reuse the existing active-state visual language, just reoriented for a vertical list)
- The collapse/expand toggle button

### 4. Responsive behavior

- Define one breakpoint (reuse an existing one in the codebase if present; otherwise a sensible default like `768px` for a hard collapse-to-icons, matching common tablet/mobile boundaries).
- Below the breakpoint: sidebar defaults to collapsed icons-only rail automatically. The user's manual toggle still works on top of this default.
- Consider whether below a second, smaller breakpoint (phone width) the sidebar should become a fully hidden off-canvas drawer instead of a persistent icon rail — only add this complexity if the existing app already has other mobile-specific behavior to match; otherwise a simple two-state (expanded/icons-only) sidebar that never fully hides is usually sufficient and matches "consistent spacing, professional look" better than introducing a new drawer/overlay interaction pattern.
- Verify the collapse transition doesn't cause layout jank: animate `width` (or a CSS custom property driving `width`) with a `transition`, and ensure text labels fade/hide in sync rather than wrapping awkwardly mid-collapse.

### 5. Consistent spacing pass

Once the shell works, do a pass over spacing specifically (this was called out explicitly as part of "polished professional look," not just the nav mechanism):
- Confirm the sidebar's internal padding, icon-to-label gap, and item-to-item spacing use the same spacing scale as the rest of the app (check existing `padding`/`gap`/`margin` values in the design-system-relevant files rather than picking new numbers).
- Confirm the main content area's padding didn't shift unintentionally when the header lost the nav links (a slimmer top bar often needs revised height/padding to avoid an oversized empty-feeling strip).
- Check every existing page still has correct spacing against the new sidebar — a `max-width` centered layout that assumed full viewport width under a top nav often needs its container logic revisited once a permanent-width sidebar is introduced alongside it.

### 6. i18n

- Every nav label continues to go through the existing translation function — no hardcoded strings introduced or left over from the old nav.
- Add a translation key for the collapse/expand toggle's accessible label (e.g. `nav.collapseSidebar` / `nav.expandSidebar`) in every existing locale file, not just the default one.

## Verification checklist

After implementing, verify with the project's actual browser-testing tool (e.g. Playwright MCP tools in this codebase) rather than static code review alone:

1. Navigate through every route via the new sidebar — confirm active-state highlighting is correct on each.
2. Toggle collapse/expand manually — confirm labels hide/show correctly, icons remain visible and correctly aligned in both states, and the transition doesn't jank or cause a layout shift in the main content area.
3. Resize the viewport below the responsive breakpoint — confirm auto-collapse triggers, and that a manual expand still works on a narrow viewport (i.e. auto-collapse is a default, not a hard lock).
4. Switch language (if the app is i18n'd) — confirm every sidebar label, including the collapse toggle's label, translates with no leftover strings in the other locale.
5. Check `browser_console_messages` (or equivalent) for new errors/warnings introduced by the restructure.
6. Spot-check 2-3 existing pages for spacing regressions against the new shell, not just the sidebar itself.

## Handoff

This skill only produces a design + implementation approach — the actual `.vue` file edits still go through whatever this project's file-modification rules require (e.g. a mandatory frontend subagent like `vue-expert` per this repo's `CLAUDE.md`). Treat the steps above as the brief to hand to that subagent, not as something this skill executes directly.
