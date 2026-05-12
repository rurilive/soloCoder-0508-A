import asyncio
import websockets
import json
import random
import time

# 测试配置
TEST_MESSAGES_COUNT = 100
WS_URL = "ws://localhost:1111/ws"
DELAY_BETWEEN_MESSAGES = 0.3  # 每条消息间隔秒数

# 昵称池
NICKNAMES = [
    "小明", "Alice", "Bob", "程序员小王", "ChatGPT",
    "测试用户1号", "David", "Emma", "前端工程师", "后端大佬",
    "产品经理", "设计师", "运维小哥", "Frank", "Grace",
    "Henry", "Ivy", "Jack", "Kate", "Leo",
    "Mia", "Nick", "Olivia", "Peter", "Queen"
]

# 消息内容模板
MESSAGE_TEMPLATES = [
    "大家好，我是{nickname}！",
    "今天天气真不错 🌞",
    "有人在吗？",
    "这个聊天室做得真不错！",
    "测试消息 #{num}",
    "Hello World! 👋",
    "Python + FastAPI + WebSocket 绝配",
    "实时消息体验太棒了！",
    "{nickname} 发来贺电",
    "数据库存储功能正常吗？",
    "第 {num} 条测试消息",
    "让我试试发送长一点的消息内容，看看显示效果怎么样，会不会自动换行或者有其他处理方式？",
    "WebSocket 连接稳定吗？",
    "收到消息的请扣1",
    "晚上吃什么好呢？🍜",
    "周末有什么安排？",
    "这个毛玻璃效果真好看",
    "深色主题护眼模式好评",
    "科技感十足！🚀",
    "测试 emoji: 😀🎉🔥💻🌟"
]

async def send_test_messages():
    """发送测试消息"""
    print(f"🚀 开始发送 {TEST_MESSAGES_COUNT} 条测试消息...")
    print(f"📍 连接到: {WS_URL}")
    print("-" * 50)
    
    try:
        async with websockets.connect(WS_URL) as websocket:
            print("✅ WebSocket 连接成功！\n")
            
            for i in range(1, TEST_MESSAGES_COUNT + 1):
                # 随机选择昵称和消息模板
                nickname = random.choice(NICKNAMES)
                template = random.choice(MESSAGE_TEMPLATES)
                
                # 生成消息内容
                content = template.format(nickname=nickname, num=i)
                
                # 偶尔加一些随机内容
                if random.random() < 0.2:
                    content += f" + 附加内容: {random.randint(1000, 9999)}"
                
                # 构建消息
                message = {
                    "nickname": nickname,
                    "content": content
                }
                
                # 发送消息
                await websocket.send(json.dumps(message))
                
                # 打印进度
                print(f"[{i:3d}/{TEST_MESSAGES_COUNT}] {nickname}: {content[:50]}{'...' if len(content) > 50 else ''}")
                
                # 等待一段时间
                await asyncio.sleep(DELAY_BETWEEN_MESSAGES)
            
            print("\n" + "-" * 50)
            print(f"✅ 成功发送 {TEST_MESSAGES_COUNT} 条消息！")
            print("💤 保持连接 5 秒后关闭...")
            
            await asyncio.sleep(5)
            
    except Exception as e:
        print(f"\n❌ 错误: {type(e).__name__}: {e}")
        return False
    
    return True

async def main():
    start_time = time.time()
    success = await send_test_messages()
    elapsed = time.time() - start_time
    
    print(f"\n⏱️  总耗时: {elapsed:.2f} 秒")
    if success:
        print("🎉 测试完成！请在浏览器中查看结果")
    else:
        print("⚠️  测试过程中出现问题")

if __name__ == "__main__":
    asyncio.run(main())
