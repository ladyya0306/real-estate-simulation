Feat/interactive macro #12
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
fix end of files.........................................................Failed

- hook id: end-of-file-fixer
- exit code: 1
- files were modified by this hook

Fixing 交易结果/log.MD

mixed line ending........................................................Passed
trim trailing whitespace.................................................Passed
check toml...............................................................Passed
check yaml...............................................................Passed
yamllint.................................................................Passed
isort....................................................................Failed

- hook id: isort
- files were modified by this hook

Fixing /home/runner/work/real-estate-simulation/real-estate-simulation/agent_behavior.py
Fixing /home/runner/work/real-estate-simulation/real-estate-simulation/real_estate_demo_v2_1.py
Fixing /home/runner/work/real-estate-simulation/real-estate-simulation/services/agent_service.py
Fixing /home/runner/work/real-estate-simulation/real-estate-simulation/services/market_service.py
Fixing /home/runner/work/real-estate-simulation/real-estate-simulation/services/transaction_service.py
Fixing /home/runner/work/real-estate-simulation/real-estate-simulation/transaction_engine.py
Skipped 26 files

flake8...................................................................Failed

- hook id: flake8
- exit code: 1

agent_behavior.py:347:5: F841 local variable 'prompt' is assigned to but never used
agent_behavior.py:866:5: F841 local variable 'max_affordable' is assigned to but never used
agent_behavior.py:879:9: F841 local variable 'supply_demand_desc' is assigned to but never used
licenses/update_license.py:76:21: E261 at least two spaces before inline comment
licenses/update_license.py:86:101: E261 at least two spaces before inline comment
property_initializer.py:64:9: F841 local variable 'bedrooms' is assigned to but never used
property_initializer.py:131:9: F601 dictionary key 'listed_price' repeated with different values
property_initializer.py:139:9: F601 dictionary key 'listed_price' repeated with different values
services/agent_service.py:84:9: F841 local variable 'p_styles' is assigned to but never used
services/agent_service.py:85:9: F841 local variable 'p_probs' is assigned to but never used
services/agent_service.py:154:25: F841 local variable 'is_prop_allocated' is assigned to but never used
services/agent_service.py:418:9: F841 local variable 'sellers' is assigned to but never used
services/agent_service.py:529:9: F841 local variable 'new_sellers' is assigned to but never used
services/intervention_service.py:178:9: F841 local variable 'avg_area' is assigned to but never used
services/intervention_service.py:180:9: F841 local variable 'new_props' is assigned to but never used
services/intervention_service.py:216:9: F841 local variable 'removed_count' is assigned to but never used
services/intervention_service.py:290:9: F841 local variable 'updates' is assigned to but never used
services/rental_service.py:100:9: F841 local variable 'batch_status_update' is assigned to but never used
services/rental_service.py:120:13: F841 local variable 'owner_ids' is assigned to but never used
services/transaction_service.py:141:17: E741 ambiguous variable name 'l'
services/transaction_service.py:180:39: E741 ambiguous variable name 'l'
services/transaction_service.py:191:17: F841 local variable 'mode' is assigned to but never used
simulation_runner.py:143:9: F841 local variable 'behavior_logger' is assigned to but never used
tools/analyze_run_032614.py:81:30: E999 SyntaxError: unterminated string literal (detected at line 81)
transaction_engine.py:42:5: F841 local variable 'history' is assigned to but never used
transaction_engine.py:148:5: F841 local variable 'history' is assigned to but never used
transaction_engine.py:481:21: E741 ambiguous variable name 'l'
transaction_engine.py:582:5: F841 local variable 'history' is assigned to but never used
transaction_engine.py:975:1: F811 redefinition of unused 'decide_negotiation_format' from line 11
utils/exchange_display.py:12:5: F401 'rich.text.Text' imported but unused
utils/exchange_display.py:72:17: E741 ambiguous variable name 'l'
utils/exchange_display.py:96:17: E741 ambiguous variable name 'l'

ruff.....................................................................Failed

- hook id: ruff
- exit code: 2

ruff failed
Cause: Failed to parse /home/runner/work/real-estate-simulation/real-estate-simulation/pyproject.toml
Cause: TOML parse error at line 27, column 1
|
27 | \[tool.ruff\]
| ^^^^^^^^^^^
Unknown rule selector: `W503`

mdformat.................................................................Failed

- hook id: mdformat
- files were modified by this hook
  Error: Process completed with exit code 1.

