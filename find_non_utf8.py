# =========== Copyright 2023 @ CAMEL-AI.org. All Rights Reserved. ===========
# Licensed under the Apache License, Version 2.0 (the “License”);
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an “AS IS” BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
# =========== Copyright 2023 @ CAMEL-AI.org. All Rights Reserved. ===========
import os


def check_encoding(file_path):
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            f.read()
        return True
    except UnicodeDecodeError:
        return False
    except Exception:
        # print(f"Skipping {file_path}: {e}")
        return True

non_utf8_files = []
for root, dirs, files in os.walk("."):
    if ".git" in root or ".venv" in root or "__pycache__" in root or ".pytest_cache" in root or "node_modules" in root:
        continue
    for file in files:
        # Check commonly edited text files
        if file.endswith(('.py', '.md', '.yaml', '.yml', '.txt', '.csv', '.json', '.js', '.html', '.css')):
            path = os.path.join(root, file)
            if not check_encoding(path):
                non_utf8_files.append(path)
                print(f"Found Non-UTF8: {path}")

# Generate conversion script content
if non_utf8_files:
    print(f"\nFound {len(non_utf8_files)} non-utf8 files.")
else:
    print("All scanned files are UTF-8 compliant.")
