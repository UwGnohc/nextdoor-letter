# 隔壁来信 · 免费上线指南

用自己的 GitHub 和 Render 账号完成一次部署，朋友就能直接用手机浏览器查看 BOYNEXTDOOR 资讯、刷新社区讨论和翻译外语标题。你的电脑可以关机。

1. 解压部署包，打开 [GitHub 新建仓库](https://github.com/new)，仓库名可填 `nextdoor-letter`，可见性选 `Private`。创建后点 `uploading an existing file`（已有文件的仓库点 `Add file → Upload files`），将解压后的所有文件拖进去，点 `Commit changes`。仓库首页应能直接看到 `render.yaml`。
2. 登录 [Render 控制台](https://dashboard.render.com/)，工作区选免费 `Hobby`。点 `New → Blueprint`，连接刚才的仓库。检查清单中只有一个 `Free` 的 Web Service，然后点 `Deploy Blueprint`。[Render 部署指南](https://render.com/docs/infrastructure-as-code)
3. 等这个 Web Service 的状态变为 `Live`，打开服务详情，复制顶部的 `onrender.com` 网址。可以先在手机上点一次「更新讨论」，再把同一个网址发给朋友。

免费实例连续 15 分钟没有访问就会休眠，下次打开通常要等约一分钟。唤醒后网页先显示随包内容，再向来源检查更新。工作区每月共享 750 个免费实例小时，流量和构建也有额度；未绑定付款方式时，超出相应额度会暂停服务或新构建。[Render 免费额度与休眠说明](https://render.com/docs/free)
