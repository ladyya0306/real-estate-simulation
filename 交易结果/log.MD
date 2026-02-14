Feat/interactive macro #26
============================= test session starts ==============================
platform linux -- Python 3.10.11, pytest-9.0.2, pluggy-1.6.0
rootdir: /home/runner/work/real-estate-simulation/real-estate-simulation
configfile: pyproject.toml
plugins: anyio-4.12.1, asyncio-1.3.0
asyncio: mode=strict, debug=False, asyncio_default_fixture_loop_scope=None, asyncio_default_test_loop_scope=function
collected 5 items / 6 errors

==================================== ERRORS ====================================
_______ ERROR collecting _archive_unused_scripts/test_initialization.py ________
ImportError while importing test module '/home/runner/work/real-estate-simulation/real-estate-simulation/_archive_unused_scripts/test_initialization.py'.
Hint: make sure your test modules/packages have valid Python names.
Traceback:
/opt/hostedtoolcache/Python/3.10.11/x64/lib/python3.10/importlib/__init__.py:126: in import_module
    return _bootstrap._gcd_import(name[level:], package, level)
_archive_unused_scripts/test_initialization.py:9: in <module>
    from database import init_db
E   ModuleNotFoundError: No module named 'database'
__________ ERROR collecting _archive_unused_scripts/test_matching.py ___________
ImportError while importing test module '/home/runner/work/real-estate-simulation/real-estate-simulation/_archive_unused_scripts/test_matching.py'.
Hint: make sure your test modules/packages have valid Python names.
Traceback:
/opt/hostedtoolcache/Python/3.10.11/x64/lib/python3.10/importlib/__init__.py:126: in import_module
    return _bootstrap._gcd_import(name[level:], package, level)
_archive_unused_scripts/test_matching.py:8: in <module>
    from models import Agent, AgentPreference
E   ModuleNotFoundError: No module named 'models'
______ ERROR collecting _archive_unused_scripts/test_negotiation_modes.py ______
ImportError while importing test module '/home/runner/work/real-estate-simulation/real-estate-simulation/_archive_unused_scripts/test_negotiation_modes.py'.
Hint: make sure your test modules/packages have valid Python names.
Traceback:
/opt/hostedtoolcache/Python/3.10.11/x64/lib/python3.10/importlib/__init__.py:126: in import_module
    return _bootstrap._gcd_import(name[level:], package, level)
_archive_unused_scripts/test_negotiation_modes.py:5: in <module>
    from transaction_engine import run_batch_bidding_async, run_flash_deal_async
E   ModuleNotFoundError: No module named 'transaction_engine'
_____ ERROR collecting _archive_unused_scripts/test_negotiation_rounds.py ______
ImportError while importing test module '/home/runner/work/real-estate-simulation/real-estate-simulation/_archive_unused_scripts/test_negotiation_rounds.py'.
Hint: make sure your test modules/packages have valid Python names.
Traceback:
/opt/hostedtoolcache/Python/3.10.11/x64/lib/python3.10/importlib/__init__.py:126: in import_module
    return _bootstrap._gcd_import(name[level:], package, level)
_archive_unused_scripts/test_negotiation_rounds.py:9: in <module>
    from models import Agent, AgentPreference, AgentStory
E   ModuleNotFoundError: No module named 'models'
_______ ERROR collecting _archive_unused_scripts/test_preference_fix.py ________
ImportError while importing test module '/home/runner/work/real-estate-simulation/real-estate-simulation/_archive_unused_scripts/test_preference_fix.py'.
Hint: make sure your test modules/packages have valid Python names.
Traceback:
/opt/hostedtoolcache/Python/3.10.11/x64/lib/python3.10/importlib/__init__.py:126: in import_module
    return _bootstrap._gcd_import(name[level:], package, level)
_archive_unused_scripts/test_preference_fix.py:9: in <module>
    from config.config_loader import SimulationConfig
E   ModuleNotFoundError: No module named 'config'
_________ ERROR collecting _archive_unused_scripts/test_tier6_logic.py _________
ImportError while importing test module '/home/runner/work/real-estate-simulation/real-estate-simulation/_archive_unused_scripts/test_tier6_logic.py'.
Hint: make sure your test modules/packages have valid Python names.
Traceback:
/opt/hostedtoolcache/Python/3.10.11/x64/lib/python3.10/importlib/__init__.py:126: in import_module
    return _bootstrap._gcd_import(name[level:], package, level)
