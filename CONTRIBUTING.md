# Contributing to ops120-zcode-plugins

Thank you for your interest in contributing! This guide will help you get started.

## Getting Started

1. Fork this repository
2. Clone your fork:
   ```bash
   git clone https://github.com/your-username/ops120-zcode-plugins.git
   ```
3. Create a feature branch:
   ```bash
   git checkout -b feature/my-feature
   ```

## Adding a New Plugin

1. Create a new directory at the repository root for your plugin
2. Set up the plugin structure:
   ```
   my-plugin/
   +-- .zcode-plugin/
   |   +-- plugin.json
   +-- skills/
       +-- my-skill/
           +-- SKILL.md
           +-- scripts/ (optional)
   ```
3. Register your plugin in `marketplace.json`
4. Test with a local ZCode installation
5. Submit a Pull Request

## Adding Features to Existing Plugins

1. Ensure your changes don't break existing functionality
2. Test with ZCode locally
3. Follow the commit convention below

## Commit Convention

We follow [Conventional Commits](https://www.conventionalcommits.org/):

- `feat:` -- A new feature
- `fix:` -- A bug fix
- `docs:` -- Documentation changes
- `style:` -- Code style changes (formatting, etc.)
- `refactor:` -- Code refactoring
- `test:` -- Adding or updating tests
- `chore:` -- Maintenance tasks

Examples:
```bash
git commit -m "feat: add new model search algorithm"
git commit -m "fix: handle missing provider gracefully"
git commit -m "docs: update installation instructions"
```

## Pull Request Process

1. Update documentation if your change affects user-facing behavior
2. Ensure your PR description clearly describes the problem and solution
3. Link any related issues
4. Request a review from a maintainer

## Code Style

- Python: Follow PEP 8
- Markdown: Keep lines readable, use headers consistently
- Commit messages: Use Conventional Commits format

## Reporting Issues

Open a GitHub issue with:
- A clear title and description
- Steps to reproduce (if applicable)
- Expected vs. actual behavior
- Your environment (OS, ZCode version, Python version)

## License

By contributing, you agree that your contributions will be licensed under the MIT License.
