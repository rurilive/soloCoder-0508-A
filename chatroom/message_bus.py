import asyncio
import json
import time
from typing import Dict, List, Callable, Optional
from dataclasses import dataclass, field
from collections import defaultdict

try:
    import aioredis
    REDIS_AVAILABLE = True
except ImportError:
    REDIS_AVAILABLE = False


@dataclass
class Metrics:
    """性能指标收集"""
    messages_received: int = 0
    messages_sent: int = 0
    messages_broadcast: int = 0
    private_messages: int = 0
    connection_count: int = 0
    broadcast_latencies: List[float] = field(default_factory=list)
    message_latencies: List[float] = field(default_factory=list)
    
    def record_broadcast_latency(self, latency: float):
        self.broadcast_latencies.append(latency)
        if len(self.broadcast_latencies) > 1000:
            self.broadcast_latencies = self.broadcast_latencies[-1000:]
    
    def record_message_latency(self, latency: float):
        self.message_latencies.append(latency)
        if len(self.message_latencies) > 1000:
            self.message_latencies = self.message_latencies[-1000:]
    
    def get_stats(self) -> Dict:
        return {
            "messages_received": self.messages_received,
            "messages_sent": self.messages_sent,
            "messages_broadcast": self.messages_broadcast,
            "private_messages": self.private_messages,
            "connection_count": self.connection_count,
            "avg_broadcast_latency": sum(self.broadcast_latencies) / len(self.broadcast_latencies) if self.broadcast_latencies else 0,
            "avg_message_latency": sum(self.message_latencies) / len(self.message_latencies) if self.message_latencies else 0,
            "p95_broadcast_latency": sorted(self.broadcast_latencies)[int(len(self.broadcast_latencies) * 0.95)] if self.broadcast_latencies else 0,
        }


