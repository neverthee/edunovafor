# 演示数据库

`eduNova.demo.sqlite` 是可公开分享的脱敏演示库，保留课程、教材和评估内容，方便克隆项目后查看业务数据。

它不包含真实用户身份、密码哈希、聊天记录、学习记录、答题记录、班级名单、上传队列、本地文件路径或外链；文本中的邮箱、手机号、身份证号和 Windows 本地路径会被替换为占位符。

演示账户仅用于本地体验：`demo_admin` / `admin123`、`demo_teacher` / `teacher123`、`demo_student` / `student123`。部署时请使用新的数据库和环境变量，绝不能使用这些公开凭据。

更新演示库：

```powershell
$env:PYTHON_EXE_OVERRIDE="C:\\Users\\86152\\.conda\\envs\\edunova2\\python.exe"
& $env:PYTHON_EXE_OVERRIDE backend/database/sanitize_demo_db.py
```
