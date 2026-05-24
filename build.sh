#!/bin/bash
set -e
cd "$(dirname "$0")"

echo "Building Bird Tracker.app..."
uv run pyinstaller bird_tracker.spec --clean --noconfirm

echo "Creating BirdTracker.dmg..."
hdiutil create \
    -volname "Bird Tracker" \
    -srcfolder "dist/Bird Tracker.app" \
    -ov -format UDZO \
    "dist/BirdTracker.dmg"

echo ""
echo "Done → dist/BirdTracker.dmg"
echo ""
echo "NOTE: The app is unsigned. When your friend opens it for the first time:"
echo "  1. macOS will say 'cannot be opened because it is from an unidentified developer'"
echo "  2. Go to System Settings → Privacy & Security → scroll down → click 'Open Anyway'"
echo "  3. They'll also need to allow camera access the first time"
