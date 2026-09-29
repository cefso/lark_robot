# 飞书 Echo 机器人（lark_robot）

基于 `lark_oapi` 的飞书机器人模版：WebSocket 长连接接收消息，OpenAPI 回显文本。

## 功能

- 长连接订阅 `im.message.receive_v1`（无需公网回调地址）
- 单聊（`p2p`）：`message.create` 发送
- 群聊：`message.reply` 回复 **@机器人** 的消息
- 文本消息回显；非文本提示改发文本
- 将正文中的 `@_user_N` 占位符替换为真实显示名
- 收 / 发两侧详细日志（事件、payload、API 响应）

## 环境要求

- Python 3.8+
- 飞书开放平台应用（需开启机器人能力，并具备接收 / 发送消息相关权限）

## 快速开始

```bash
# 1. 安装依赖
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# 2. 配置凭证
cp .env.example .env
# 编辑 .env，填入 APP_ID、APP_SECRET

# 3. 运行
python main.py
```

也可用环境变量（会覆盖 `.env` 中的同名项，因 `load_dotenv` 默认不覆盖已有变量）：

```bash
export APP_ID=cli_xxxxxxxxxxxxxxxx
export APP_SECRET=xxxxxxxxxxxxxxxx
python main.py
```

## 配置说明

| 变量 | 说明 |
|------|------|
| `APP_ID` 或 `FEISHU_APP_ID` | 应用 App ID |
| `APP_SECRET` 或 `FEISHU_APP_SECRET` | 应用 App Secret |

本地密钥写在 `.env` 中，已由 `.gitignore` 忽略，**不要提交到仓库**。

## 开放平台侧

1. 创建企业自建应用，获取 App ID / App Secret
2. 添加「机器人」应用能力
3. 开通接收消息、发送消息等 `im` 相关权限
4. 发布版本并在群聊 / 单聊中使用机器人

## 项目结构

```text
.
├── main.py            # 机器人主程序
├── requirements.txt   # Python 依赖
├── .env.example       # 环境变量样例（复制为 .env 后填写）
└── .gitignore
```

## 消息处理约定

| 场景 | 行为 |
|------|------|
| 单聊文本 | 回显：`收到你发送的消息：...` |
| 群聊且 @机器人 | 同上，使用回复接口 |
| 群聊未 @ | 忽略，避免刷屏 |
| 非文本消息 | 提示发送文本消息 |

## 参考

- [使用长连接接收事件](https://open.feishu.cn/document/uAjLw4CM/ukTMukTMukTM/reference/im-v1/message/events/receive)
- [发送消息](https://open.feishu.cn/document/uAjLw4CM/ukTMukTMukTM/reference/im-v1/message/create)
- [回复消息](https://open.larkoffice.com/document/server-docs/im-v1/message/reply)
