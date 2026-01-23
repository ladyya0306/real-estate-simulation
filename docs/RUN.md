# 🚀 快速运行指南

## 第一步：配置 DeepSeek API Key

1. **编辑配置文件**：
   ```bash
   # 方式 1：直接修改 .env.deepseek 文件
   # 将 sk-your-deepseek-api-key-here 替换为你的真实 API Key
   ```

2. **或者使用环境变量**（推荐）：
   ```powershell
   # Windows PowerShell
   $env:DEEPSEEK_API_KEY = "sk-你的API密钥"
   ```

   ```bash
   # Linux / macOS / Git Bash
   export DEEPSEEK_API_KEY=sk-你的API密钥
   ```

## 第二步：安装依赖

```bash
# 确保在项目根目录
cd d:\GitProj\oasis-main

# 使用 Poetry 安装（推荐）
poetry install

# 或使用 pip
pip install pandas==2.2.2 igraph==0.11.6 cairocffi==1.7.1 \
    sentence-transformers==3.0.0 neo4j==5.23.0 camel-ai==0.2.78
```

## 第三步：运行示例

```bash
# 在项目根目录运行
python quick_start_deepseek.py
```

## 预期输出

你会看到类似这样的输出：

```
🏝️ Oasis 快速启动 - DeepSeek 版本
==================================================

1️⃣ 配置 DeepSeek 模型...
✅ DeepSeek 模型配置完成

2️⃣ 定义智能体行动...

3️⃣ 创建智能体...
✅ 创建了 3 个智能体：Alice, Bob, Carol

4️⃣ 配置数据库...
✅ 数据库路径：deepseek_simulation.db

5️⃣ 创建 Oasis 环境...
✅ 环境创建成功

6️⃣ 初始化环境...
✅ 环境初始化完成

==================================================
📝 第一步：Alice 发帖...
==================================================
✅ Alice 发帖完成

==================================================
🤖 第二步：所有智能体自主行动...
==================================================
✅ 所有智能体行动完成

...（后续步骤）

✨ 运行成功！
```

## 第四步：查看结果

### 查看数据库内容

```bash
# 进入 SQLite
sqlite3 deepseek_simulation.db

# 查看所有帖子
SELECT * FROM post;

# 查看行为轨迹
SELECT * FROM trace;

# 退出
.quit
```

### 使用 Python 查看

```python
import sqlite3
import pandas as pd

conn = sqlite3.connect('deepseek_simulation.db')

# 查看帖子
posts = pd.read_sql("SELECT * FROM post", conn)
print(posts)

# 查看行为
traces = pd.read_sql("SELECT * FROM trace", conn)
print(traces)

conn.close()
```

## 常见问题

### Q1：找不到模块？
```bash
# 确认已安装 camel-ai
pip show camel-ai

# 如果没有，安装它
pip install camel-ai==0.2.78
```

### Q2：API Key 错误？
确认环境变量设置正确：
```powershell
# 检查环境变量
echo $env:DEEPSEEK_API_KEY  # PowerShell
echo $DEEPSEEK_API_KEY      # Linux/macOS
```

### Q3：运行很慢？
这是正常的，因为 LLM 需要时间推理。每个智能体的决策大约需要 1-3 秒。

## 下一步

运行成功后，你可以：

1. **修改智能体数量**：在 `quick_start_deepseek.py` 中添加更多智能体
2. **修改行动类型**：在 `available_actions` 中添加更多行动
3. **运行其他示例**：查看 `examples/` 目录
4. **查看文档**：阅读之前创建的配置指南

祝你使用愉快！🎉
