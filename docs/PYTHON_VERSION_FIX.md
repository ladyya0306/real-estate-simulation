# ⚠️ Python 版本兼容性问题解决方案

## 问题

你当前的 Python 版本是 **3.13.9**，但 Oasis 项目要求：

- ✅ **Python 3.10.x**
- ✅ **Python 3.11.x**
- ❌ **不支持 Python 3.12 及以上**

安装失败原因：`tiktoken` 包无法在 Python 3.13 上编译。

______________________________________________________________________

## 解决方案

### 方案一：使用 Anaconda/Miniconda（推荐）

这是最简单的方式，可以同时管理多个 Python 版本。

#### 步骤 1：安装 Miniconda

下载并安装：https://docs.anaconda.com/miniconda/

#### 步骤 2：创建 Python 3.10 环境

```powershell
# 创建名为 oasis 的虚拟环境，使用 Python 3.10
conda create -n oasis python=3.10 -y

# 激活环境
conda activate oasis

# 验证 Python 版本
python --version
# 应该显示：Python 3.10.x
```

#### 步骤 3：安装依赖

```powershell
# 在 oasis 环境中安装
pip install camel-ai pandas igraph cairocffi sentence-transformers neo4j

# 或者使用项目的 Poetry
cd d:\GitProj\oasis-main
pip install poetry
poetry install
```

#### 步骤 4：运行项目

```powershell
# 确保在 oasis 环境中
conda activate oasis

# 设置 API Key
$env:DEEPSEEK_API_KEY = "sk-你的密钥"

# 运行
python quick_start_deepseek.py
```

______________________________________________________________________

### 方案二：使用 pyenv-win（高级）

管理多个 Python 版本的工具。

#### 安装 pyenv-win

```powershell
# 使用 PowerShell (以管理员身份运行)
Invoke-WebRequest -UseBasicParsing -Uri "https://raw.githubusercontent.com/pyenv-win/pyenv-win/master/pyenv-win/install-pyenv-win.ps1" -OutFile "./install-pyenv-win.ps1"
./install-pyenv-win.ps1
```

#### 安装并使用 Python 3.10

```powershell
# 安装 Python 3.10
pyenv install 3.10.11

# 在项目目录设置 Python 版本
cd d:\GitProj\oasis-main
pyenv local 3.10.11

# 验证
python --version
```

______________________________________________________________________

### 方案三：使用 Python 虚拟环境（需要另外安装 Python 3.10）

如果你已经安装了 Python 3.10：

```powershell
# 使用 Python 3.10 创建虚拟环境
C:\Path\To\Python310\python.exe -m venv oasis_env

# 激活虚拟环境
.\oasis_env\Scripts\Activate.ps1

# 安装依赖
pip install camel-ai pandas igraph cairocffi sentence-transformers neo4j

# 运行
python quick_start_deepseek.py
```

______________________________________________________________________

### 方案四：修改项目代码（临时方案，不推荐）

如果你想继续使用 Python 3.13，可以尝试：

```powershell
# 安装预编译的 tiktoken（如果有）
pip install tiktoken --only-binary :all:

# 如果失败，尝试从源码安装（需要 C++ 编译器）
pip install tiktoken --no-binary :all:
```

但这可能会遇到其他兼容性问题。

______________________________________________________________________

## 推荐步骤（最快）

```powershell
# 1. 下载并安装 Miniconda
# https://docs.anaconda.com/miniconda/

# 2. 打开新的 PowerShell 窗口

# 3. 创建环境
conda create -n oasis python=3.10 -y
conda activate oasis

# 4. 进入项目目录
cd d:\GitProj\oasis-main

# 5. 安装依赖
pip install camel-ai

# 6. 设置 API Key
$env:DEEPSEEK_API_KEY = "sk-你的密钥"

# 7. 运行
python quick_start_deepseek.py
```

______________________________________________________________________

## 验证安装

安装完成后，验证：

```powershell
# 检查 Python 版本
python --version
# 应该是 3.10.x 或 3.11.x

# 检查 camel-ai
python -c "import camel; print(camel.__version__)"
# 应该输出版本号

# 检查 oasis
python -c "import oasis; print('Oasis imported successfully')"
```

______________________________________________________________________

## 常见问题

### Q: Conda 安装后找不到命令？

重新打开 PowerShell 窗口，或运行：

```powershell
C:\Users\你的用户名\miniconda3\Scripts\activate
```

### Q: 激活环境失败？

确保 PowerShell 执行策略允许运行脚本：

```powershell
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
```

### Q: 还是安装失败？

提供完整的错误信息，我可以帮你具体分析。

______________________________________________________________________

选择方案一（Conda）是最简单和推荐的方式！🎯
