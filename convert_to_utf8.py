# =========== Copyright 2023 @ CAMEL-AI.org. All Rights Reserved. ===========
# Licensed under the Apache License, Version 2.0 (the ¡°License¡±);
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an ¡°AS IS¡± BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
# =========== Copyright 2023 @ CAMEL-AI.org. All Rights Reserved. ===========
import os

files_to_convert = [
    r".\agent_behavior.py",
    r".\inconsistency_report.md",
    r".\simulation_runner.py",
    r".\analyze_shortage.py"
]

for file_path in files_to_convert:
    if os.path.exists(file_path):
        try:
            # Try reading with GBK (common for Chinese Windows)
            with open(file_path, 'r', encoding='gbk') as f:
                content = f.read()
            
            # Write back with UTF-8
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(content)
            print(f"Converted {file_path} to UTF-8")
        except UnicodeDecodeError:
            print(f"Failed to read {file_path} with GBK. Trying CP1252...")
            try:
                with open(file_path, 'r', encoding='cp1252') as f:
                    content = f.read()
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(content)
                print(f"Converted {file_path} to UTF-8 (from CP1252)")
            except Exception as e:
                print(f"Failed to convert {file_path}: {e}")
        except Exception as e:
            print(f"Error processing {file_path}: {e}")
    else:
        print(f"File not found: {file_path}")
