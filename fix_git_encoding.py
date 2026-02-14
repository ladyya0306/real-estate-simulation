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
