# PaddleOCR 3.x GPU 支持修复说明

## 问题描述

运行 `process_video.py --with-frames --use-gpu` 时出现错误：
```
ValueError: Unknown argument: use_gpu
```

## 原因分析

PaddleOCR 3.x 版本改变了 GPU 控制方式：
- ❌ **旧版本**：通过 `use_gpu=True/False` 参数控制
- ✅ **新版本**：通过 `paddle.device.set_device('gpu:0')` 或 `paddle.device.set_device('cpu')` 控制

同时，许多参数名称也发生了变化：
- `use_angle_cls` → `use_textline_orientation`
- `det_db_thresh` → `text_det_thresh`
- `det_db_box_thresh` → `text_det_box_thresh`
- `det_db_unclip_ratio` → `text_det_unclip_ratio`
- `rec_batch_num` → `text_recognition_batch_size`

## 修复内容

### 1. ocr_utils.py

```python
# 修复前
ocr = PaddleOCR(
    lang=lang,
    use_gpu=use_gpu,  # ❌ 不支持
    use_angle_cls=True,
    det_db_thresh=0.2,
    ...
)

# 修复后
import paddle
if use_gpu and paddle.is_compiled_with_cuda():
    paddle.device.set_device('gpu:0')  # ✅ 正确方式
else:
    paddle.device.set_device('cpu')

ocr = PaddleOCR(
    lang=lang,
    use_textline_orientation=True,  # ✅ 新参数名
    text_det_thresh=0.2,  # ✅ 新参数名
    ...
)
```

### 2. ocr_bilingual.py

同样的修复方式：
- 在创建 PaddleOCR 实例前使用 `paddle.device.set_device()`
- 更新所有参数名称以匹配 PaddleOCR 3.x API

## 使用方法

修复后，GPU 加速功能正常工作：

```bash
# 自动检测 GPU（推荐）
python process_video.py video.mp4 --with-frames

# 强制使用 GPU
python process_video.py video.mp4 --with-frames --use-gpu

# 强制使用 CPU
python process_video.py video.mp4 --with-frames  # 不加 --use-gpu

# 双语言 OCR
python ocr_bilingual.py image.png --gpu
```

## GPU 检测逻辑

```python
def check_gpu_available():
    """检测GPU是否可用"""
    try:
        import paddle
        return paddle.is_compiled_with_cuda()
    except Exception:
        return False

def init_ocr(use_gpu=None):
    """初始化OCR"""
    # 自动检测
    if use_gpu is None:
        use_gpu = check_gpu_available()
    
    # 设置设备
    import paddle
    if use_gpu and paddle.is_compiled_with_cuda():
        paddle.device.set_device('gpu:0')
        print("✅ 使用 GPU 加速")
    else:
        paddle.device.set_device('cpu')
        if use_gpu:
            print("⚠️ GPU 不可用，使用 CPU 模式")
    
    # 创建 OCR 实例（不传 use_gpu 参数）
    ocr = PaddleOCR(...)
    return ocr
```

## 验证修复

运行以下命令验证：

```bash
# 1. 语法检查
python3 -m py_compile ocr_utils.py ocr_bilingual.py

# 2. GPU 检测测试
python test_gpu.py

# 3. 实际处理测试（如果有测试图片）
python ocr_bilingual.py test_image.png --debug
```

## 兼容性说明

- ✅ 兼容 PaddleOCR 3.x 版本
- ✅ 保持向前兼容：GPU 不可用时自动降级到 CPU
- ✅ 参数名称已全部更新到新版 API
- ✅ 功能完全正常：自动检测、强制 GPU、强制 CPU

## 相关文档

- [GPU_ACCELERATION.md](GPU_ACCELERATION.md) - 完整配置指南
- [GPU_EXAMPLES.md](GPU_EXAMPLES.md) - 使用示例
- [GPU_QUICKSTART.md](../GPU_QUICKSTART.md) - 快速开始

---

**修复时间**: 2024年12月26日  
**PaddleOCR 版本**: 3.x  
**Paddle 版本**: 3.2.2
