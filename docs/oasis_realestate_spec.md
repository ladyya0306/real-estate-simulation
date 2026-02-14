# Oasis 房地产沙盘 MVP 改造技术规格书 (V1.0)

本文档旨在规划将 Oasis 社交模拟平台改造为“虚拟房地产交易沙盘”的技术细节，作为 Vibe Coding 的执行蓝图。

## 1. 核心目标

构建一个规则透明、基于离散时间步（Step）的房地产交易实验平台，支持策略实验与 AI 决策研究。

- **阶段目标 (MVP)**: 代码无报错运行 100 个仿真步（Step），价格曲线展现基本的供需波动逻辑。
- **交付形式**: 独立模块 `oasis_realestate`，不侵入原 `oasis` 核心逻辑。

______________________________________________________________________

## 2. 业务规则定义 (Business Logic)

### 2.1 资产 (Property)

- **核心属性**:

  - `id`: 唯一标识符
  - `quality`: 品质等级 (INT: 1=低, 2=中, 3=高)
    - 价值锚点: 低 \< 300w, 中 \[300w, 500w\], 高 > 500w
  - `zone`: 区域 (ENUM: 'A', 'B', 'C')
    - A=核心城区, B=核心镇街, C=普通镇街
  - `owner_id`: 当前持有者 ID (系统初始持有或 Agent 持有)
  - `status`: 状态 (ENUM: 'off_market', 'for_sale')
  - `listed_price`: 挂牌价 (仅当 status='for_sale' 时有效)

- **初始供给**:

  - 市场启动时，部分房产分配给“初始房东”Agent，部分可设为系统持有或空置（待定，MVP 先按全部分配给初始房东简化）。

### 2.2 交易机制 (Trading Engine)

- **时间模型**:

  - 1 Step = 1 个月。
  - **并发决策**: 所有 Agent 在 Step N 读取市场状态并提交订单。
  - **统一清算**: 系统收集所有订单，在 Step N 结束时统一撮合。

- **撮合逻辑 (集合竞价简化版)**:

  - **场景**: 买家对特定房产出价 (Bid)，或对特定条件的房产出价（MVP 建议：买家直接对具体挂牌房产下 `buy_order`）。
  - **成交规则**:
    - 卖方挂单 (Sell Order) 设定 `ask_price`。
    - 买方下买单 (Buy Order) 设定 `bid_price`。
    - **规则 1**: 若 `bid_price` >= `ask_price`，则成交。
    - **规则 2 (竞争)**: 若同一房产有多个买家出价，价高者得；同价则随机。
    - **成交价**: 取 `(ask_price + bid_price) / 2` (中间价) 或直接取 `ask_price` (简化)。
      - *注*: 用户提到“买家资产是售价 1.2-1.5 倍时出手”，这是**决策逻辑**，不是**成交规则**。成交规则需确定最终价格。MVP 建议：**成交价 = 卖方挂牌价** (First come first served or Highest bid wins at ask price)。

- **租赁**: MVP 阶段**不支持**租赁。

### 2.3 智能体 (Agent)

- **角色**: 流动角色 (Owner/Buyer)。Agent 既可以是房东也可以是潜在买家。
- **资金**:
  - `cash`: 现金余额。
  - `income`: 月收入（用于偿还贷款）。
  - **贷款 (Leverage)**:
    - 首付比例: 30% (Fixed)
    - 利率: 3% (Fixed)
    - 购买力计算: `Max_Budget = Cash / 0.3` (简化，暂不考虑月供压力上限，或仅做简单校验)。

______________________________________________________________________

## 3. 技术实现路径 (Implementation)

### 3.1 目录结构

在项目根目录新建 `oasis_realestate`，结构如下：

```text
oasis_realestate/
├── __init__.py
├── agent/
│   ├── __init__.py
│   ├── real_estate_agent.py      # 继承自 BaseAgent，实现交易决策
│   └── actions.py                # 定义 MarketAction (List, Bid, Cancel)
├── platform/
│   ├── __init__.py
│   ├── real_estate_platform.py   # 继承自 BasePlatform，实现撮合与清算
│   └── database.py               # 定义新表结构
├── environment/
│   └── env.py                    # 适配房地产的 Observation 转换
└── simulation/
    └── run_simulation.py         # 启动脚本
```

### 3.2 数据库 Schema (SQL)

不再使用 `post` 等表，新建以下表 (SQLite):

