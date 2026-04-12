# Project History

## [2026-04-09] UI/UX Refactor & Next.js Migration

### Overview
Successfully migrated the application from monolithic HTML prototypes to a modular Next.js architecture featuring the "Ethereal Intelligence" design system.

### Changes Logged

#### 1. Design System & Theming
- **Color Alignment**: Standardized all background and surface colors to a neutral dark hex (`#060f15`) for visual consistency across all views.
- **Accessibility Fix**: Darkened all "on" color tokens (`on-primary`, `on-secondary`, etc.) to the base background color (`#060f15`) to ensure high contrast for text on light-colored buttons.
- **Tailwind Configuration**: Overhauled `tailwind.config.ts` with custom design tokens including `primary-dim`, `surface-container-low`, and `secondary-fixed`.
- **Global CSS**: Updated `globals.css` with:
  - "Living Canvas" radial gradient backgrounds.
  - Glassmorphism effects (`.glass-panel`).
  - Material Symbols font integration.
  - Premium typography helpers (`display-lg`, `headline-sm`, `body-lg`).

#### 2. Architecture & Layout
- **Persistent Shell**: Updated `src/app/layout.tsx` to include a globally persistent **Sidebar** and **Header**, ensuring seamless navigation.
- **Componentization**: Created reusable React components in `src/components/`:
  - `layout/Sidebar.tsx`: Navigation with active route highlighting and user profile.
  - `layout/Header.tsx`: Dynamic title logic based on current route.
  - `layout/RightUtilityPanel.tsx`: Contextual tools side panel for the chat view.
  - `chat/ChatInputBar.tsx`: Floating command bar with contextual action chips.

#### 3. New Routes & Page Implementation
- **`/` (Home)**: Implemented the Welcome Page featuring the Hero section and feature bento-grid.
- **`/chat`**: Created the main Chat Interface with message feeds and contextual panels.
- **`/history`**: Created the Archives view featuring the session history bento-grid.

#### 4. Cleanup
- **Legacy Files Removal**: Deleted the diagnostic and sample HTML files:
  - `fullChatHistory.html`
  - `mainChatInterface.html`
  - `welcome_page.html`

---

## [2026-04-09] MetaClaw Integration (Phase 1)

### Overview
Successfully integrated the **MetaClaw Learning Proxy** (Phase 1) to enable persistent memory and skill injection. This architecture places MetaClaw as a transparent proxy between the frontend and the LLM providers.

### Changes Logged

#### 1. Backend LLM Adapter
- **Provider Support**: Added `metaclaw` provider to the backend's `get_or_create_agent` factory.
- **Protocol**: Switched to `ChatOpenAI` adapter for MetaClaw communication to maintain OpenAI compatibility.
- **Dependencies**: Added `langchain-openai` to `backend/requirements.txt`.
- **Environment**: Updated `.env.example` with `METACLAW_API_KEY` and `METACLAW_BASE_URL`.

#### 2. Frontend Configuration
- **Model Config**: Updated `src/lib/config.ts` to include MetaClaw as a valid provider with an expanded model list (Gemini, Llama, Claude).
- **Settings UI**: Updated `src/components/chat/chat-settings.tsx` to include provider selection and custom API key reminders for the proxy.
- **Type Safety**: Updated `src/lib/types.ts` to include `'metaclaw'` in the `ChatSettings` provider union type.

#### 3. Documentation & Organization
- **Architecture**: Created `docs/METACLAW_PROPOSAL.md` (Design) and `docs/METACLAW_INTEGRATION.md` (Roadmap).
- **Relocation**: Moved all standalone `.md` files (DOCKER, METACLAW, history, etc.) into the `docs/` folder for better repository structure.
- **Verification**: Created `scratch/test_metaclaw.py` for automated proxy connection testing.

---
*End of log for MetaClaw Phase 1.*
