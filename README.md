
一款基于机器学习的Web日志统计分析与异常检测命令行工具


# Presentation
**1\. 访问量统计**
``` bash
analog> show statistics requests current day
```

![](https://raw.githubusercontent.com/Testzero-wz/analog/master/_img/18-36-03.jpg)


**2\. 日志审查**
``` bash
analog> show log of current month
```

![](https://raw.githubusercontent.com/Testzero-wz/analog/master/_img/10-15-19.jpg)

**3\. IP、请求等统计**
``` bash
analog> show statistics requests current day top 20
```
![](https://raw.githubusercontent.com/Testzero-wz/analog/master/_img/10-17-25.jpg)
``` bash
analog> show statistics url current day top 20
```

![](https://raw.githubusercontent.com/Testzero-wz/analog/master/_img/10-18-13.jpg)

**4\.恶意请求统计**

包括恶意IP定位、恶意请求统计，恶意IP地理分布统计，正、异常请求比
``` bash
analog>  show analysis of current month
```
![](https://raw.githubusercontent.com/Testzero-wz/analog/master/_img/10-19-52.jpg)


![](https://raw.githubusercontent.com/Testzero-wz/analog/master/_img/10-21-32.jpg)

# Installation
1\. 安装依赖
``` bash
 $ pip install -r requirements.txt
```
# Prepare
若想使用异常检测功能，则必须提供自己的日志训练样本。（统计图表功能则不需要）

**1\. 在`analog`根目录下的`config.ini`配置好数据库参数(程序使用的是MYSQL，确保存在数据库环境)**

![](https://raw.githubusercontent.com/Testzero-wz/analog/master/_img/18-24-56.jpg)

**2\. 准备机器学习训练样本以及用于参数优化的黑白样本**

三个样本在目录`analog/sample_set`下，分别是`train.txt`、`test_black_log.txt`和`test_white_log.txt`。
训练样本尽量使样本数量为5000-10000条(视网站情况适量加减，太少不准确，太多影响参数优化速度)，且尽可能覆盖正常访问流量，保证异常率不超过15%，否则会影响模型预测效果；白样本则要求尽量全为正常流量，黑样本可以自己从日志里面挑选出来异常的流量，也可以在github上找一些payload放进去，格式可以是日志格式，也可以是纯请求路径格式。同时尽量保持数大于500条（工作量大概在20分钟左右）

**3\. 使用`train`或者`retrain`命令训练模型** 

可以使用`train progress`命令获取训练进度或重载当前模型

# About
使用的预测模型为`Oneclass-SVM`，内核为`rbf`，参数遍历取最优。

特征提取用的是TF-IDF计算2-grams截取未url解码的请求路径，特征向量空间为100*100，取的是`string.printable`可打印字符

![](https://raw.githubusercontent.com/Testzero-wz/analog/master/_img/10-44-57.jpg)

由于analog是基于正则提取的日志，目前只写了`nginx的标准日志`，往后将继续更新、完善以支持更多的日志格式。

有好的idea也可以请求pull，欢迎在issue中提出问题！

如遇Bug,可以键入bedug，进入debug模式，获取错误信息并在issue中提出，以帮助我改善代码。

更多解释及用法详见博客：[Wz's Blog](https://www.wzsite.cn/2018/10/22/%E5%9F%BA%E4%BA%8E%E6%9C%BA%E5%99%A8%E5%AD%A6%E4%B9%A0%E7%9A%84Web%E6%97%A5%E5%BF%97%E5%BC%82%E5%B8%B8%E6%A3%80%E6%B5%8B%E5%AE%9E%E8%B7%B5/)

# TODO
1. 日志实时更新
2. 提高检测模型效率
3. 提高检测模型F1值

# Reference
+ McPAD-A Multiple Classifier System for Accurate Payload-based Anomaly Detection
+ Preprocessing Web Logs for Web Intrusion 
+ System Log Analysis for Anomaly Detection
+ Cybersercurity-data-mining
+ Anomaly-detection-via-server-log
+ Anomaly Detection of Web-based Attacks
+ 基于机器学习的web异常检测 - 阿里聚安全





