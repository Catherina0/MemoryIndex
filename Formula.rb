# MemoryIndex Homebrew Formula
# 
# 这是一个 Homebrew Formula 模板
# 
# 使用方法：
# 1. 创建自己的 tap：
#    brew tap-new Catherina0/memoryindex
# 2. 复制此文件到：
#    $(brew --repository)/Library/Taps/catherina0/homebrew-memoryindex/Formula/memoryindex.rb
# 3. 安装：
#    brew install Catherina0/memoryindex/memoryindex

class Memoryindex < Formula
  include Language::Python::Virtualenv

  desc "智能视频知识库系统 - 视频下载、OCR识别、全文搜索"
  homepage "https://github.com/Catherina0/MemoryIndex"
  url "https://github.com/Catherina0/MemoryIndex/archive/refs/tags/v1.0.0.tar.gz"
  sha256 "REPLACE_WITH_ACTUAL_SHA256"  # 使用: shasum -a 256 filename
  license "MIT"
  head "https://github.com/Catherina0/MemoryIndex.git", branch: "main"

  depends_on "python@3.11"
  depends_on "ffmpeg"
  depends_on "portaudio" => :optional

  # Python 依赖
  resource "paddlepaddle" do
    url "https://files.pythonhosted.org/packages/..."
    sha256 "..."
  end

  # 更多资源...

  def install
    virtualenv_install_with_resources
    
    # 创建配置目录
    (etc/"memoryindex").mkpath
    
    # 安装示例配置
    (etc/"memoryindex/config_example.py").write <<~EOS
      # MemoryIndex Configuration
      # Copy to ~/.memoryindex/config.py and modify
      DB_PATH = "#{var}/memoryindex/memory.db"
      OUTPUT_PATH = "#{var}/memoryindex/output"
    EOS
  end

  def post_install
    (var/"memoryindex").mkpath
    (var/"memoryindex/output").mkpath
    (var/"memoryindex/storage").mkpath
  end

  def caveats
    <<~EOS
      MemoryIndex 已安装！

      快速开始：
        memidx search "关键词"
        memidx list
        memidx-process video.mp4

      数据目录：
        #{var}/memoryindex/

      查看帮助：
        memidx --help

      更多文档：
        https://github.com/Catherina0/MemoryIndex
    EOS
  end

  test do
    system bin/"memidx", "--help"
    system bin/"memidx", "list", "--limit", "1"
  end
end

# ============================================
# 快速发布到 Homebrew 的步骤
# ============================================
#
# 1. 准备发布
#    git tag -a v1.0.0 -m "Release v1.0.0"
#    git push origin v1.0.0
#
# 2. 创建 GitHub Release
#    - 在 GitHub 上创建 Release
#    - 上传 tar.gz 文件
#
# 3. 计算 SHA256
#    curl -L https://github.com/Catherina0/MemoryIndex/archive/refs/tags/v1.0.0.tar.gz | shasum -a 256
#
# 4. 更新 Formula
#    - 替换上面的 REPLACE_WITH_ACTUAL_SHA256
#
# 5. 创建自己的 Tap
#    brew tap-new Catherina0/memoryindex
#    cd $(brew --repository)/Library/Taps/catherina0/homebrew-memoryindex
#    mkdir -p Formula
#    cp /path/to/this/file Formula/memoryindex.rb
#
# 6. 测试安装
#    brew install --build-from-source Catherina0/memoryindex/memoryindex
#    brew test memoryindex
#    brew audit --strict memoryindex
#
# 7. 发布 Tap
#    cd $(brew --repository)/Library/Taps/catherina0/homebrew-memoryindex
#    git add Formula/memoryindex.rb
#    git commit -m "Add memoryindex formula"
#    git push
#
# 8. 用户安装
#    brew tap Catherina0/memoryindex
#    brew install memoryindex
