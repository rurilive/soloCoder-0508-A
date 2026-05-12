import httpx
import json
from typing import Optional, Dict, Any
from pydantic import BaseModel

from ..config.settings import get_logger

logger = get_logger(__name__)


class AIConfig(BaseModel):
    base_url: str
    api_key: str
    model: str


class ReviewResult(BaseModel):
    status: str
    comment: str


def _normalize_base_url(base_url: str) -> str:
    original = base_url
    base_url = base_url.rstrip('/')
    if not base_url.endswith('/v1'):
        base_url = f"{base_url}/v1"
    logger.debug(f"Normalized base URL: {original} -> {base_url}")
    return base_url


def _build_prompt(url: str) -> str:
    return f"""请审核以下URL是否合规，判断是否包含违法、有害、欺诈、色情、暴力或其他违规内容。

URL: {url}

请按照以下JSON格式返回结果（只返回JSON，不要有其他内容）：
{{
    "status": "approved" | "rejected" | "needs_manual_review",
    "comment": "审核说明，包括判断理由"
}}

审核标准：
- approved: URL内容合规，无违规内容
- rejected: URL包含明显违规内容
- needs_manual_review: 无法确定，需要人工审核"""


def _build_request_payload(model: str, prompt: str) -> Dict[str, Any]:
    return {
        "model": model,
        "messages": [
            {
                "role": "system",
                "content": "你是一个专业的内容审核员，负责审核URL链接是否合规。请严格按照要求返回JSON格式的结果。"
            },
            {
                "role": "user",
                "content": prompt
            }
        ],
        "temperature": 0.1,
        "max_tokens": 500
    }


def _parse_ai_response(content: str) -> ReviewResult:
    logger.debug(f"Parsing AI response content length: {len(content)} characters")
    logger.debug(f"Raw response content preview: {repr(content[:300])}")
    
    try:
        json_start = content.find('{')
        json_end = content.rfind('}') + 1
        
        if json_start < 0 or json_end <= json_start:
            logger.warning(f"No valid JSON object found in AI response. Content preview: {content[:200]}")
            return ReviewResult(
                status="needs_manual_review",
                comment=f"AI返回格式不正确: 未找到有效的JSON对象。原始内容: {content[:200]}"
            )
        
        json_str = content[json_start:json_end]
        logger.debug(f"Extracted JSON string: {json_str}")
        
        parsed = json.loads(json_str)
        logger.info(f"Successfully parsed AI response: {parsed}")
        
        status = parsed.get("status", "needs_manual_review")
        comment = parsed.get("comment", "AI审核结果")
        
        if status not in ["approved", "rejected", "needs_manual_review"]:
            logger.warning(f"Invalid review status from AI: '{status}'")
            return ReviewResult(
                status="needs_manual_review",
                comment=f"AI返回了无效的审核状态: '{status}'。请检查AI配置或模型是否正确。"
            )
        
        logger.info(f"AI review completed - Status: {status}, Comment: {comment[:100]}...")
        return ReviewResult(status=status, comment=comment)
        
    except json.JSONDecodeError as e:
        logger.error(f"JSON decode error: {str(e)}. Content: {content[:200]}")
        return ReviewResult(
            status="needs_manual_review",
            comment=f"AI返回结果解析失败: JSON解析错误 - {str(e)}。原始内容: {content[:200]}"
        )
    except Exception as e:
        logger.exception(f"Unexpected error parsing AI response: {str(e)}")
        return ReviewResult(
            status="needs_manual_review",
            comment=f"处理AI响应时发生未知错误: {str(e)}"
        )


def _handle_http_error(status_code: int, response_text: str = "") -> ReviewResult:
    logger.error(f"AI service returned HTTP error: {status_code}")
    logger.debug(f"Response text for error {status_code}: {response_text[:500]}")
    
    error_messages = {
        401: "AI服务认证失败: 无效的API密钥或权限不足",
        403: "AI服务访问被拒绝: 账户可能被封禁或限制",
        404: "AI服务端点不存在: 请检查base_url配置是否正确",
        429: "AI服务请求过于频繁: 已达到速率限制，请稍后重试",
        500: "AI服务内部错误: 服务器端出现问题，请稍后重试",
        502: "AI服务网关错误: 服务暂时不可用",
        503: "AI服务不可用: 服务正在维护或已下线",
        504: "AI服务超时: 网关超时，请稍后重试"
    }
    
    base_message = error_messages.get(status_code, f"AI服务调用失败: HTTP {status_code}")
    
    try:
        if response_text:
            error_detail = json.loads(response_text)
            if "error" in error_detail:
                error_info = error_detail["error"]
                if isinstance(error_info, dict):
                    error_msg = error_info.get("message", "")
                    if error_msg:
                        logger.error(f"AI service error message: {error_msg}")
                        return ReviewResult(
                            status="needs_manual_review",
                            comment=f"{base_message} - {error_msg}"
                        )
    except (json.JSONDecodeError, KeyError, TypeError) as e:
        logger.warning(f"Could not parse error response: {e}")
    
    return ReviewResult(status="needs_manual_review", comment=base_message)


