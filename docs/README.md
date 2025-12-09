# Minin Documentation Index

Welcome to the Minin documentation! This directory contains comprehensive guides for architecture, implementation, development, and maintenance.

## 📋 Quick Links

- **[Main README](../README.md)** - Project overview and setup instructions
- **[CLAUDE.md](../CLAUDE.md)** - Development guide for Claude Code
- **[API Endpoints](./API_ENDPOINTS.md)** - REST API specification
- **[Database Schema](./schema.sql)** - Complete database structure (DBML)

---

## 🏗️ Architecture & Design

### Core Systems
- **[Database Schema](./schema.sql)** - Complete database structure with DBML notation
- **[API Endpoints](./API_ENDPOINTS.md)** - REST API documentation and specifications
- **[Caching Implementation](./CACHING_IMPLEMENTATION.md)** - Multi-language translation caching strategy

### System Implementations
- **[Learning Progress System](./LEARNING_PROGRESS_SYSTEM.md)** - Spaced repetition and progress tracking
- **[Learning Progress Implementation Summary](./LEARNING_PROGRESS_IMPLEMENTATION_SUMMARY.md)** - Summary of progress system implementation

---

## 🎮 Feature Implementation Guides

### Quiz System
- **[Quiz System Implementation Guide](./QUIZ_SYSTEM_IMPLEMENTATION_GUIDE.md)** - Complete quiz system architecture
- **[Quiz Type Toggles Plan](./QUIZ_TYPE_TOGGLES_PLAN.md)** - User preferences for quiz types
- **[Intermediate Quiz Plan](./INTERMEDIATE_QUIZ_PLAN.md)** - Advanced quiz features
- **[Quiz Testing Guide](./QUIZ_TESTING_GUIDE.md)** - Testing strategies for quiz functionality
- **[Quiz Error Handling](./quiz-error-handling.md)** - Error handling patterns for quiz system

### User Interface
- **[Practice Page Implementation](./PRACTICE_PAGE_IMPLEMENTATION.md)** - Practice interface and workflows
- **[Frontend Display Guide](./FRONTEND_DISPLAY_GUIDE.md)** - Frontend UI patterns and best practices
- **[Spell Check Frontend Spec](./SPELL_CHECK_FRONTEND_SPEC.md)** - Spell checking functionality specification
- **[Translate Page Dynamic Columns Refactor](./translate-page-dynamic-columns-refactor.md)** - Translation UI improvements

---

## 🛠️ Development Guides

### Workflow & Processes
- **[Agents Workflow](./AGENTS.md)** - AI agent development workflow and best practices
- **[Logging Guide](./LOGGING_GUIDE.md)** - Application logging patterns and configuration

### Code Quality & Refactoring
- **[Language Service Refactoring](./LANGUAGE_SERVICE_REFACTORING.md)** - Language service architecture improvements

---

## 🔒 Database & Safety

- **[Database Safety](./DB_SAFETY.md)** - Database best practices and safety guidelines
- **[Safe Testing](./SAFE_TESTING.md)** - Testing without breaking production data

---

## 🐛 Maintenance & History

- **[Bug Fixes Summary](./BUG_FIXES_SUMMARY.md)** - Recent bug fixes and resolutions
- **[Backlog](./backlog.md)** - Known issues, technical debt, and future features
- **[Project Cleanup Recommendations](./PROJECT_CLEANUP_RECOMMENDATIONS.md)** - Pre-publication cleanup guide

---

## 📚 Documentation Categories

### By Topic

**Architecture**: Schema, API Endpoints, Caching
**Features**: Quiz System, Practice Page, Learning Progress
**Development**: Agents, Logging, Testing
**Maintenance**: Backlog, Bug Fixes, Safety

### By User Type

**New Developers**: Start with README.md → CLAUDE.md → Database Schema → API Endpoints
**Feature Developers**: AGENTS.md → Feature-specific guides → Testing guides
**DevOps/Maintainers**: DB_SAFETY.md → Logging Guide → Backup scripts
**Code Reviewers**: Bug Fixes Summary → Backlog → Implementation guides

---

## 🚀 Getting Started Path

1. **Setup**: Read [Main README](../README.md) for installation
2. **Architecture**: Review [Database Schema](./schema.sql) and [API Endpoints](./API_ENDPOINTS.md)
3. **Development**: Follow [CLAUDE.md](../CLAUDE.md) for development workflow
4. **Feature Work**: Read [Agents Workflow](./AGENTS.md) for AI-assisted development
5. **Testing**: Use [Safe Testing](./SAFE_TESTING.md) practices

---

## 📝 Contributing to Documentation

When adding new documentation:

1. Use consistent naming: `SCREAMING_SNAKE_CASE.md` or `kebab-case.md`
2. Add entry to this README.md index
3. Include cross-references to related docs
4. Keep diagrams and code examples up-to-date
5. Date major updates at the bottom of the document

---

**Documentation Index Maintained By**: Project Contributors
**Last Updated**: December 9, 2025