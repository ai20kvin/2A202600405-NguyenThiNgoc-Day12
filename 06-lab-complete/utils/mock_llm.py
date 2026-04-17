"""
Real LLM Agent — sử dụng OpenAI API.
"""
import os
import logging
from typing import List, Dict
from openai import OpenAI
from app.config import settings

logger = logging.getLogger(__name__)

# Khởi tạo client
# Lưu ý: OpenAI sẽ tự tìm biến môi trường OPENAI_API_KEY nếu không truyền vào
client = None
if settings.openai_api_key:
    client = OpenAI(api_key=settings.openai_api_key)


def ask(question: str, history: List[Dict] = None) -> str:
    """
    Gửi câu hỏi tới OpenAI và nhận câu trả lời.
    Hỗ trợ truyền lịch sử hội thoại để Agent có ngữ cảnh.
    """
    if not client:
        return "⚠️ OpenAI API Key chưa được cấu hình. Vui lòng kiểm tra lại môi trường."

    try:
        # Chuẩn bị tin nhắn cho LLM
        messages = [{"role": "system", "content": "You are a helpful and professional AI assistant."}]
        
        # Nếu có lịch sử, thêm vào tin nhắn (loại bỏ trường 'ts' không cần thiết cho OpenAI)
        if history:
            for h in history:
                messages.append({
                    "role": h["role"],
                    "content": h["content"]
                })
        else:
            # Nếu không có lịch sử, chỉ thêm câu hỏi hiện tại
            messages.append({"role": "user", "content": question})

        # Gọi OpenAI
        response = client.chat.completions.create(
            model=settings.llm_model,
            messages=messages,
            temperature=0.7,
            max_tokens=1000
        )

        return response.choices[0].message.content

    except Exception as e:
        logger.error(f"Error calling OpenAI API: {e}")
        return f"❌ Lỗi khi kết nối với AI Agent: {str(e)}"


def ask_stream(question: str, history: List[Dict] = None):
    """
    Mock streaming response — hỗ trợ tương đương nếu cần trong tương lai.
    """
    if not client:
        yield "OpenAI API Key is missing."
        return

    try:
        messages = [{"role": "system", "content": "You are a helpful AI assistant."}]
        if history:
            for h in history:
                messages.append({"role": h["role"], "content": h["content"]})
        else:
            messages.append({"role": "user", "content": question})

        stream = client.chat.completions.create(
            model=settings.llm_model,
            messages=messages,
            stream=True
        )

        for chunk in stream:
            if chunk.choices[0].delta.content:
                yield chunk.choices[0].delta.content

    except Exception as e:
        yield f"Stream error: {str(e)}"
