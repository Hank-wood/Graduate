# MongoDB Database/Collection 含义说明
建议使用软件 MongoBooster 查看, 在台式机上已经安装并购买授权
```
train: 训练集, 从知乎采集的原始数据(时间切片数据)
test: 测试集, 从知乎采集的原始数据(时间切片数据)
analysis: 
    user: 存储用户关系
    dynamic_train: 训练集的动态传播网络推断结果
    dynamic_test: 测试集的动态传播网络推断结果
    all_a: dynamic_train和dynamic_test的并集,即所有答案的静态传播网络推断结果
    static_test: 测试集的静态传播网络推断结果
    answer: {
        aid: 答案id,
        fo_count: 回答者follower数(maybe None),
        layer: 传播层数,
        follow: follow关系数量,
        notification: notification关系数量,
        qlink: qlink关系数量,
        recommendation: recommendation关系数量,
        upvote_num: 点赞数量,
        comment_num: 评论数量,
        collect_num: 收藏数量
    }
    influence: {
        fo_count: follower数量,
        succ_count: 以该节点为根的子树的节点个数(不包括根节点)
    }
    receiver: {
        'fo_count': 回答者follower数(maybe None),
        'time': 按时间排序的接收者的行为时间
    }
```

# 重要代码文件说明
```
dynamic/ 数据采集相关,可以不管
infer/
    dynamic_infer.py: 动态传播网络推断
    train.py: 训练静态传播网络推断要用的follow关系分类模型
    static_infer.py: 静态传播网络推断
    evaluate.py: 动态传播网络推断效果评价
    diffusion_tree.html, draw.js: D3.js可视化相关
    analysis/
        collect_data.py: 往answer, influence, receiver collection写入内容
        analysis.ipynb: ipython notebook文件
```
        
# 实验重现
* 数据采集,传播网络推断都可以不管,直接使用推断好的结果即可
* 4.4静态传播网络推断实验评价: evaluate.py直接运行即可
* 5.4传播网络可视化:  
    在component.py中调用load_and_display_graph(aid),可视化图案会在浏览器中显示
    参见其__main__. 如果显示不出图案,原因是对应的dynamic_test中没有这个答案,修改313行
    `tree_data = db2.dynamic_test.find_one({'aid': aid}, {'_id': 0})`,
    把dynamic_test改成dynamic_train即可
* 5.5知识传播规律分析:  
    运行 ipython notebook, 打开analysis.ipynb, 从上往下依次运行代码片段.
    具体还请学习 ipython notebook 使用
* 5.6水军识别: 可以不管

        