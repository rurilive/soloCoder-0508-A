#!/usr/bin/env python3
"""
聊天室性能测试脚本
用于模拟高并发场景下的WebSocket连接和消息发送
"""

import asyncio
import json
import time
import statistics
import argparse
from typing import List, Dict
from dataclasses import dataclass, field
import websockets
import httpx


@dataclass
class TestResult:
    """测试结果"""
    total_connections: int = 0
    successful_connections: int = 0
    failed_connections: int = 0
    connection_times: List[float] = field(default_factory=list)
    
    total_messages_sent: int = 0
    total_messages_received: int = 0
    message_latencies: List[float] = field(default_factory=list)
    
    start_time: float = 0
    end_time: float = 0
    
    errors: List[str] = field(default_factory=list)
    
    def get_summary(self) -> Dict:
        """获取测试摘要"""
        duration = self.end_time - self.start_time
        
        return {
            "connections": {
                "total": self.total_connections,
                "successful": self.successful_connections,
                "failed": self.failed_connections,
                "success_rate": (self.successful_connections / self.total_connections * 100) if self.total_connections > 0 else 0,
                "avg_connect_time_ms": statistics.mean(self.connection_times) * 1000 if self.connection_times else 0,
                "p95_connect_time_ms": sorted(self.connection_times)[int(len(self.connection_times) * 0.95)] * 1000 if self.connection_times else 0,
            },
            "messages": {
                "sent": self.total_messages_sent,
                "received": self.total_messages_received,
                "avg_latency_ms": statistics.mean(self.message_latencies) * 1000 if self.message_latencies else 0,
                "p95_latency_ms": sorted(self.message_latencies)[int(len(self.message_latencies) * 0.95)] * 1000 if self.message_latencies else 0,
                "throughput_per_second": self.total_messages_received / duration if duration > 0 else 0,
            },
            "duration": duration,
            "errors": self.errors[:10],  # 只保留前10个错误
        }


