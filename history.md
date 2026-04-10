# Project History

## [2026-04-10] Advanced Intelligence & Logic Implementation

### Overview
Finalized the core logic for chat persistence, Model Context Protocol (MCP) integration, and professional-grade UI refinements, transforming the application into a production-ready AI interface.

### Changes Logged

#### 1. Smart Session & History Management
- **Persistent Memory Vault**: Implemented a comprehensive history system using Zustand middleware. 
  - **Auto-Archive**: Sessions are now automatically saved to local storage upon leaving the chat page or after every message.
  - **Intelligent Updating**: Returning to an existing chat session now updates the same entry and moves it to the top of the history instead of creating duplicates.
  - **Session Timeout**: Implemented a 1-hour activity window. If a user returns after an hour, the chat is archived and cleared to start fresh, while retaining provider/model settings.
- **Memory Vault UI**: Enhanced the `/history` view with:
  - **Aura Backgrounds**: Blurred radial gradients (primary, secondary, tertiary) behind each history item for a premium depth effect.
  - **Interactive States**: Smooth hover transitions and quick-action delete buttons.

#### 2. MCP Ecosystem Enhancements
- **Metadata Discovery**: Added a new FastAPI endpoint `/mcp/metadata` that performs a "handshake" with MCP servers to retrieve their actual names.
- **Verified Tooling UI**: Updated the Right Utility Panel to show verified server names (e.g., "Postgres-MCP") instead of generic URLs, including a visual loading state during verification.
- **Improved Management**: Enhanced the MCP addition flow with input validation, duplicate checks, and toast notifications.

#### 3. Professional Chat UX Redesign
- **Neural Textbox Layout**: Moved away from traditional mobile-style chat bubbles to a centered, professional "Content Area" for AI responses, maximizing readability for long outputs and code.
- **Multimodal Input Support**: 
  - Swapped the standard input for an **auto-expanding textarea**.
  - Added support for **Shift+Enter** for new lines while keeping **Enter** for sending.
  - **Auto-Focus**: Converted logic to ensure the cursor automatically returns to the input field after the AI finishes its response.
- **Vietnamese IME Optimization**: Fixed a critical bug where typing in Vietnamese (Telex/VNI) caused double message submissions by implementing `isComposing` state checks.

#### 4. Developer Productivity
- **Console Debug Tools**: Exposed `chatHistory()` and `purge()` functions to the global `window` object, allowing developers to inspect data or reset the environment directly from the browser console.

---

## [2026-04-09] UI/UX Refactor & Next.js Migration

### Overview
Successfully migrated the application from monolithic HTML prototypes to a modular Next.js architecture featuring the "Ethereal Intelligence" design system.

### Changes Logged

#### 1. Design System & Theming
- **Color Alignment**: Standardized all background and surface colors to a neutral dark hex (`#060f15`) for visual consistency.
- **Accessibility Fix**: Darkened all "on" color tokens to ensure high contrast for text.
- **Tailwind Configuration**: Overhauled `tailwind.config.ts` with custom design tokens (M3 system).

#### 2. Architecture & Layout
- **Persistent Shell**: Integrated globally persistent Sidebar and Header.
- **Componentization**: Created modular components for Sidebar, Header, Right Panel, and Chat Input.

#### 3. New Routes & Page Implementation
- **`/` (Home)**: Welcome Page with Hero section and feature bento-grid.
- **`/chat`**: Main Chat Interface.
- **`/history`**: Archives view.

#### 4. Cleanup
- **Legacy Files Removal**: Deleted old diagnostic HTML files.

---
*End of log for 2026-04-10.*