_archive_unused_scripts/test_tier6_logic.py:9: in <module>
    from agent_behavior import (determine_listing_strategy,
E   ModuleNotFoundError: No module named 'agent_behavior'
=========================== short test summary info ============================
ERROR _archive_unused_scripts/test_initialization.py
ERROR _archive_unused_scripts/test_matching.py
ERROR _archive_unused_scripts/test_negotiation_modes.py
ERROR _archive_unused_scripts/test_negotiation_rounds.py
ERROR _archive_unused_scripts/test_preference_fix.py
ERROR _archive_unused_scripts/test_tier6_logic.py
!!!!!!!!!!!!!!!!!!! Interrupted: 6 errors during collection !!!!!!!!!!!!!!!!!!!!
============================== 6 errors in 0.69s ===============================
Error: Process completed with exit code 2.



Add pytest to requirements.txt for CI tests #25
Run pytest
============================= test session starts ==============================
platform linux -- Python 3.10.11, pytest-9.0.2, pluggy-1.6.0
rootdir: /home/runner/work/real-estate-simulation/real-estate-simulation
configfile: pyproject.toml
plugins: anyio-4.12.1, asyncio-1.3.0
asyncio: mode=strict, debug=False, asyncio_default_fixture_loop_scope=None, asyncio_default_test_loop_scope=function
collected 5 items / 6 errors

==================================== ERRORS ====================================
_______ ERROR collecting _archive_unused_scripts/test_initialization.py ________
ImportError while importing test module '/home/runner/work/real-estate-simulation/real-estate-simulation/_archive_unused_scripts/test_initialization.py'.
Hint: make sure your test modules/packages have valid Python names.
Traceback:
/opt/hostedtoolcache/Python/3.10.11/x64/lib/python3.10/importlib/__init__.py:126: in import_module
    return _bootstrap._gcd_import(name[level:], package, level)
_archive_unused_scripts/test_initialization.py:9: in <module>
    from database import init_db
E   ModuleNotFoundError: No module named 'database'
__________ ERROR collecting _archive_unused_scripts/test_matching.py ___________
ImportError while importing test module '/home/runner/work/real-estate-simulation/real-estate-simulation/_archive_unused_scripts/test_matching.py'.
Hint: make sure your test modules/packages have valid Python names.
Traceback:
/opt/hostedtoolcache/Python/3.10.11/x64/lib/python3.10/importlib/__init__.py:126: in import_module
    return _bootstrap._gcd_import(name[level:], package, level)
_archive_unused_scripts/test_matching.py:8: in <module>
    from models import Agent, AgentPreference
E   ModuleNotFoundError: No module named 'models'
______ ERROR collecting _archive_unused_scripts/test_negotiation_modes.py ______
ImportError while importing test module '/home/runner/work/real-estate-simulation/real-estate-simulation/_archive_unused_scripts/test_negotiation_modes.py'.
Hint: make sure your test modules/packages have valid Python names.
Traceback:
/opt/hostedtoolcache/Python/3.10.11/x64/lib/python3.10/importlib/__init__.py:126: in import_module
    return _bootstrap._gcd_import(name[level:], package, level)
_archive_unused_scripts/test_negotiation_modes.py:5: in <module>
    from transaction_engine import run_batch_bidding_async, run_flash_deal_async
E   ModuleNotFoundError: No module named 'transaction_engine'
_____ ERROR collecting _archive_unused_scripts/test_negotiation_rounds.py ______
ImportError while importing test module '/home/runner/work/real-estate-simulation/real-estate-simulation/_archive_unused_scripts/test_negotiation_rounds.py'.
Hint: make sure your test modules/packages have valid Python names.
Traceback:
/opt/hostedtoolcache/Python/3.10.11/x64/lib/python3.10/importlib/__init__.py:126: in import_module
    return _bootstrap._gcd_import(name[level:], package, level)
_archive_unused_scripts/test_negotiation_rounds.py:9: in <module>
    from models import Agent, AgentPreference, AgentStory
E   ModuleNotFoundError: No module named 'models'
_______ ERROR collecting _archive_unused_scripts/test_preference_fix.py ________
ImportError while importing test module '/home/runner/work/real-estate-simulation/real-estate-simulation/_archive_unused_scripts/test_preference_fix.py'.
Hint: make sure your test modules/packages have valid Python names.
Traceback:
/opt/hostedtoolcache/Python/3.10.11/x64/lib/python3.10/importlib/__init__.py:126: in import_module
    return _bootstrap._gcd_import(name[level:], package, level)
_archive_unused_scripts/test_preference_fix.py:9: in <module>
    from config.config_loader import SimulationConfig
E   ModuleNotFoundError: No module named 'config'
_________ ERROR collecting _archive_unused_scripts/test_tier6_logic.py _________
ImportError while importing test module '/home/runner/work/real-estate-simulation/real-estate-simulation/_archive_unused_scripts/test_tier6_logic.py'.
Hint: make sure your test modules/packages have valid Python names.
Traceback:
/opt/hostedtoolcache/Python/3.10.11/x64/lib/python3.10/importlib/__init__.py:126: in import_module
    return _bootstrap._gcd_import(name[level:], package, level)
_archive_unused_scripts/test_tier6_logic.py:9: in <module>
    from agent_behavior import (determine_listing_strategy,
E   ModuleNotFoundError: No module named 'agent_behavior'
=========================== short test summary info ============================
ERROR _archive_unused_scripts/test_initialization.py
ERROR _archive_unused_scripts/test_matching.py
ERROR _archive_unused_scripts/test_negotiation_modes.py
ERROR _archive_unused_scripts/test_negotiation_rounds.py
ERROR _archive_unused_scripts/test_preference_fix.py
ERROR _archive_unused_scripts/test_tier6_logic.py
!!!!!!!!!!!!!!!!!!! Interrupted: 6 errors during collection !!!!!!!!!!!!!!!!!!!!
============================== 6 errors in 0.76s ===============================
Error: Process completed with exit code 2.