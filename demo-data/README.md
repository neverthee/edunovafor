# 当前本地演示数据

这份数据包对应当前本地的“我的课程、知识库、评估测试”。它用于演示或初始化新的空环境，不是生产数据备份。

包含：

- `database/eduNova.sqlite`：16 门课程、19 份教材、9 个评估和 4 条知识库队列记录；真实用户、密码哈希、聊天、学习和答题记录均已移除，替换为 3 个演示账号。
- `backend/uploads/materials/17`、`backend/uploads/materials/18`：课程原始资料、生成的教案、PPT、小游戏与预览文件。
- `backend/uploads/chapters/17`：课程章节数据。
- `uploads/knowledge_base/17`、`uploads/knowledge_base/18`：对应课程的本地知识库索引。

不包含 `.env`、用户身份与行为数据、处理缓存、临时视频或 PDF 页面切图。

如需在新的空演示环境恢复，先备份现有运行数据，然后把本目录的 `backend/uploads`、`uploads` 和 `database/eduNova.sqlite` 分别复制到项目的同名运行目录。不要在已有生产数据的环境中直接覆盖。
