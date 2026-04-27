# Deployment Checklist

- [ ] Deploy `unbiased-ai-decision` backend to Cloud Run and record the final URL
- [ ] Update `FLUTTER_API_BASE_URL` in `firebase_options` / `app_runtime`
- [ ] Build Flutter web with `flutter build web --dart-define=FIREBASE_API_KEY=...`
- [ ] Deploy Flutter web to Firebase Hosting with `firebase deploy`
- [ ] Record the 60-second demo video following `video_script.md`
- [ ] Upload the demo video to YouTube as unlisted and copy the URL
- [ ] Add the deployed URL and YouTube URL to `README.md`, `SUBMISSION.md`, and `unbiased-ai-decision/README.md`
- [ ] Add real screenshots to `docs/screenshots/`
- [ ] Run `pytest backend/tests/` and confirm all tests pass
- [ ] Run `flutter test` and confirm all widget tests pass
- [ ] Push to GitHub and confirm CI passes
- [ ] Submit the GitHub repo URL, YouTube URL, and deployed URL through the Google Solution Challenge portal
