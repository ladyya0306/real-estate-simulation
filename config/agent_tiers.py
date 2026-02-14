# =========== Copyright 2023 @ CAMEL-AI.org. All Rights Reserved. ===========
# Licensed under the Apache License, Version 2.0 (the “License”);
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an “AS IS” BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
# =========== Copyright 2023 @ CAMEL-AI.org. All Rights Reserved. ===========

"""
Agent Income Tier Configuration for Million Agent Simulation
"""

AGENT_TIER_CONFIG = {
    "tier_boundaries": {  # Annual Income (CNY) lower bounds
        "ultra_high": 1000000,   # >= 100w
        "high": 500000,          # >= 50w
        "middle": 200000,        # >= 20w
        "lower_middle": 100000,  # >= 10w
        "low": 0                 # < 10w
    },

    "tier_distribution": {  # Ratio out of 100 (Population Structure)
        "ultra_high": 1,    # 1% - Elite
        "high": 9,          # 9% - Upper Class
        "middle": 30,       # 30% - Middle Class
        "lower_middle": 40, # 40% - Working Class
        "low": 20           # 20% - Low Income
    },

    # Financial Init Parameters (Random Range Multipliers based on Income)
    "init_params": {
        "ultra_high": {"cash_ratio": (5, 20), "property_count": (3, 6)},
        "high":       {"cash_ratio": (3, 10), "property_count": (1, 3)},
        "middle":     {"cash_ratio": (1, 5),  "property_count": (0, 2)},
        "lower_middle":{"cash_ratio": (0.5, 3),"property_count": (0, 1)},
        "low":        {"cash_ratio": (0, 1),  "property_count": (0, 0)}
    }
}

def get_tier_by_income(income: float) -> str:
    """Return tier name for a given income"""
    bounds = AGENT_TIER_CONFIG["tier_boundaries"]
    if income >= bounds["ultra_high"]: return "ultra_high"
    if income >= bounds["high"]: return "high"
    if income >= bounds["middle"]: return "middle"
    if income >= bounds["lower_middle"]: return "lower_middle"
    return "low"
