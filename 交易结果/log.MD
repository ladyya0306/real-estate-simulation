Fix all linting errors (flake8, isort, pyproject.toml) #13
Run pre-commit run --all-files
\[INFO\] Initializing environment for https://github.com/pre-commit/pre-commit-hooks.
Warning:  repo `https://github.com/pre-commit/pre-commit-hooks` uses deprecated stage names (commit, push) which will be removed in a future version.  Hint: often `pre-commit autoupdate --repo https://github.com/pre-commit/pre-commit-hooks` will fix this.  if it does not -- consider reporting an issue to that repo.
\[INFO\] Initializing environment for https://github.com/adrienverge/yamllint.git.
\[INFO\] Initializing environment for https://github.com/pycqa/isort.
Warning:  repo `https://github.com/pycqa/isort` uses deprecated stage names (commit, merge-commit, push) which will be removed in a future version.  Hint: often `pre-commit autoupdate --repo https://github.com/pycqa/isort` will fix this.  if it does not -- consider reporting an issue to that repo.
\[INFO\] Initializing environment for https://github.com/PyCQA/flake8.
\[INFO\] Initializing environment for https://github.com/PyCQA/flake8:Flake8-pyproject.
\[INFO\] Initializing environment for https://github.com/astral-sh/ruff-pre-commit.
\[INFO\] Initializing environment for https://github.com/executablebooks/mdformat.
\[INFO\] Initializing environment for https://github.com/executablebooks/mdformat:mdformat-gfm,mdformat_frontmatter,mdformat_footnote.
\[INFO\] Installing environment for https://github.com/pre-commit/pre-commit-hooks.
\[INFO\] Once installed this environment will be reused.
\[INFO\] This may take a few minutes...
\[INFO\] Installing environment for https://github.com/adrienverge/yamllint.git.
\[INFO\] Once installed this environment will be reused.
\[INFO\] This may take a few minutes...
\[INFO\] Installing environment for https://github.com/pycqa/isort.
\[INFO\] Once installed this environment will be reused.
\[INFO\] This may take a few minutes...
\[INFO\] Installing environment for https://github.com/PyCQA/flake8.
\[INFO\] Once installed this environment will be reused.
\[INFO\] This may take a few minutes...
\[INFO\] Installing environment for https://github.com/astral-sh/ruff-pre-commit.
\[INFO\] Once installed this environment will be reused.
\[INFO\] This may take a few minutes...
\[INFO\] Installing environment for https://github.com/executablebooks/mdformat.
\[INFO\] Once installed this environment will be reused.
\[INFO\] This may take a few minutes...
fix end of files.........................................................Passed
mixed line ending........................................................Passed
trim trailing whitespace.................................................Passed
check toml...............................................................Passed
check yaml...............................................................Passed
yamllint.................................................................Passed
isort....................................................................Passed
flake8...................................................................Failed

- hook id: flake8
- exit code: 1

property_initializer.py:61:9: F841 local variable 'bedrooms' is assigned to but never used
services/agent_service.py:80:9: F841 local variable 'p_weights' is assigned to but never used
services/agent_service.py:145:17: F841 local variable 'is_prop_allocated' is assigned to but never used
services/agent_service.py:418:9: F841 local variable 'sellers' is assigned to but never used
services/agent_service.py:529:9: F841 local variable 'new_sellers' is assigned to but never used
services/transaction_service.py:141:17: E741 ambiguous variable name 'l'
services/transaction_service.py:177:13: F401 'transaction_engine.decide_negotiation_format' imported but unused
services/transaction_service.py:180:39: E741 ambiguous variable name 'l'
services/transaction_service.py:189:17: F841 local variable 'market_hint' is assigned to but never used
simulation_runner.py:143:9: F841 local variable 'behavior_logger' is assigned to but never used
transaction_engine.py:975:1: F811 redefinition of unused 'decide_negotiation_format' from line 11

ruff.....................................................................Failed

- hook id: ruff
- exit code: 2

ruff failed
Cause: Failed to parse /home/runner/work/real-estate-simulation/real-estate-simulation/pyproject.toml
Cause: TOML parse error at line 14, column 1
|
14 | \[tool.ruff\]
| ^^^^^^^^^^^
Unknown rule selector: `W503`

