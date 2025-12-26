# OCR GPU 加速快速指南

## ✨ 新功能

OCR 模块现已支持 GPU 加速，可显著提升处理速度（3-5倍）。

## 🚀 快速开始

### 1. 检测 GPU

```bash
python test_gpu.py
```

### 2. 处理视频（自动检测 GPU）

```bash
# 系统会自动检测并使用 GPU（如果可用）
python process_video.py video.mp4 --with-frames
```

### 3. 强制使用 GPU

```bash
python process_video.py video.mp4 --with-frames --use-gpu
```

### 4. 单图片 OCR

```bash
# 自动检测
python ocr_bilingual.py image.png

# 强制 GPU
python ocr_bilingual.py image.png --gpu

# 强制 CPU
python ocr_bilingual.py image.png --cpu
```

### 5. 性能测试

```bash
python test_gpu.py image.png --compare
```

## 📊 性能提升

| 场景 | CPU | GPU | 加速 |
|------|-----|-----|------|
| 单帧 | 3.5秒 | 0.8秒 | **4.4x** |
| 52帧视频 | 180秒 | 40秒 | **4.5x** |

## 🔧 GPU 环境配置

### 检查要求

```bash
# 检查 NVIDIA 驱动
nvidia-smi

# 检查 CUDA
nvcc --version
```

### 安装 PaddlePaddle GPU 版本

```bash
# CUDA 11.x
pip install paddlepaddle-gpu==2.6.1 -i https://mirror.baidu.com/pypi/simple

# CUDA 12.x
pip install paddlepaddle-gpu==2.6.1.post120 -i https://mirror.baidu.com/pypi/simple
```

### 验证安装

```bash
python -c "import paddle; print('CUDA:', paddle.is_compiled_with_cuda())"
```

## 💡 使用建议

1. **自动模式（推荐）**：不指定 GPU 参数，让系统自动检测
2. **批量处理**：GPU 在批量处理时性能提升最明显
3. **监控使用**：使用 `nvidia-smi` 监控 GPU 状态
4. **显存不足**：使用 mobile 模型代替 server 模型

## 📚 详细文档

- [完整配置指南](docs/GPU_ACCELERATION.md)
- [使用示例](docs/GPU_EXAMPLES.md)
- [更新日志](docs/IMPROVEMENTS_2024_12.md)

## ⚠️ 注意事项

- ✅ 系统会自动降级：GPU 不可用时自动使用 CPU
- ✅ macOS 不支持 CUDA，建议使用 CPU 模式
- ✅ 首次使用会下载 GPU 模型（10-30秒）
- ⚠️ 显存不足时使用 mobile 模型

## 🆘 故障排除

### GPU 未被检测

```bash
# 1. 检查驱动和 CUDA
nvidia-smi
nvcc --version

# 2. 验证 PaddlePaddle
python -c "import paddle; print(paddle.is_compiled_with_cuda())"

# 3. 重装 GPU 版本（如果输出 False）
pip uninstall paddlepaddle
pip install paddlepaddle-gpu==2.6.1 -i https://mirror.baidu.com/pypi/simple
```

### 显存不足

```bash
# 使用轻量模型
python process_video.py video.mp4 --with-frames --use-gpu \
    --ocr-det-model mobile --ocr-rec-model mobile
```

---

**更新时间**: 2024年12月26日  
**版本**: v1.0
