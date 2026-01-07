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

// MARK: - OCR 核心逻辑
func recognizeText(from imageURL: URL, config: OCRConfig) -> [String] {
    guard
        let nsImage = NSImage(contentsOf: imageURL),
        let cgImage = nsImage.cgImage(forProposedRect: nil, context: nil, hints: nil)
    else {
        fputs("错误：无法加载图片 \(imageURL.path)\n", stderr)
        return []
    }
    
    var recognizedTexts: [String] = []
    let semaphore = DispatchSemaphore(value: 0)
    
    // 1. 创建 OCR 请求
    let request = VNRecognizeTextRequest { request, error in
        defer { semaphore.signal() }
        
        if let error = error {
            fputs("错误：识别失败 - \(error.localizedDescription)\n", stderr)
            return
        }
        
        guard let results = request.results as? [VNRecognizedTextObservation] else {
            return
        }
        
        // 2. 提取文本（按位置从上到下排序）
        for observation in results.sorted(by: { $0.boundingBox.origin.y > $1.boundingBox.origin.y }) {
            if let candidate = observation.topCandidates(1).first {
                recognizedTexts.append(candidate.string)
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
    
    // 4. 执行请求
    let handler = VNImageRequestHandler(cgImage: cgImage, options: [:])
    
    do {
        try handler.perform([request])
        semaphore.wait()  // 等待异步完成
    } catch {
        fputs("错误：执行 OCR 失败 - \(error.localizedDescription)\n", stderr)
        return []
    }
    
    return recognizedTexts
}

// MARK: - Main Entry
func main() {
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

main()
