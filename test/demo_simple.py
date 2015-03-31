#!/usr/bin/env python
# -*- coding: utf-8 -*-

from readability import Readability


if __name__ == '__main__':
    with open('test/cases/google_code.html') as f:
        html = f.read().decode('utf8')

    parser = Readability(html)

    print 'depth\ttextlen\tp_br\t+\t-\toffset\tpriority\tposition'
    for i in parser.tops:
        #print i.keys()
        print '{depth}\t{textlen}\t{p_br}\t{positive}\t{negative}\t{offset}\t{priority}\t{pos}'.format(**dict(
            depth=i['depth'],
            textlen=i['text_len'],
            p_br=i['p_br_num'],
            positive=i['positive_score'],
            negative=i['negative_score'],
            offset=i['offset'],
            priority=i['priority'],
            pos=i['node'].get_path()
        ))

    n0 = parser.tops[0]['node']
    print type(n0)
    print n0.get_path()
