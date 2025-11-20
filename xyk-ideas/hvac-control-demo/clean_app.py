import re

# 读取当前文件
with open('app.py', 'r', encoding='utf-8') as f:
    content = f.read()

# 移除JavaScript代码块
# 找到html.Script("""开始到"""),结束的块
pattern = r'html\.Script\(\s*""".*?"""\s*\),'
content = re.sub(pattern, '', content, flags=re.DOTALL)

# 移除clientside callback
pattern2 = r'app\.clientside_callback\(.*?\),'
content = re.sub(pattern2, '', content, flags=re.DOTALL)

# 写入文件
with open('app_clean.py', 'w', encoding='utf-8') as f:
    f.write(content)

print('Cleaned app.py created as app_clean.py')
