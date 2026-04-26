---
title: 工作-googleTest
allDay: false
startTime: 10:30
endTime: 21:00
date: 2026-02-10
completed: null
---
#googletest 
extern关键字解决执行程序所在cpp找到shim中函数符号的问题；但是runner聚合对象ims_osal_objs却找不到shim？
难道只有runner里涉及到的符号，在链接期间才会被查找，而ims_osal_objs里没有直接调用的符号就不会被查找吗？


80个project加入googleTest project，在任意被测试模块插入函数探针？？


