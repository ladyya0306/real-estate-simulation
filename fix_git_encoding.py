# =========== Copyright 2023 @ CAMEL-AI.org. All Rights Reserved. ===========
# Licensed under the Apache License, Version 2.0 (the ��License��);
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an ��AS IS�� BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
# =========== Copyright 2023 @ CAMEL-AI.org. All Rights Reserved. ===========
import os
import subprocess


def get_tracked_files():
    try:
        # Force utf-8 for git output to avoid decoding errors on file paths
        result = subprocess.run(['git', 'ls-files'], capture_output=True, text=True, encoding='utf-8', errors='replace')
        return result.stdout.splitlines()
    except Exception as e:
        print(f"Git error: {e}")
        return []


def convert_to_utf8(filepath):
    if not os.path.exists(filepath):
        return

    try:
        with open(filepath, 'rb') as f:
            raw = f.read()

        content = None
        encoding = None

        # 1. Try UTF-8
        try:
            content = raw.decode('utf-8')
            encoding = 'utf-8'
        except UnicodeDecodeError:
            # 2. Try GB18030 (Superset of GBK/GB2312)
            try:
                content = raw.decode('gb18030')
                encoding = 'gb18030'
            except UnicodeDecodeError:
                print(f"Skipping {filepath}: Cannot decode (Binary?)")
                return

        # If it was GBK, write back as UTF-8
        # OR if it was UTF-8 but had BOM? (Python handles BOM with utf-8-sig but let's stick to simple utf-8)
        if encoding == 'gb18030':
            print(f"Converting {filepath} from GB18030 to UTF-8")
            with open(filepath, 'w', encoding='utf-8', newline='\n') as f:
                f.write(content)

    except Exception as e:
        print(f"Error processing {filepath}: {e}")


if __name__ == "__main__":
    files = get_tracked_files()
    print(f"Scanning {len(files)} tracked files...")
    for f in files:
        if f.endswith('.py') or f.endswith('.md') or f.endswith('.txt') or f.endswith('.yaml') or f.endswith('.yml') or f.endswith('.csv'):
            convert_to_utf8(f)
    print("Done.")

