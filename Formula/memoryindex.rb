class Memoryindex < Formula
  include Language::Python::Virtualenv

  desc "智能视频知识库系统 - 视频下载、OCR识别、全文搜索一体化解决方案"
  homepage "https://github.com/Catherina0/MemoryIndex"
  url "https://github.com/Catherina0/MemoryIndex/archive/refs/tags/v1.0.0.tar.gz"
  sha256 ""  # 需要在打标签后计算真实的 SHA256
  license "GPL-3.0-or-later"

  depends_on "python@3.11"
  depends_on "ffmpeg"

  # 核心 Python 依赖
  resource "numpy" do
    url "https://files.pythonhosted.org/packages/numpy-1.26.0.tar.gz"
    sha256 ""
  end

  resource "groq" do
    url "https://files.pythonhosted.org/packages/groq-0.4.0.tar.gz"
    sha256 ""
  end

  resource "python-dotenv" do
    url "https://files.pythonhosted.org/packages/python-dotenv-1.0.0.tar.gz"
    sha256 ""
  end

  resource "yt-dlp" do
    url "https://files.pythonhosted.org/packages/yt-dlp-2024.8.6.tar.gz"
    sha256 ""
  end

  resource "tabulate" do
    url "https://files.pythonhosted.org/packages/tabulate-0.9.0.tar.gz"
    sha256 ""
  end

  resource "Whoosh" do
    url "https://files.pythonhosted.org/packages/Whoosh-2.7.4.tar.gz"
    sha256 ""
  end

  resource "jieba" do
    url "https://files.pythonhosted.org/packages/jieba-0.42.1.tar.gz"
    sha256 ""
  end

  def install
    virtualenv_install_with_resources
  end

  def caveats
    <<~EOS
      MemoryIndex 已安装！

      快速开始：
        memidx search "关键词"           # 搜索视频内容
        memidx-process video.mp4         # 处理本地视频
        memidx-download URL              # 下载并处理在线视频
        memidx-archive URL               # 归档网页内容

      配置 Groq API（用于语音识别和AI摘要）：
        1. 获取 API Key: https://console.groq.com/keys
        2. 创建配置文件:
           echo "GROQ_API_KEY=your_key_here" > ~/.memoryindex.env
           export GROQ_ENV_FILE=~/.memoryindex.env

      可选功能：
        • PaddleOCR（跨平台OCR）：
          pip install paddlepaddle paddleocr opencv-python
        
        • 网页归档功能：
          pip install crawl4ai playwright beautifulsoup4 html2text DrissionPage

      更多文档: https://github.com/Catherina0/MemoryIndex#readme
    EOS
  end

  test do
    system "#{bin}/memidx", "--help"
    system "#{bin}/memidx-process", "--help"
    system "#{bin}/memidx-download", "--help"
    system "#{bin}/memidx-archive", "--help"
  end
end
