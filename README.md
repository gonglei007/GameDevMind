
<p align="center">
  <img src="images/GLTOP_logo_circle_512x512.png" height="128">
  <h2 align="center">游戏开发图谱（技术侧）</h2>
  <p align="center">
    一起来解决游戏研运中各种技术相关的问题
  </p>
</p>
[![](https://img.shields.io/github/watchers/gonglei007/GameDevMind.svg)](https://github.com/gonglei007/GameDevMind/watchers)
[![](https://img.shields.io/github/stars/gonglei007/GameDevMind.svg)](https://github.com/gonglei007/GameDevMind/stargazers)
[![](https://img.shields.io/github/forks/gonglei007/GameDevMind.svg)](https://github.com/gonglei007/GameDevMind/network/members)
![](https://img.shields.io/github/repo-size/gonglei007/GameDevMind.svg)
[![](https://img.shields.io/github/contributors/gonglei007/GameDevMind.svg)](https://github.com/gonglei007/GameDevMind/graphs/contributors)


*[中文](README.md)* | *[English](README-en.md)*

```cpp
#include <iostream>
int main(){
    std::cout << "Hello, Game Development World!" << std::endl;
    return 0;
}
```

<br/>
<br/>

## 介绍
<p>
&emsp;&emsp;游戏行业已走过了半个世纪，但时至今日，游戏开发者们还是要花大把时间重复的去做着别人做过的事情。<br/>
</p>
<p>
&emsp;&emsp;我们整理了一套技术侧的《游戏开发图谱》，希望能帮助游戏开发者们在处理问题的时候，能快速地找问题要考虑的要点、方向或方案。
<br/>
<p>
&emsp;&emsp;我们无法让所有做过的事情不再重复，但我们愿意分享，使得更多游戏开发者在已知的事情上尽量节省时间。节省出更多精力投入到有创造性的工作中去。
<br/>
</p>


<div align="center">
    <table style="width:640px;">
        <thead style="font-weight: bold; font-style: italic;">
            <tr>
                <td>&emsp;&emsp;✅ “有”什么？&emsp;&emsp;</td>
                <td>&emsp;&emsp;❌ “没有”什么？&emsp;&emsp;</td>
            </tr>
        </thead>
        <tbody>
            <tr>
                <td>&emsp;&emsp; ✓ 做什么用的？用在哪里？&emsp;&emsp;</td>
                <td>&emsp;&emsp; × <strike>系统的知识讲解。</strike>&emsp;&emsp;</td>
            </tr>
            <tr>
                <td>&emsp;&emsp; ✓ 会遇到哪些问题？用什么去解决？&emsp;&emsp;</td>
                <td>&emsp;&emsp; × <strike>具体的实现细节。</strike>&emsp;&emsp;</td>
            </tr>
            <tr>
                <td>&emsp;&emsp; ✓ 要考虑到的要点或方法。&emsp;&emsp;</td>
                <td>&emsp;&emsp; × <strike>完整的解决方案。</strike>&emsp;&emsp;</td>
            </tr>
        </tbody>
    </table>
</div>

## 总览
<p>
&emsp;&emsp;游戏研运团队在技术上需要具备几大能力：基础能力、技术能力、研发能力、管理能力、商品化能力。<br/>
&emsp;&emsp;不是说每个成员都要具备这些能力，但整个团队是需要这些能力来支撑游戏产品研运并盈利的。
</p>
<br/>

![图1、这是知识树的框架，展开的知识树可以点击下面的github链接查看。](exports/0.总览.png)
<br/>

## 目录

### 1.基础能力
<p>

```cpp
游戏产品也是一种软件产品，所有的软件研发，就需要有一些共通的基础能力。
这些基础能力是软件开发的基本功，基本功越强，整个产品的开发过程就会越稳健、高效。
```

</p>

* [1.1.编程语言](mds/1.1.编程语言.md)
    * [1.1.1.编程语言共通概念](mds/1.1.1.编程语言共通概念.md)
    * [1.1.2.C++语言](mds/1.1.2.C++语言.md)
    * [1.1.3.C#语言](mds/1.1.3.C%23%E8%AF%AD%E8%A8%80.md)
    * [1.1.4.JS语言](mds/1.1.4.JS语言.md)
    * [1.1.5.编程语言综合](mds/1.1.5.编程语言综合.md)
* [1.2.程序设计](mds/1.2.程序设计.md)
    * [1.2.1.设计模式](mds/1.2.1.设计模式.md)
    * [1.2.2.数据结构](mds/1.2.2.数据结构.md)
    * [1.2.3.算法](mds/1.2.3.算法.md)
    * [1.2.4.代码重构](mds/1.2.4.代码重构.md)
* [1.3.通用基础](mds/1.3.通用基础.md)
    * [1.3.1.数学](mds/1.3.1.数学.md)
    * [1.3.2.人工智能](mds/1.3.2.人工智能.md)
    * [1.3.3.操作系统](mds/1.3.3.操作系统.md)
    * [1.3.4.计算机组成原理](mds/1.3.4.计算机组成原理.md)
    * [1.3.5.计算机网络](mds/1.3.5.计算机网络.md)
<br/>

### 2.技术能力
<p>

```cpp
游戏软件有其特定的技术要求，要研发游戏产品，就可能会需要具备这些技术。
```

</p>

* [2.1.客户端技术](mds/2.1.客户端技术.md)
    * [2.1.1.图形与渲染](mds/2.1.1.图形与渲染.md)
    * [2.1.2.物理](mds/2.1.2.物理.md)
    * [2.1.3.UI](mds/2.1.3.UI.md)
    * [2.1.4.声音](mds/2.1.4.声音.md)
    * [2.1.5.动画与特效](mds/2.1.5.动画与特效.md)
    * [2.1.6.游戏引擎概念与应用](mds/2.1.6.游戏引擎概念与应用.md)
    * [2.1.7.平台开发](mds/2.1.7.平台开发.md)
* [2.2.服务端技术](mds/2.2.服务端技术.md)
    * [2.2.1.网络与通信](mds/2.2.1.网络与通信.md)
    * [2.2.2.数据库](mds/2.2.2.数据库.md)
    * [2.2.3.服务端中间件](mds/2.2.3.服务端中间件.md)
* [2.3.开发者工具箱](mds/2.3.开发者工具箱.md)
<br/>

### 3.研发能力
<p>


```cpp
游戏是一种有艺术成分的商品，它是由数字内容和互动功能构建起来的。
开发一款游戏产品，要有跟其它软件产品不同的一系列的技术、方法、流程。
```

</p>

* [3.1.客户端产品研发](mds/3.1.客户端产品研发.md)
    * [3.1.1.客户端底层通用系统](mds/3.1.1.客户端底层通用系统.md)
    * [3.1.2.客户端3D场景开发](mds/3.1.2.客户端3D场景开发.md)
    * [3.1.3.客户端优化](mds/3.1.3.客户端优化.md)
    * [3.1.4.客户端网络系统](mds/3.1.4.客户端网络系统.md)
    * [3.1.5.效果与表现](mds/3.1.5.效果与表现.md)
* [3.2.服务端产品研发](mds/3.2.服务端产品研发.md)
    * [3.2.1.服务端架构](mds/3.2.1.服务端架构.md)
    * [3.2.2.网游网络同步](mds/3.2.2.网游网络同步.md)
    * [3.2.3.服务端优化](mds/3.2.3.服务端优化.md)
    * [3.2.4.服务端基础功能](mds/3.2.4.服务端基础功能.md)
* [3.3.业务层功能系统](mds/3.3.业务层功能系统.md)
* [3.4.生产工具研发](mds/3.4.生产工具研发.md)
    * [3.4.1.游戏引擎原理与开发](mds/3.4.1.游戏引擎原理与开发.md)
    * [3.4.2.编辑器开发](mds/3.4.2.编辑器开发.md)
    * [3.4.3.工具开发与应用](mds/3.4.3.工具开发与应用.md)
<br/>

### 4.管理能力
<p>

```cpp
管理中最具挑战的是尺度、分寸与随机应变。
火候少一分，生了；火候多一分，焦了。
追求的是复杂的事情简单化，面对的也可能是简单的事情复杂化。
```

</p>

* [4.1.工程管理](mds/4.1.工程管理.md)
    * [4.1.1.数字内容生产线](mds/4.1.1.数字内容生产线.md)
    * [4.1.2.系统开发生产线](mds/4.1.2.系统开发生产线.md)
    * [4.1.3.DevOps](mds/4.1.3.DevOps.md)
    * [4.1.4.开发工作流](mds/4.1.4.开发工作流.md)
* [4.2.项目管理](mds/4.2.项目管理.md)
    * [4.2.1.项目管理综合](mds/4.2.1.项目管理综合.md)
    * [4.2.2.版本管理](mds/4.2.2.版本管理.md)
    * [4.2.3.质量保证](mds/4.2.3.质量保证.md)
    * [4.2.4.团队与组织](mds/4.2.4.团队与组织.md)
    * [4.2.5.SCRUM](mds/4.2.5.SCRUM.md)
* [4.3.技术中台](mds/4.3.技术中台.md)
    * [4.3.1.快速开发框架](mds/4.3.1.快速开发框架.md)
    * [4.3.2.技术支持](mds/4.3.2.技术支持.md)
<br/>

### 5.商品化能力
<p>

```cpp
作为一个组织，不论你有什么样的技术或能力，一个最重要的目标是——赚钱。
在当下的市场环境下，一款好玩的游戏做出来了不一定就能够赚钱。
还需要有一系列商品化能力，才能让产品运转和盈利，让团队持续存活。

/* 这里只展示跟技术有关的那些事情 */
```

</p>

* [5.1.运维技术](mds/5.1.运维技术.md)
    * [5.1.1.网络维护](mds/5.1.1.网络维护.md)
    * [5.1.2.数据存储](mds/5.1.2.数据存储.md)
    * [5.1.3.资产管理](mds/5.1.3.资产管理.md)
    * [5.1.4.Linux系统](mds/5.1.4.Linux系统.md)
    * [5.1.5.中间件](mds/5.1.5.中间件.md)
    * [5.1.6.网络安全](mds/5.1.6.网络安全.md)
* [5.2.产品运营支持](mds/5.2.产品运营支持.md)
    * [5.2.1.GM后台](mds/5.2.1.GM后台.md)
    * [5.2.2.数据统计分析](mds/5.2.2.数据统计分析.md)
    * [5.2.3.产品热更新](mds/5.2.3.产品热更新.md)
    * [5.2.4.产品本地化](mds/5.2.4.产品本地化.md)
    * [5.2.5.开发配合](mds/5.2.5.开发配合.md)
* [5.3.产品商业化](mds/5.3.产品商业化.md)
    * [5.3.1.游戏安全](mds/5.3.1.游戏安全.md)
    * [5.3.2.帐号与支付](mds/5.3.2.帐号与支付.md)
<br/>

## 交流讨论
欢迎进群、进讨论区交流和分享游戏开发中遇到的问题或者解决方案。

|  |  |
| --- | -------- |
| QQ群: | 242500383 [![GLTOP游戏研发与技术1群](https://pub.idqqimg.com/wpa/images/group.png)](https://qm.qq.com/cgi-bin/qm/qr?k=fy4Z65nE-5Jd1ay8FkJpDc9iPJyW3d38&jump_from=webapi) |
|  |  |
| 讨论区: | [https://github.com/gonglei007/GameDevMind/discussions](https://github.com/gonglei007/GameDevMind/discussions) |

<br/>

## 联系我们

[-微信扫码-]<br/>

<img src="images/联系人-G.L.png?raw=true" alt="drawing" width="96"/>

<br/><br/>

## 缩略预览
![图2、这个知识图谱还在持续的补充扩展中](overview/overview-h.png)
<br/>

## 编辑与查看
* 资料库使用XMind编辑内容（/xminds/目录）。<br/>
* 也可以快速查看导出图（/exports/目录）。<br/>
* markdown文本内容（/mds/目录）。<br/>

## 贡献者


| [公雷(发起者)](https://github.com/gonglei007),&emsp; [Game Atom](https://github.com/gameatom),&emsp; [管仲才](https://github.com/guanzhongcai),&emsp; [王栋](https://github.com/wangdng),&emsp; ... |
| :---: |

【虚席以待...】 诚挚的邀请更多参与者来一起完善资料库。
<br/>

## 支持者
### Stargazers
[![Stargazers repo roster for @gonglei007/GameDevMind](https://reporoster.com/stars/gonglei007/GameDevMind)](https://github.com/gonglei007/GameDevMind/stargazers)
<br/>
### Forkers
[![Forkers repo roster for @gonglei007/GameDevMind](https://reporoster.com/forks/gonglei007/GameDevMind)](https://github.com/gonglei007/GameDevMind/network/members)
<br/>

## 历史

<div>

[2022-11-11]<br/>
* 对所有资料进行了一次大幅的整理、重构。<br/>

</div>

<div>

[2022-06-22]<br/>
* 第一个版本的资料库提交到了github。<br/>

</div>

