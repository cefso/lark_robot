"""飞书机器人 echo 模版：收文本消息后回显。

配置方式（任选其一）:
  1. 把 .env.example 复制为 .env，填入 APP_ID / APP_SECRET
  2. export APP_ID=cli_xxx; export APP_SECRET=xxx

运行:
  python main.py
"""

import json
import logging
import os
from typing import Any, Optional

from dotenv import load_dotenv

import lark_oapi as lark
from lark_oapi.api.im.v1 import (
    CreateMessageRequest,
    CreateMessageRequestBody,
    P2ImMessageReceiveV1,
    ReplyMessageRequest,
    ReplyMessageRequestBody,
)

logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s %(levelname)s [%(name)s] %(message)s",
    force=True,
)
logger = logging.getLogger("echo-bot")

# 读取项目根目录下的 .env（若存在）；已有环境变量不会被覆盖
load_dotenv()

# main() 里创建，事件回调里使用
client: Optional[lark.Client] = None


def _app_id() -> str:
    return os.getenv("APP_ID") or os.getenv("FEISHU_APP_ID") or ""


def _app_secret() -> str:
    return os.getenv("APP_SECRET") or os.getenv("FEISHU_APP_SECRET") or ""


def _to_dict(obj: Any) -> Any:
    """把 SDK 对象尽量转成可打印的 dict（用于日志）。"""
    if obj is None:
        return None
    if isinstance(obj, (str, int, float, bool)):
        return obj
    if isinstance(obj, (list, tuple)):
        return [_to_dict(x) for x in obj]
    if isinstance(obj, dict):
        return {str(k): _to_dict(v) for k, v in obj.items()}
    # lark_oapi 模型一般有 lark_oapi 的序列化能力
    for attr in ("dict", "to_dict", "lark_dict"):
        fn = getattr(obj, attr, None)
        if callable(fn):
            try:
                return _to_dict(fn())
            except Exception:
                pass
    d = getattr(obj, "__dict__", None)
    if isinstance(d, dict):
        return {
            str(k): _to_dict(v)
            for k, v in d.items()
            if not k.startswith("_")
        }
    return repr(obj)


def _safe_json(data: Any) -> str:
    try:
        return json.dumps(data, ensure_ascii=False, indent=2, default=str)
    except Exception:
        return repr(data)


def log_received_event(data: P2ImMessageReceiveV1) -> None:
    """详细打印收到的事件。"""
    event = data.event
    msg = event.message
    sender = event.sender

    raw_content = msg.content
    parsed_content: Any = raw_content
    if msg.message_type == "text":
        try:
            parsed_content = json.loads(raw_content)
        except (TypeError, json.JSONDecodeError):
            parsed_content = {"_raw_content": raw_content}

    mentions = []
    for m in msg.mentions or []:
        mentions.append(_to_dict(m))

    sender_info = _to_dict(sender) if sender is not None else None
    message_info = {
        "message_id": msg.message_id,
        "root_id": getattr(msg, "root_id", None),
        "parent_id": getattr(msg, "parent_id", None),
        "chat_id": msg.chat_id,
        "chat_type": msg.chat_type,
        "message_type": msg.message_type,
        "create_time": getattr(msg, "create_time", None),
        "content": parsed_content,
        "raw_content": raw_content,
        "mentions": mentions,
    }

    logger.info("========== RECEIVED EVENT ==========")
    logger.info("event_type: %s", getattr(data.header, "event_type", "im.message.receive_v1"))
    logger.info("event_id: %s", getattr(data.header, "event_id", None))
    logger.info("sender:\n%s", _safe_json(sender_info))
    logger.info("message:\n%s", _safe_json(message_info))
    logger.info("full_event:\n%s", _safe_json(_to_dict(event)))
    logger.info("====================================")


def log_outbound(api: str, payload: dict) -> None:
    logger.info("---------- OUTBOUND SEND ----------")
    logger.info("api: %s", api)
    logger.info("payload:\n%s", _safe_json(payload))
    logger.info("------------------------------------")


