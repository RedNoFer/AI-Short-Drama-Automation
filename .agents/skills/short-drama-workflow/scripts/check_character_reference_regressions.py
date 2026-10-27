#!/usr/bin/env python3
"""Run focused positive/negative checks for CAST-01..04."""
from copy import deepcopy
from validate_compact_package import check_character_reference_closure
NAMES={'CHAR_01':'许妍','CHAR_02':'周凯','CHAR_03':'孟露','CHAR_06':'塔纳'}
BASE={'【时间轴】':'0-4秒，孟露（口型对白，口型同步）"周凯是谁？"',
      '【参考】':'CHAR_03＝人物图',
      '【公共总规范】':'角色一致性：孟露：身份外观遵循 CHAR_03 人物参考图。\n声线锁定：孟露＝测试。'}
count=0
def run(label,sections,bound,expected=None):
    global count
    errors=[]
    check_character_reference_closure(sections,{'角色':bound},NAMES,label,errors)
    assert (any(expected in x for x in errors) if expected else not errors),(label,errors)
    count+=1
s=deepcopy(BASE);s['【参考】']='';run('正文有孟露但绑定和参考均漏',s,[],'CAST-01')
s=deepcopy(BASE);s['【参考】']='';run('已绑无参考',s,['CHAR_03'],'CAST-02')
s=deepcopy(BASE);s['【参考】']+='；CHAR_01＝人物图';run('参考未绑定',s,['CHAR_03'],'CAST-02')
s=deepcopy(BASE);s['【公共总规范】']+='\n许妍：素颜；';run('公共层多余身份',s,['CHAR_03'],'CAST-03')
s=deepcopy(BASE);s['【公共总规范】']=s['【公共总规范】'].replace('声线锁定：','声线锁定：许妍＝测试；');run('多余声线',s,['CHAR_03'],'CAST-04')
run('台词提及其他人不算出镜',deepcopy(BASE),['CHAR_03'])
s=deepcopy(BASE);s['【公共总规范】']=s['【公共总规范】'].replace('声线锁定：孟露＝','声线锁定：CHAR_03＝');run('代码声线',s,['CHAR_03'])
s=deepcopy(BASE);s['【时间轴】']='0-4秒，孟露开口："测试"（口型对白，口型同步）。';run('标签在台词后',s,['CHAR_03'])
s=deepcopy(BASE);s['【时间轴】']='0-4秒，孟露与许妍同镜，她开口："测试"（口型对白，口型同步）。';s['【参考】']+='；CHAR_01＝人物图';s['【公共总规范】']+='\n';run('多人代词不擅删声线',s,['CHAR_01','CHAR_03'])
s=deepcopy(BASE);s['【时间轴】']='0-4秒，孟露开口："泰语"（口型对白，中文义：瓦塔纳坤这个姓）。';run('中文义中同字姓氏排除',s,['CHAR_03'])
s=deepcopy(BASE);s['【时间轴】']+='（空间：画内孟露；画外许妍、周凯）';run('空间尾未出镜名单排除',s,['CHAR_03'])
s=deepcopy(BASE);s['【时间轴】']='0-4秒，孟露（画外延续，无口型）"测试"';run('具名画外声必须绑定',s,[],'CAST-01')
print(f'CAST回归：{count}/{count}通过')
