# GPU 加速配置指南

本文档介绍如何为 OCR 功能配置和使用 GPU 加速。

## 📋 目录

- [GPU 加速优势](#gpu-加速优势)
- [环境要求](#环境要求)
- [安装配置](#安装配置)
- [使用方法](#使用方法)
- [性能测试](#性能测试)
- [故障排除](#故障排除)

## 🚀 GPU 加速优势

使用 GPU 加速可以显著提升 OCR 处理速度：

| 场景 | CPU 耗时 | GPU 耗时 | 加速比 |
|------|---------|---------|--------|
| 单帧识别 | ~3.5秒 | ~0.8秒 | **4.4x** |
| 视频处理 (52帧) | ~180秒 | ~40秒 | **4.5x** |
| 批量处理 (100帧) | ~350秒 | ~80秒 | **4.4x** |

**推荐场景**：
- ✅ 大量视频需要处理
- ✅ 实时或近实时OCR需求
- ✅ 高分辨率图像识别
- ✅ 批量文档处理

## 💻 环境要求

### 硬件要求

- **NVIDIA GPU**：支持 CUDA 计算的显卡
  - 推荐：GTX 1060 6GB 或更高
  - 最低：GTX 750 Ti 或更高
- **显存**：至少 2GB（推荐 4GB+）
- **系统内存**：至少 8GB（推荐 16GB+）

### 软件要求

1. **NVIDIA 驱动**
   - Linux: 450.80.02 或更高
   - Windows: 452.39 或更高

2. **CUDA Toolkit**
   - CUDA 11.x (推荐 11.2+)
   - 或 CUDA 12.x (推荐 12.0+)

3. **cuDNN**
   - cuDNN 8.x (匹配 CUDA 版本)

## 🔧 安装配置

### 步骤 1: 检查 GPU 和 CUDA

```bash
# 检查 NVIDIA 驱动
nvidia-smi

# 检查 CUDA 版本
nvcc --version
```

### 步骤 2: 安装 PaddlePaddle GPU 版本

根据你的 CUDA 版本选择对应的 PaddlePaddle：

#### CUDA 11.x (推荐)

```bash
# 卸载 CPU 版本（如果已安装）
pip uninstall paddlepaddle

# 安装 GPU 版本
pip install paddlepaddle-gpu==2.6.1 -i https://mirror.baidu.com/pypi/simple
```

#### CUDA 12.x

```bash
# 卸载 CPU 版本（如果已安装）
pip uninstall paddlepaddle

# 安装 GPU 版本
pip install paddlepaddle-gpu==2.6.1.post120 -i https://mirror.baidu.com/pypi/simple
```

#### macOS (Apple Silicon - MPS)

```bash
# Apple Silicon Mac 可以使用 Metal Performance Shaders (MPS)
# 注意：PaddlePaddle 对 MPS 支持有限，建议使用 CPU 版本
pip install paddlepaddle
```

**重要说明**：PaddleOCR 3.x 版本的 GPU 支持通过 Paddle 的设备管理实现，不再使用 `use_gpu` 参数。系统会自动通过 `paddle.device.set_device()` 来控制使用 GPU 或 CPU。

### 步骤 3: 验证安装

```bash
# 创建测试脚本
python -c "
import paddle
print('PaddlePaddle version:', paddle.__version__)
print('CUDA available:', paddle.is_compiled_with_cuda())
if paddle.is_compiled_with_cuda():
    print('CUDA version:', paddle.version.cuda())
    print('cuDNN version:', paddle.version.cudnn())
"
```

预期输出：
```
PaddlePaddle version: 2.6.1
CUDA available: True
CUDA version: 11.2
cuDNN version: 8.2
```

## 📘 使用方法

### 方式 1: 命令行参数（推荐）

```bash
# 处理视频时启用 GPU
python process_video.py video.mp4 --with-frames --use-gpu

# 使用双语言 OCR 工具
python ocr_bilingual.py image.png --gpu --debug
```

### 方式 2: 在代码中使用

```python
from ocr_utils import init_ocr, check_gpu_available

# 自动检测 GPU
gpu_available = check_gpu_available()
ocr = init_ocr(use_gpu=gpu_available)

# 强制使用 GPU
ocr = init_ocr(use_gpu=True)

# 强制使用 CPU
ocr = init_ocr(use_gpu=False)
```

### 方式 3: 双语言 OCR

```python
from ocr_bilingual import ocr_bilingual

# 自动检测 GPU（推荐）
results = ocr_bilingual(
    image_path="image.png",
    use_gpu=None  # None = 自动检测
)

# 强制使用 GPU
results = ocr_bilingual(
    image_path="image.png",
    use_gpu=True,
    debug=True  # 显示 GPU 状态
)
```

## 📊 性能测试

### 使用测试脚本

项目提供了专门的 GPU 测试脚本：

```bash
# 检测 GPU 可用性
python test_gpu.py

# 测试单张图片识别性能
python test_gpu.py path/to/image.png

# CPU vs GPU 性能对比
python test_gpu.py path/to/image.png --compare
```

### 示例输出

```
======================================================================
🔍 GPU 检测测试
======================================================================
✅ GPU 可用！将使用GPU加速

🏁🏁🏁🏁🏁🏁🏁🏁🏁🏁🏁🏁🏁🏁🏁🏁🏁🏁🏁🏁🏁🏁🏁🏁🏁🏁🏁🏁🏁🏁🏁🏁🏁🏁🏁
开始CPU vs GPU性能对比测试
🏁🏁🏁🏁🏁🏁🏁🏁🏁🏁🏁🏁🏁🏁🏁🏁🏁🏁🏁🏁🏁🏁🏁🏁🏁🏁🏁🏁🏁🏁🏁🏁🏁🏁🏁

======================================================================
⚡ OCR 性能测试: CPU模式
======================================================================
>> 初始化OCR模型...
   初始化耗时: 2.45秒
>> 识别图片: test.png
   识别耗时: 3.52秒
   识别到 15 条文本

======================================================================
⚡ OCR 性能测试: GPU模式
======================================================================
>> 初始化OCR模型...
✅ GPU 可用，将启用GPU加速
   初始化耗时: 1.82秒
>> 识别图片: test.png
   识别耗时: 0.78秒
   识别到 15 条文本

======================================================================
📊 性能对比结果
======================================================================
模式         初始化         识别           总耗时         加速比
----------------------------------------------------------------------
CPU            2.45秒       3.52秒       5.97秒     1.00x
GPU            1.82秒       0.78秒       2.60秒     2.30x
======================================================================

🚀 GPU相比CPU快 2.30 倍

✅ 测试完成
```

## 🔍 故障排除

### 问题 1: GPU 未被检测到

**症状**：运行时显示 "GPU 不可用，将使用CPU模式"

**解决方法**：

1. 检查 CUDA 是否正确安装：
   ```bash
   nvidia-smi
   nvcc --version
   ```

2. 验证 PaddlePaddle GPU 版本：
   ```bash
   python -c "import paddle; print(paddle.is_compiled_with_cuda())"
   ```

3. 确认安装了正确的 PaddlePaddle GPU 版本（匹配 CUDA 版本）

### 问题 2: CUDA Out of Memory

**症状**：错误信息包含 "CUDA out of memory"

**解决方法**：

1. 减少批处理大小：
   ```python
   ocr = init_ocr(use_gpu=True)
   # 在 PaddleOCR 中修改 rec_batch_num
   ```

2. 降低图像分辨率：
   ```python
   # 在预处理时缩小图像
   from PIL import Image
   img = Image.open('large_image.png')
   img = img.resize((img.width // 2, img.height // 2))
   ```

3. 使用 mobile 模型而非 server 模型：
   ```bash
   python process_video.py video.mp4 --with-frames --use-gpu \
       --ocr-det-model mobile --ocr-rec-model mobile
   ```

### 问题 3: GPU 比 CPU 慢

**可能原因**：

1. **图像太小**：GPU 在小图像上的优势不明显
2. **批处理过小**：GPU 并行能力未充分利用
3. **驱动/CUDA 问题**：版本不匹配或配置错误

**解决方法**：

1. 批量处理多张图片以发挥 GPU 优势
2. 确保使用最新的 NVIDIA 驱动
3. 检查 CUDA 和 cuDNN 版本是否匹配

### 问题 4: 在 macOS 上无法使用 GPU

**说明**：

- macOS 不支持 NVIDIA CUDA
- Apple Silicon (M1/M2/M3) 可以使用 Metal Performance Shaders (MPS)
- 但 PaddlePaddle 对 MPS 支持有限

**建议**：

- 在 macOS 上使用 CPU 模式
- 或使用支持 MPS 的其他 OCR 库（如 EasyOCR）

## 🎯 性能优化建议

### 1. 选择合适的模型

```bash
# 高精度 + GPU（推荐用于重要内容）
python process_video.py video.mp4 --with-frames --use-gpu \
    --ocr-det-model server --ocr-rec-model server

# 平衡性能（推荐日常使用）
python process_video.py video.mp4 --with-frames --use-gpu \
    --ocr-det-model mobile --ocr-rec-model server

# 极速模式（推荐快速处理）
python process_video.py video.mp4 --with-frames --use-gpu \
    --ocr-det-model mobile --ocr-rec-model mobile
```

### 2. 批量处理

GPU 在批量处理时性能提升最明显：

```bash
# 批量处理多个视频
for video in videos/*.mp4; do
    python process_video.py "$video" --with-frames --use-gpu
done
```

### 3. 监控 GPU 使用

```bash
# 在另一个终端监控 GPU 状态
watch -n 1 nvidia-smi
```

## 📚 相关资源

- [PaddlePaddle GPU 安装文档](https://www.paddlepaddle.org.cn/install/quick)
- [CUDA Toolkit 下载](https://developer.nvidia.com/cuda-downloads)
- [cuDNN 下载](https://developer.nvidia.com/cudnn)
- [PaddleOCR 官方文档](https://github.com/PaddlePaddle/PaddleOCR)

## 🆘 获取帮助

如果遇到问题：

1. 查看本文档的故障排除部分
2. 检查项目的 [Issues](https://github.com/your-repo/issues)
3. 查阅 PaddlePaddle 官方文档
4. 在项目中提交新 Issue

---

**最后更新**: 2024年12月26日