class PerformanceTester:
    """性能测试器"""
    
    def __init__(self, host: str = "localhost", port: int = 1111, room: str = "默认房间"):
        self.host = host
        self.port = port
        self.room = room
        self.ws_url = f"ws://{host}:{port}/ws/{room}"
        self.http_url = f"http://{host}:{port}"
        self.result = TestResult()
        self.active_connections: Dict[int, websockets.WebSocketClientProtocol] = {}
        self._connection_lock = asyncio.Lock()
        
    async def connect_user(self, user_id: int) -> bool:
        """连接单个用户"""
        nickname = f"test_user_{user_id}"
        start_time = time.time()
        
        try:
            ws = await websockets.connect(f"{self.ws_url}/{nickname}")
            connect_time = time.time() - start_time
            
            async with self._connection_lock:
                self.active_connections[user_id] = ws
                self.result.successful_connections += 1
                self.result.connection_times.append(connect_time)
            
            # 等待接收初始消息（用户列表等）
            try:
                await asyncio.wait_for(ws.recv(), timeout=2.0)
            except asyncio.TimeoutError:
                pass
            
            return True
            
        except Exception as e:
            async with self._connection_lock:
                self.result.failed_connections += 1
                self.result.errors.append(f"User {user_id}: {str(e)}")
            return False
    
    async def send_messages(self, user_id: int, num_messages: int, delay: float = 0.1):
        """发送消息"""
        if user_id not in self.active_connections:
            return
        
        ws = self.active_connections[user_id]
        
        for i in range(num_messages):
            try:
                message = {
                    "content": f"Message {i} from user {user_id}",
                    "timestamp": time.time()
                }
                start_time = time.time()
                
                await ws.send(json.dumps(message))
                
                # 等待接收消息
                try:
                    response = await asyncio.wait_for(ws.recv(), timeout=5.0)
                    latency = time.time() - start_time
                    
                    async with self._connection_lock:
                        self.result.total_messages_sent += 1
                        self.result.total_messages_received += 1
                        self.result.message_latencies.append(latency)
                except asyncio.TimeoutError:
                    async with self._connection_lock:
                        self.result.total_messages_sent += 1
                except Exception as e:
                    async with self._connection_lock:
                        self.result.errors.append(f"Receive error (user {user_id}): {str(e)}")
                
                await asyncio.sleep(delay)
                
            except Exception as e:
                async with self._connection_lock:
                    self.result.errors.append(f"Send error (user {user_id}): {str(e)}")
                break
    
    async def get_server_stats(self) -> Dict:
        """获取服务器性能指标"""
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(f"{self.http_url}/api/stats/performance")
                if response.status_code == 200:
                    return response.json()
        except Exception as e:
            print(f"Failed to get server stats: {e}")
        return {}
    
    async def run_test(self, num_users: int, messages_per_user: int, message_delay: float = 0.05, ramp_up: float = 0.1):
        """运行性能测试"""
        print(f"🚀 开始性能测试: {num_users} 个用户, 每个用户发送 {messages_per_user} 条消息")
        print(f"   服务器: {self.http_url}")
        print(f"   房间: {self.room}")
        print()
        
        self.result.total_connections = num_users
        self.result.start_time = time.time()
        
        # 1. 逐步建立连接
        print(f"📡 正在建立 {num_users} 个连接...")
        connect_tasks = []
        for i in range(num_users):
            task = asyncio.create_task(self.connect_user(i))
            connect_tasks.append(task)
            await asyncio.sleep(ramp_up)  # 逐步增加负载
        
        await asyncio.gather(*connect_tasks)
        
        print(f"   ✅ 成功建立 {self.result.successful_connections} 个连接")
        print(f"   ❌ 失败 {self.result.failed_connections} 个连接")
        print()
        
        if self.result.successful_connections == 0:
            print("❌ 没有成功建立连接，测试终止")
            self.result.end_time = time.time()
            return self.result
        
        # 等待系统稳定
        await asyncio.sleep(2)
        
        # 获取初始状态
        initial_stats = await self.get_server_stats()
        
        # 2. 发送消息
        print(f"💬 开始发送消息...")
        message_tasks = []
        for user_id in self.active_connections.keys():
            task = asyncio.create_task(self.send_messages(user_id, messages_per_user, message_delay))
            message_tasks.append(task)
        
        await asyncio.gather(*message_tasks)
        
        print(f"   ✅ 发送了 {self.result.total_messages_sent} 条消息")
        print(f"   ✅ 收到了 {self.result.total_messages_received} 条消息")
        print()
        
        # 获取最终状态
        final_stats = await self.get_server_stats()
        
        # 3. 清理连接
        print("🔌 正在关闭连接...")
        for user_id, ws in list(self.active_connections.items()):
            try:
                await ws.close()
            except:
                pass
        
        self.active_connections.clear()
        self.result.end_time = time.time()
        
        # 4. 输出结果
        print()
        print("=" * 70)
        print("📊 测试结果")
        print("=" * 70)
        
        summary = self.result.get_summary()
        
        print("\n📡 连接性能:")
        print(f"   总连接数: {summary['connections']['total']}")
        print(f"   成功连接: {summary['connections']['successful']}")
        print(f"   失败连接: {summary['connections']['failed']}")
        print(f"   成功率: {summary['connections']['success_rate']:.2f}%")
        print(f"   平均连接时间: {summary['connections']['avg_connect_time_ms']:.2f}ms")
        print(f"   P95 连接时间: {summary['connections']['p95_connect_time_ms']:.2f}ms")
        
        print("\n💬 消息性能:")
        print(f"   发送消息数: {summary['messages']['sent']}")
        print(f"   接收消息数: {summary['messages']['received']}")
        print(f"   平均延迟: {summary['messages']['avg_latency_ms']:.2f}ms")
        print(f"   P95 延迟: {summary['messages']['p95_latency_ms']:.2f}ms")
        print(f"   吞吐量: {summary['messages']['throughput_per_second']:.2f} 消息/秒")
        
        print(f"\n⏱️  总测试时间: {summary['duration']:.2f} 秒")
        
        if summary['errors']:
            print(f"\n⚠️  错误数: {len(self.result.errors)}")
            for i, error in enumerate(summary['errors'][:5]):
                print(f"   {i+1}. {error}")
        
        print("\n" + "=" * 70)
        print("📡 服务器性能指标:")
        print("=" * 70)
        
        if final_stats:
            print(f"   当前连接数: {final_stats.get('connections', {}).get('total_connections', 0)}")
            print(f"   活跃房间数: {final_stats.get('connections', {}).get('active_rooms', 0)}")
            
            msg_bus = final_stats.get('message_bus', {})
            print(f"   发送消息总数: {msg_bus.get('messages_sent', 0)}")
            print(f"   广播消息数: {msg_bus.get('messages_broadcast', 0)}")
            print(f"   私信数量: {msg_bus.get('private_messages', 0)}")
            print(f"   平均消息延迟: {msg_bus.get('avg_message_latency_ms', 0):.2f}ms")
            print(f"   平均广播延迟: {msg_bus.get('avg_broadcast_latency', 0):.2f}ms")
        
        print()
        print("=" * 70)
        
        return self.result


