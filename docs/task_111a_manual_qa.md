# Task 111a Manual QA — Word Progress and Timeline Clip Editing

Use this checklist after launching `python wave_toy.py`.

## Create Word progress

1. Open **Articulation Timeline** and load or build a short word chain.
2. Click **Preview Word**.
   - Confirm a word render progress dialog appears with stage text.
   - Confirm it closes when preview playback starts.
3. Click **Create Word**.
   - Confirm progress appears during render and asset saving.
   - Confirm the dialog closes and the Speech Asset is created.
4. Click **Export Word**.
   - Confirm progress appears while saving and closes on success.

## Timeline clip editing

1. Create a clip by rendering/sending a word to the Timeline or using **Add Sound**.
2. Click the clip body.
   - Confirm the clip becomes selected and the inspector shows the selected clip ID.
3. Drag the clip body later in the Timeline.
   - Confirm the start time and inspector update while dragging.
   - Confirm the source audio reference is unchanged.
4. Choose **Trim Left / Trim Right**, then drag the left and right clip handles.
   - Confirm the visible clip region changes.
   - Confirm left trim updates source offset and right trim updates duration.
5. Choose **Stretch Clip**, then drag a clip edge.
   - Confirm duration, stretch ratio, waveform width, and inspector fields update.
6. Move the playhead inside the selected clip and click **Split at Playhead**.
   - Confirm two adjacent clips are created and both preserve the source reference.
