import asyncio
import sys
from typing import Optional

sys.path.insert(0, '/data/projects/work/soloCoder-0508/a')

from backend.app.services.ai_service import review_url_with_ai, AIConfig
from backend.app.database.connection import SessionLocal
from backend.app.models.ai_config import AIConfig as DBConfig


def get_ai_config_from_db() -> Optional[DBConfig]:
    db = SessionLocal()
    try:
        config = db.query(DBConfig).first()
        return config
    finally:
        db.close()


async def test_ai_config():
    print("=" * 80)
    print("  从数据库读取AI配置并测试")
    print("=" * 80)
    
    db_config = get_ai_config_from_db()
    
    if not db_config:
        print("\n✗ 数据库中没有找到AI配置")
        print("请先在管理后台配置AI参数")
        return
    
    print(f"\n读取到配置:")
    print(f"  base_url: {db_config.base_url}")
    print(f"  api_key: {db_config.api_key[:8]}***")
    print(f"  model: {db_config.model}")
    print(f"  enabled: {db_config.enabled}")
    
    config = AIConfig(
        base_url=db_config.base_url,
        api_key=db_config.api_key,
        model=db_config.model
    )
    
    test_url = "https://example.com"
    
    print(f"\n{'=' * 80}")
    print("  开始测试")
    print(f"{'=' * 80}")
    print(f"\n测试URL: {test_url}")
    print("\n请稍候...\n")
    
    result = await review_url_with_ai(test_url, config)
    
    print(f"{'=' * 80}")
    print("  测试结果")
    print(f"{'=' * 80}")
    print(f"\n审核状态: {result.status}")
    print(f"审核说明: {result.comment}")
    
    if result.status in ["approved", "rejected"]:
        print("\n✓ AI 配置正确，工作正常！")
    elif "认证失败" in result.comment:
        print("\n✗ API Key 无效，请检查配置")
    elif "端点不存在" in result.comment:
        print("\n✗ base_url 配置错误，请检查")
    elif "连接失败" in result.comment:
        print("\n✗ 无法连接到AI服务，请检查网络或base_url")
    else:
        print("\n! 需要进一步检查配置")


if __name__ == "__main__":
    asyncio.run(test_ai_config())
