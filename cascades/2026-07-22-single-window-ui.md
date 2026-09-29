# Cascade: Single-Window / Sidebar UI

**Created:** 2026-07-22
**Goal:** Turn the Image Toolkit Hub into one window with a left sidebar (Sort / Rank / Auto / Export / Config) that swaps content panels, instead of the current card-grid Hub that launches a **subprocess** grid sorter and stacks modal-on-modal dialogs.
**Theme:** Keep the existing dark charcoal theme (`ui_theme.py`). No new palette.

## Decisions locked
- Single-window/sidebar architecture (user-selected mockup).
- Dark charcoal theme retained.

## Current state (measured 2026-07-22)
- `app_hub.py` → `ImageToolkitHub(tk.Tk)` (1682 lines). Header + two-column content (tool cards left, folder/settings panels right). `launch_grid_sorter()` does `subprocess.Popen([sys.executable, 'image_sorter_enhanced.py'])`, `withdraw()`s the hub, polls `check_closed()`, then `reload_config_from_disk()` + `deiconify()`.
- `image_sorter_enhanced.py` → `ImageSorter(tk.Tk)` (2459 lines). Its own root + `mainloop`. Root coupling: 3× `self.title()` (status), `self.state('zoomed')` + `self.attributes('-fullscreen')` + F11 toggle, **17× `self.bind()`** (1/2/3/space/r/R/Esc/F11/Ctrl-A/Ctrl-T/Ctrl-Z/Ctrl-Shift-Z + Button-1..5), `self.destroy()` on finish. **No `self.protocol()` handler** (simplifies embedding). Standalone `__main__` launch block at line 2400.
- Other tools: Ranker = `ImageRankerDialog` (Toplevel); Auto-sort runs in-process with progress dialog; Export/Visual/Trash/TermManager/AutoTag = modal dialogs.

## Risks & safeguards
- **Phase B is the hard part**: `ImageSorter` deeply assumes it is the root. Mitigate by (a) keeping a standalone `__main__` entry that wraps the frame in a throwaway `tk.Tk` (preserves `python image_sorter_enhanced.py` + tests), and (b) testing after each sub-step.
- **Keyboard scope**: root binds fire regardless of visible panel. Fix: panel `activate()`/`deactivate()` register/unregister binds on the hub root so keys only act on the active mode.
- **Single-process memory**: subprocess currently isolates the sorter's large-image memory. Embedding shares the Hub process — keep the existing post-grid `gc.collect()`; watch memory on big collections.
- Each phase ends in plan mode with the next phase loaded (per workflow). `EnterPlanMode` gate before each phase's code.

---

## Phase A — Single-window shell + prove the panel pattern  ✅ DONE (2026-07-23)
Files: `app_hub.py`
Implemented:
- New `SidebarButton` class (app_hub.py, after `ToolCard`): accent left-border when active, hover states.
- `setup_ui()` rebuilt into `outer > body(sidebar | content | rail) + status bar`.
  - `_build_sidebar()`: title + nav Home/Sort/Rank/Auto/Export/Config. Home & Config are panel
    entries (tracked in `self.sidebar_buttons`); Sort/Rank/Auto/Export call the existing launchers.
  - `self.content` container + `self.panels` dict + `show_panel(name)` (pack/pack_forget, updates
    sidebar active state).
  - `_build_status_bar()` + `set_status(text)` (updates `self.status_label`).
  - Right rail (`rail`, 340px): `SourceFolderPanel` + `OutputFolderPanel`, persistent.
  - `_build_home_panel()`: the scrollable tool-card grid (all tools) + workflow footer tip.
  - `_build_config_panel()`: relocated `create_settings_panel()` + Term Manager link.
- `create_settings_panel()` unchanged; now hosted in the Config panel instead of the right rail.
- `launch_grid_sorter` still subprocess (unchanged) — Phase B replaces it.
Verified: headless smoke test (withdrawn window, state/deiconify neutralized) — panels registered,
show_panel switches + toggles active state, rail + status bar + settings vars all wired, no exceptions
through `update_idletasks()`.
⚠️ USER visual check pending: `python app_hub.py` → confirm 3 columns render, sidebar switches
Home/Config, folder rail + settings work, Sort/Rank/Auto/Export launchers still function.
⚠️ NEXT: Phase B — embed the grid sorter as a panel.