mdformat.................................................................Passed
Error: Process completed with exit code 1.

Feat/interactive macro #14
Run pre-commit run --all-files
\[INFO\] Initializing environment for https://github.com/pre-commit/pre-commit-hooks.
Warning:  repo `https://github.com/pre-commit/pre-commit-hooks` uses deprecated stage names (commit, push) which will be removed in a future version.  Hint: often `pre-commit autoupdate --repo https://github.com/pre-commit/pre-commit-hooks` will fix this.  if it does not -- consider reporting an issue to that repo.
\[INFO\] Initializing environment for https://github.com/adrienverge/yamllint.git.
\[INFO\] Initializing environment for https://github.com/pycqa/isort.
Warning:  repo `https://github.com/pycqa/isort` uses deprecated stage names (commit, merge-commit, push) which will be removed in a future version.  Hint: often `pre-commit autoupdate --repo https://github.com/pycqa/isort` will fix this.  if it does not -- consider reporting an issue to that repo.
\[INFO\] Initializing environment for https://github.com/PyCQA/flake8.
\[INFO\] Initializing environment for https://github.com/PyCQA/flake8:Flake8-pyproject.
\[INFO\] Initializing environment for https://github.com/astral-sh/ruff-pre-commit.
\[INFO\] Initializing environment for https://github.com/executablebooks/mdformat.
\[INFO\] Initializing environment for https://github.com/executablebooks/mdformat:mdformat-gfm,mdformat_frontmatter,mdformat_footnote.
\[INFO\] Installing environment for https://github.com/pre-commit/pre-commit-hooks.
\[INFO\] Once installed this environment will be reused.
\[INFO\] This may take a few minutes...
\[INFO\] Installing environment for https://github.com/adrienverge/yamllint.git.
\[INFO\] Once installed this environment will be reused.
\[INFO\] This may take a few minutes...
\[INFO\] Installing environment for https://github.com/pycqa/isort.
\[INFO\] Once installed this environment will be reused.
\[INFO\] This may take a few minutes...
\[INFO\] Installing environment for https://github.com/PyCQA/flake8.
\[INFO\] Once installed this environment will be reused.
\[INFO\] This may take a few minutes...
\[INFO\] Installing environment for https://github.com/astral-sh/ruff-pre-commit.
\[INFO\] Once installed this environment will be reused.
\[INFO\] This may take a few minutes...
\[INFO\] Installing environment for https://github.com/executablebooks/mdformat.
\[INFO\] Once installed this environment will be reused.
\[INFO\] This may take a few minutes...
fix end of files.........................................................Passed
mixed line ending........................................................Passed
trim trailing whitespace.................................................Passed
check toml...............................................................Passed
check yaml...............................................................Passed
yamllint.................................................................Passed
isort....................................................................Passed
flake8...................................................................Failed

- hook id: flake8
- exit code: 1

property_initializer.py:61:9: F841 local variable 'bedrooms' is assigned to but never used
services/agent_service.py:80:9: F841 local variable 'p_weights' is assigned to but never used
services/agent_service.py:145:17: F841 local variable 'is_prop_allocated' is assigned to but never used
services/agent_service.py:418:9: F841 local variable 'sellers' is assigned to but never used
services/agent_service.py:529:9: F841 local variable 'new_sellers' is assigned to but never used
services/transaction_service.py:141:17: E741 ambiguous variable name 'l'
services/transaction_service.py:177:13: F401 'transaction_engine.decide_negotiation_format' imported but unused
services/transaction_service.py:180:39: E741 ambiguous variable name 'l'
services/transaction_service.py:189:17: F841 local variable 'market_hint' is assigned to but never used
simulation_runner.py:143:9: F841 local variable 'behavior_logger' is assigned to but never used
transaction_engine.py:975:1: F811 redefinition of unused 'decide_negotiation_format' from line 11

ruff.....................................................................Failed

- hook id: ruff
- exit code: 2

ruff failed
Cause: Failed to parse /home/runner/work/real-estate-simulation/real-estate-simulation/pyproject.toml
Cause: TOML parse error at line 14, column 1
|
14 | \[tool.ruff\]
| ^^^^^^^^^^^
Unknown rule selector: `W503`

mdformat.................................................................Passed
Error: Process completed with exit code 1.
