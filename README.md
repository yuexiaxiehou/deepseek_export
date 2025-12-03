本工具仅供学习交流和个人数据备份使用，请勿用于非法用途，请遵守 DeepSeek 官方服务条款。

# 使用说明
1、双击运行程序
2、输入Authorization 和 cookie
3、选择只获取会话列表，还是获取全部对话详情

运行程序会在程序所在目录生成两个文件夹，一个文件夹负责报错生成的会话列表，json格式；一个文件夹负责保存详细会话内容，markdown格式。
# Authorization 和 cookie获取方式
用电脑浏览器打开
https://chat.deepseek.com/ 并登录。
按下键盘上的 F12 键（打开开发者工具）。
点击 “网络 (Network)” 标签。
刷新一下网页。 在列表中找到名为 fetch_page?lte_cursor.pinned=false 的请求，点击它。
在右侧找到 “请求头 (Request Headers)”，复制 Authorization 后面 Bearer 之后的那串字符，和下面cookie对应的值。
