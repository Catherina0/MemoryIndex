# Groq API 配置指南

## 1️⃣ 获取 Groq API Key

1. 访问 [Groq Console](https://console.groq.com/keys)
2. 登录或注册账号
3. 创建新的 API Key
4. 复制生成的 API Key

## 2️⃣ 配置环境变量

### 方法 A：编辑 .env 文件（推荐）

```bash
cd /Users/catherina/Documents/GitHub/knowledge/video_report
nano .env  # 或用其他编辑器打开
```

将 `GROQ_API_KEY` 替换为你的真实 API Key：

```env
GROQ_API_KEY=gsk_xxxxxxxxxxxxxxxxxxxxxxxxxxxx

# 可选：调整模型配置
GROQ_ASR_MODEL=whisper-large-v3-turbo
GROQ_LLM_MODEL=llama-3.3-70b-versatile
GROQ_MAX_TOKENS=4096
GROQ_TEMPERATURE=0.7
```

### 方法 B：临时设置环境变量

```bash
export GROQ_API_KEY="gsk_xxxxxxxxxxxxxxxxxxxxxxxxxxxx"
python process_video.py /path/to/video.mp4
```

## 3️⃣ 验证配置

运行一个简单测试：

```bash
cd /Users/catherina/Documents/GitHub/knowledge/video_report
source .venv/bin/activate

python3 -c "
import os
from dotenv import load_dotenv
from groq import Groq

load_dotenv()
api_key = os.getenv('GROQ_API_KEY')

if api_key:
    print('✅ API Key 已加载')
    client = Groq(api_key=api_key)
    print('✅ Groq 客户端初始化成功')
else:
    print('❌ API Key 未设置')
"
```

## 4️⃣ 使用示例

### 基础用法（音频转文字 + 总结）

```bash
python process_video.py /path/to/video.mp4
```

**流程：**
1. 提取音频 → `output/audio/xxx.wav`
2. Groq Whisper 转写 → 文本
3. Groq LLM 总结 → 报告
4. 保存到 `output/reports/xxx_report.txt`

### 完整流程（抽帧 + OCR + 总结）

```bash
python process_video.py /path/to/video.mp4 --with-frames
```

**流程：**
1. 提取音频 → Groq Whisper 转写
2. 抽帧 → PaddleOCR 识别
3. 合并音频文字 + OCR 文字
4. Groq LLM 总结 → 报告

## 5️⃣ Groq 模型说明

### 语音转文字（ASR）
- `whisper-large-v3` - 最高精度（推荐）
- `whisper-large-v3-turbo` - 更快速度，稍低精度

### 文本生成（LLM）
- `llama-3.3-70b-versatile` - 最新 Llama 3.3（推荐）
- `mixtral-8x7b-32768` - Mixtral，超长上下文
- `llama-3.1-70b-versatile` - Llama 3.1

更多模型见：https://console.groq.com/docs/models

## 6️⃣ 调整参数

编辑 `.env` 文件：

```env
# 最大输出 token 数（报告长度）
GROQ_MAX_TOKENS=4096

# 温度参数（0.0-1.0）
# 越低越保守精确，越高越有创意
GROQ_TEMPERATURE=0.7
```

## 7️⃣ 故障排查

### API Key 无效
```
错误: Authentication failed
解决: 检查 .env 中的 GROQ_API_KEY 是否正确
```

### 达到速率限制
```
错误: Rate limit exceeded
解决: 等待几分钟或升级 Groq 套餐
```

### 音频文件过大
```
错误: File size limit exceeded
解决: Groq Whisper 限制 25MB，可以先压缩音频
```

### API Key 未加载
```
⚠️  GROQ_API_KEY 未设置，使用占位符
解决: 
1. 确认 .env 文件存在
2. 确认 GROQ_API_KEY 已设置
3. 重新激活虚拟环境
```

## 8️⃣ 安全提示

⚠️ **重要：不要提交 .env 文件到 Git**

`.env` 文件已添加到 `.gitignore`，但请确保：

```bash
# 检查 .env 是否被忽略
git status

# 如果不小心添加了，移除：
git rm --cached .env
git commit -m "Remove .env from git"
```

## 9️⃣ 费用说明

Groq 提供免费额度：
- ✅ Whisper 转写：免费
- ✅ LLM 推理：每天有免费配额

查看使用情况：https://console.groq.com/settings/limits

## 🔟 完整工作流示例

```bash
# 1. 激活环境
cd /Users/catherina/Documents/GitHub/knowledge/video_report
source .venv/bin/activate

# 2. 确认 API Key
cat .env | grep GROQ_API_KEY

# 3. 处理视频
python process_video.py ~/Downloads/meeting.mp4 --with-frames

# 4. 查看结果
cat output/reports/meeting_report.txt
```

## 📚 相关链接

- [Groq Documentation](https://console.groq.com/docs)
- [Groq Python SDK](https://github.com/groq/groq-python)
- [Whisper API Reference](https://console.groq.com/docs/speech-text)
- [Chat API Reference](https://console.groq.com/docs/text-chat)
