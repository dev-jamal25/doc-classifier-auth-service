Frontend service for the authenticated document-classifier console.

## Stack

- Vite
- React
- TypeScript
- Tailwind CSS
- react-router-dom
- lucide-react
- framer-motion

## Local Development

```bash
npm install
npm run dev
```

If Nodist crashes or cannot resolve Node on Windows, run this once in the
current PowerShell session before npm commands:

```powershell
$env:NODIST_X64 = "0"
npm install
npm run build
```

This machine currently has Node `20.10.0` installed under Nodist's non-x64
store, while `NODIST_X64=1` makes Nodist look in an empty x64 store.

The UI is currently mock-only. Login accepts any non-empty email and password,
stores a local mock admin user, and protects `/dashboard` with that mock session.

## Build

```bash
npm run build
```
