# Install pre-commit tool globally using uv if not already installed
uv tool install pre-commit --force

# Install the git hook scripts in the current repository
pre-commit install
pre-commit install --hook-type commit-msg

Write-Host "Pre-commit hooks successfully installed and configured for this project!" -ForegroundColor Green
Write-Host "Mypy and Ruff will now run automatically on every 'git commit'." -ForegroundColor Cyan
