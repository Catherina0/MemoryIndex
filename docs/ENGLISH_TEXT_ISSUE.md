# 英文文本识别问题诊断报告

## 🔍 问题分析

测试图片：地铁场景视频帧
- frame_00001.png: 地铁车厢内，包含多个英文标识和警告信息
- frame_00006.png: OLD STREET 地铁站标识（大号英文）

### 当前识别结果
```
frame_00006.png:
✓ 检测到: "我出现在你生命中的意义" (中文字幕)
✗ 未检测到: "OLD STREET" (主要标识)
✗ 未检测到: "THE SIGNIFICANCE OF MY PRESENCE IN YOUR LIFE" (英文字幕)
```

### 根本原因

通过调试发现，问题出在**检测阶段**，而非识别阶段：

1. **OCR检测结果**: 只检测到1个文本区域（底部中文字幕）
2. **原因**: 使用 `lang='ch'` 时，PaddleOCR 的检测模型主要针对中文文本优化
3. **英文标识特点**: 
   - 白色文字在复杂背景上
   - 字体较大但对比度相对较低
   - 非标准排版（地铁标识设计）

## 💡 解决方案

### 方案 1: 使用多语言/英文模式（推荐）

目前我们使用的是单一语言模式 `lang='ch'`，这限制了英文检测能力。

**修改方式**:

#### 1.1 在 `ocr_utils.py` 中添加多语言支持：

```python
def init_ocr_multilang(use_gpu=False, det_model="mobile", rec_model="mobile"):
    """
    初始化多语言OCR模型，同时支持中英文
    """
    ocr = PaddleOCR(
        # 尝试使用latin或en语言模型
        lang='latin',  # 或 'en'
        use_angle_cls=True,
        det_db_thresh=0.15,
        det_db_box_thresh=0.45,
        det_db_unclip_ratio=2.0,
        rec_batch_num=6,
    )
    return ocr
```

#### 1.2 或者使用两次OCR（中文一次，英文一次）：

```python
def ocr_image_bilingual(ocr_ch, ocr_en, image_path, min_score=0.25):
    """同时使用中英文OCR，合并结果"""
    # 中文OCR
    text_ch = ocr_image(ocr_ch, image_path, min_score)
    # 英文OCR
    text_en = ocr_image(ocr_en, image_path, min_score)
    # 合并结果（去重）
    return text_ch + "\n" + text_en
```

### 方案 2: 使用更精确的 Server 模型

```bash
# 使用 server 模型可能提升检测能力
make ocr VIDEO=test/test.mp4 DET_MODEL=server REC_MODEL=server
```

### 方案 3: 调整图片预处理

问题可能也与图片质量有关：
- 提高视频抽帧质量
- 增加对比度
- 二值化处理

## 🚀 立即测试

### 测试英文模式

```bash
cd /Users/catherina/Documents/GitHub/knowledge

# 测试 lang='en' 模式
python3 << 'EOF'
from paddleocr import PaddleOCR

# 初始化英文OCR
ocr_en = PaddleOCR(
    lang='en',
    use_angle_cls=True,
    det_db_thresh=0.15,
    det_db_box_thresh=0.45,
    det_db_unclip_ratio=2.0,
)

# 测试
result = ocr_en.ocr('output/test_20251211_184948/frames/frame_00006.png')
if result and len(result) > 0:
    item = result[0]
    if hasattr(item, 'get'):
        texts = item.get('rec_texts', [])
        scores = item.get('rec_scores', [])
        print(f"检测到 {len(texts)} 个文本区域:")
        for text, score in zip(texts, scores):
            print(f"  [{score:.3f}] {text}")
EOF
```

### 测试 latin 多语言模式

```bash
python3 << 'EOF'
from paddleocr import PaddleOCR

ocr = PaddleOCR(
    lang='latin',  # 支持拉丁字母（包括英文）
    use_angle_cls=True,
    det_db_thresh=0.1,  # 更低的阈值
    det_db_box_thresh=0.4,
    det_db_unclip_ratio=2.5,
)

result = ocr.ocr('output/test_20251211_184948/frames/frame_00006.png')
# 查看结果...
EOF
```

## 📝 建议的最终方案

由于这是地铁场景视频，既有中文字幕又有英文标识，建议采用**双OCR策略**：

1. **中文OCR** (`lang='ch'`) - 识别字幕
2. **英文OCR** (`lang='en'` 或 `lang='latin'`) - 识别标识
3. **合并结果** - 输出完整内容

### 实现步骤

1. 修改 `ocr_utils.py` 添加双语言支持
2. 修改 `process_video.py` 使用双OCR
3. 测试效果

## 🔧 临时解决方案

如果暂时不修改代码，可以：

```bash
# 方法1: 运行两次，一次中文，一次英文
make ocr VIDEO=test.mp4  # 中文模式
# 然后手动改 lang='en' 再运行一次

# 方法2: 使用 server 模型
make ocr VIDEO=test.mp4 DET_MODEL=server REC_MODEL=server
```

## 📊 预期效果

使用双语言模式后，预计可识别：

```
frame_00006.png (OLD STREET站):
✓ OLD STREET (主标识)
✓ 我出现在你生命中的意义 (中文字幕)
✓ THE SIGNIFICANCE OF MY PRESENCE IN YOUR LIFE (英文字幕)
✓ 其他地铁标识文字
```

---

**更新时间**: 2025-12-11  
**状态**: 待实施
