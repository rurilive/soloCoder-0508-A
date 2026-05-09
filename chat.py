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

def main():
    api_url = get_env_var("API_URL", "https://api.openai.com/v1")
    api_key = get_env_var("API_KEY", required=True)
    model = get_env_var("MODEL", "gpt-3.5-turbo")
    context_size = int(get_env_var("CONTEXT_SIZE", "4096"))
    
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
    print(f"API: {api_url}")
    print("输入 'quit', 'exit' 或按 Ctrl+C 退出")
    print("-" * 50)
    
    try:
        while True:
            user_input = input("\nYou: ").strip()
            
            if not user_input:
                continue
            
            if user_input.lower() in ['quit', 'exit', 'q']:
                print("再见！")
                break
            
            messages.append({"role": "user", "content": user_input})
            
            while total_tokens > context_size and len(messages) > 4:
                removed = messages.pop(0)
                if len(removed["content"]) > 10:
                    total_tokens -= len(removed["content"]) // 4
            
            print("Assistant: ", end="", flush=True)
            assistant_response = ""
            
            try:
                stream = client.chat.completions.create(
                    model=model,
                    messages=messages,
                    stream=True
                )
                
                for chunk in stream:
                    if chunk.choices[0].delta.content:
                        content = chunk.choices[0].delta.content
                        print(content, end="", flush=True)
                        assistant_response += content
                
                print()
                
                messages.append({"role": "assistant", "content": assistant_response})
                total_tokens += (len(user_input) + len(assistant_response)) // 4
                
            except Exception as e:
                print(f"\n错误: {e}", file=sys.stderr)
                if messages and messages[-1]["role"] == "user":
                    messages.pop()
    
    except KeyboardInterrupt:
        print("\n\n再见！")

if __name__ == "__main__":
    main()
