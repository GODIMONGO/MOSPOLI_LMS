# A04 Design System Foundations

## Scope
- Role: `A04 Design System Foundations`.
- Sources used: `info.md` section `8` (baseline UI rules), `16.1` (architecture constraints), `21` (textual visual references).
- Stack constraint respected: CSS-only foundations for Flask + Jinja templates. No framework introduced.

## Artifacts
- `static/design/tokens.css`
- `static/design/typography.css`

## Foundations Summary

### Colors
- Page and surface tokens align with the light pastel direction from section 21.
- Semantic content tokens included for course card types:
  - `--ds-color-semantic-info` (green)
  - `--ds-color-semantic-task` (lilac)
  - `--ds-color-semantic-video` (pink)
  - `--ds-color-semantic-test` (cyan)
- Status sets included for success/warning/info/danger states.

### Type
- Local Montserrat loaded via `@font-face` from `static/fonts/Montserrat/*`.
- Base scale includes section 8 targets: `12/14/16/20/36` plus bridge sizes used in current UI (`24/32`).
- Semantic text-style tokens added: display/title/body/caption/button.

### Spacing, Radius, Effects
- 8px spacing baseline (`--ds-space-1`..`--ds-space-8`).
- Radius scale matches section 8 guidance (10-20px).
- Shadow and focus-ring tokens unify existing visual effects.

## Migration Plan By File

### Step 0 (integration wiring by merge owner)
- In base templates, add style includes before feature CSS:
  1. `static/design/tokens.css`
  2. `static/design/typography.css`
- Keep existing CSS loaded after foundations to avoid regressions during first pass.

### `static/courses/courses.css`
1. Replace hardcoded accent and neutrals with tokens:
- `#002fff` -> `var(--ds-color-accent-strong)`
- `#6D9DEC` -> `var(--ds-color-accent-primary)`
- `#ccc` / `#e0e0e0` -> border tokens
2. Replace spacing and radius constants:
- `10px`, `2rem`, `1.5rem`, `2rem radius` -> `--ds-space-*` and `--ds-radius-*`
3. Replace typography family declarations with `var(--ds-font-family-base)` + semantic size/weight tokens.

### `static/my_curse/my_curse.css`
1. Map backgrounds/surfaces to tokens:
- `#fff`, `#F5F5F5`, `#F9F9FF`, `#EEEEEE` -> surface/background tokens
2. Normalize card/sidebar radii (`12px`, `20px`, `10px`) to radius scale tokens.
3. Replace text colors (`#4b5563`, `#6D6D6D`, `#6D9DEC`) with text/accent tokens.
4. Replace shadows/focus visuals with shared `--ds-shadow-*` and `--ds-focus-ring`.

### `static/my_curse/my_curse_block.css`
1. Replace semantic block colors:
- `#E9FAF0` and `#106C3F` -> semantic info + readable foreground tokens.
- `#654285` -> accent-violet token.
2. Convert typography blocks to semantic type tokens (title/body/caption).
3. Normalize radii (`15px`, `4px`, `3px`) to foundation scale.
4. Replace ad-hoc shadow/focus values with foundation tokens.

### `static/input_file/input_file.css`
1. Keep existing variable names for first pass, but map their values to foundation aliases.
2. In second pass, replace local vars with direct `--ds-*` references.
3. Consolidate repeated status chips (`success/info/danger`) to status token palette.
4. Normalize modal/card/button radii and shadows to foundation radius/shadow tokens.

## Suggested Migration Sequence
1. `static/input_file/input_file.css` (already variable-driven, lowest migration risk).
2. `static/courses/courses.css` (compact file, fast wins).
3. `static/my_curse/my_curse.css`.
4. `static/my_curse/my_curse_block.css` (highest semantic density).

## Impact Statement
- Files touched:
  - `static/design/tokens.css`
  - `static/design/typography.css`
  - `docs/agents/A04_foundations.md`
- Contracts not touched:
  - `routes/*`
  - `templates/*`
  - `static/*` feature styles (read-only in this task)
  - Any JS behavior/API schema
