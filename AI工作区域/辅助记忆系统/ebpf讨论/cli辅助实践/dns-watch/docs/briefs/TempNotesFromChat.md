各个prompts和instructions.md是网页版chat根据和我的自然对话描述形成的，但是形成的正式文档我总觉得隔了一层，以下是逐行阅读的记录：

core goals???
observability：最大的目标。
mvp：正确，最小mvp才能缓解我的疲劳情绪。
network observability：进一步的goal。
doc as first-class outputs:正确，加入AI tool就是为了治理。

dns-watch-brief.md
title部分的确是我想要的，打印跟踪dns的行为，小的可读的诊断图。

my question is only about:
the result of dns,包括这里的要解析的name，成功以及失败，查询时间，因为查询时间涉及业务的耗时，这里AI给我列出的问题的确要全面一些。

我感觉why this matters和core problem重合了，

broader value of dns-watch 描述有点误差，broader value只能由我记忆下linux在internet公网行的行为，但我工作中的问题是在专网+公网发生的，即ims的补充业务的dns查询结果失败重试问题。

我把secondary users的ebpf engineers调整到了first users，同时删去了teammate。

why exist：
两个原因都贴合我的描述：1.ebpf 2.work story

why ebpf：
ebpf is powerful，dns-watch本身就是为了ebpf实践而创建，但AI补充的也对，不一定要用ebpf，这个补充的内容不是我提到的，but ok。

current focus：
mvp。


mvp v0：
费曼学习法，剋。

具体的mvp output， success condition，


后面太多了，等ai输出具体结果，看到哪里有问题再回来修改吧。

readme.md完全和brief重合。

todo.md
decide child processes are whether explicitly excluded,这一项并不在我的知识范畴内，稍后其实我可以自己改一下使其包含child看看。latency这个也不在我的知识范畴。
partially degrate这个也不在我的知识范畴。

design：
这几个设计都不在我的知识范畴内

验证以及测试，这里用一个sh脚本？能不能和googleTest来做？
其实我的理解最终产物应该是spec，scenario，when，and，output。

