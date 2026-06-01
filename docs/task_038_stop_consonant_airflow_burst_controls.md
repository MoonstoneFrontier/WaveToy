# Task 038: Stop Consonant Airflow and Burst Controls

## Problem

T and D stop consonants previously reused the same broad colored-noise path used for hiss-like consonants. That made the release sound too sustained and too bright, especially for D, and it made Air Pressure, Teeth Gap, Closure, and Burst Strength feel weak or cosmetic.

The main audible symptom was that D could default toward a TS-like release instead of a shorter, voiced, duller D.

## Stop control mapping

Stop rendering now uses a stop-specific burst model instead of directly reusing fricative hiss.

- **Air Pressure** controls release energy. Low values make a soft release; high values make a stronger burst/turbulence transient.
- **Teeth Gap** controls release brightness and sharpness. Low values create a tighter, brighter, more piercing release; high values widen and darken the burst.
- **Closure** controls how much the sound is held/gated before release. Low values allow a less stopped consonant; high values create a clearer closure before the pop.
- **Burst Strength** controls release pop amount and transient length. Zero removes the release pop/hiss nearly entirely; high values create a stronger, longer transient.

## T versus D

T is kept as an unvoiced, brighter stop with a longer release window and higher default release energy. D is voiced by default and now uses lower air pressure, wider teeth gap, darker noise color, lower burst strength, and stronger voiced onset.

D also receives a voiced-stop noise multiplier so its high-frequency burst is substantially weaker than T. It should only approach a TS-like sound when the user intentionally raises Air Pressure and Burst Strength while tightening Teeth Gap.

## Stop burst helper

The stop path now uses `_stop_burst_parameters()` and `_stop_burst_noise()` to shape transient burst duration, amplitude, brightness, and voiced onset. `_stop_burst_noise()` applies stop-specific spectral shaping with darker filtering for voiced stops such as D/B/G and brighter releases for unvoiced stops such as T/P/K when the controls call for it.

## Continuous renderer consistency

Continuous Mouth Motion uses the same stop burst parameters for stop events. Sustained frame noise is reduced for stop phonemes, and the burst event uses the stop-specific burst helper so stop-to-vowel transitions do not inherit an uncontrolled fricative hiss tail.

## Manual tuning notes

Suggested checks after selecting the T or D preset:

1. Set **Burst** to 0: release pop/hiss should nearly disappear.
2. Set **Air Pressure** low/high: release loudness should clearly change.
3. Set **Teeth Gap** low/high: low is sharper/brighter, high is duller/less piercing.
4. Set **Closure** low/high: low is less stopped, high has a clearer pre-release hold.
5. Select D and confirm it is voiced, shorter, darker, and less hissy than T.
6. Create D + AH and compare with T + AH; D should be closer to “da,” while T should remain sharper.
7. Render Continuous Mouth Motion and Clip Crossfade paths to confirm both respect the controls.

Debug output for stop rendering uses the `[WaveToy Stop]` prefix and includes phoneme name, voicing, air pressure, teeth gap, closure, burst strength, closure samples, burst samples, burst gain, burst brightness, and voiced onset gain.
