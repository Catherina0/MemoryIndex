#!/usr/bin/env swift

// vision_ocr.swift
// Apple Vision Framework OCR 脚本
// 用法: swift vision_ocr.swift <image_path> [--lang zh-Hans,en-US] [--level accurate]

import Foundation
import Vision
import AppKit

// MARK: - 命令行参数解析
struct OCRConfig {
    let imagePath: String
    let languages: [String]
    let recognitionLevel: VNRequestTextRecognitionLevel
    let useLanguageCorrection: Bool
    
    static func parse(args: [String]) -> OCRConfig? {
        guard args.count >= 2 else {
            printUsage()
            return nil
        }
        
        let imagePath = args[1]
        var languages = ["zh-Hans", "en-US"]  // 默认：简体中文 + 英文
        var level: VNRequestTextRecognitionLevel = .accurate
        var useCorrection = true
        
        var i = 2
        while i < args.count {
            switch args[i] {
            case "--lang":
                if i + 1 < args.count {
                    languages = args[i + 1].components(separatedBy: ",")
                    i += 2
                } else {
                    i += 1
                }
            case "--level":
                if i + 1 < args.count {
                    level = args[i + 1] == "fast" ? .fast : .accurate
                    i += 2
                } else {
                    i += 1
                }
            case "--no-correction":
                useCorrection = false
                i += 1
            default:
                i += 1
            }
        }
        
        return OCRConfig(
            imagePath: imagePath,
            languages: languages,
            recognitionLevel: level,
            useLanguageCorrection: useCorrection
        )
    }
    
    static func printUsage() {
        let usage = """
        用法: swift vision_ocr.swift <image_path> [选项]
        
        选项:
          --lang <langs>         语言列表（逗号分隔），默认: zh-Hans,en-US
                                 可用: zh-Hans, zh-Hant, en-US, ja-JP, ko-KR 等
          --level <fast|accurate> 识别精度，默认: accurate
          --no-correction        禁用语言纠错
        
        示例:
          swift vision_ocr.swift image.png
          swift vision_ocr.swift image.png --lang en-US --level fast
          swift vision_ocr.swift image.png --lang zh-Hans,ja-JP
        """
        fputs(usage + "\n", stderr)
    }
}

// MARK: - 文本排序逻辑
struct TextBlock {
    let text: String
    let bbox: CGRect // Normalized 0..1, origin bottom-left
}

func sortTextBlocks(_ blocks: [TextBlock]) -> [String] {
    // 简单的行聚类算法
    // 1. 按 Y 轴降序排列 (从上到下)
    let sortedByY = blocks.sorted { $0.bbox.origin.y > $1.bbox.origin.y }
    
    var rows: [[TextBlock]] = []
    
    for block in sortedByY {
        var added = false
        // 尝试加入现有行
        // 若当前 block 的 Y 与某行的中心 Y 接近，则归入该行
        // 阈值 0.015 约为 1.5% 屏幕高度，适合一般文本行距
        if let lastRow = rows.last {
            let lastY = lastRow[0].bbox.origin.y // 使用行首元素作为基准
            if abs(block.bbox.origin.y - lastY) < 0.015 {
                rows[rows.count - 1].append(block)
                added = true
            }
        }
        
        if !added {
             rows.append([block])
        }
    }
    
    // 2. 行内排序 (按 X 轴升序: 从左到右)
    var result: [String] = []
    for row in rows {
        let sortedRow = row.sorted { $0.bbox.origin.x < $1.bbox.origin.x }
        for block in sortedRow {
            result.append(block.text)
        }
    }
    
    return result
}

// MARK: - OCR 核心逻辑
func recognizeText(from imageURL: URL, config: OCRConfig) -> [String] {
    guard
        let nsImage = NSImage(contentsOf: imageURL),
        let cgImage = nsImage.cgImage(forProposedRect: nil, context: nil, hints: nil)
    else {
        fputs("错误：无法加载图片 \(imageURL.path)\n", stderr)
        return []
    }
    
    var recognizedBlocks: [TextBlock] = []
    
    // 1. 创建 OCR 请求
    let request = VNRecognizeTextRequest { request, error in
        if let error = error {
            fputs("错误：识别失败 - \(error.localizedDescription)\n", stderr)
            return
        }
        
        guard let results = request.results as? [VNRecognizedTextObservation] else {
            return
        }
        
        // 2. 提取文本块
        for observation in results {
            if let candidate = observation.topCandidates(1).first {
                recognizedBlocks.append(TextBlock(text: candidate.string, bbox: observation.boundingBox))
            }
        }
    }
    
    // 3. 配置识别参数
    request.recognitionLanguages = config.languages
    request.recognitionLevel = config.recognitionLevel
    request.usesLanguageCorrection = config.useLanguageCorrection
    
    // 可选：自动检测语言（iOS 16+/macOS 13+）
    if #available(macOS 13.0, *) {
        request.automaticallyDetectsLanguage = true
    }
    
    // 4. 执行请求 (同步)
    let handler = VNImageRequestHandler(cgImage: cgImage, options: [:])
    
    do {
        // VNImageRequestHandler.perform 是同步阻塞的，无需信号量
        try handler.perform([request])
    } catch {
        fputs("错误：执行 OCR 失败 - \(error.localizedDescription)\n", stderr)
        return []
    }
    
    // 5. 智能排序
    return sortTextBlocks(recognizedBlocks)
}

// MARK: - Main Entry
func main() {
    autoreleasepool {
        let args = CommandLine.arguments
        
        guard let config = OCRConfig.parse(args: args) else {
            exit(1)
        }
        
        let imageURL = URL(fileURLWithPath: config.imagePath)
        
        guard FileManager.default.fileExists(atPath: config.imagePath) else {
            fputs("错误：文件不存在 - \(config.imagePath)\n", stderr)
            exit(1)
        }
        
        let texts = recognizeText(from: imageURL, config: config)
        
        // 输出结果（每行一个识别文本）
        for text in texts {
            print(text)
        }
    
        exit(texts.isEmpty ? 1 : 0)
    }
}

main()
