import asyncio
import sys
from typing import Dict, Any
from backend.app.services.ai_service import (
    review_url_with_ai,
    AIConfig,
    ReviewResult,
    _normalize_base_url
)


class AIConfigTester:
    def __init__(self, base_url: str, api_key: str, model: str):
        self.config = AIConfig(
            base_url=base_url,
            api_key=api_key,
            model=model
        )
        self.test_url = "https://example.com"
        self.results: Dict[str, Any] = {}

    def print_section(self, title: str):
        print("\n" + "=" * 80)
        print(f"  {title}")
        print("=" * 80)

    def print_result(self, test_name: str, passed: bool, message: str = ""):
        status = "✓ PASS" if passed else "✗ FAIL"
        print(f"\n{test_name:<50} [{status}]")
        if message:
            print(f"  {message}")
        self.results[test_name] = {"passed": passed, "message": message}

    def test_config_format(self) -> bool:
        self.print_section("配置格式验证")
        
        all_passed = True
        
        if not self.config.base_url:
            self.print_result("base_url 非空检查", False, "base_url 不能为空")
            all_passed = False
        else:
            self.print_result("base_url 非空检查", True, f"base_url: {self.config.base_url}")
        
        if not self.config.api_key:
            self.print_result("api_key 非空检查", False, "api_key 不能为空")
            all_passed = False
        else:
            masked_key = self.config.api_key[:8] + "*" * (len(self.config.api_key) - 8)
            self.print_result("api_key 非空检查", True, f"api_key: {masked_key} (长度: {len(self.config.api_key)})")
        
        if not self.config.model:
            self.print_result("model 非空检查", False, "model 不能为空")
            all_passed = False
        else:
            self.print_result("model 非空检查", True, f"model: {self.config.model}")
        
        return all_passed

    def test_url_normalization(self) -> bool:
        self.print_section("URL 规范化测试")
        
        try:
            normalized = _normalize_base_url(self.config.base_url)
            self.print_result(
                "URL 规范化", 
                True, 
                f"原始: {self.config.base_url} -> 规范化: {normalized}"
            )
            return True
        except Exception as e:
            self.print_result("URL 规范化", False, f"错误: {str(e)}")
            return False

    async def test_api_connection(self) -> bool:
        self.print_section("API 连接测试")
        
        print(f"\n正在连接到: {_normalize_base_url(self.config.base_url)}/chat/completions")
        print(f"测试模型: {self.config.model}")
        print(f"测试URL: {self.test_url}")
        print("\n请稍候，正在发送测试请求...\n")
        
        try:
            result = await review_url_with_ai(self.test_url, self.config)
            
            if result.status == "needs_manual_review":
                if "认证失败" in result.comment:
                    self.print_result("API 认证", False, result.comment)
                    return False
                elif "端点不存在" in result.comment:
                    self.print_result("API 端点", False, result.comment)
                    return False
                elif "连接失败" in result.comment:
                    self.print_result("API 连接", False, result.comment)
                    return False
                elif "请求超时" in result.comment:
                    self.print_result("API 超时", False, result.comment)
                    return False
                elif "配置不完整" in result.comment:
                    self.print_result("配置完整性", False, result.comment)
                    return False
                elif "服务调用失败" in result.comment:
                    self.print_result("API 调用", False, result.comment)
                    return False
                else:
                    self.print_result(
                        "API 响应解析", 
                        True, 
                        f"连接成功! 审核状态: {result.status}, 说明: {result.comment}"
                    )
                    return True
            else:
                self.print_result(
                    "API 完整测试", 
                    True, 
                    f"配置完全正确! 审核状态: {result.status}, 说明: {result.comment}"
                )
                return True
                
        except Exception as e:
            self.print_result("API 调用异常", False, f"发生未预期的错误: {str(e)}")
            return False

    def test_model_list(self) -> bool:
        self.print_section("常用模型参考")
        
        common_models = [
            "gpt-4",
            "gpt-4-turbo-preview",
            "gpt-4-0125-preview",
            "gpt-4-1106-preview",
            "gpt-3.5-turbo",
            "gpt-3.5-turbo-0125",
            "gpt-3.5-turbo-1106",
        ]
        
        print(f"\n当前配置模型: {self.config.model}")
        print("\n常用模型列表:")
        for model in common_models:
            marker = "  ✓" if model.lower() in self.config.model.lower() else "   "
            print(f"{marker} {model}")
        
        return True

    async def run_all_tests(self) -> Dict[str, Any]:
        self.print_section("开始 AI 配置验证测试")
        print(f"\n测试时间: {asyncio.get_event_loop().time()}")
        
        all_passed = True
        
        all_passed &= self.test_config_format()
        all_passed &= self.test_url_normalization()
        all_passed &= await self.test_api_connection()
        self.test_model_list()
        
        self.print_section("测试总结")
        
        passed_count = sum(1 for r in self.results.values() if r["passed"])
        total_count = len(self.results)
        
        print(f"\n总测试数: {total_count}")
        print(f"通过: {passed_count}")
        print(f"失败: {total_count - passed_count}")
        
        if all_passed:
            print("\n✓ 所有测试通过! AI 配置正确。")
        else:
            print("\n✗ 部分测试失败，请检查配置。")
            print("\n失败的测试:")
            for test_name, result in self.results.items():
                if not result["passed"]:
                    print(f"  - {test_name}: {result['message']}")
        
        return {
            "all_passed": all_passed,
            "results": self.results,
            "config": {
                "base_url": self.config.base_url,
                "model": self.config.model,
                "api_key_length": len(self.config.api_key)
            }
        }


async def main():
    import argparse
    
    parser = argparse.ArgumentParser(description="测试 OpenAI API 配置")
    parser.add_argument("--base-url", required=True, help="API 基础 URL")
    parser.add_argument("--api-key", required=True, help="API 密钥")
    parser.add_argument("--model", required=True, help="模型名称")
    
    args = parser.parse_args()
    
    tester = AIConfigTester(
        base_url=args.base_url,
        api_key=args.api_key,
        model=args.model
    )
    
    await tester.run_all_tests()


if __name__ == "__main__":
    asyncio.run(main())
