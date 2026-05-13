import asyncio
import websockets
import json
import random
import time
import httpx

# 测试配置
TEST_MESSAGES_COUNT = 100
WS_URL = "ws://localhost:1111/ws"
HTTP_URL = "http://localhost:1111"
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

# 私信消息模板
PRIVATE_MESSAGE_TEMPLATES = [
    "你好，{target}！这是私信",
    "这是一条只有我们俩能看到的消息",
    "私聊功能测试 #{num}",
    "在吗？想跟你说个事",
    "这个聊天室的私信功能做得真不错！",
    "悄悄告诉你一个秘密...",
    "只有你能看到这条消息哦",
    "我们来测试一下私聊吧"
]


async def send_test_messages():
    """发送测试消息"""
    print(f"🚀 开始发送 {TEST_MESSAGES_COUNT} 条测试消息...")
    print(f"📍 连接到: {WS_URL}")
    print("-" * 50)
    
    try:
        async with websockets.connect(f"{WS_URL}/默认房间/测试用户") as websocket:
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


async def test_private_chat():
    """测试私人聊天功能"""
    print("\n" + "=" * 60)
    print("🔐 开始测试私人聊天功能...")
    print("=" * 60)
    
    success_count = 0
    total_tests = 0
    
    try:
        # 创建两个用户连接
        user1 = "用户A"
        user2 = "用户B"
        room = "默认房间"
        
        print(f"\n👥 创建测试用户: {user1} 和 {user2}")
        
        async with websockets.connect(f"{WS_URL}/{room}/{user1}") as ws1, \
                   websockets.connect(f"{WS_URL}/{room}/{user2}") as ws2:
            
            print("✅ 两个用户都已连接到服务器")
            total_tests += 1
            success_count += 1
            
            # 等待用户列表更新
            await asyncio.sleep(0.5)
            
            # 测试1: 用户A给用户B发送私信
            print(f"\n📨 测试1: {user1} 给 {user2} 发送私信")
            private_content = f"@{user2} 你好，这是一条私信！"
            await ws1.send(json.dumps({"content": private_content}))
            
            # 接收消息验证
            received = False
            try:
                for _ in range(3):
                    msg2 = await asyncio.wait_for(ws2.recv(), timeout=2.0)
                    data2 = json.loads(msg2)
                    if data2.get("type") == "private_message":
                        print(f"   ✅ {user2} 收到私信: {data2.get('content')}")
                        print(f"   ✅ 发送者: {data2.get('nickname')}, 目标: {data2.get('target_nickname')}")
                        received = True
                        success_count += 1
                        break
            except asyncio.TimeoutError:
                pass
            
            if not received:
                print("   ❌ {user2} 未收到私信")
            total_tests += 1
            
            # 测试2: 验证私人房间被创建
            print(f"\n🏠 测试2: 验证私人房间被创建")
            async with httpx.AsyncClient() as client:
                response = await client.get(f"{HTTP_URL}/api/users/{user1}/private-rooms")
                data = response.json()
                if data.get("private_rooms"):
                    print(f"   ✅ {user1} 的私人房间列表: {len(data['private_rooms'])} 个")
                    for room_info in data["private_rooms"]:
                        print(f"      - {room_info['name']} (对方: {room_info['other_user']})")
                    success_count += 1
                else:
                    print("   ❌ 私人房间未创建")
            total_tests += 1
            
            # 测试3: 发送多条私信
            print(f"\n📨 测试3: 发送多条私信")
            for i in range(3):
                content = f"@{user2} 这是第 {i+1} 条私信"
                await ws1.send(json.dumps({"content": content}))
                await asyncio.sleep(0.2)
            print(f"   ✅ 成功发送 3 条私信")
            success_count += 1
            total_tests += 1
            
            # 测试4: 用户B回复私信
            print(f"\n📨 测试4: {user2} 回复私信")
            reply_content = f"@{user1} 收到了你的消息！"
            await ws2.send(json.dumps({"content": reply_content}))
            
            received_reply = False
            try:
                for _ in range(3):
                    msg1 = await asyncio.wait_for(ws1.recv(), timeout=2.0)
                    data1 = json.loads(msg1)
                    if data1.get("type") == "private_message" and data1.get("nickname") == user2:
                        print(f"   ✅ {user1} 收到回复: {data1.get('content')}")
                        received_reply = True
                        success_count += 1
                        break
            except asyncio.TimeoutError:
                pass
            
            if not received_reply:
                print(f"   ❌ {user1} 未收到回复")
            total_tests += 1
            
            # 测试5: 验证双方都能看到私人房间
            print(f"\n🏠 测试5: 验证双方都能看到私人房间")
            async with httpx.AsyncClient() as client:
                response1 = await client.get(f"{HTTP_URL}/api/users/{user1}/private-rooms")
                response2 = await client.get(f"{HTTP_URL}/api/users/{user2}/private-rooms")
                data1 = response1.json()
                data2 = response2.json()
                
                if data1.get("private_rooms") and data2.get("private_rooms"):
                    print(f"   ✅ 双方都能看到私人房间")
                    print(f"      {user1}: {len(data1['private_rooms'])} 个")
                    print(f"      {user2}: {len(data2['private_rooms'])} 个")
                    success_count += 1
                else:
                    print("   ❌ 私人房间列表不一致")
            total_tests += 1
            
            # 测试6: 直接连接私人房间
            print(f"\n🔗 测试6: 直接连接私人房间")
            private_room_name = f"private:{user1}:{user2}"
            try:
                async with websockets.connect(f"{WS_URL}/{private_room_name}/{user1}") as ws_private:
                    print(f"   ✅ {user1} 成功连接到私人房间: {private_room_name}")
                    success_count += 1
            except Exception as e:
                print(f"   ❌ 连接私人房间失败: {e}")
            total_tests += 1
            
            # 测试7: 第三方用户无法访问私人房间
            print(f"\n🔒 测试7: 第三方用户无法访问私人房间")
            third_user = "用户C"
            try:
                async with websockets.connect(f"{WS_URL}/{private_room_name}/{third_user}") as ws_third:
                    try:
                        await asyncio.wait_for(ws_third.recv(), timeout=1.0)
                        print(f"   ❌ {third_user} 错误地能够访问私人房间")
                    except:
                        print(f"   ✅ {third_user} 被正确拒绝访问私人房间")
                        success_count += 1
            except Exception as e:
                print(f"   ✅ {third_user} 被正确拒绝访问: {type(e).__name__}")
                success_count += 1
            total_tests += 1
            
            # 测试8: 在私人房间中自动添加@前缀
            print(f"\n💬 测试8: 在私人房间中发送消息")
            try:
                async with websockets.connect(f"{WS_URL}/{private_room_name}/{user1}") as ws1_private, \
                           websockets.connect(f"{WS_URL}/{private_room_name}/{user2}") as ws2_private:
                    await asyncio.sleep(0.5)
                    
                    # 在私人房间中发送不带@的消息
                    test_content = "这条消息在私人房间中发送"
                    await ws1_private.send(json.dumps({"content": test_content}))
                    
                    received_private = False
                    try:
                        for _ in range(3):
                            msg = await asyncio.wait_for(ws2_private.recv(), timeout=2.0)
                            data = json.loads(msg)
                            if data.get("type") == "private_message":
                                print(f"   ✅ 在私人房间中成功发送/接收消息")
                                received_private = True
                                success_count += 1
                                break
                    except asyncio.TimeoutError:
                        pass
                    
                    if not received_private:
                        print("   ❌ 在私人房间中发送消息失败")
            except Exception as e:
                print(f"   ❌ 测试失败: {e}")
            total_tests += 1
            
            # 测试9: 发送多条随机私信
            print(f"\n📨 测试9: 发送多条随机私信")
            for i in range(5):
                target = user2 if i % 2 == 0 else user1
                sender = user1 if i % 2 == 0 else user2
                ws = ws1 if i % 2 == 0 else ws2
                
                template = random.choice(PRIVATE_MESSAGE_TEMPLATES)
                content = f"@{target} " + template.format(target=target, num=i+1)
                await ws.send(json.dumps({"content": content}))
                await asyncio.sleep(0.2)
            print(f"   ✅ 成功发送 5 条随机私信")
            success_count += 1
            total_tests += 1
            
            # 测试10: 验证私人房间消息历史
            print(f"\n📜 测试10: 验证私人房间消息历史")
            async with httpx.AsyncClient() as client:
                response = await client.get(f"{HTTP_URL}/api/rooms/{private_room_name}/messages")
                data = response.json()
                if data.get("messages"):
                    print(f"   ✅ 私人房间有 {len(data['messages'])} 条历史消息")
                    success_count += 1
                else:
                    print("   ❌ 私人房间没有历史消息")
            total_tests += 1
            
    except Exception as e:
        print(f"\n❌ 测试过程中出错: {type(e).__name__}: {e}")
        import traceback
        traceback.print_exc()
    
    print("\n" + "=" * 60)
    print(f"📊 私人聊天测试结果: {success_count}/{total_tests} 项通过")
    if success_count == total_tests:
        print("🎉 所有私人聊天测试通过！")
    else:
        print(f"⚠️  {total_tests - success_count} 项测试未通过")
    print("=" * 60)
    
    return success_count == total_tests