async def run_benchmark():
    """运行基准测试套件"""
    parser = argparse.ArgumentParser(description="聊天室性能测试")
    parser.add_argument("--users", type=int, default=100, help="并发用户数")
    parser.add_argument("--messages", type=int, default=10, help="每个用户发送的消息数")
    parser.add_argument("--delay", type=float, default=0.05, help="消息发送间隔(秒)")
    parser.add_argument("--ramp-up", type=float, default=0.01, help="连接建立间隔(秒)")
    parser.add_argument("--host", type=str, default="localhost", help="服务器地址")
    parser.add_argument("--port", type=int, default=1111, help="服务器端口")
    parser.add_argument("--room", type=str, default="默认房间", help="测试房间")
    
    args = parser.parse_args()
    
    print("🎮 聊天室性能测试套件")
    print("=" * 70)
    
    tester = PerformanceTester(host=args.host, port=args.port, room=args.room)
    
    await tester.run_test(
        num_users=args.users,
        messages_per_user=args.messages,
        message_delay=args.delay,
        ramp_up=args.ramp_up
    )


async def run_load_test_series():
    """运行系列负载测试"""
    print("🏋️  负载测试系列")
    print("=" * 70)
    
    test_cases = [
        (10, 20, 0.1, "小流量测试: 10用户"),
        (50, 10, 0.05, "中流量测试: 50用户"),
        (100, 10, 0.02, "高流量测试: 100用户"),
        (200, 5, 0.01, "超高流量测试: 200用户"),
    ]
    
    results = []
    
    for num_users, messages_per_user, delay, desc in test_cases:
        print(f"\n{'='*70}")
        print(f"开始 {desc}")
        print(f"{'='*70}\n")
        
        tester = PerformanceTester()
        result = await tester.run_test(
            num_users=num_users,
            messages_per_user=messages_per_user,
            message_delay=delay,
            ramp_up=0.005
        )
        results.append((desc, result.get_summary()))
        
        # 等待服务器恢复
        await asyncio.sleep(5)
    
    # 输出汇总
    print("\n\n")
    print("=" * 80)
    print("📋 负载测试汇总")
    print("=" * 80)
    
    for desc, summary in results:
        print(f"\n{desc}:")
        print(f"  连接成功率: {summary['connections']['success_rate']:.2f}%")
        print(f"  平均消息延迟: {summary['messages']['avg_latency_ms']:.2f}ms")
        print(f"  吞吐量: {summary['messages']['throughput_per_second']:.2f} 消息/秒")
    
    print("\n" + "=" * 80)


if __name__ == "__main__":
    import sys
    
    if "--series" in sys.argv:
        asyncio.run(run_load_test_series())
    else:
        asyncio.run(run_benchmark())
