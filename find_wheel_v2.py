import json
import urllib.request
import sys

def get_wheel(package, version):
    url = f"https://pypi.org/pypi/{package}/{version}/json"
    try:
        with urllib.request.urlopen(url) as r:
            data = json.load(r)
            for f in data['urls']:
                if 'macosx' in f['filename'] and f['packagetype'] == 'bdist_wheel':
                     # Prefer universal2
                    if 'universal2' in f['filename']:
                         return f
            return None
    except Exception as e:
        print(e)
        return None

# Check pydantic latest
url = "https://pypi.org/pypi/pydantic/json"
data = json.load(urllib.request.urlopen(url))
pydantic_ver = data['info']['version']
print(f"Latest Pydantic: {pydantic_ver}")

# Check pydantic-core latest
url = "https://pypi.org/pypi/pydantic-core/json"
data = json.load(urllib.request.urlopen(url))
core_ver = data['info']['version']
print(f"Latest Core: {core_ver}")

# Get wheels for them
w_pydantic = get_wheel("pydantic", pydantic_ver)
w_core = get_wheel("pydantic-core", core_ver)

if w_pydantic:
    print(f"PYDANTIC_URL={w_pydantic['url']}")
    print(f"PYDANTIC_SHA={w_pydantic['digests']['sha256']}")

if w_core:
    print(f"CORE_URL={w_core['url']}")
    print(f"CORE_SHA={w_core['digests']['sha256']}")
