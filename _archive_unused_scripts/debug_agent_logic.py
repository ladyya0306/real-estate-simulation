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

import sqlite3

import pandas as pd


def analyze_logic():
    conn = sqlite3.connect(r"d:\GitProj\oasis-main\results\run_20260208_013024\simulation.db")

    # Load Data
    agents = pd.read_sql("SELECT * FROM agents_static", conn)
    finance = pd.read_sql("SELECT * FROM agents_finance", conn)
    market = pd.read_sql("SELECT * FROM properties_market", conn)
    active = pd.read_sql("SELECT * FROM active_participants", conn)

    # Merge
    df = pd.merge(agents, finance, on='agent_id')

    # Calculate Owned Properties Count
    owned = market[market['owner_id'].notna()].groupby('owner_id').size().reset_index(name='owned_count')
    df = pd.merge(df, owned, left_on='agent_id', right_on='owner_id', how='left')
    df['owned_count'] = df['owned_count'].fillna(0)

    # Merge Active Status
    # active table has: agent_id, role, llm_intent_summary
    df = pd.merge(df, active[['agent_id', 'role', 'llm_intent_summary']], on='agent_id', how='left')

    # Fill NaN for agents not in active_participants (Observer/Seller?)
    df['llm_intent_summary'] = df['llm_intent_summary'].fillna('')

    print(f"Total Agents: {len(df)}")

    # Check 1: "First Time Buyer" but owns property
    # Keywords: "刚需", "首套", "无房", "上车"
    keywords = ["刚需", "首套", "无房", "上车", "necessary"]

    inconsistent_buyers = []

    for _, row in df.iterrows():
        story = str(row['background_story']) + str(row.get('llm_intent_summary', ''))
        has_starter_keyword = any(k in story for k in keywords)

        if has_starter_keyword and row['owned_count'] > 0:
            inconsistent_buyers.append({
                'id': row['agent_id'],
                'name': row['name'],
                'owned': row['owned_count'],
                'cash': row['cash'],
                'story': row['background_story'],
                'intent': row['llm_intent_summary']
            })

    print(f"\n[Logic Check 1] 'First Time Buyer' narrative but OWNS property: {len(inconsistent_buyers)} cases")
    for case in inconsistent_buyers[:5]:
        print(f" - Agent {case['id']} ({case['name']}): Owns {case['owned']}, Cash {case['cash']:,.0f}")
        print(f"   Story: {case['story']}")
        print(f"   Intent: {case['intent']}")
        print("-" * 30)

    # Check 2: "Poor" narrative but High Cash
    # Keywords: "积蓄不多", "saving not much", "limited budget"
    poor_keywords = ["积蓄不多", "limited", "tight", "不多", "not much"]
    rich_threshold = 2000000 # 2M CNY

    rich_poor_agents = []
    for _, row in df.iterrows():
        story = str(row['background_story'])
        is_poor_narrative = any(k in story for k in poor_keywords)

        if is_poor_narrative and row['cash'] > rich_threshold:
             rich_poor_agents.append({
                'id': row['agent_id'],
                'cash': row['cash'],
                'story': row['background_story']
            })

    print(f"\n[Logic Check 2] 'Poor' narrative but High Cash (>2M): {len(rich_poor_agents)} cases")
    for case in rich_poor_agents[:5]:
        print(f" - Agent {case['id']}: Cash {case['cash']:,.0f}")
        print(f"   Story: {case['story']}")

if __name__ == "__main__":
    analyze_logic()
