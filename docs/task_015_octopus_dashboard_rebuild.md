# Task 015 — Octopus Dashboard Rebuild

## Goal

Rebuild the WaveToy dashboard so the Wave Explorer is the clear center of attention and the major feature controls sit around it like octopus limbs.

## Layout changes

- Promoted the Wave Explorer into the center of the dashboard.
- Removed the redundant standalone Wave Explorer dashboard button from the side controls.
- Renamed the large popup launcher to **🔍 Big View** and kept it attached to the central Wave Explorer panel.
- Replaced the former left-plus-right dashboard arrangement with a three-column octopus layout:
  - Upper left: **🎚 Shape Mix**
  - Upper center: **🎯 Pitch Toys**
  - Upper right: **🎼 Tuning Map**
  - Middle left: **👂 Stereo Space**
  - Middle right: **✨ Sound Magic**
  - Lower left: **🌈 Experiments**
  - Lower right: **💾 Save Sound**
- Kept all limb buttons at a fixed **220 × 140** size so their geometry is consistent and not content-dependent.

## Wave Explorer content

The central Wave Explorer now includes a readable summary strip with:

- Current sound name placeholder (`Custom Wave`)
- Main note and octave
- Current tuning label
- Pitch bend state
- Mute/solo summary

The central panel focuses on the resulting waveform and high-level sound status instead of dense parameter controls.

## Button redesign

Each limb button now follows a simpler visual pattern:

1. Large label at the top.
2. One symbolic preview in the center.
3. One short status line at the bottom.

The previews intentionally avoid miniature editors, sliders, dense parameter text, and overlapping labels.

## Stereo workspace

The permanent dashboard no longer gives the stereo workspace visual dominance. Stereo controls are accessed by the **👂 Stereo Space** limb and shown only in the workspace drawer when requested.

## Verification notes

- The waveform is visually dominant in the dashboard.
- Limb buttons are large, consistent, and readable.
- Button previews use simplified pictograms rather than miniature control panels.
- The separate Wave Explorer launcher was removed from the side column.
- The dashboard is designed to fit a 1280-pixel-wide window without horizontal scrolling.
