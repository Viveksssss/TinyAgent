import ast
import inspect
import re
import os
from string import Template
from typing import List, Callable, Tuple
import platform

import click
from dotenv import load_dotenv
from anthropic import Anthropic

from prompt_template import react_system_prompt_template


class ReActAgent:
    def __init__(self, tools: List[Callable], model: str, project_directory: str):
        self.tools = {func.__name__: func for func in tools}
        self.model = model
        self.project_directory = project_directory
        self.client = Anthropic(
            api_key=os.getenv("ANTHROPIC_AUTH_TOKEN"),
            base_url=os.getenv("ANTHROPIC_BASE_URL"),
        )

    def run(self, user_input: str):
        print(f"\n🔄 开始处理: {user_input}")
        print("-" * 40)

        system_prompt = self.render_system_prompt(react_system_prompt_template)
        messages = [
            {
                "role": "user",
                "content": f"<question>{user_input}</question>",
            },
        ]

        while True:
            # 获取模型响应
            print(f"\n💭 AI思考中...")
            content = self.call_model(messages, system_prompt)

            # 解析思考过程
            thought_match = re.search(r"<thought>(.*?)</thought>", content, re.DOTALL)
            if thought_match:
                thought = thought_match.group(1)
                print(f"\n📍 AI思考:")
                print(thought.strip())

            # 检查是否到达最终答案
            if "<final_answer>" in content:
                final_answer = re.search(
                    r"<final_answer>(.*?)</final_answer>", content, re.DOTALL
                )
                if final_answer:
                    print("\n✅ 最终答案:")
                    print("-" * 30)
                    print(final_answer.group(1).strip())
                    print("-" * 30)
                    return final_answer.group(1)

            # 解析行动
            action_match = re.search(r"<action>(.*?)</action>", content, re.DOTALL)
            if not action_match:
                raise RuntimeError("模型未输出<action>标签")
            action = action_match.group(1)
            tool_name, args = self.parse_action(action)

            # 显示行动
            args_str = ', '.join([repr(arg) for arg in args])
            print(f"\n🔧 执行操作: {tool_name}({args_str})")
            print("-" * 30)

            # 确认执行（仅在终端命令时）
            if tool_name == "run_terminal_command":
                should_continue = input("\n继续执行? [y/N]: ").strip().lower()
                if should_continue != "y":
                    print("\n❌ 操作已取消")
                    return "操作被用户取消"

            # 执行工具
            try:
                observation = self.tools[tool_name](*args)
            except Exception as e:
                observation = f"工具执行错误: {str(e)}"

            # 显示观察结果
            print(f"\n📋 结果:")
            print(observation)
            print("-" * 30)

            # 添加到消息历史
            obs_msg = f"<observation>{observation}</observation>"
            messages.append(
                {
                    "role": "user",
                    "content": obs_msg,
                },
            )

    def parse_action(self, code_str: str) -> Tuple[str, List[str]]:
        match = re.match(r"(\w+)\((.*)\)", code_str, re.DOTALL)
        if not match:
            raise ValueError("Invalid function call syntax")

        func_name = match.group(1)
        args_str = match.group(2).strip()

        # 手动解析参数，特别处理包含多行内容的字符串
        args = []
        current_arg = ""
        in_string = False
        string_char = None
        i = 0
        paren_depth = 0

        while i < len(args_str):
            char = args_str[i]

            if not in_string:
                if char in ['"', "'"]:
                    in_string = True
                    string_char = char
                    current_arg += char
                elif char == "(":
                    paren_depth += 1
                    current_arg += char
                elif char == ")":
                    paren_depth -= 1
                    current_arg += char
                elif char == "," and paren_depth == 0:
                    # 遇到顶层逗号，结束当前参数
                    args.append(self._parse_single_arg(current_arg.strip()))
                    current_arg = ""
                else:
                    current_arg += char
            else:
                current_arg += char
                if char == string_char and (i == 0 or args_str[i - 1] != "\\"):
                    in_string = False
                    string_char = None

            i += 1

        # 添加最后一个参数
        if current_arg.strip():
            args.append(self._parse_single_arg(current_arg.strip()))

        return func_name, args

    def _parse_single_arg(self, arg_str: str):
        """解析单个参数"""
        arg_str = arg_str.strip()

        # 如果是字符串字面量
        if (arg_str.startswith('"') and arg_str.endswith('"')) or (
            arg_str.startswith("'") and arg_str.endswith("'")
        ):
            # 移除外层引号并处理转义字符
            inner_str = arg_str[1:-1]
            # 处理常见的转义字符
            inner_str = inner_str.replace('\\"', '"').replace("\\'", "'")
            inner_str = inner_str.replace("\\n", "\n").replace("\\t", "\t")
            inner_str = inner_str.replace("\\r", "\r").replace("\\\\", "\\")
            return inner_str

        # 尝试使用 ast.literal_eval 解析其他类型
        try:
            return ast.literal_eval(arg_str)
        except (SyntaxError, ValueError):
            # 如果解析失败，返回原始字符串
            return arg_str

    def get_tool_list(self) -> str:
        tool_descriptions = []
        for func in self.tools.values():
            name = func.__name__
            signature = str(inspect.signature(func))
            doc = inspect.getdoc(func)
            tool_descriptions.append(f"- {name}{signature}: {doc}")

        return "\n".join(tool_descriptions)

    def render_system_prompt(self, system_prompt_template: str) -> str:
        tool_list = self.get_tool_list()
        file_list = ", ".join(
            os.path.abspath(os.path.join(self.project_directory, f))
            for f in os.listdir(self.project_directory)
        )

        return Template(system_prompt_template).substitute(
            operating_system=self.get_operating_system_name(),
            tool_list=tool_list,
            file_list=file_list,
        )

    @staticmethod
    def get_api_key() -> str:
        api_key = os.getenv("ANTHROPIC_AUTH_TOKEN")
        if not api_key:
            raise ValueError(
                "未找到 OPENROUTER_API_KEY 环境变量，请在 .env 文件中设置。"
            )
        return api_key

    def call_model(self, messages, system_prompt) -> str:
        print("⏳ 正在与AI模型交互中，请稍候...")
        try:
            response = self.client.messages.create(
                model=self.model, max_tokens=1024, messages=messages, system=system_prompt
            )
            # 处理不同的响应类型
            if hasattr(response.content[0], 'text'):
                content = response.content[0].text
            else:
                content = str(response.content[0])
            messages.append({"role": "assistant", "content": content})
            return content
        except Exception as e:
            error_msg = f"模型调用错误: {str(e)}"
            print(f"\n❌ {error_msg}")
            raise RuntimeError(error_msg)

    def get_operating_system_name(self):
        os_map = {"Darwin": "macOS", "Windows": "Windows", "Linux": "Linux"}

        return os_map.get(platform.system(), "Unknown")


