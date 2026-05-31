# Styling convention — CSS Modules (default)

Written into the new project's CLAUDE.md `## Conventions` (or `.claude/rules/styling.md`) when the user picks **CSS Modules** at Step 4. CSS Modules is the scaffold's default styling approach.

## What to scaffold

- Pass `--no-tailwind` to `create-next-app`. Do **not** install shadcn/ui.
- Co-locate a `*.module.css` next to each component (`Foo.tsx` → `Foo.module.css`).
- `create-next-app --no-tailwind` already ships `src/app/page.module.css` + global `src/app/globals.css` — keep that pattern as the reference shape.

## Convention text (drop into CLAUDE.md `## Conventions`)

> **Styling: CSS Modules.** Each component gets a co-located `*.module.css` file; import it as `styles` and reference `className={styles.foo}`. No inline `style={{...}}` for anything beyond truly dynamic values (computed positions, etc.). No Tailwind utility classes. Define design tokens as CSS custom properties scoped to a component-root class (mirror `src/app/page.module.css`); put genuinely global tokens/resets in `src/app/globals.css`.

## Why CSS Modules is the default

- Scoped by default — no global class collisions, no naming-convention discipline (BEM etc.) needed.
- Zero extra dependencies — it's built into Next.js.
- Plain CSS knowledge transfers directly; nothing framework-specific to learn.

## Other choices (Step 4 offers these too)

- **plain CSS** — one global stylesheet. Simplest; fine for tiny projects. Same `--no-tailwind`, no shadcn.
- **Tailwind** — utility-first. Available for users who prefer it; omit `--no-tailwind`. Never the scaffold's default or recommended pick.
- **Tailwind + shadcn/ui** — Tailwind plus prebuilt components; run shadcn init after `create-next-app`.

When the user picks a non-CSS-Modules option, generate that stack's idiomatic setup instead and skip the CSS-Modules convention text above.
