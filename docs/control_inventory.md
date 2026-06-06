# WaveToy Control Inventory — Task 101

This inventory classifies major visible controls by user function. It is intentionally focused on review/planning and does not move controls.

Visibility levels:

- `always_visible`
- `contextual`
- `advanced_collapsed`
- `menu_only`

Categories:

- `navigation`
- `primary_action`
- `secondary_action`
- `transport`
- `source_assignment`
- `timing_control`
- `expression_control`
- `destructive_action`
- `import_export`
- `diagnostic`
- `advanced_debug`
- `library_management`
- `project_storage`
- `status_display`

| Control label | Current location | Callback method | Category | User goal supported | Should stay here | Recommended location | Visibility level | Risk if moved |
|---|---|---|---|---|---|---|---|---|
| New Project | File menu | `_new_project` | project_storage | Start clean project | Yes | File menu + Settings/Project | menu_only | Medium: project dirty prompts. |
| Open Project | File menu | `_open_project` | project_storage | Open saved project | Yes | File menu + Start/Recent | menu_only | Medium: project path expectations. |
| Save Project | File menu | `_save_project` | project_storage | Save current project | Yes | File menu + project status shortcut | menu_only | High: data loss if hidden. |
| Save Project As | File menu | `_save_project_as` | project_storage | Choose project save path | Yes | File menu + Settings/Project | menu_only | High: project schema/path. |
| Open Data Directory | File menu | `_open_data_directory` | project_storage | Find app data files | No | Settings → Storage | menu_only now; always_visible in Settings | Low. |
| Change Data Directory | File menu | `_change_data_directory` | project_storage | Change storage root | No | Settings → Storage migration | menu_only now; contextual in Settings | High: storage root switch. |
| Reveal Recovery Folder | File menu | `_reveal_recovery_folder` | project_storage | Find autosave/recovery files | No | Settings → Storage/Recovery | menu_only now; contextual in Settings | Medium. |
| Export Library Entry | File menu | `_export_library_entry` | import_export | Share selected asset entry | No | Assets selected-asset actions | menu_only | Low-medium: selected asset context. |
| Import Library Entry | File menu | `_import_library_entry` | import_export | Import external asset JSON | No | Assets toolbar | menu_only | Medium: import validation. |
| Save Current Profiles | Library menu | `_save_profile_assets` | library_management | Persist profile snapshots | No | Assets → Profiles / Speech Builder → Profiles | menu_only | Low. |
| Refresh Speech Asset Library | Library menu | `_refresh_asset_library_view` | library_management | Rescan assets | No | Assets toolbar | menu_only | Low. |
| Undo Performance Edit | Edit menu | `_undo_performance_edit` | secondary_action | Undo automation/timing edits | Yes | Edit menu + Performance toolbar | menu_only/contextual | Medium: selected timeline state. |
| Redo Performance Edit | Edit menu | `_redo_performance_edit` | secondary_action | Redo automation/timing edits | Yes | Edit menu + Performance toolbar | menu_only/contextual | Medium. |
| Speech Diagnostics | View menu | show dock lambda | diagnostic | Open voice/resonance diagnostics | Yes | View menu + Advanced Diagnostics | menu_only | Low. |
| About WaveToy | Help menu/global | `_show_about` | diagnostic | Learn app info | Yes | Help | menu_only/always_visible help | Low. |
| ▶ Play | Global command bar | `_global_play` | transport | Play active workspace | Maybe | Global only if context label is explicit | always_visible | Medium: active tab ambiguity. |
| 🔁 Loop | Global command bar | `_global_loop` | transport | Loop active workspace | Maybe | Global only if context label is explicit | always_visible | Medium: active tab ambiguity. |
| ■ Stop | Global command bar | `_global_stop` | transport | Stop playback | Yes | Global universal stop | always_visible | High: safety/stop access. |
| Render / Create | Global command bar | `_global_render_create` | primary_action | Generate active output | No | Workspace-specific primary toolbar | contextual | High: ambiguous output. |
| Add to Timeline | Global command bar | `_global_add_to_timeline` | secondary_action | Send current item to arrangement | No | Sound/Speech/Assets contextual action | contextual | Medium: wrong asset target. |
| Save / Export | Global command bar | `_global_save_export` | import_export | Save/export active item | No | Explicit Save Project / Export Audio / Export Word / Export Mix | contextual | High: ambiguous persistence. |
| Reset | Global command bar | `_global_reset_context` | destructive_action | Reset current context | No | Contextual reset/clear actions only | contextual | High: destructive ambiguity. |
| Project path label | Shell under global bar | `_project_status_text` | status_display | Know current project path/dirty state | Yes | Shell + Settings/Project | always_visible | Low. |
| ＋ Wave | Voice Lab | wave row add callback | primary_action | Add synth wave layer | Yes | Sound Design → Classic | contextual | Low. |
| All / Clear Solo | Voice Lab | clear solo callback | secondary_action | Restore all wave layers audible | Yes | Sound Design → Classic mixer | contextual | Low. |
| Preset buttons | Voice Lab | preset callbacks | secondary_action | Start from sound examples | Maybe | Sound Design → Presets | contextual | Low. |
| ▶ Play | Voice Lab | `_play` | transport | Play current generated sound | Yes | Sound Design toolbar | contextual | Medium: duplicate global play. |
| 🔁 Loop | Voice Lab | `_toggle_live_loop` | transport | Loop generated sound | Yes | Sound Design toolbar | contextual | Medium. |
| ■ Stop | Voice Lab | `_stop` | transport | Stop sound playback | Yes | Sound Design toolbar | contextual | Low. |
| Save Audio | Voice Lab | `_save` | import_export | Export generated audio | Yes | Sound Design export toolbar | contextual | Medium: distinguish from project save. |
| Load Audio | Voice Lab | `_load_sound` | import_export | Load external audio | Maybe | Assets/Arrangement import or Sound Design import | contextual | Medium. |
| Note Wheel | Classic/Wave Explorer | `_open_note_wheel` | expression_control | Select note/pitch emotionally | Yes | Sound Design pitch section | contextual | Low. |
| Voice Font Import Recording | Voice Font | `_import_voice_font_recording` | import_export | Future consent-first capture import | Maybe | Assets → Voice Font Planning | contextual | Low. |
| Voice Font Record | Voice Font | future notice lambda | advanced_debug | Future disabled recording placeholder | No | Voice Font Planning advanced/future | advanced_collapsed | Low. |
| Voice Font Analyze | Voice Font | future notice lambda | advanced_debug | Future disabled analysis placeholder | No | Voice Font Planning advanced/future | advanced_collapsed | Low. |
| Open Future Workflow Note | Voice Font | `_show_future_workflow_notice` | diagnostic | Explain planned flow | No | Help/Voice Font notes | advanced_collapsed | Low. |
| Play Phoneme | Articulation Lab | `_play_phoneme_preview` | transport | Preview current phoneme | Maybe | Selected Phoneme Workbench Actions | contextual | Medium: current vs selected confusion. |
| Loop Phoneme Preview | Articulation Lab | `_toggle_phoneme_loop` | transport | Audition current phoneme repeatedly | Maybe | Selected Phoneme Workbench Actions | contextual | Medium. |
| Stop Preview | Articulation Lab | `_stop_phoneme_preview` | transport | Stop phoneme preview | Yes | Workbench/global stop | contextual | Low. |
| Apply Current Wave | Articulation Lab | `_apply_current_wave_to_phoneme` | source_assignment | Assign current classic wave to current phoneme | No | Selected Phoneme Workbench Source | contextual | High: source metadata. |
| Reset Voice | Articulation Lab | `_reset_current_phoneme_source` | source_assignment | Restore default voice for current phoneme | No | Selected Phoneme Workbench Source | contextual | Medium. |
| Add to Articulation Timeline | Articulation Lab | `_add_current_phoneme_to_chain` | primary_action | Append current phoneme to chain | No | Speech Builder chain toolbar | contextual | Low-medium. |
| Save Phoneme | Articulation Lab drawer | `_save_current_phoneme` | library_management | Save edited phoneme | Maybe | Workbench Actions / Assets | contextual | Low. |
| Phoneme preset buttons | Articulation Lab drawers | `_make_phoneme_preset_button` callbacks | navigation | Choose phoneme preset | Yes | Speech Builder phoneme drawer | contextual | Low. |
| Open Timing / Performance | Articulation Timeline → Timeline → Chain | `_show_articulation_timing_page` | navigation | Jump to timing controls | Temporary | Selected Workbench Timing link | contextual | Low. |
| Add Current | Articulation Timeline → Chain | `_add_current_phoneme_to_chain` | primary_action | Append phoneme to chain | Yes | Speech Builder chain toolbar | contextual | Low. |
| Create Syllable | Articulation Timeline → Chain | `_create_articulation_syllable` | secondary_action | Build syllable from chain context | Maybe | Speech Builder Actions / Assets | contextual | Medium. |
| Apply Current Wave to Selected | Articulation Timeline → Chain Wave Source | `_apply_current_wave_to_selected_chain_item` | source_assignment | Assign source to selected chain phoneme | No | Selected Phoneme Workbench Source | contextual | High: core workflow. |
| Apply Current Wave to Chain | Articulation Timeline → Chain Wave Source | `_apply_current_wave_to_whole_chain` | source_assignment | Assign source to all chain phonemes | No | Workbench Source bulk menu | contextual | High: bulk mutation. |
| Reset Selected to Default Voice | Articulation Timeline → Chain Wave Source | `_reset_selected_chain_item_source` | source_assignment | Restore selected default source | No | Workbench Source | contextual | Medium. |
| Reset Chain Sources | Articulation Timeline → Chain Destructive | `_reset_whole_chain_source` | destructive_action | Restore all default sources | No | Workbench Source bulk destructive with confirmation | contextual | High. |
| Clear Chain | Articulation Timeline → Chain Destructive | `_clear_articulation_chain` | destructive_action | Remove chain cards | Maybe | Chain toolbar destructive overflow | contextual | High. |
| Live Preview | Articulation Timeline → Chain | `_set_live_preview_enabled` | transport | Auto-audition edits | Maybe | Workbench Actions/Preview | contextual | Medium: playback lifecycle. |
| ▶ Play Word | Articulation Timeline → Chain/Render | `_play_articulation_word` | transport | Play rendered smoothed word | Yes | Speech Builder render toolbar | contextual | Medium. |
| Create Word | Articulation Timeline → Chain/Render | `_create_articulation_word` | primary_action | Create named speech asset | Yes | Speech Builder render toolbar | contextual | Medium: asset side effects. |
| ▶ Play Chain | Articulation Timeline → Chain/Render | `_play_articulation_chain` | transport | Play raw sequence | Yes | Chain toolbar | contextual | Low. |
| Send Word to Timeline | Articulation Timeline → Render | `_send_articulation_word_to_timeline` | secondary_action | Add rendered word to arrangement | No | Render result action / Assets card | contextual | Medium. |
| Send Phoneme | Articulation Timeline → Render | `_send_current_phoneme_to_timeline` | secondary_action | Add current phoneme to arrangement | No | Workbench Actions / Assets card | contextual | Medium. |
| Send Chain | Articulation Timeline → Render | `_send_articulation_chain_to_timeline` | secondary_action | Add chain to arrangement | No | Render result action | contextual | Medium. |
| Export Word | Articulation Timeline → Render | `_export_articulation_word` | import_export | Export rendered word audio | Yes | Speech Builder Render | contextual | Medium. |
| Save Chain | Articulation Timeline → Render | `_save_articulation_chain` | import_export | Save chain JSON | Yes | Speech Builder chain toolbar / Assets | contextual | High: schema. |
| Load Chain | Articulation Timeline → Render | `_load_articulation_chain` | import_export | Load chain JSON | Yes | Speech Builder chain toolbar / Assets | contextual | High: schema. |
| Validate Continuous | Articulation Timeline → Motion/Advanced | validation callback | advanced_debug | Test continuous renderer | No | Advanced Motion drawer | advanced_collapsed | Medium: experimental rendering. |
| Run Stop Test | Articulation Timeline → Motion/Advanced | stop-test callback | advanced_debug | Verify stop consonant behavior | No | Advanced Diagnostics | advanced_collapsed | Low. |
| Reset Continuous Tuning | Articulation Timeline → Motion/Advanced | reset tuning callback | destructive_action | Restore continuous tuning | No | Advanced Motion destructive | advanced_collapsed | Medium. |
| Save Profile Set | Articulation Timeline → Profiles | `_save_profile_assets` | library_management | Save voice/profile states | Maybe | Assets → Profiles | contextual | Low. |
| Open Voice Box / Resonance Controls | Articulation Timeline → Profiles | show diagnostics dock lambda | diagnostic | Tune voice/resonance internals | Maybe | Advanced Diagnostics | advanced_collapsed | Low. |
| CV/VC Preview Combination | Articulation Timeline → CV/VC Library | `_preview_cv_vc_combination` | transport | Audition consonant/vowel combo | Yes | Speech Builder phoneme drawer | contextual | Low. |
| Append to Chain | Articulation Timeline → CV/VC Library | `_append_cv_vc_combination_to_chain` | primary_action | Add combo to chain | Yes | Speech Builder phoneme drawer | contextual | Low. |
| Replace Chain | Articulation Timeline → CV/VC Library | `_load_cv_vc_combination_to_chain` | destructive_action | Replace current chain with combo | Maybe | Speech Builder drawer destructive | contextual | High. |
| Add to Speech Assets | Articulation Timeline → CV/VC Library | `_add_cv_vc_combination_to_speech_assets` | library_management | Save combo asset | Maybe | Assets / drawer secondary | contextual | Low. |
| Export Library JSON | Articulation Timeline → CV/VC Library | `_export_cv_vc_library_json` | import_export | Export combo data | Maybe | Assets export | contextual | Low. |
| Selected Phoneme Controls | Articulation Timeline → Visual Speech Timeline | selected-component methods | timing_control | Edit selected timeline block timing | No | Selected Phoneme Workbench Timing | contextual | High: selection semantics. |
| Save Waveform Analysis | Articulation Timeline → Inspector | save analysis callback | diagnostic | Persist waveform analysis | No | Advanced Inspector | advanced_collapsed | Low. |
| Save Formant Analysis | Articulation Timeline → Inspector | save formant callback | diagnostic | Persist formant analysis | No | Advanced Inspector | advanced_collapsed | Low. |
| Load Analysis Metadata | Articulation Timeline → Inspector | load metadata callback | diagnostic | Load analysis JSON | No | Advanced Inspector | advanced_collapsed | Low. |
| Play Word Motion | Articulation Timeline → Motion | `_play_articulation_motion` | transport | Preview visual mouth motion | Maybe | Speech Builder Motion | contextual | Medium. |
| Loop Word Motion | Articulation Timeline → Motion | `_loop_articulation_motion` | transport | Loop motion preview | Maybe | Speech Builder Motion | contextual | Medium. |
| Stop Motion | Articulation Timeline → Motion | `_stop_articulation_motion` | transport | Stop motion preview | Yes | Motion toolbar / global stop | contextual | Low. |
| Slow Motion Visual Only | Articulation Timeline → Motion | `_slow_articulation_motion` | diagnostic | Inspect animation | No | Motion advanced | advanced_collapsed | Low. |
| Export Viseme JSON | Articulation Timeline → Motion | `_export_viseme_json` | import_export | Export generic viseme frames | Yes | Motion export drawer | contextual | Medium: file compatibility. |
| Export Animation JSON | Articulation Timeline → Motion | `_export_animation_json` | import_export | Export animation frames | Yes | Motion export drawer | contextual | Medium. |
| Saved phoneme ▶ Play | Saved phoneme card | `_play_saved_phoneme` | transport | Audition saved phoneme | Yes | Assets/Speech Builder saved phoneme card | contextual | Low. |
| Saved phoneme Delete | Saved phoneme card | `_delete_saved_phoneme` | destructive_action | Remove saved phoneme | Yes | Assets card destructive overflow | contextual | High: delete file. |
| Saved phoneme Load | Saved phoneme card | `_load_saved_phoneme` | library_management | Load phoneme into editor | Yes | Assets/Speech Builder card | contextual | Low. |
| Saved phoneme Rename | Saved phoneme card | `_rename_saved_phoneme` | library_management | Rename saved phoneme | Yes | Assets card | contextual | Medium: path rename. |
| Saved phoneme Duplicate | Saved phoneme card | `_duplicate_saved_phoneme` | library_management | Copy saved phoneme | Yes | Assets card | contextual | Low. |
| Graphical shortcut buttons | Graphical Editor | `_graphical_workflow_section` navigation callbacks | navigation | Jump to related advanced tabs | Maybe | Sound Design mode links | contextual | Low. |
| ＋ Layer | Graphical Editor → Wave section | wave add callback | primary_action | Add graphical wave layer | Yes | Sound Design Graphical | contextual | Low. |
| ⧉ Duplicate | Graphical Editor → Wave section | duplicate callback | secondary_action | Duplicate layer | Yes | Sound Design Graphical | contextual | Low. |
| Clear Solo | Graphical Editor → Wave section | clear solo callback | secondary_action | Reset solo layer state | Yes | Sound Design Graphical | contextual | Low. |
| Curve buttons | Graphical Editor → Chain/Pitch | curve callbacks | expression_control | Shape transitions/envelopes | Yes | Sound Design Graphical | contextual | Low. |
| Mute / Solo / Copy / Remove | Graphical Editor layer rows | layer callbacks | secondary/destructive | Manage layers | Yes | Sound Design Graphical rows | contextual | Medium for remove. |
| Timeline Play | Timeline | `_timeline_play_story` | transport | Play arrangement | Yes | Arrangement toolbar | contextual | Low. |
| Timeline Stop | Timeline | `_timeline_stop_story` | transport | Stop arrangement | Yes | Arrangement toolbar/global stop | contextual | Low. |
| Render Mix | Timeline | `_timeline_render_mix` | primary_action | Render arrangement mix | Yes | Arrangement toolbar | contextual | Medium. |
| Add Sound | Timeline | `_drop_story_sound` | secondary_action | Add sound clip | Maybe | Arrangement asset drawer | contextual | Low. |
| Add Lane | Timeline | `_add_story_lane` | secondary_action | Add arrangement lane | Yes | Arrangement toolbar | contextual | Low. |
| Add Voice Lane | Timeline | `_add_voice_lane` | secondary_action | Add voice lane | Yes | Arrangement toolbar | contextual | Low. |
| Zoom In / Zoom Out | Timeline | `_timeline_zoom` | navigation | Adjust timeline view | Yes | Arrangement toolbar | contextual | Low. |
| Select/Move | Timeline tool bar | `_timeline_set_tool("select")` | navigation | Select/move clips | Yes | Arrangement tool palette | contextual | Low. |
| Trim Tool | Timeline tool bar | `_timeline_set_tool("trim")` | navigation | Trim clip edges | Yes | Arrangement tool palette | contextual | Low. |
| Time Stretch | Timeline tool bar | `_timeline_set_tool("stretch")` | navigation | Stretch clip duration | Yes | Arrangement tool palette | contextual | Low-medium. |
| Split | Timeline tool bar | `_timeline_split_selected` | secondary_action | Split selected clip | Yes | Arrangement tool palette | contextual | Medium. |
| Delete | Timeline tool bar | `_timeline_delete_selected` | destructive_action | Delete selected clip | Yes | Arrangement tool palette | contextual | High. |
| Duplicate Clip | Timeline tool bar | `_timeline_duplicate_selected` | secondary_action | Duplicate clip | Yes | Arrangement tool palette | contextual | Low. |
| Export Last Mix | Timeline tool bar | `_timeline_export_last_mix` | import_export | Export rendered mix | Yes | Arrangement render/export area | contextual | Medium. |
| Snap | Timeline tool bar | `_timeline_snap_changed` | timing_control | Control clip snapping | Yes | Arrangement toolbar | contextual | Low. |
| Stretch Quality | Timeline tool bar | `_timeline_stretch_quality_changed` | timing_control | Select stretch quality | Maybe | Arrangement advanced timing | contextual | Low. |
| Import Sounds | Timeline Audio Assets drawer | `_timeline_import_sounds` | import_export | Import audio files | Yes | Arrangement asset drawer + Assets | contextual | Medium. |
| Add Word | Speech Assets panel | speech asset add callback | library_management | Add created word to asset bin | Maybe | Assets/Speech Builder output | contextual | Low. |
| Clear | Speech Assets panel | speech asset clear callback | destructive_action | Clear speech asset bin/filter | Maybe | Assets picker overflow | contextual | Medium. |
| Library Load | Speech Asset Library | `_load_selected_library_entry` | library_management | Load selected saved asset | Yes | Assets selected panel | contextual | Medium: asset type handling. |
| Library Rename | Speech Asset Library | `_rename_selected_library_entry` | library_management | Rename asset | Yes | Assets selected panel | contextual | Medium. |
| Library Duplicate | Speech Asset Library | `_duplicate_selected_library_entry` | library_management | Duplicate asset | Yes | Assets selected panel | contextual | Low. |
| Library Delete | Speech Asset Library | `_delete_selected_library_entry` | destructive_action | Delete saved asset | Yes | Assets selected panel destructive | contextual | High: file deletion. |
| Library Favorite | Speech Asset Library | `_toggle_selected_library_favorite` | library_management | Mark favorite | Yes | Assets selected panel | contextual | Low. |
| Library Tags/Notes | Speech Asset Library | `_edit_selected_library_tags_notes` | library_management | Annotate asset | Yes | Assets selected panel | contextual | Low. |
| Library Refresh | Speech Asset Library | `_refresh_asset_library_view` | library_management | Rescan assets | Yes | Assets toolbar | contextual | Low. |
| Library Import Entry | Speech Asset Library | `_import_library_entry` | import_export | Import asset JSON | Yes | Assets toolbar | contextual | Medium. |
| Library Export Entry | Speech Asset Library | `_export_library_entry` | import_export | Export selected asset | Yes | Assets selected panel | contextual | Medium. |
| Library Save Profiles | Speech Asset Library | `_save_profile_assets` | library_management | Save profile assets | Maybe | Assets → Profiles | contextual | Low. |
| Wave Explorer dashboard buttons | Wave Explorer | visual panel callbacks | navigation | Choose sound-design workspace | Yes | Sound Design Explorer | contextual | Low. |
| Wave Explorer Save | Presets workspace | `_save` | import_export | Save/export sound | Maybe | Sound Design export toolbar | contextual | Medium. |
| Wave Explorer Load | Presets workspace | `_load_sound` | import_export | Load audio/sound | Maybe | Sound Design import/Assets | contextual | Medium. |
| Reset Voice Box | Speech Diagnostics dock | `_reset_voice_box_state` | destructive_action | Reset voice-box model | Yes | Advanced Diagnostics | advanced_collapsed | Medium. |
| Reset Resonance | Speech Diagnostics dock | `_reset_resonance_state` | destructive_action | Reset resonance model | Yes | Advanced Diagnostics | advanced_collapsed | Medium. |