## Phase B — Embed the grid sorter as a panel  ✅ DONE (2026-07-23)
Files: `image_sorter_enhanced.py` (major), `app_hub.py` (wire Sort panel)
Implemented in `image_sorter_enhanced.py`:
- `ImageSorter(tk.Tk)` → `tk.Frame`; `__init__(self, parent, hub, folder, num_rows, random_order,
  copy_instead_of_move)`, `super().__init__(parent)`, `self.hub`, `self._sizing_done`,
  `self._check_bg_after_id`, `self._key_bindings`.
- Window-op helpers: `_update_title()` (hub.set_status embedded / toplevel.title standalone),
  `_is_fullscreen()` (True only standalone+fullscreen). Replaced 3× `self.title`, all
  `self.attributes('-fullscreen')` reads, `toggle_fullscreen()` (no-op when embedded).
- Lazy grid sizing: `setup_ui()` sets placeholder dims + binds `<Configure>`; `_on_frame_configure()`
  + `_perform_sizing()` compute `screen_width/height`/`row_height` from real allocated size (or screen
  when standalone-fullscreen) then run the deferred `load_initial_images()` / `show_welcome_message()`.
- `activate()` / `deactivate()`: keyboard binds on the toplevel, mouse Button-1..5 on the canvas,
  menubar attach/detach (`setup_menu()` builds against toplevel but does NOT attach), focus set,
  and background-loading `after()` cancel + `background_loading=False` on deactivate.
- `_exit()`: embedded → `hub.close_sort_panel()`; standalone → destroy toplevel. Replaced the two
  `self.destroy()` (Exit menu + `perform_action('exit')`).
- Dialog parents routed to `self.winfo_toplevel()` (tag-db Toplevel + import/export filedialogs).
- `__main__` wraps the frame in a throwaway fullscreen `tk.Tk`, `pack` + `activate()` + `mainloop`.
Implemented in `app_hub.py`:
- `import gc`. Sort sidebar entry + Home "Manual Grid Sorter" card → `open_sort_panel`.
- `open_sort_panel()` builds a FRESH `ImageSorter(self.content, self, folder, ...)` from
  `get_basic_settings()` / active sources, registers `panels['sort']`, `show_panel('sort')`,
  `sorter.activate()`.
- `close_sort_panel()` → `show_panel('home')`; `_close_sort_panel_internal()` deactivates + destroys
  the frame, drops it from `panels`, `reload_config_from_disk()`, `gc.collect()`.
- `show_panel()` generalized: switching away from a live `'sort'` panel tears it down first.
- `launch_grid_sorter()` kept as a thin alias → `open_sort_panel()`.
Verified (headless, withdrawn roots — no focus grab):
- Embedded lifecycle: open → **loaded 24 real images at 94.7% grid fill** → switch away tears down →
  reopen builds a fresh instance → `close_sort_panel` returns Home. Menubar attach/detach, sidebar
  active state, key-binding scope all correct.
- Sizing math: 1600×900 → row_height (900-120)//3 = 260, welcome fired once, idempotent, width≤1 ignored.
- Standalone (`hub=None`): title routes to toplevel, `toggle_fullscreen` flips root attr, `_exit`
  destroys toplevel. Syntax OK; `import image_sorter_enhanced`/`app_hub` clean.
⚠️ USER visual check pending: `python app_hub.py` → Sort renders in-window, sort via keys AND mouse,
  clicking sidebar/rail does NOT sort, switch to Config/Home and back (fresh grid) with no console
  TclError; `python image_sorter_enhanced.py` standalone still opens fullscreen and works.
⚠️ NEXT: Phase C — migrate remaining modes + polish.

## Phase C — Migrate remaining modes, unify state, polish
Files: `image_ranker_dialog.py`, `app_hub.py`, dialog files, docs
1. Rank (`ImageRankerDialog`) → Rank panel. Auto-sort → Auto panel (reuse in-process runner). Batch export → Export panel.
2. Rarely-used tools (Visual sort, Trash cleanup, Term manager, Auto-tag) stay modal but launch from a **Tools** menu/section, themed consistently.
3. Unify: shared status bar shows counts/progress per mode; global shortcuts routed by active panel.
4. Visual polish: sidebar active state, consistent card/section spacing, typography.
5. Update `docs/UI_REDESIGN_PLAN.md` (Phase 3 status) and `CLAUDE.md`.
⚠️ NEXT: done — full single-window app.
