# AI Agent - 基于ReAct模式的智能助手

一个基于ReAct（Reasoning + Acting）模式的Python AI Agent项目，能够自主执行任务并与环境交互。

## 功能特性

- **ReAct思维链**：结合推理和行动的智能决策模式
- **工具调用**：支持文件读写、终端命令执行等多种工具
- **交互式对话**：实时显示AI的思考过程和行动步骤
- **安全控制**：终端命令白名单机制，确保执行安全
- **可扩展架构**：易于添加新的工具和功能

## 安装

```bash
# 克隆项目
git clone https://github.com/Viveksssss/TinyAgent.git
cd agent

# 安装依赖
pip install -e .
```

或使用uv：

```bash
uv sync
```

## 配置

1. 创建 `.env` 文件：

```env
ANTHROPIC_AUTH_TOKEN=your_api_key_here
ANTHROPIC_BASE_URL=https://api.anthropic.com  # 可选，默认使用官方API
```

2. 获取API密钥：
   - 访问 [Anthropic Console](https://console.anthropic.com)
   - 创建API密钥并配置到环境变量中

## 使用方法

### 基本使用

```bash
python main.py <项目目录路径> [--model <模型名称>]
```

示例：

```bash
# 使用默认模型（glm-4.5-air）
python main.py /path/to/your/project

# 指定使用其他模型
python main.py /path/to/your/project --model claude-3-opus-20240229
```

### 交互流程

1. 启动Agent后，输入您的任务或问题
2. AI将开始思考并分解任务
3. 根据需要调用工具执行操作
4. 实时显示思考过程和执行结果
5. 最终给出答案

### 输出格式说明

Agent使用以下XML标签格式进行交互：

- `<question>` - 用户问题
- `<thought>` - AI的思考过程
- `<action>` - 执行的工具操作
- `<observation>` - 工具执行结果
- `<final_answer>` - 最终答案

## 内置工具

### 文件操作工具

- `read_file(file)` - 读取文件内容
- `write_file(file, content)` - 写入文件内容

### 系统工具

- `run_terminal_command(command)` - 执行终端命令（带白名单限制）

### 工具列表查看

Agent启动时会自动显示所有可用工具的列表，包括：
- 函数名称
- 函数签名
- 函数文档

## 开发指南

### 添加新工具

1. 在 `main.py` 中定义新函数

```python
def your_new_tool(param1, param2):
    """工具描述"""
    # 实现功能
    return result
```

2. 将函数添加到工具列表

```python
tools = [read_file, write_file, run_terminal_command, your_new_tool]
```

### 修改系统提示模板

编辑 `prompt_template.py` 文件来自定义AI的行为模式：

```python
react_system_prompt_template = """
# 自定义提示内容
"""
```

## 项目结构

```
agent/
├── main.py              # 主程序入口
├── prompt_template.py   # 系统提示模板
├── self_improvement.md  # 自我提升指南
├── README.md            # 项目文档
├── pyproject.toml       # 项目配置
├── .env.example         # 环境变量示例
└── .gitignore          # Git忽略文件
```

## 安全说明

- 终端命令执行采用白名单机制，仅允许预定义的安全命令
- 文件操作仅限当前工作目录
- 所有API调用都经过认证

## 示例任务

### 文件分析

```
请分析当前目录下所有的Python文件，统计函数数量
```

### 代码修改

```
帮我修改main.py文件，添加一个新的工具函数来计算文件行数
```

### 项目整理

```
创建一个docs目录，将所有.md文件移动到该目录下
```

## 注意事项

1. 确保API密钥安全，不要提交到版本控制
2. 在生产环境中使用时，建议添加额外的安全措施
3. Agent的思考过程可能会输出详细日志，可根据需要调整

## 贡献

欢迎提交Issue和Pull Request来改进这个项目。

## 许可证

[MIT License](LICENSE)