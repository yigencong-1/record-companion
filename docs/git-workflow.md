# Git 日常使用

| 项目 | 设置 |
|---|---|
| 工作位置 | 自己克隆的仓库根目录 |
| 分支 | main |
| origin | https://github.com/yigencong-1/record-companion.git |
| 远程仓库 | [yigencong-1/record-companion](https://github.com/yigencong-1/record-companion) |
| 可见性 | Public |

Git提交在本地保存一个版本；推送将该版本上传到GitHub。后续本地文件变化仍需提交和推送，不会因为App项目关联自动上传。

## 同学如何参与

按[贡献说明](../CONTRIBUTING.md)从自己的Fork提交PR，目标分支为原仓库main。同学无原仓库写权限，不能直接推送或合并main；由用户审阅并合并。

main启用至少一名有写权限者审阅、新提交使旧批准失效、禁止强推与删除。所有者保留管理员例外，以下本地提交/推送示例供所有者使用。若将来邀请具有写权限的协作者，需重新审查权限，避免改变“同学只提PR”的约定。

## 查看状态

下面的命令从自己的仓库根目录执行。

~~~powershell
git status
git remote -v
git log -1 --oneline
~~~

## 保存并上传本次修改

先检查实际改动，选择本次需要保存的文件。下面以简报和决策记录为例：

~~~powershell
git diff
git add docs/project-brief.md docs/decisions.md
git commit -m "docs: update player design decisions"
git push
~~~

代码、硬件或结构文件按实际修改路径添加，提交说明描述具体变化。

## 获取远程更新

先查看工作区状态，处理本地尚未提交的变化，再更新：

~~~powershell
git status
git pull --ff-only
~~~

若提示分支分歧或冲突，交给主控检查具体差异并处理，不直接强制覆盖。

## 来源与凭据

- 所有者的origin指向原仓库，同学的origin指向各自Fork。外部作品和组件仓库记录在[来源文档](../references/sources.md)。
- 本机使用已有Git Credential Manager登录。凭据不写入工程、示例命令或文档。
- 构建目录、缓存与本地敏感配置由.gitignore排除；提交前仍检查实际文件。
- Git不会保存空目录，本轮用.gitkeep保留未来工程目录。正式加入文件后可按需要移除标记。

