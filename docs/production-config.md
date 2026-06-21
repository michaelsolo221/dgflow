# Night Line — Production Configuration

## speakingRate

`speakingRate` is configured in `app.json` under `audioProcessingConfig.synthesizeSpeechConfigs["en-US"].speakingRate`. Current value: `1.0` (normal speed).

Speaking rate is a platform-level setting, NOT a per-persona instruction. Persona-level pacing hints (e.g. "speak slowly") in instruction.txt are unreliable on the live model. Adjust `speakingRate` here for global pacing changes.

Valid range: `0.25` (very slow) to `4.0` (very fast).

## Voice Settings Persistence

Voice model (e.g. Journey, Studio voices) is configured in CES Console, not in `app.json`. Voice selection persists across `cxas push` deployments — pushing a new agent version does NOT reset voice settings.

To change voices: CES Console → Agent Settings → Voice Configuration.

## GCS Bucket

Audio eval recording bucket: `gs://<your-project>-night-line-evals` (configured in `loggingSettings.evaluationAudioRecordingConfig.gcsBucket`). Must be a real GCS bucket — placeholder strings return HTTP 400 on every eval run.
