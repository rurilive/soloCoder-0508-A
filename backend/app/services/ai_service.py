import httpx
import json
from typing import Optional
from pydantic import BaseModel

class AIConfig(BaseModel):
    base_url: str
    api_key: str
    model: str

class ReviewResult(BaseModel):
    status: str
    comment: str

async def review_url_with_ai(url: str, config: AIConfig) -> ReviewResult:
    prompt = f"""请审核以下URL是否合规，判断是否包含违法、有害、欺诈、色情、暴力或其他违规内容。

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

    try:
        base_url = config.base_url.rstrip('/')
        if not base_url.endswith('/v1'):
            base_url = f"{base_url}/v1"
        
        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.post(
                f"{base_url}/chat/completions",
                headers={
                    "Authorization": f"Bearer {config.api_key}",
                    "Content-Type": "application/json"
                },
                json={
                    "model": config.model,
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
            )
            
            if response.status_code != 200:
                return ReviewResult(
                    status="needs_manual_review",
                    comment=f"AI服务调用失败: HTTP {response.status_code}"
                )
            
            result = response.json()
            content = result["choices"][0]["message"]["content"]
            
            try:
                json_start = content.find('{')
                json_end = content.rfind('}') + 1
                if json_start >= 0 and json_end > json_start:
                    json_str = content[json_start:json_end]
                    parsed = json.loads(json_str)
                    status = parsed.get("status", "needs_manual_review")
                    comment = parsed.get("comment", "AI审核结果")
                    
                    if status not in ["approved", "rejected", "needs_manual_review"]:
                        status = "needs_manual_review"
                    
                    return ReviewResult(status=status, comment=comment)
                else:
                    return ReviewResult(
                        status="needs_manual_review",
                        comment=f"AI返回格式不正确: {content[:200]}"
                    )
            except json.JSONDecodeError:
                return ReviewResult(
                    status="needs_manual_review",
                    comment=f"AI返回结果解析失败: {content[:200]}"
                )
                
    except httpx.TimeoutException:
        return ReviewResult(
            status="needs_manual_review",
            comment="AI服务请求超时"
        )
    except Exception as e:
        return ReviewResult(
            status="needs_manual_review",
            comment=f"AI审核过程中出错: {str(e)}"
        )