```sql
-- 房产表
CREATE TABLE IF NOT EXISTS property (
    id TEXT PRIMARY KEY,
    quality INTEGER, -- 1, 2, 3
    zone TEXT,       -- 'A', 'B', 'C'
    owner_id TEXT,
    status TEXT,     -- 'off_market', 'for_sale'
    listed_price REAL,
    created_at INTEGER
);

-- 挂单表 (Order Book Snapshot)
CREATE TABLE IF NOT EXISTS market_order (
    order_id TEXT PRIMARY KEY,
    agent_id TEXT,
    property_id TEXT,
    order_type TEXT, -- 'sell', 'buy'
    price REAL,
    step_num INTEGER,
    status TEXT      -- 'active', 'filled', 'cancelled'
);

-- 交易记录表
CREATE TABLE IF NOT EXISTS transaction_history (
    tx_id TEXT PRIMARY KEY,
    property_id TEXT,
    seller_id TEXT,
    buyer_id TEXT,
    price REAL,
    step_num INTEGER,
    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- Agent 状态快照 (用于计算 Gini 等)
CREATE TABLE IF NOT EXISTS agent_metric (
    agent_id TEXT,
    step_num INTEGER,
    cash REAL,
    property_count INTEGER,
    total_asset_value REAL,
    PRIMARY KEY (agent_id, step_num)
);
```

### 3.3 Agent 决策逻辑 (Rule + LLM)

- **Input (Observation)**:

  - 市场公开挂牌列表 (Filter by Affordability)。
  - 自身资产 (Cash, Owned Properties)。
  - 近期市场均价 (Market Trends)。

- **Logic (Hybrid)**:

  1. **Rule Filter**:
     - 剔除买不起的 (Price > Cash / 0.3)。
     - 剔除明显溢价过高的 (Price > Avg_Price * 1.5)。
  1. **LLM Decision (Optional for MVP)**:
     - Prompt: "你是买家，当前市场均价 X，这套房卖 Y，位于 A 区，你的收入是 Z。是否出价？"
     - Output: `Action: Bid(property_id, price)` or `Action: Wait`.
  1. **Rule Fallback (MVP Initial)**:
     - 简单贪婪策略：如果 (Income > Mortgage) AND (Price \< Undervalued_Threshold)，则买入。

### 3.4 平台撮合逻辑 (Platform.step)

1. **Collect**: 收集本 Step 所有 `MarketAction`。
1. **Process Sells**: 更新 `property` 表状态为 `for_sale`，写入 `market_order`。
1. **Process Buys**:
   - 遍历所有 Buy Orders。
   - 检查资金是否足够 (含贷款额度)。
   - 匹配对应 Sell Order。
   - **Clearing**:
     - 扣除买家 Cash (首付)。
     - 增加卖家 Cash (全款，假设银行放款由系统瞬间完成)。
     - 更新 `property.owner_id`。
     - 记录 `transaction_history`。
1. **Metrics**: 计算并记录本 Step 的成交量、均价等。

______________________________________________________________________

## 4. 实验设计与观测

### 4.1 核心指标 (KPI)

- **计算时机**: 仿真结束后统一计算 (Post-processing)。
- **指标**:
  - `Volume`: `COUNT(transaction_history) GROUP BY step_num`
  - `Avg Price`: `AVG(price) GROUP BY step_num`
  - `Vacancy`: `COUNT(property WHERE owner_id IS NULL OR is_empty)` (需定义空置逻辑，暂忽略)
  - `Gini`: 基于 `agent_metric.total_asset_value` 计算。

### 4.2 政策干预 (Policy Intervention)

- **机制**: 在 `Platform` 类中预留 `policy_config` 字典。
- **运行时干预**:
  - 提供 `platform.update_policy(key, value)` 接口。
  - 支持在仿真循环外部调用，例如：
    ```python
    # Step 50: 增加税率
    if step == 50:
        env.platform.update_policy('tax_rate', 0.05)
    ```

______________________________________________________________________

## 5. 待确认细节 (Next Discussion)

为了完善 **3.3 Agent 决策逻辑**，我们需要深入探讨：

1. **卖方逻辑**: 房东什么时候想卖房？
   - *假设*: 资金短缺？看到房价高涨想套现？还是随机置换？
1. **买方逻辑**: 除了“买得起”，什么驱动购买？
   - *假设*: 刚需（没有房必须买）？投资（预期未来涨价）？
1. **贷款偿还**: 既然引入了贷款，是否需要每个 Step 扣除月供？如果现金不足会断供/法拍吗？
   - *MVP 建议*: 简化，只扣首付，暂不模拟月供扣款和破产，假设 Agent 收入足够覆盖。

______________________________________________________________________

**\[文档结束\]**