def read_file(file):
    with open(file, "r", encoding="utf-8") as f:
        return f.read()


def write_file(file, content):
    with open(file, "w", encoding="utf-8") as f:
        f.write(content.replace("\\n", "\n"))
    return "写入成功"


def list_files(directory: str) -> List[str]:
    return [f for f in os.listdir(directory) if os.path.isfile(f)]


def search_files(directory: str, pattern: str) -> List[str]:
    results = []
    for root, _, files in os.walk(directory):
        for file in files:
            if re.search(pattern, file):
                results.append(os.path.join(root, file))
    return results


def run_terminal_command(command):
    import subprocess
    import shlex
    import shutil

    # 允许的安全命令列表（根据需要扩展）
    ALLOWED_COMMANDS = {
        'ls', 'pwd', 'cd', 'cat', 'head', 'tail', 'grep', 'find',
        'echo', 'mkdir', 'rmdir', 'cp', 'mv', 'wc', 'sort', 'uniq',
        'chmod', 'chown', 'ps', 'kill', 'pkill', 'which', 'where',
        'date', 'cal', 'df', 'du', 'free', 'top', 'htop', 'man',
        'python', 'python3', 'pip', 'git', 'ssh', 'scp', 'rsync',
        'curl', 'wget', 'tar', 'gzip', 'zip', 'unzip', 'ssh',
        'ping', 'netstat', 'ss', 'lsof', 'file', 'stat'
    }

    # 白名单检查 - 只允许特定的命令
    try:
        # 解析命令
        cmd_parts = shlex.split(command)
        if not cmd_parts:
            return "错误：空命令"

        base_cmd = cmd_parts[0].split('/')[0]  # 获取基础命令名

        # 检查是否在白名单中
        if base_cmd not in ALLOWED_COMMANDS:
            return f"错误：命令 '{base_cmd}' 不在允许列表中"

        # 对于 cd 命令，需要特殊处理
        if base_cmd == 'cd':
            if len(cmd_parts) != 2:
                return "错误：cd 命令需要一个参数"
            target_path = cmd_parts[1]
            # 只允许相对路径或特定的绝对路径
            if target_path.startswith('/') and '/..' in target_path:
                return "错误：不允许访问父目录"
            try:
                os.chdir(target_path)
                return f"已切换目录到: {os.getcwd()}"
            except Exception as e:
                return f"切换目录失败: {str(e)}"

        # 对于其他命令，使用绝对路径执行
        cmd_path = cmd_parts[0]
        if not os.path.exists(cmd_path):
            # 如果不在当前目录，尝试在 PATH 中查找
            cmd_path = shutil.which(cmd_parts[0])
            if not cmd_path:
                return f"错误：找不到命令 {cmd_parts[0]}"

        # 执行命令
        result = subprocess.run(
            cmd_parts,
            timeout=30,
            capture_output=True,
            text=True,
            cwd=os.getcwd()  # 使用当前工作目录
        )

        if result.returncode == 0:
            return result.stdout or "执行成功"
        else:
            return f"错误: {result.stderr}"

    except subprocess.TimeoutExpired:
        return "错误：执行超时"
    except Exception as e:
        return f"执行错误: {str(e)}"


@click.command()
@click.argument(
    "project_directory", type=click.Path(exists=True, file_okay=False, dir_okay=True)
)
@click.option("--model", "-m", default="glm-4.5-air", help="指定使用的模型")
def main(project_directory, model):
    load_dotenv()
    project_dir = os.path.abspath(project_directory)

    tools = [read_file, write_file, run_terminal_command]

    agent = ReActAgent(tools=tools, model=model, project_directory=project_dir)

    task = input("\n📝 请输入您的任务或问题: ").strip()
    if not task:
        print("❌ 错误：任务不能为空")
        return

    final_answer = agent.run(task)

    print("\n🎉 任务完成")
    print("-" * 30)
    print("最终答案:")
    print(final_answer)
    print("-" * 30)


if __name__ == "__main__":
    main()
