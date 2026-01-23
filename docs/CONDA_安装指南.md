# Miniconda 安装和使用指南（保姆级）

## 第一步：安装 Miniconda

### 1. 双击运行安装程序

双击你下载的 `Miniconda3-xxx-Windows-x86_64.exe` 文件

### 2. 安装向导

- **Welcome 界面**：点击 `Next`
- **License Agreement**：点击 `I Agree`
- **Installation Type**：选择 `Just Me (recommended)`，点击 `Next`
- **安装路径**：保持默认即可（通常是 `C:\Users\你的用户名\miniconda3`），点击 `Next`
- **Advanced Options**：
  - ✅ **勾选**：`Add Miniconda3 to my PATH environment variable`（重要！）
  - ✅ **勾选**：`Register Miniconda3 as my default Python`
  - 点击 `Install`
- 等待安装完成，点击 `Finish`

---

## 第二步：验证安装

### 方式 1：使用 Anaconda Prompt（推荐）

1. 按 `Win` 键，搜索 **"Anaconda Prompt (miniconda3)"**
2. 点击打开，会看到黑色命令行窗口
3. 输入以下命令验证：

```bash
conda --version
```

应该显示类似：`conda 24.x.x`

### 方式 2：使用 PowerShell

1. 关闭之前的 PowerShell 窗口（如果有）
2. 重新打开 PowerShell
3. 输入：

```powershell
conda --version
```

如果显示版本号，说明安装成功！

---

## 第三步：初始化 Conda（如果需要）

如果上面的命令提示 `conda: 无法识别的命令`，在 PowerShell 中运行：

```powershell
# 初始化 conda for PowerShell
C:\Users\你的用户名\miniconda3\Scripts\conda.exe init powershell

# 关闭并重新打开 PowerShell
```

---

## 第四步：创建 Oasis 环境

现在开始创建 Python 3.10 环境！

### 在 Anaconda Prompt 或 PowerShell 中运行：

```bash
# 1. 创建名为 oasis 的环境，使用 Python 3.10
conda create -n oasis python=3.10 -y
```

会看到输出：
```
Collecting package metadata...
Solving environment...
...
Preparing transaction: done
Verifying transaction: done
Executing transaction: done
```

等待 1-2 分钟，完成后：

```bash
# 2. 激活环境
conda activate oasis
```

**成功标志**：命令提示符前面会出现 `(oasis)`，例如：
```
(oasis) PS D:\GitProj\oasis-main>
```

```bash
# 3. 验证 Python 版本
python --version
```

应该显示：`Python 3.10.x`（不再是 3.13）

---

## 第五步：安装 Oasis 依赖

确认环境是 `(oasis)` 状态下：

```bash
# 进入项目目录
cd d:\GitProj\oasis-main

# 安装 camel-ai（会自动安装其他依赖）
pip install camel-ai
```

等待安装完成（可能需要 3-5 分钟）

安装完成后验证：

```bash
# 验证 camel-ai
python -c "import camel; print('✅ camel-ai 安装成功')"

# 验证 oasis
python -c "import oasis; print('✅ oasis 可以导入')"
```

---

## 第六步：设置 DeepSeek API Key 并运行

```powershell
# 设置 API Key（替换为你的真实密钥）
$env:DEEPSEEK_API_KEY = "sk-你的DeepSeek密钥"

# 运行快速启动脚本
python quick_start_deepseek.py
```

---

## 完整命令速查（复制粘贴）

打开 **Anaconda Prompt** 或 **PowerShell**，依次运行：

```bash
# 1. 创建环境
conda create -n oasis python=3.10 -y

# 2. 激活环境
conda activate oasis

# 3. 进入项目目录
cd d:\GitProj\oasis-main

# 4. 安装依赖
pip install camel-ai

# 5. 设置 API Key（替换 sk-xxx）
$env:DEEPSEEK_API_KEY = "sk-你的密钥"

# 6. 运行
python quick_start_deepseek.py
```

---

## 常见问题

### Q1: 找不到 Anaconda Prompt？

**方法 1**：按 `Win` 键，搜索 "Anaconda Prompt"

**方法 2**：直接在普通 PowerShell 中：
```powershell
C:\Users\你的用户名\miniconda3\Scripts\activate
conda activate oasis
```

### Q2: `conda activate oasis` 报错？

PowerShell 需要初始化：
```powershell
# 运行初始化
C:\Users\你的用户名\miniconda3\Scripts\conda.exe init powershell

# 关闭并重新打开 PowerShell

# 再次尝试
conda activate oasis
```

### Q3: 每次运行都需要激活环境吗？

**是的！** 每次打开新的终端窗口，都需要运行：
```bash
conda activate oasis
```

### Q4: 如何退出 oasis 环境？

```bash
conda deactivate
```

命令提示符前的 `(oasis)` 会消失

### Q5: 如何查看所有环境？

```bash
conda env list
```

会显示：
```
# conda environments:
#
base                     C:\Users\xxx\miniconda3
oasis                 *  C:\Users\xxx\miniconda3\envs\oasis
```

星号 `*` 表示当前激活的环境

---

## 快速操作清单

✅ 安装 Miniconda  
✅ 打开 Anaconda Prompt 或 PowerShell  
✅ 运行 `conda create -n oasis python=3.10 -y`  
✅ 运行 `conda activate oasis`  
✅ 确认提示符显示 `(oasis)`  
✅ 运行 `cd d:\GitProj\oasis-main`  
✅ 运行 `pip install camel-ai`  
✅ 设置 `$env:DEEPSEEK_API_KEY = "sk-xxx"`  
✅ 运行 `python quick_start_deepseek.py`  

---

## 下一次使用

之后每次使用 Oasis，只需要：

```bash
# 1. 打开 Anaconda Prompt 或 PowerShell
# 2. 激活环境
conda activate oasis

# 3. 进入项目
cd d:\GitProj\oasis-main

# 4. 设置 API Key
$env:DEEPSEEK_API_KEY = "sk-你的密钥"

# 5. 运行脚本
python quick_start_deepseek.py
```

---

现在可以开始了！🚀
