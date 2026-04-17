# UV 包和虚拟环境管理

本项目使用 [uv](https://github.com/astral-sh/uv) 进行包管理和虚拟环境管理。

## 环境信息

- Python: 3.12
- 虚拟环境: `.venv/`
- 项目名: `code`

## 常用命令

### 虚拟环境

```bash
# 激活虚拟环境
source .venv/bin/activate

# 或使用 uv 运行（无需激活）
uv run python <script.py>
```

### 包管理

```bash
# 安装包
uv add <package>

# 安装开发依赖
uv add --dev <package>

# 移除包
uv remove <package>

# 同步依赖（从 pyproject.toml）
uv sync

# 更新依赖
uv update
```

### 运行脚本

```bash
# 使用虚拟环境中的 Python 运行
uv run python <script.py>
```

## 提示

- 所有依赖安装都使用 `uv add`，不要使用 `pip`
- 提交代码时确保 `pyproject.toml` 和 `uv.lock` 一起提交
- 新开发者运行 `uv sync` 即可还原环境
