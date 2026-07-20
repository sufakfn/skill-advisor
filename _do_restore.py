
import re
from pathlib import Path

# 读 build_cache.py
content = Path('scripts/build_cache.py').read_text(encoding='utf-8')

# 找 merge 函数
start = content.find('def merge_all_sources(conn):')
end = content.find(chr(10) + 'def ', start + 100)
if end == -1:
    end = content.find(chr(10) + '# ===', start + 100)

# 新函数 - 从文件读取
new_func = Path('_merge_correct.py').read_text(encoding='utf-8')

# 替换
new_content = content[:start] + new_func + content[end:]
Path('scripts/build_cache.py').write_text(new_content, encoding='utf-8')

import ast
try:
    ast.parse(new_content)
    print('OK')
except SyntaxError as e:
    print(f'Error: {e}')