def log_response(success: bool, response: Any, api: str) -> None:
    body = {
        "success": success,
        "code": getattr(response, "code", None),
        "msg": getattr(response, "msg", None),
        "log_id": response.get_log_id() if hasattr(response, "get_log_id") else None,
        "data": _to_dict(getattr(response, "data", None)),
    }
    level = logging.INFO if success else logging.ERROR
    logger.log(level, "---------- OUTBOUND RESULT (%s) ----------", api)
    logger.log(level, "response:\n%s", _safe_json(body))
    if not success and getattr(response, "msg", None):
        logger.error("send message failed: code=%s msg=%s log_id=%s",
                     body["code"], body["msg"], body["log_id"])
    logger.log(level, "-----------------------------------------")


def send_text(data: P2ImMessageReceiveV1, text: str) -> None:
    """单聊用 create，群聊用 reply（官方推荐做法）。"""
    if client is None:
        logger.error("client is not initialized")
        return

    msg = data.event.message
    content = json.dumps({"text": text}, ensure_ascii=False)

    if msg.chat_type == "p2p":
        api = "im.v1.message.create"
        payload = {
            "receive_id_type": "chat_id",
            "receive_id": msg.chat_id,
            "msg_type": "text",
            "content": json.loads(content),
            "content_raw": content,
        }
        log_outbound(api, payload)
        request = (
            CreateMessageRequest.builder()
            .receive_id_type("chat_id")
            .request_body(
                CreateMessageRequestBody.builder()
                .receive_id(msg.chat_id)
                .msg_type("text")
                .content(content)
                .build()
            )
            .build()
        )
        response = client.im.v1.message.create(request)
    else:
        api = "im.v1.message.reply"
        payload = {
            "message_id": msg.message_id,
            "msg_type": "text",
            "content": json.loads(content),
            "content_raw": content,
        }
        log_outbound(api, payload)
        request = (
            ReplyMessageRequest.builder()
            .message_id(msg.message_id)
            .request_body(
                ReplyMessageRequestBody.builder()
                .msg_type("text")
                .content(content)
                .build()
            )
            .build()
        )
        response = client.im.v1.message.reply(request)

    log_response(response.success(), response, api)


def replace_mentions(text: str, mentions) -> str:
    """把正文里的 @_user_N 占位符替换为真实显示名。"""
    for m in mentions or []:
        key = getattr(m, "key", None) or ""
        name = getattr(m, "name", None) or key
        if key:
            text = text.replace(key, f"@{name}")
    return text


def on_message_receive(data: P2ImMessageReceiveV1) -> None:
    try:
        log_received_event(data)

        msg = data.event.message

        if msg.message_type == "text":
            try:
                text = json.loads(msg.content)["text"]
            except (KeyError, json.JSONDecodeError, TypeError):
                text = ""
            text = replace_mentions(text, msg.mentions)
            reply = f"收到你发送的消息：{text}"
        else:
            reply = (
                "解析消息失败，请发送文本消息\n"
                "parse message failed, please send text message"
            )

        # 群聊只回复 @ 机器人 的消息，避免刷屏
        if msg.chat_type != "p2p":
            mentions = data.event.message.mentions or []
            if not mentions:
                logger.info(
                    "skip group message without mentions, message_id=%s",
                    msg.message_id,
                )
                return

        logger.info("reply_text: %s", reply)
        send_text(data, reply)
    except Exception:
        logger.exception("on_message_receive failed")


def main() -> None:
    global client

    app_id, app_secret = _app_id(), _app_secret()
    if not app_id or not app_secret:
        raise SystemExit("请设置 APP_ID 和 APP_SECRET 环境变量")

    logger.info(
        "config loaded: APP_ID=%s..., APP_SECRET=%s...",
        app_id[:8],
        (app_secret[:4] + "****") if app_secret else "",
    )

    client = lark.Client.builder().app_id(app_id).app_secret(app_secret).build()

    event_handler = (
        lark.EventDispatcherHandler.builder("", "")
        .register_p2_im_message_receive_v1(on_message_receive)
        .build()
    )

    ws_client = lark.ws.Client(
        app_id,
        app_secret,
        event_handler=event_handler,
        log_level=lark.LogLevel.DEBUG,
    )
    logger.info("starting feishu ws client (long connection) ...")
    ws_client.start()


if __name__ == "__main__":
    main()