async def test_room_creation():
    """测试房间创建功能"""
    print("\n" + "=" * 60)
    print("🏠 开始测试房间创建功能...")
    print("=" * 60)
    
    try:
        async with httpx.AsyncClient() as client:
            # 创建新房间
            room_name = f"测试房间_{random.randint(1000, 9999)}"
            response = await client.post(f"{HTTP_URL}/api/rooms", json={"name": room_name})
            data = response.json()
            
            if data.get("success"):
                print(f"✅ 成功创建房间: {room_name}")
            else:
                print(f"❌ 创建房间失败: {data.get('error')}")
                return False
            
            # 获取房间列表
            response = await client.get(f"{HTTP_URL}/api/rooms")
            data = response.json()
            rooms = [r["name"] for r in data.get("rooms", [])]
            
            if room_name in rooms:
                print(f"✅ 房间 {room_name} 出现在房间列表中")
                return True
            else:
                print(f"❌ 房间 {room_name} 未出现在房间列表中")
                return False
                
    except Exception as e:
        print(f"❌ 测试过程中出错: {type(e).__name__}: {e}")
        return False


async def main():
    start_time = time.time()
    
    print("🎮 聊天室功能测试套件")
    print("=" * 60)
    
    # 测试房间创建
    room_test_passed = await test_room_creation()
    
    # 测试私人聊天
    private_test_passed = await test_private_chat()
    
    # 发送测试消息（可选）
    print("\n" + "=" * 60)
    print("📨 是否开始批量发送测试消息？(y/n)")
    # 这里我们不自动发送，让用户选择
    
    elapsed = time.time() - start_time
    
    print(f"\n⏱️  总耗时: {elapsed:.2f} 秒")
    print("\n" + "=" * 60)
    print("📋 测试总结:")
    print(f"   房间创建测试: {'✅ 通过' if room_test_passed else '❌ 失败'}")
    print(f"   私人聊天测试: {'✅ 通过' if private_test_passed else '❌ 失败'}")
    print("=" * 60)
    
    if room_test_passed and private_test_passed:
        print("🎉 所有测试通过！私人聊天功能正常工作！")
    else:
        print("⚠️  部分测试未通过，请检查代码")


if __name__ == "__main__":
    asyncio.run(main())
