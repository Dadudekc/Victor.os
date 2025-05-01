# Naming Conventions

This document outlines the standard naming conventions used throughout the
Dream.OS project for files, variables, classes, functions, and components.

Adhering to these conventions ensures consistency, readability, and
maintainability across the codebase.

## 1. File Naming

### 1.1 React Components (.tsx)

- **Convention:** `PascalCase`
- **Suffix:** `.component.tsx` (Optional, but recommended for clarity)
- **Example:** `UserProfileCard.component.tsx`, `DataTable.tsx`

### 1.2 Custom Hooks (.ts)

- **Convention:** `camelCase`
- **Suffix:** `.hook.ts` (Optional, but recommended for clarity, especially if
  near component with similar name)
- **Example:** `useFetchData.hook.ts`, `useWindowSize.ts`

### 1.3 Non-Code Assets (Images, Styles, Data, etc.)

- **Convention:** `kebab-case`
- **Examples:** `user-profile-icon.svg`, `main-styles.css`,
  `error-messages.json`, `logo-white.png`

### 1.4 Service Modules (.ts)

- **Convention:** Use `PascalCase` if the module's primary export is a class (e.g., `AuthenticationService.service.ts` exports `class AuthenticationService`). Use `camelCase` if the module primarily exports functions or objects (e.g., `userData.service.ts` exports functions like `fetchUserData`, `updateUserData`).
- **Suffix:** `.service.ts`
- **Example:** `AuthenticationService.service.ts`, `userData.service.ts`

### 1.5 Type Definitions (.ts)

- **Convention:** `PascalCase` (often matching the primary interface/type)
- **Suffix:** `.types.ts`
- **Example:** `User.types.ts`, `ApiResponse.types.ts`

### 1.6 Python Modules/Scripts/Tests (.py)

- **Convention:** `snake_case`
- **Examples:** `agent_bus.py`, `file_utils.py`, `process_data.py`, `test_file_utils.py`

### 1.7 General Principles

- Use descriptive names.
- Avoid abbreviations where possible, unless widely understood (e.g., `utils`).
- Separate words clearly using the appropriate casing convention for the file
  type.

## 2. Code Element Naming (Variables, Functions, Classes)

_(Language-specific conventions apply - e.g., PEP 8 for Python)_

- **Variables & Functions:** Generally `snake_case` (e.g., `user_data`,
  `calculate_total`).
- **Classes:** `PascalCase` (e.g., `UserProfile`, `TaskManager`).
- **Constants:** `UPPER_SNAKE_CASE` (e.g., `MAX_RETRIES`, `API_ENDPOINT`).