async def review_url_with_ai(url: str, config: AIConfig) -> ReviewResult:
    logger.info(f"Starting AI review for URL: {url}")
    logger.info(f"AI Config - base_url: {config.base_url}, model: {config.model}")
    
    if not url:
        logger.error("Empty URL provided for review")
        return ReviewResult(status="needs_manual_review", comment="错误: 待审核的URL为空")
    
    if not config.base_url or not config.api_key or not config.model:
        logger.error(f"Invalid AI config - base_url: {bool(config.base_url)}, api_key: {bool(config.api_key)}, model: {bool(config.model)}")
        return ReviewResult(status="needs_manual_review", comment="错误: AI配置不完整，请检查base_url、api_key和model")
    
    try:
        base_url = _normalize_base_url(config.base_url)
        prompt = _build_prompt(url)
        payload = _build_request_payload(config.model, prompt)
        
        logger.debug(f"Sending request to: {base_url}/chat/completions")
        logger.debug(f"Request payload keys: {list(payload.keys())}")
        
        async with httpx.AsyncClient(timeout=60.0) as client:
            try:
                response = await client.post(
                    f"{base_url}/chat/completions",
                    headers={
                        "Authorization": f"Bearer {config.api_key}",
                        "Content-Type": "application/json"
                    },
                    json=payload
                )
                logger.info(f"AI service response status: {response.status_code}")
            except httpx.ConnectError as e:
                logger.error(f"Connection error when calling AI service: {str(e)}")
                return ReviewResult(
                    status="needs_manual_review",
                    comment=f"AI服务连接失败: 无法连接到 {config.base_url}，请检查网络连接或base_url配置"
                )
            except httpx.TimeoutException as e:
                logger.error(f"Timeout when calling AI service: {str(e)}")
                return ReviewResult(
                    status="needs_manual_review",
                    comment="AI服务请求超时: 服务器响应时间过长，请稍后重试"
                )
            except httpx.TooManyRedirects as e:
                logger.error(f"Too many redirects for AI service: {str(e)}")
                return ReviewResult(
                    status="needs_manual_review",
                    comment="AI服务重定向次数过多: 请检查base_url配置"
                )
            except httpx.RequestError as e:
                logger.error(f"Request error from AI service: {type(e).__name__} - {str(e)}")
                return ReviewResult(
                    status="needs_manual_review",
                    comment=f"AI服务请求错误: {type(e).__name__} - {str(e)}"
                )
            
            if response.status_code != 200:
                return _handle_http_error(response.status_code, response.text)
            
            try:
                result = response.json()
                logger.debug(f"AI response JSON keys: {list(result.keys())}")
            except json.JSONDecodeError as e:
                logger.error(f"Failed to parse AI JSON response: {str(e)}")
                logger.debug(f"Raw response text: {response.text[:500]}")
                return ReviewResult(
                    status="needs_manual_review",
                    comment=f"AI服务返回无效的JSON响应: HTTP 200但内容无法解析"
                )
            
            if "choices" not in result or not isinstance(result["choices"], list) or len(result["choices"]) == 0:
                logger.error(f"Missing or invalid 'choices' field in response. Available keys: {list(result.keys())}")
                return ReviewResult(
                    status="needs_manual_review",
                    comment="AI服务响应格式错误: 缺少或无效的'choices'字段"
                )
            
            choice = result["choices"][0]
            if "message" not in choice or "content" not in choice["message"]:
                logger.error(f"Missing message.content in choice. Choice keys: {list(choice.keys())}")
                return ReviewResult(
                    status="needs_manual_review",
                    comment="AI服务响应格式错误: choices中缺少'message.content'字段"
                )
            
            content = choice["message"]["content"]
            logger.info("Successfully received content from AI service, starting parsing...")
            return _parse_ai_response(content)
            
    except httpx.InvalidURL as e:
        logger.error(f"Invalid URL configuration: {config.base_url}, error: {str(e)}")
        return ReviewResult(
            status="needs_manual_review",
            comment=f"AI服务配置错误: 无效的URL '{config.base_url}'"
        )
    except ValueError as e:
        logger.error(f"Value error in AI review: {str(e)}")
        return ReviewResult(
            status="needs_manual_review",
            comment=f"AI服务配置错误: {str(e)}"
        )
    except Exception as e:
        logger.exception(f"Unexpected error in AI review process: {type(e).__name__} - {str(e)}")
        return ReviewResult(
            status="needs_manual_review",
            comment=f"AI审核过程中发生未知错误: {type(e).__name__} - {str(e)}"
        )
