#!/usr/bin/env python3
import os
import sys
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

def main():
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
    
    messages = []
    total_tokens = 0
    
    print(f"LLM 命令行对话工具")
    print(f"模型: {model}")
    print(f"上下文大小限制: {context_size} tokens")
    print(f"思考模式: {'开启' if think_mode else '关闭'}")
    print(f"API: {api_url}")
    print("-" * 50)
    print("命令: /think on/off - 切换思考模式")
    print("      /clear - 清空对话历史")
    print("      quit/exit - 退出")
    
    try:
        while True:
            user_input = input("\nYou: ").strip()
            
            if not user_input:
                continue
            
            if user_input.lower() in ['quit', 'exit', 'q']:
                print("再见！")
                break
            
            if user_input.lower().startswith('/think'):
                parts = user_input.split()
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
            
            if user_input.lower() == '/clear':
                messages = []
                total_tokens = 0
                print("对话历史已清空")
                continue
            
            messages.append({"role": "user", "content": user_input})
            
            while total_tokens > context_size and len(messages) > 4:
                removed = messages.pop(0)
                if len(removed["content"]) > 10:
                    total_tokens -= len(removed["content"]) // 4
            
            print("Assistant: ", end="", flush=True)
            assistant_response = ""
            thinking_content = ""
            in_thinking = think_mode
            
            try:
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
                
                messages.append({"role": "assistant", "content": final_content})
                total_tokens += (len(user_input) + len(final_content)) // 4
                
            except Exception as e:
                print(f"\n错误: {e}", file=sys.stderr)
                if messages and messages[-1]["role"] == "user":
                    messages.pop()
    
    except KeyboardInterrupt:
        print("\n\n再见！")

if __name__ == "__main__":
    main()
