# Frontend for Dream.OS

This directory houses all JavaScript, TypeScript, HTML, CSS, and other browser-facing assets and applications for Dream.OS.

All JS/TS tools, test rigs, and visual UIs live here.

## Structure

- `/scoreboard`: Contains the scoreboard application (from `runtime/dashboard`).
- `/sky_viewer`: Contains the sky viewer application (from `apps/sky_viewer`).
- `/templates`: Contains shared templates (e.g., Jinja2, from root `templates/`).
- `/automation`: Contains browser automation drivers and related scripts (from `drivers/`).
- `/profiles`: Contains browser profiles (e.g., for Chrome, from `chrome_profile/`).
- `package.json`: Project manifest and dependencies.
- `package-lock.json`: Exact dependency tree.
- `tsconfig.json`: TypeScript configuration.
- ... (other configuration files like `.npmignore`, `.prettierrc.json`)

## Getting Started

1. Ensure Node.js and npm are installed.
2. Navigate to the `frontend/` directory.
3. Run `npm install` to install dependencies (requires `package.json` to be present and correct).
4. Use `npm run <script_name>` (e.g., `npm run start`, `npm run build`) to execute project scripts (defined in `package.json`). 