class MessageBus:
    """基于Redis Pub/Sub的消息总线，支持多实例横向扩展"""
    
    def __init__(self, redis_url: str = "redis://localhost:6379/0", use_redis: bool = None):
        self.use_redis = use_redis if use_redis is not None else REDIS_AVAILABLE
        self.redis_url = redis_url
        self.redis = None
        self.pubsub = None
        self.subscribers: Dict[str, List[Callable]] = defaultdict(list)
        self.metrics = Metrics()
        self._listen_task = None
        self._running = False
        
        # 本地消息队列（无Redis时使用）
        self.local_queues: Dict[str, asyncio.Queue] = defaultdict(asyncio.Queue)
        
        # 批量处理配置
        self.batch_size = 100
        self.batch_timeout = 0.01  # 10ms
        self._pending_batches: Dict[str, List] = defaultdict(list)
        self._batch_timers: Dict[str, Optional[asyncio.Task]] = {}
        
        # 连接健康检查
        self._health_check_interval = 30
        self._health_check_task = None
    
    async def initialize(self):
        """初始化消息总线"""
        if self.use_redis:
            try:
                self.redis = await aioredis.from_url(self.redis_url)
                self.pubsub = self.redis.pubsub()
                self._running = True
                self._listen_task = asyncio.create_task(self._listen())
                self._health_check_task = asyncio.create_task(self._health_check())
                print("MessageBus: Redis Pub/Sub initialized")
            except Exception as e:
                print(f"MessageBus: Failed to connect to Redis, using local mode: {e}")
                self.use_redis = False
        else:
            print("MessageBus: Using local mode (Redis not available)")
    
    async def close(self):
        """关闭消息总线"""
        self._running = False
        
        for timer in self._batch_timers.values():
            if timer:
                timer.cancel()
        
        if self._listen_task:
            self._listen_task.cancel()
        
        if self._health_check_task:
            self._health_check_task.cancel()
        
        if self.pubsub:
            await self.pubsub.close()
        
        if self.redis:
            await self.redis.close()
    
    async def _listen(self):
        """监听Redis消息"""
        if not self.use_redis:
            return
        
        try:
            async for message in self.pubsub.listen():
                if message["type"] == "message":
                    channel = message["channel"].decode()
                    data = json.loads(message["data"].decode())
                    self.metrics.messages_received += 1
                    
                    for callback in self.subscribers.get(channel, []):
                        try:
                            await callback(data)
                        except Exception as e:
                            print(f"MessageBus: Callback error for {channel}: {e}")
        except asyncio.CancelledError:
            pass
        except Exception as e:
            print(f"MessageBus: Listen error: {e}")
            if self._running:
                await asyncio.sleep(1)
                asyncio.create_task(self._listen())
    
    async def _health_check(self):
        """健康检查"""
        while self._running:
            try:
                if self.redis:
                    await self.redis.ping()
            except Exception as e:
                print(f"MessageBus: Health check failed: {e}")
                # 尝试重连
                try:
                    self.redis = await aioredis.from_url(self.redis_url)
                    self.pubsub = self.redis.pubsub()
                    # 重新订阅所有频道
                    for channel in self.subscribers.keys():
                        await self.pubsub.subscribe(channel)
                except Exception as e:
                    print(f"MessageBus: Reconnect failed: {e}")
            
            await asyncio.sleep(self._health_check_interval)
    
    async def subscribe(self, channel: str, callback: Callable):
        """订阅频道"""
        self.subscribers[channel].append(callback)
        
        if self.use_redis and self.pubsub:
            await self.pubsub.subscribe(channel)
    
    async def unsubscribe(self, channel: str, callback: Callable = None):
        """取消订阅"""
        if callback:
            if callback in self.subscribers[channel]:
                self.subscribers[channel].remove(callback)
        else:
            self.subscribers[channel].clear()
        
        if self.use_redis and self.pubsub and not self.subscribers[channel]:
            await self.pubsub.unsubscribe(channel)
    
    async def publish(self, channel: str, message: Dict):
        """发布消息"""
        start_time = time.time()
        
        if self.use_redis and self.redis:
            await self.redis.publish(channel, json.dumps(message))
        else:
            # 本地模式：直接放入队列
            if channel in self.subscribers:
                for callback in self.subscribers[channel]:
                    try:
                        await callback(message)
                    except Exception as e:
                        print(f"MessageBus: Local callback error: {e}")
        
        self.metrics.messages_sent += 1
        self.metrics.record_message_latency((time.time() - start_time) * 1000)
    
    async def _flush_batch(self, channel: str):
        """批量发送消息"""
        if not self._pending_batches[channel]:
            return
        
        messages = self._pending_batches[channel]
        self._pending_batches[channel] = []
        
        if self.use_redis and self.redis:
            pipeline = self.redis.pipeline()
            for msg in messages:
                pipeline.publish(channel, json.dumps(msg))
            await pipeline.execute()
        else:
            for msg in messages:
                for callback in self.subscribers.get(channel, []):
                    try:
                        await callback(msg)
                    except Exception as e:
                        print(f"MessageBus: Batch callback error: {e}")
        
        self.metrics.messages_sent += len(messages)
    
    async def publish_batched(self, channel: str, message: Dict):
        """批量发布消息"""
        self._pending_batches[channel].append(message)
        
        if len(self._pending_batches[channel]) >= self.batch_size:
            await self._flush_batch(channel)
            if channel in self._batch_timers and self._batch_timers[channel]:
                self._batch_timers[channel].cancel()
                self._batch_timers[channel] = None
        elif channel not in self._batch_timers or not self._batch_timers[channel]:
            async def flush_after_timeout():
                await asyncio.sleep(self.batch_timeout)
                await self._flush_batch(channel)
                self._batch_timers[channel] = None
            
            self._batch_timers[channel] = asyncio.create_task(flush_after_timeout())
    
    def get_metrics(self) -> Dict:
        """获取性能指标"""
        return self.metrics.get_stats()


# 全局消息总线实例
message_bus: Optional[MessageBus] = None


async def get_message_bus(redis_url: str = "redis://localhost:6379/0") -> MessageBus:
    """获取消息总线单例"""
    global message_bus
    if message_bus is None:
        message_bus = MessageBus(redis_url)
        await message_bus.initialize()
    return message_bus
