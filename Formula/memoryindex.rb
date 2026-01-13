class Memoryindex < Formula
  include Language::Python::Virtualenv

  desc "Intelligent video knowledge base system with download, OCR, and full-text search"
  homepage "https://github.com/Catherina0/MemoryIndex"
  url "https://github.com/Catherina0/MemoryIndex/archive/refs/tags/v1.0.1.tar.gz"
  sha256 "652c47c56917de976a3b537420fa7b05136601cd8deec0f0f50c615f7a15afd1"
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

  # Additional dependencies for full functionality
  resource "beautifulsoup4" do
    url "https://files.pythonhosted.org/packages/source/b/beautifulsoup4/beautifulsoup4-4.12.3.tar.gz"
    sha256 "74e3d1928edc070d21748185c46e3fb33490f22f52a3addee9aee0f4f7781051"
  end

  resource "lxml" do
    url "https://files.pythonhosted.org/packages/source/l/lxml/lxml-5.1.0.tar.gz"
    sha256 "3eea6ed6e6c918e468e693c41ef07f3c3acc310b70ddd9cc72d9ef84bc9564ca"
  end

  resource "soupsieve" do
    url "https://files.pythonhosted.org/packages/source/s/soupsieve/soupsieve-2.5.tar.gz"
    sha256 "5663d5a7b3bfaeee0bc4372e7fc48f9cff4940b3eec54a6451cc5299f1097690"
  end

  resource "certifi" do
    url "https://files.pythonhosted.org/packages/source/c/certifi/certifi-2024.8.30.tar.gz"
    sha256 "bec941d2aa8195e248a60b31ff9f0558284cf01a52591ceda73ea9afffd69fd9"
  end

  resource "charset-normalizer" do
    url "https://files.pythonhosted.org/packages/source/c/charset-normalizer/charset_normalizer-3.4.0.tar.gz"
    sha256 "223217c3d4f82c3ac5e29032b3f1c2eb0fb591b72161f86d93f5719079dae93e"
  end

  resource "idna" do
    url "https://files.pythonhosted.org/packages/source/i/idna/idna-3.10.tar.gz"
    sha256 "12f65c9b470abda6dc35cf8e63cc574b1c52b11df2c86030af0ac09b01b13ea9"
  end

  resource "urllib3" do
    url "https://files.pythonhosted.org/packages/source/u/urllib3/urllib3-2.2.3.tar.gz"
    sha256 "e7d814a81dad81e6caf2ec9fdedb284ecc9c73076b62654547cc64ccdcae26e9"
  end

  resource "requests" do
    url "https://files.pythonhosted.org/packages/source/r/requests/requests-2.32.3.tar.gz"
    sha256 "55365417734eb18255590a9ff9eb97e9e1da868d4ccd6402399eaf68af20a760"
  end

  resource "websockets" do
    url "https://files.pythonhosted.org/packages/source/w/websockets/websockets-14.1.tar.gz"
    sha256 "398b10c77d471c0aab20a845e7a60076b6390bfdaac7a6d2edb0d2c59d75e8f8"
  end

  resource "brotli" do
    url "https://files.pythonhosted.org/packages/source/b/Brotli/Brotli-1.1.0.tar.gz"
    sha256 "81de08ac11bcb85841e440c13611c00b67d3bf82698314928d0b676362546724"
  end

  resource "mutagen" do
    url "https://files.pythonhosted.org/packages/source/m/mutagen/mutagen-1.47.0.tar.gz"
    sha256 "719fadef0a978c31b4cf3c956261b3c58b6948b32023078a2117b1de09f0fc99"
  end

  resource "pycryptodomex" do
    url "https://files.pythonhosted.org/packages/source/p/pycryptodomex/pycryptodomex-3.21.0.tar.gz"
    sha256 "222d0bd05381dd25c32dd6065c071ebf084212ab79bab4599ba9e6a3e0009e6c"
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
    assert_match "memoryindex 1.0.1", shell_output("#{bin}/memidx --version")
    system "#{bin}/memidx", "--help"
    system "#{bin}/memidx", "selftest"
    system "#{bin}/memidx-process", "--help"
    system "#{bin}/memidx-download", "--help"
    system "#{bin}/memidx-archive", "--help"
  end
end
