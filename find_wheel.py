import json
import urllib.request
import sys

def get_wheel(package, version):
    url = f"https://pypi.org/pypi/{package}/{version}/json"
    try:
        with urllib.request.urlopen(url) as r:
            data = json.load(r)
            for f in data['urls']:
                # Look for macos universal2 wheel
                if 'macosx' in f['filename'] and f['packagetype'] == 'bdist_wheel':
                    # Prefer universal2
                    if 'universal2' in f['filename']:
                         return f
                    # Fallback to x86_64 if no universal (though for pydantic-core universal usually exists)
            
            # If no universal, print what we found
            print(f"No universal2 wheel found for {package} {version}. Available: {[x['filename'] for x in data['urls'] if 'macosx' in x['filename']]}")
            return None
    except Exception as e:
        print(e)
        return None

w = get_wheel("pydantic-core", "2.16.3") # Let's try to match pydantic-core version with compatible pydantic.
# Wait, the previous tool output claimed pydantic-core 2.41.5. 
# Let's check what Pydantic version the user installed.
# The user's pyproject.toml says `pydantic>=2.0.0`.
# When I ran `get_pydantic_res.py` before, it seemingly picked `pydantic 2.12.5` ??? 
# and `pydantic-core 2.41.5`.
# Let's check `pydantic-core` 2.41.5 wheels correctly.

w2 = get_wheel("pydantic-core", "2.14.6") # Old?

# Let's just use the latest info from PyPI for both to ensure compatibility.
w_latest = get_wheel("pydantic-core", "2.14.6") 

# Actually, let's look at the output of `python3 -c ...` above. It said `2.41.5`. 
# So pydantic-core IS 2.41.5.

target_core = get_wheel("pydantic-core", "2.14.6") # Placeholder
# Code to fetch latest stable versions compatible.
# I'll just fetch info for "pydantic" and let it tell me its required core version? 
# No, simpler to just get the latest matching pair if I can, or just get the wheels for the versions I found earlier.

# Let's GET the wheel for pydantic-core 2.41.5 specifically.
w_core = get_wheel("pydantic-core", "2.14.6") # Wait, if latest is 2.41.5, I should use that.
w_real = get_wheel("pydantic-core", "2.27.2") # Try some recent one?
w_exact = get_wheel("pydantic-core", "2.41.5")

if w_exact:
    print(f"FOUND: {w_exact['url']} {w_exact['digests']['sha256']}")
else:
    print("Not found")
