# PWA Installation Guide

## ✅ Your VibeCode app is now PWA-ready!

### What's Been Added:
1. **Web App Manifest** (`public/manifest.json`) - App metadata and icon configuration
2. **Service Worker** (`public/sw.js`) - Offline caching and background sync
3. **App Icons** - Matrix-themed SVG icons (192x192 and 512x512)
4. **Updated HTML** - Meta tags and service worker registration

### How to Install:

#### **Chrome/Edge (Recommended)**
1. Make sure your frontend server is running:
   ```bash
   cd frontend
   npm run dev
   ```
2. Open `http://localhost:5173` in Chrome or Edge
3. Look for the **install icon** (⊕) in the address bar (right side)
4. Click it and select **"Install"**
5. The app will open in its own window
6. You'll find "VibeCode" in your Start menu and desktop

#### **Alternative Installation Methods**
- **Chrome**: Menu (⋮) → More tools → Create shortcut → Check "Open as window"
- **Edge**: Menu (⋯) → Apps → Install this site as an app
- **Firefox**: Address bar icon → Install

### Features After Installation:
✓ Runs in standalone window (no browser UI)
✓ Desktop shortcut created
✓ Shows in Start menu / taskbar
✓ Offline support via service worker
✓ Launches like a native app
✓ Green matrix-themed icon

### Testing the PWA:
1. Start backend: `python backend/main.py`
2. Start frontend: `cd frontend && npm run dev`
3. Open browser and install
4. Test offline: Close browser, launch from desktop icon

### Building for Production:
```bash
cd frontend
npm run build
# Serve the dist folder with a static server
npx serve dist
```

Then install from the production URL.

---

**Note**: The backend (FastAPI server) must be running for full functionality. Consider using the `run_sefs.bat` to start both servers simultaneously.
