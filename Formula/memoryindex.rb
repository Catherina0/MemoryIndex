class Memoryindex < Formula
  include Language::Python::Virtualenv

  desc "Intelligent video knowledge base system with download, OCR, and full-text search"
  homepage "https://github.com/Catherina0/MemoryIndex"
  url "https://github.com/Catherina0/MemoryIndex/archive/refs/tags/v1.0.4.tar.gz"
  sha256 "f2f938688cdd9d01a4932239997600e464516c1afd57c5977dc9c47e457e1f4f"
  license "GPL-3.0-or-later"

  depends_on "ffmpeg"
  depends_on "python@3.11"
  depends_on "yt-dlp"

  def install
    virtualenv_install_with_resources
  end

  def caveats
    <<~EOS
      To use speech recognition and AI summary features, configure Groq API:
        echo "GROQ_API_KEY=your_key_here" > ~/.memoryindex.env
        export GROQ_ENV_FILE=~/.memoryindex.env

      Get API key from: https://console.groq.com/keys
    EOS
  end

  test do
    assert_match "memoryindex 1.0.4", shell_output("#{bin}/memidx --version")
    system "#{bin}/memidx", "selftest"
  end
end
