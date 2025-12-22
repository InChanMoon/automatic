# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

네이버 블로그 자동화 시스템 - Naver blog automation system that handles content generation and publishing. The system uses Playwright with stealth mode for browser automation and integrates with Google Sheets/Drive for data management.

## Setup Commands

```bash
# Create virtual environment
python -m venv venv
venv\Scripts\activate  # Windows

# Install dependencies
pip install -r requirements_phase1.txt

# Install Playwright browser
python -m playwright install chromium
```

## Running the Applications

```bash
# Publisher Bot (GUI) - publishes generated content to Naver blog
python publisher_bot.py

# Content Creator Pro (GUI) - generates blog content using AI
python content_creator_pro_v3.py
```

## Architecture

### Core Flow
```
Content Generation (Gemini/Claude API)
           ↓
   Google Sheets (콘텐츠 시트)
           ↓
   Publisher Engine
           ↓
   Naver Blog (via Playwright)
```

### Key Components

**GUI Applications:**
- `publisher_bot.py` - Main publisher GUI with account group selection, headless mode toggle
- `content_creator_pro_v3.py` - Content generator GUI with AI model selection
- `publisher_engine.py` - Core publishing logic with caching and multi-bot concurrency support

**Source Modules (`src/`):**
- `publisher/naver_blog_publisher.py` - Playwright-based Naver blog automation with stealth
- `content/gemini_generator.py` - Gemini API content generation (gemini-2.5-flash)
- `content/claude_generator.py` - Claude API content generation (claude-3-5-sonnet)
- `sheets/content_manager_v3.py` - Content CRUD with status workflow (ready → publishing → published)
- `sheets/account_manager.py` - Account rotation by group with status tracking
- `sheets/publish_settings_manager.py` - Per-group publishing settings
- `drive/image_manager.py` - Google Drive image management with local caching
- `utils/text_image_generator.py` - Auto-generate images from text with markers

### Google Sheets Structure

Sheets are organized by group (e.g., `콘텐츠_사기`, `계정_현금화`):
- Content sheets: account_group, keyword, title, content, status, scheduled_time, etc.
- Account sheets: account_id, password, status (active/suspended/banned/captcha), last_used
- Settings sheet: Per-group publishing configuration

### Configuration

Copy `config_template.json` to `config.json` and fill in:
- `gemini_api.api_key` - Gemini API key
- `claude_api.api_key` - Claude API key
- `google_sheets.spreadsheet_id` - Google Sheets ID
- `google_drive.image_root_folder_id` - Drive folder for images

Credentials: `credentials/google_service_account.json` (Google Service Account)

### Image Marker System

Content can include image placement markers:
- `{img:1}` - Insert image #1
- `{img:1-3}` - Insert images #1 through #3

When `auto_generate_images=True`, images are generated from title/paragraph text.

### Content Status Workflow

`ready` → `publishing` → `published` (or `failed`)

Publisher uses locking mechanism for multi-bot concurrency via `lock_bot_id` field.

### Key Patterns

- All sheets managers inherit from `src/sheets/base.py` (SheetsBase)
- API calls use `@retry_with_backoff` decorator from `src/utils/retry.py`
- Publisher caches settings for 60 seconds to minimize API calls
- Captcha handling attempts auto-solve via Gemini, falls back to manual input