CI: Enable workflow for feature branches (feat/\*) #11
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
fix end of files.........................................................Failed

- hook id: end-of-file-fixer
- exit code: 1
- files were modified by this hook

Fixing 交易结果/log.MD

mixed line ending........................................................Passed
trim trailing whitespace.................................................Passed
check toml...............................................................Passed
check yaml...............................................................Passed
yamllint.................................................................Passed
isort....................................................................Failed

- hook id: isort
- files were modified by this hook

Fixing /home/runner/work/real-estate-simulation/real-estate-simulation/agent_behavior.py
Fixing /home/runner/work/real-estate-simulation/real-estate-simulation/real_estate_demo_v2_1.py
Fixing /home/runner/work/real-estate-simulation/real-estate-simulation/services/agent_service.py
Fixing /home/runner/work/real-estate-simulation/real-estate-simulation/services/market_service.py
Fixing /home/runner/work/real-estate-simulation/real-estate-simulation/services/transaction_service.py
Fixing /home/runner/work/real-estate-simulation/real-estate-simulation/transaction_engine.py
Skipped 26 files

flake8...................................................................Failed

- hook id: flake8
- exit code: 1

agent_behavior.py:347:5: F841 local variable 'prompt' is assigned to but never used
agent_behavior.py:866:5: F841 local variable 'max_affordable' is assigned to but never used
agent_behavior.py:879:9: F841 local variable 'supply_demand_desc' is assigned to but never used
licenses/update_license.py:76:21: E261 at least two spaces before inline comment
licenses/update_license.py:86:101: E261 at least two spaces before inline comment
property_initializer.py:64:9: F841 local variable 'bedrooms' is assigned to but never used
property_initializer.py:131:9: F601 dictionary key 'listed_price' repeated with different values
property_initializer.py:139:9: F601 dictionary key 'listed_price' repeated with different values
services/agent_service.py:84:9: F841 local variable 'p_styles' is assigned to but never used
services/agent_service.py:85:9: F841 local variable 'p_probs' is assigned to but never used
services/agent_service.py:154:25: F841 local variable 'is_prop_allocated' is assigned to but never used
services/agent_service.py:418:9: F841 local variable 'sellers' is assigned to but never used
services/agent_service.py:529:9: F841 local variable 'new_sellers' is assigned to but never used
services/intervention_service.py:178:9: F841 local variable 'avg_area' is assigned to but never used
services/intervention_service.py:180:9: F841 local variable 'new_props' is assigned to but never used
services/intervention_service.py:216:9: F841 local variable 'removed_count' is assigned to but never used
services/intervention_service.py:290:9: F841 local variable 'updates' is assigned to but never used
services/rental_service.py:100:9: F841 local variable 'batch_status_update' is assigned to but never used
services/rental_service.py:120:13: F841 local variable 'owner_ids' is assigned to but never used
services/transaction_service.py:141:17: E741 ambiguous variable name 'l'
services/transaction_service.py:180:39: E741 ambiguous variable name 'l'
services/transaction_service.py:191:17: F841 local variable 'mode' is assigned to but never used
simulation_runner.py:143:9: F841 local variable 'behavior_logger' is assigned to but never used
tools/analyze_run_032614.py:81:30: E999 SyntaxError: unterminated string literal (detected at line 81)
transaction_engine.py:42:5: F841 local variable 'history' is assigned to but never used
transaction_engine.py:148:5: F841 local variable 'history' is assigned to but never used
transaction_engine.py:481:21: E741 ambiguous variable name 'l'
transaction_engine.py:582:5: F841 local variable 'history' is assigned to but never used
transaction_engine.py:975:1: F811 redefinition of unused 'decide_negotiation_format' from line 11
utils/exchange_display.py:12:5: F401 'rich.text.Text' imported but unused
utils/exchange_display.py:72:17: E741 ambiguous variable name 'l'
utils/exchange_display.py:96:17: E741 ambiguous variable name 'l'

ruff.....................................................................Failed

- hook id: ruff
- exit code: 2

ruff failed
Cause: Failed to parse /home/runner/work/real-estate-simulation/real-estate-simulation/pyproject.toml
Cause: TOML parse error at line 27, column 1
|
27 | \[tool.ruff\]
| ^^^^^^^^^^^
Unknown rule selector: `W503`

mdformat.................................................................Failed

- hook id: mdformat
- files were modified by this hook
  Error: Process completed with exit code 1.
