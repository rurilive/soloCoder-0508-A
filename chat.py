#!/usr/bin/env python3
import argparse
import os
import sys
import io
from pathlib import Path
from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()

def get_env_var(name: str, default: str = None, required: bool = False) -> str:
    value = os.getenv(name, default)
    if required and not value:
        print(f"错误: 环境变量 {name} 未设置，请检查 .env 文件", file=sys.stderr)
        sys.exit(1)
    return value

def str_to_bool(value: str) -> bool:
    return value.lower() in ('true', '1', 'yes', 'on', 't', 'y')

def read_multiline_input(prompt: str) -> str:
    print(prompt, end="", flush=True)
    lines = []
    empty_line_count = 0
    
    while True:
        try:
            line = input()
        except EOFError:
            break
        
        if line.strip() == "":
            empty_line_count += 1
            if empty_line_count >= 3:
                break
            lines.append("")
        else:
            empty_line_count = 0
            lines.append(line)
    
    return "\n".join(lines).rstrip()

def read_prompt_from_file(filename: str) -> str:
    try:
        with open(filename, 'r', encoding='utf-8') as f:
            content = f.read().rstrip('\n')
        print(f"已从文件读取 prompt: {filename}")
        return content
    except FileNotFoundError:
        print(f"错误: 文件未找到: {filename}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"读取文件时出错: {e}", file=sys.stderr)
        sys.exit(1)

def save_response_to_file(filename: str, prompt: str, response: str) -> None:
    output_path = Path(filename).stem + ".responses.md"
    try:
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write("# Prompt\n\n")
            f.write(prompt)
            f.write("\n\n# Response\n\n")
            f.write(response)
            f.write("\n")
        print(f"\n响应已保存到: {output_path}")
    except Exception as e:
        print(f"\n保存文件时出错: {e}", file=sys.stderr)

def get_chat_response(client, model, messages, think_mode, user_input):
    print("Assistant: ", end="", flush=True)
    assistant_response = ""
    thinking_content = ""
    in_thinking = think_mode
    
    stream = client.chat.completions.create(
        model=model,
        messages=messages,
        stream=True,
        **({"stream_options": {"include_usage": True}} if not think_mode else {})
    )
    
    for chunk in stream:
        if not chunk.choices:
            continue
        
        delta = chunk.choices[0].delta
        
        if hasattr(delta, 'reasoning_content') and delta.reasoning_content:
            if in_thinking and not thinking_content:
                print("\n[思考中...]", end="\n", flush=True)
            thinking_content += delta.reasoning_content
            print(delta.reasoning_content, end="", flush=True)
        elif delta.content:
            if in_thinking and thinking_content:
                print("\n--- 思考结束 ---\n", end="", flush=True)
                in_thinking = False
            content = delta.content
            print(content, end="", flush=True)
            assistant_response += content
    
    print()
    
    final_content = assistant_response
    if thinking_content:
        final_content = f"[思考过程]\n{thinking_content}\n\n[回答]\n{assistant_response}"
    
    return final_content, assistant_response

def run_file_mode(client, model, think_mode, fromfile):
    print(f"LLM 命令行对话工具 - 文件模式")
    print(f"模型: {model}")
    print(f"思考模式: {'开启' if think_mode else '关闭'}")
    print("-" * 50)
    
    user_input = read_prompt_from_file(fromfile)
    messages = [{"role": "user", "content": user_input}]
    
    print("\nPrompt:")
    print("-" * 50)
    print(user_input)
    print("-" * 50)
    
    try:
        final_content, assistant_response = get_chat_response(
            client, model, messages, think_mode, user_input
        )
        save_response_to_file(fromfile, user_input, final_content)
    except Exception as e:
        print(f"\n错误: {e}", file=sys.stderr)

def run_interactive_mode(client, model, context_size, think_mode):
    messages = []
    total_tokens = 0
    
    print(f"LLM 命令行对话工具")
    print(f"模型: {model}")
    print(f"上下文大小限制: {context_size} tokens")
    print(f"思考模式: {'开启' if think_mode else '关闭'}")
    print(f"API: {client.base_url}")
    print("-" * 50)
    print("提示: 支持多行输入，连续按 3 次回车结束输入")
    print("命令: /think on/off - 切换思考模式")
    print("      /clear - 清空对话历史")
    print("      quit/exit - 退出")
    
    try:
        while True:
            user_input = read_multiline_input("\nYou: ").rstrip('\n')
            
            if not user_input.strip():
                continue
            
            first_line = user_input.split('\n')[0].strip()
            
            if first_line.lower() in ['quit', 'exit', 'q']:
                print("再见！")
                break
            
            if first_line.lower().startswith('/think'):
                parts = first_line.split()
                if len(parts) >= 2:
                    if parts[1].lower() in ['on', '1', 'true', 'yes']:
                        think_mode = True
                        print("思考模式已开启")
                    elif parts[1].lower() in ['off', '0', 'false', 'no']:
                        think_mode = False
                        print("思考模式已关闭")
                else:
                    print(f"当前思考模式: {'开启' if think_mode else '关闭'}")
                    print("用法: /think on  或  /think off")
                continue
            
            if first_line.lower() == '/clear':
                messages = []
                total_tokens = 0
                print("对话历史已清空")
                continue
            
            messages.append({"role": "user", "content": user_input})
            
            while total_tokens > context_size and len(messages) > 4:
                removed = messages.pop(0)
                if len(removed["content"]) > 10:
                    total_tokens -= len(removed["content"]) // 4
            
            try:
                final_content, assistant_response = get_chat_response(
                    client, model, messages, think_mode, user_input
                )
                messages.append({"role": "assistant", "content": final_content})
                total_tokens += (len(user_input) + len(final_content)) // 4
                
            except Exception as e:
                print(f"\n错误: {e}", file=sys.stderr)
                if messages and messages[-1]["role"] == "user":
                    messages.pop()
    except KeyboardInterrupt:
        print("\n\n再见！")

def main():
    parser = argparse.ArgumentParser(description='LLM 命令行对话工具')
    parser.add_argument('--fromfile', type=str, help='从指定文件读取 prompt，响应保存到 filename.responses.md')
    
    args = parser.parse_args()
    
    api_url = get_env_var("API_URL", "https://api.openai.com/v1")
    api_key = get_env_var("API_KEY", required=True)
    model = get_env_var("MODEL", "gpt-3.5-turbo")
    context_size = int(get_env_var("CONTEXT_SIZE", "4096"))
    think_mode = str_to_bool(get_env_var("THINK_MODE", "false"))
    
    if not api_url.endswith("/v1"):
        api_url = api_url.rstrip("/") + "/v1"
    
    client = OpenAI(
        api_key=api_key,
        base_url=api_url
    )
    
    if args.fromfile:
        run_file_mode(client, model, think_mode, args.fromfile)
        return
    
    try:
        run_interactive_mode(client, model, context_size, think_mode)
    except KeyboardInterrupt:
        print("\n\n再见！")

if __name__ == "__main__":
    main()
