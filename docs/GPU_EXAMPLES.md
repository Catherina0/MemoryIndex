# GPU 加速使用示例

本文档提供 GPU 加速 OCR 功能的快速使用示例。

## 🚀 快速开始

### 1. 检测 GPU 可用性

```bash
python test_gpu.py
```

输出示例：
```
======================================================================
🔍 GPU 检测测试
======================================================================
✅ GPU 可用！将使用GPU加速
```

或者：
```
⚠️ GPU 不可用，将使用CPU模式
```

### 2. 处理视频（启用 GPU）

```bash
# 基础用法
python process_video.py video.mp4 --with-frames --use-gpu

# 完整参数
python process_video.py video.mp4 \
    --with-frames \
    --use-gpu \
    --ocr-det-model server \
    --ocr-rec-model server
```

### 3. 单图片 OCR（双语言模式）

```bash
# 自动检测 GPU
python ocr_bilingual.py image.png

# 强制使用 GPU
python ocr_bilingual.py image.png --gpu --debug

# 强制使用 CPU
python ocr_bilingual.py image.png --cpu
```

### 4. 性能对比测试

```bash
# CPU vs GPU 性能对比
python test_gpu.py image.png --compare
```

## 📝 代码示例

### 示例 1: 自动检测 GPU

```python
from ocr_utils import init_ocr, check_gpu_available

# 检测 GPU
if check_gpu_available():
    print("✅ GPU 可用")
else:
    print("⚠️ GPU 不可用")

# 自动选择（推荐）
ocr = init_ocr(use_gpu=None)  # None = 自动检测

# 处理图片
result = ocr.ocr("image.png")
```

### 示例 2: 强制使用 GPU

```python
from ocr_utils import init_ocr

# 强制使用 GPU
ocr = init_ocr(
    lang='ch',
    use_gpu=True,  # 强制 GPU
    det_model='server',
    rec_model='server'
)

# 处理图片
result = ocr.ocr("image.png")
```

### 示例 3: 双语言 OCR

```python
from ocr_bilingual import ocr_bilingual

# 自动检测 GPU
results = ocr_bilingual(
    "image.png",
    enhance=True,
    debug=True,
    use_gpu=None  # 自动检测
)

print(f"中文文本: {len(results['chinese'])} 条")
print(f"英文文本: {len(results['english'])} 条")
print(f"总计: {len(results['all_texts'])} 条")
```

### 示例 4: 批量处理（发挥 GPU 优势）

```python
from pathlib import Path
from ocr_utils import init_ocr, ocr_image

# 初始化 OCR（使用 GPU）
ocr = init_ocr(use_gpu=True)

# 批量处理
image_dir = Path("frames")
results = []

for image_path in image_dir.glob("*.png"):
    text = ocr_image(
        ocr,
        str(image_path),
        min_score=0.3,
        debug=False,
        hybrid_mode=True
    )
    results.append({
        'image': image_path.name,
        'text': text
    })
    print(f"✓ 处理完成: {image_path.name}")

print(f"\n总计处理 {len(results)} 张图片")
```

## 🎯 性能优化技巧

### 1. 选择合适的模型

```python
# 高精度（慢）
ocr = init_ocr(use_gpu=True, det_model='server', rec_model='server')

# 平衡模式（推荐）
ocr = init_ocr(use_gpu=True, det_model='mobile', rec_model='server')

# 快速模式（快）
ocr = init_ocr(use_gpu=True, det_model='mobile', rec_model='mobile')
```

### 2. 批量处理提升效率

GPU 在批量处理时性能提升最明显：

```bash
# 批量处理多个视频
for video in videos/*.mp4; do
    python process_video.py "$video" --with-frames --use-gpu
done
```

### 3. 监控 GPU 使用情况

```bash
# 在处理视频时，打开另一个终端
watch -n 1 nvidia-smi
```

## ⚠️ 注意事项

1. **首次运行**：首次使用 GPU 时，PaddleOCR 会下载 GPU 优化模型（约 10-30秒）

2. **显存限制**：如果遇到 "CUDA out of memory" 错误：
   - 使用 mobile 模型而非 server 模型
   - 减少图像分辨率
   - 一次处理更少的图片

3. **自动降级**：如果 GPU 不可用，系统会自动切换到 CPU 模式，不会报错

4. **macOS 限制**：macOS（包括 Apple Silicon）不支持 CUDA，建议使用 CPU 模式

## 🔍 故障排除

### GPU 未被检测到

```bash
# 检查 NVIDIA 驱动
nvidia-smi

# 检查 CUDA
nvcc --version

# 检查 PaddlePaddle GPU 支持
python -c "import paddle; print(paddle.is_compiled_with_cuda())"
```

如果输出 `False`，需要重新安装 PaddlePaddle GPU 版本。

### 性能没有提升

可能原因：
- 图片太小（GPU 优势不明显）
- 单张处理（建议批量处理）
- CUDA/驱动配置问题

## 📚 更多信息

- 详细配置指南：[GPU_ACCELERATION.md](./GPU_ACCELERATION.md)
- PaddleOCR 文档：https://github.com/PaddlePaddle/PaddleOCR
- CUDA 安装：https://developer.nvidia.com/cuda-downloads

---

**提示**：如果遇到问题，请先查看 [GPU_ACCELERATION.md](./GPU_ACCELERATION.md) 中的故障排除部分。
