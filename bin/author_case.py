"""
Try to correct author names that are written in all uppercase or all lowercase.

Produces a list of changes that can be read by change_authors.py.

"""

import sys
import os.path
import anthology
import logging
logging.basicConfig(level=logging.INFO)


# https://gist.githubusercontent.com/stevejackson/1429696/raw/0ae04f6d1af406a43ca617b2bdb9b2ef7034ba5a/gistfile1.txt
pinyin = {
    'a', 'ba', 'pa', 'ma', 'fa', 'da', 'ta', 'na', 'la', 'ga', 'ka', 'ha', 'zha', 'cha', 'sha', 'za', 'ca', 'sa', 
    'ai', 'bai', 'pai', 'mai', 'dai', 'tai', 'nai', 'lai', 'gai', 'kai', 'hai', 'zhai', 'chai', 'shai', 'zai', 'cai', 'sai', 
    'an', 'ban', 'pan', 'man', 'fan', 'dan', 'tan', 'nan', 'lan', 'gan', 'kan', 'han', 'zhan', 'chan', 'shan', 'ran', 'zan', 'can', 'san',
    'ang', 'bang', 'pang', 'mang', 'fang', 'dang', 'tang', 'nang', 'lang', 'gang', 'kang', 'hang', 'zhang', 'chang', 'shang', 'rang', 'zang', 'cang', 'sang', 
    'ao', 'bao', 'pao', 'mao', 'dao', 'tao', 'nao', 'lao', 'gao', 'kao', 'hao', 'zhao', 'chao', 'shao', 'rao', 'zao', 'cao', 'sao', 
    'e', 'me', 'de', 'te', 'ne', 'le', 'ge', 'ke', 'he', 'zhe', 'che', 'she', 're', 'ze', 'ce', 'se', 
    'ei', 'bei', 'pei', 'mei', 'fei', 'dei', 'nei', 'lei', 'gei', 'hei', 'shei', 'zei', 
    'beng', 'peng', 'meng', 'feng', 'deng', 'teng', 'neng', 'leng', 'geng', 'keng', 'heng', 'zheng', 'cheng', 'sheng', 'reng', 'zeng', 'ceng', 'seng', 
    'er', 
    'yi', 'bi', 'pi', 'mi', 'di', 'ti', 'ni', 'li', 'ji', 'qi', 'xi', 
    'zhi', 'chi', 'shi', 'ri', 'zi', 'ci', 'si', 
    'ya', 'dia', 'lia', 'jia', 'qia', 'xia', 
    'yan', 'bian', 'pian', 'mian', 'dian', 'tian', 'nian', 'lian', 'jian', 'qian', 'xian', 
    'yang', 'niang', 'liang', 'jiang', 'qiang', 'xiang', 
    'yao', 'biao', 'piao', 'miao', 'diao', 'tiao', 'niao', 'liao', 'jiao', 'qiao', 'xiao', 
    'ye', 'bie', 'pie', 'mie', 'die', 'tie', 'nie', 'lie', 'jie', 'qie', 'xie', 'yin', 'bin', 'pin', 'min', 'nin', 'lin', 'jin', 'qin', 'xin', 
    'ying', 'bing', 'ping', 'ming', 'ding', 'ting', 'ning', 'ling', 'jing', 'qing', 'xing',
    'yo', # ?
    'yong', 'jiong', 'qiong', 'xiong', 
    'you', 'miu', 'diu', 'niu', 'liu', 'jiu', 'qiu', 'xiu', 
    'o', 'bo', 'po', 'mo', 'fo', 'lo', 
    'weng',
    'dong', 'tong', 'nong', 'long', 'gong', 'kong', 'hong', 'zhong', 'chong', 'rong', 'zong', 'cong', 'song', 
    'ou', 'pou', 'mou', 'fou', 'dou', 'tou', 'nou', 'lou', 'gou', 'kou', 'hou', 'zhou', 'chou', 'shou', 'rou', 'zou', 'cou', 'sou', 
    'wu', 'bu', 'pu', 'mu', 'fu', 'du', 'tu', 'nu', 'lu', 'gu', 'ku', 'hu', 'zhu', 'chu', 'shu', 'ru', 'zu', 'cu', 'su', 
    'wa', 'gua', 'kua', 'hua', 'zhua', 'shua',
    'wai', 'guai', 'kuai', 'huai', 'chuai', 'shuai', 
    'wan', 'duan', 'tuan', 'nuan', 'luan', 'guan', 'kuan', 'huan', 'zhuan', 'chuan', 'shuan', 'ruan', 'zuan', 'cuan', 'suan', 
    'wang', 'guang', 'kuang', 'huang', 'zhuang', 'chuang', 'shuang', 
    'yue', 'nve', 'lve', 'jue', 'que', 'xue', 
    'wei', 'dui', 'tui', 'gui', 'kui', 'hui', 'zhui', 'chui', 'shui', 'rui', 'zui', 'cui', 'sui', 
    'wen', 'dun', 'tun', 'lun', 'gun', 'kun', 'hun', 'zhun', 'chun', 'shun', 'run', 'zun', 'cun', 'sun', 
    'wo', 'duo', 'tuo', 'nuo', 'luo', 'guo', 'kuo', 'huo', 'zhuo', 'chuo', 'shuo', 'ruo', 'zuo', 'cuo', 'suo', 
    'yu', 'nv', 'lv', 'ju', 'qu', 'xu', 
    'yuan', 'juan', 'quan', 'xuan', 
    'yun', 'jun', 'qun', 'xun', 
}

def normalize(s):
    if s == s.upper() and (len(s) >= 4 or s.lower() in pinyin):
        s = s.title()
    elif s == s.lower():
        s = s.title()
    return s

if __name__ == "__main__":
    scriptdir = os.path.dirname(os.path.abspath(__file__))
    datadir = os.path.join(scriptdir, '..', 'data')
    anth = anthology.Anthology(importdir=datadir)
    for paperid, paper in anth.papers.items():
        for role in ['author', 'editor']:
            if role in paper.attrib:
                for name, personid in paper.attrib[role]:
                    first_norm = normalize(name.first)
                    last_norm = normalize(name.last)
                    if name.first != first_norm or name.last != last_norm:
                        print('{}\t{}\t{} || {}\t{} || {}'.format(paperid, role, name.first, name.last, first_norm, last_norm))
