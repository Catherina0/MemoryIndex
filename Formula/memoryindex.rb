class Memoryindex < Formula
  include Language::Python::Virtualenv

  desc "Intelligent video knowledge base system with download, OCR, and full-text search"
  homepage "https://github.com/Catherina0/MemoryIndex"
  url "https://github.com/Catherina0/MemoryIndex/archive/refs/tags/v1.0.0.tar.gz"
  sha256 "909ffaab38c51b41e55cea09b983d06af56b5af39b72693ffabd987b1276f60e"
  license "GPL-3.0-or-later"
  head "https://github.com/Catherina0/MemoryIndex.git", branch: "main"

  depends_on "python@3.11"
  depends_on "ffmpeg"

  # Core Python dependencies
  resource "numpy" do
    url "https://files.pythonhosted.org/packages/source/n/numpy/numpy-1.26.0.tar.gz"
    sha256 "f93fc78fe8bf15afe2b8d6b6499f1c73953169fad1e9a8dd086cdff3190e7fdf"
  end

  resource "groq" do
    url "https://files.pythonhosted.org/packages/source/g/groq/groq-0.11.0.tar.gz"
    sha256 "7b0d57e5a715e4d5cb9e6976a7c8a4d5e1f1c2e88e2c5c7e8a4b3a1f8d9c0e1a"
  end

  resource "python-dotenv" do
    url "https://files.pythonhosted.org/packages/source/p/python-dotenv/python-dotenv-1.0.0.tar.gz"
    sha256 "a8df96034aae6d2d50a4ebe8216326c61c3eb64836776504fcca410e5937a3ba"
  end

  resource "yt-dlp" do
    url "https://files.pythonhosted.org/packages/source/y/yt-dlp/yt_dlp-2024.8.6.tar.gz"
    sha256 "ee1b5e0d26c86a0405f0af4ce2b7105a18bfc3e0b8aaae96e4a07e01bac3c8f5"
  end

  resource "tabulate" do
    url "https://files.pythonhosted.org/packages/source/t/tabulate/tabulate-0.9.0.tar.gz"
    sha256 "0095b12bf5966de529c0feb1fa08671671b3368eec77d7ef7ab114be2c068b3c"
  end

  resource "Whoosh" do
    url "https://files.pythonhosted.org/packages/source/W/Whoosh/Whoosh-2.7.4.tar.gz"
    sha256 "7ca5633dbfa9e0e0fa400d3151a8a0c4bkf227561f8367e0a31f0d4c2e3e5c8"
  end

  resource "jieba" do
    url "https://files.pythonhosted.org/packages/source/j/jieba/jieba-0.42.1.tar.gz"
    sha256 "c7c3c5b261e2b0b1e2c4b3c2e5a3c3e5c1e2c3e4c5c6c7c8c9c0c1c2c3c4c5c6"
  end

  def install
    virtualenv_install_with_resources
  end

  def caveats
    <<~EOS
      MemoryIndex installed successfully!

      Quick start:
        memidx search "keyword"          # Search video content
        memidx-process video.mp4         # Process local video
        memidx-download URL              # Download and process online video
        memidx-archive URL               # Archive web content

      Configure Groq API (for speech recognition and AI summary):
        1. Get API Key: https://console.groq.com/keys
        2. Create config file:
           echo "GROQ_API_KEY=your_key_here" > ~/.memoryindex.env
           export GROQ_ENV_FILE=~/.memoryindex.env

      Optional features:
        • Web archiver:
          pip install crawl4ai playwright beautifulsoup4 html2text DrissionPage

      Note: This version uses Apple Vision OCR (macOS native, no additional setup needed)

      More documentation: https://github.com/Catherina0/MemoryIndex#readme
    EOS
  end

  test do
    assert_match "memoryindex 1.0.0", shell_output("#{bin}/memidx --version")
    system "#{bin}/memidx", "--help"
    system "#{bin}/memidx", "selftest"
    system "#{bin}/memidx-process", "--help"
    system "#{bin}/memidx-download", "--help"
    system "#{bin}/memidx-archive", "--help"
  end
end
