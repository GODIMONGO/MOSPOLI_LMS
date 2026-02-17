# A13 Mobile Adaptation

Sources used: `info.md` sections `5.5`, `16.1`, `21` (with focus on `21.10 Image #9` mobile behavior).

## Scope
- Ownership-only output:
  - `static/my_curse/mobile.css`
  - `static/courses/mobile.css`
  - `static/input_file/mobile.css`
  - `docs/agents/A13_mobile.md`
- No edits in `templates/*` and `routes/*` per architecture constraints from `16.1`.

## Breakpoint Plan
1. `<= 900px`: switch dense desktop layouts to single-column or wrapped controls.
2. `<= 720px`/`<= 640px`: reduce spacing and typography to avoid horizontal overflow.
3. `<= 480px`/`<= 420px`: compact mode for narrow phones, preserve tap targets.

## Media Query Changes by File

### `static/my_curse/mobile.css`
- `<= 900px`:
  - `app-shell` becomes vertical (`sidebar` above content).
  - `sidebar-nav` becomes horizontal-scroll rail.
  - `overview-header` switches to one-column flow.
  - `curse-block` spacing compacted for long mobile feed.
  - `item-link` allows multi-line clamped text to protect readability.
  - tap zones set to >= `40x40` for:
    - `.custom-checkbox span`
    - `.cross`
    - `.pill-close`
  - expanded card meta (`.task-card-meta`) stacks vertically.
- `<= 640px`:
  - smaller nav card width and title sizes.
- `<= 420px`:
  - tighter inner paddings and slightly smaller tap controls (`38x38`) for very narrow devices.

### `static/courses/mobile.css`
- `<= 720px`:
  - hero/search compacted.
  - header (`All sections` + page title) stacked for smaller width.
  - `course-row` keeps readable two-line/three-line naming and full-width right metrics block.
  - row and reset-button tap comfort reinforced (min `40px`/`56px` scale).
- `<= 480px`:
  - reduced icon/input sizes and wrapped right-side course metrics.

### `static/input_file/mobile.css`
- `<= 900px`:
  - toolbar wraps, buttons expanded to `40x40`.
  - path block becomes vertical.
  - upload queue and file items become vertical cards.
  - file action buttons keep min `40px` touch height.
  - modal actions stack to full-width mobile buttons.
- `<= 420px`:
  - extra compact side paddings and balanced toolbar groups.

## Overflow Risks Covered
- Long course names: increased line clamps and wrapping on mobile contexts.
- Long file names/paths: `overflow-wrap: anywhere`.
- Dense action groups: wrapped/stacked layouts for toolbar, queue, file actions.
- Dense card controls: checkbox/toggle areas enlarged for touch.

## Integration Note
- `mobile.css` files were added only inside ownership scope.
- Because `templates/*` were intentionally not changed, CSS linking/import must be handled separately if not already wired by the integration layer.

## Touched Files
- `static/my_curse/mobile.css`
- `static/courses/mobile.css`
- `static/input_file/mobile.css`
- `docs/agents/A13_mobile.md`

## Contracts Not Touched
- `templates/*`
- `routes/*`
- `main.py` route contracts
- existing desktop CSS files (`static/*/*.css`) outside ownership scope
