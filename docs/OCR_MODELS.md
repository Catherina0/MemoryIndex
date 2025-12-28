# OCR 模型选择指南

## 概述

本项目使用 PaddleOCR 进行视频帧的文字识别。PaddleOCR 提供了不同性能级别的模型，您可以根据设备性能和需求选择合适的模型。

## 模型类型

### 1. Mobile 模型（轻量级）

**特点：**
- ✅ 速度快
- ✅ 内存占用小
- ✅ 适合普通设备
- ⚠️ 识别精度相对较低

**适用场景：**
- 普通笔记本电脑
- 无 GPU 的设备
- 需要快速处理的场景
- 视频内容文字清晰度较高

**使用方法：**
```bash
# 默认使用 mobile 模型
make ocr VIDEO=/path/to/video.mp4

# 或显式指定
make ocr VIDEO=/path/to/video.mp4 DET_MODEL=mobile REC_MODEL=mobile
```

### 2. Server 模型（高精度）

**特点：**
- ✅ 识别精度高
- ✅ 适合复杂文字场景
- ⚠️ 速度较慢
- ⚠️ 内存占用大

**适用场景：**
- 高性能工作站
- 有 GPU 的设备
- 视频内容文字模糊或复杂
- 需要高精度识别的场景

**使用方法：**
```bash
# 使用 server 模型（高精度）
make ocr VIDEO=/path/to/video.mp4 DET_MODEL=server REC_MODEL=server
```

### 3. 混合模式（平衡）

可以混合使用检测和识别模型，实现速度和精度的平衡：

```bash
# 快速检测 + 高精度识别
make ocr VIDEO=/path/to/video.mp4 DET_MODEL=mobile REC_MODEL=server

# 高精度检测 + 快速识别
make ocr VIDEO=/path/to/video.mp4 DET_MODEL=server REC_MODEL=mobile
```

## 模型对比

| 特性 | Mobile 模型 | Server 模型 |
|------|------------|------------|
| **速度** | 快 (1-2秒/帧) | 慢 (3-5秒/帧) |
| **内存** | ~500MB | ~2GB |
| **精度** | 85-90% | 95-98% |
| **适用设备** | 普通笔记本 | 高性能机器 |
| **推荐场景** | 清晰文字 | 模糊/复杂文字 |

## GPU 加速

> **注意**：新版 PaddleOCR 会自动检测和使用 GPU（如果可用）。
> 无需手动指定，系统会自动优化。

如果您的设备有 NVIDIA GPU 和 CUDA 支持：
1. 安装 GPU 版本的 PaddlePaddle
2. OCR 会自动使用 GPU 加速
3. 速度可提升 3-5 倍

## 性能基准测试

基于 52 帧视频（约 50 秒）的测试结果：

### MacBook Pro M1 (16GB RAM)

| 配置 | 总耗时 | 单帧耗时 |
|------|--------|----------|
| Mobile + Mobile | ~90秒 | ~1.7秒 |
| Mobile + Server | ~120秒 | ~2.3秒 |
| Server + Mobile | ~150秒 | ~2.9秒 |
| Server + Server | ~180秒 | ~3.5秒 |

## 推荐配置

### 🚀 快速模式（推荐新手）

```bash
make ocr VIDEO=video.mp4
```

默认使用 mobile 模型，速度快，适合大多数场景。

### 🎯 高精度模式（推荐重要内容）

```bash
make ocr VIDEO=video.mp4 DET_MODEL=server REC_MODEL=server
```

使用 server 模型，精度最高，适合重要文档。

### ⚖️ 平衡模式（推荐日常使用）

```bash
make ocr VIDEO=video.mp4 DET_MODEL=mobile REC_MODEL=server
```

检测快速，识别精准，性价比最高。

## 常见问题

### Q: 如何选择合适的模型？

**A:** 根据以下因素决定：

1. **设备性能**
   - 普通笔记本 → mobile
   - 高性能工作站 → server

2. **视频内容**
   - 清晰PPT/演示文稿 → mobile
   - 手写字/模糊文字 → server

3. **时间要求**
   - 快速预览 → mobile
   - 详细分析 → server

### Q: 模型会自动下载吗？

**A:** 是的，首次使用时会自动下载：
- Mobile 模型：约 10-15MB
- Server 模型：约 50-100MB

模型缓存在 `~/.paddlex/official_models/` 目录。

### Q: 如何清理模型缓存？

```bash
# 清理所有模型缓存
rm -rf ~/.paddlex/official_models/

# 下次运行时会重新下载
```

### Q: OCR 识别不准确怎么办？

1. 尝试使用 server 模型提高精度
2. 检查视频清晰度
3. 调整帧率（`--fps` 参数）
4. 查看抽帧图片质量

### Q: 能否使用其他语言？

可以，通过 `--ocr-lang` 参数指定：

```bash
# 英文
python process_video.py video.mp4 --with-frames --ocr-lang en

# 繁体中文
python process_video.py video.mp4 --with-frames --ocr-lang chinese_cht
```

## 故障排除

### 问题：OCR 很慢

**解决方案：**
1. 使用 mobile 模型
2. 减少抽帧频率
3. 检查 CPU 占用情况

### 问题：识别率低

**解决方案：**
1. 使用 server 模型
2. 提高视频分辨率
3. 增加抽帧频率以捕获更多内容

### 问题：内存不足

**解决方案：**
1. 使用 mobile 模型
2. 减少同时处理的帧数
3. 关闭其他程序释放内存

## 性能优化建议

1. **首选 mobile 模型** - 对于大多数清晰视频已经足够
2. **批量处理** - 多个视频时，先用 mobile 快速处理，重要的再用 server
3. **合理抽帧** - 不需要每秒都抽取，1-2秒一帧通常足够
4. **预览后决定** - 先用 mobile 看效果，不满意再用 server

## 更新日志

### 2025-12-11
- ✅ 修复新版 PaddleOCR API 兼容性
- ✅ 添加模型选择功能
- ✅ 改进错误处理机制
- ✅ 自动检测 GPU 加速

---

💡 **提示**：建议先用默认的 mobile 模型测试，如果识别效果不理想再考虑使用 server 模型。
