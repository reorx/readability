#!/usr/bin/env python
# -*- coding: utf-8 -*-

# TODO argparse
# TODO option to strip text in elements
# TODO fix bug for newest beautifulsoup4

import re
import math
import logging
import urlparse
import posixpath
from bs4 import BeautifulSoup
from bs4.element import Tag, NavigableString


def get_tag_path(tag, with_attrs=False):
    path = tag.name
    if with_attrs:
        path += unicode(tag.attrs)
    for name in [i.name for i in tag.parents][:-1]:
        path = name + u'/' + path
    return path


Tag.get_path = get_tag_path


logger = logging.getLogger('readability')


REGEX_PATTERNS = {
    'unlikelyCandidates': "combx|comment|comments|cmt|cmts|community|disqus|extra|foot|header|menu|\
                           remark|rss|shoutbox|sidebar|sponsor|ad-break|agegate|\
                           pagination|pager|popup|tweet|twitter",  # x

    'okMaybeItsACandidate': "and|article|body|column|main|shadow|post",

    'socialPlugins': "linkwithin|jiathis",

    'positive': "article|body|content|entry|hentry|main|page|pagination|post|text|\
                 blog|story|footnote",  # x

    'negative': "combx|comment|cmt|com|contact|foot|footer|masthead|media|\
                 meta|outbrain|promo|related|scroll|shoutbox|sidebar|sponsor|\
                 shopping|tags|tool|widget",  # x

    'extraneous': "print|archive|comment|discuss|e[\-]?mail|share|reply|all|login|\
                   sign|single",

    'divToPElements': "<(a|blockquote|dl|div|img|ol|p|pre|table|ul)",  # x

    'replaceBrs': "<br[^>]*>[ \n\r\t]*",  # x

    'replaceFonts': "<(/?)font[^>]*>",  # x

    'shouldNotExist': "<wbr[^>]*>",  # x

    'normalize': "\s{2,}",

    'killBreaks': "(<br\s*/?>(\s|&nbsp;?)*)+",  # x

    'nextLink': "(next|weiter|continue|>([^\|]|$)|»([^\|]|$))",

    'prevLink': "(prev|earl|old|new|<|«)",
}


REGEX_OBJS = {}

for k, v in REGEX_PATTERNS.iteritems():
    REGEX_OBJS[k] = re.compile(v, re.IGNORECASE)


PURE_STRINGS_FILTER = ['\n']


TAGS = {
    'common_block': ['div', 'fieldset', 'aside', 'article', 'blockquote',
                     'footer', 'form', 'header', 'main', 'nav', 'p', 'pre',
                     'section', 'table', 'ul', 'ol',
                     'h1', 'h2', 'h3', 'h4', 'h5', 'h6']
}


class Readability:
    """
    Find the deepest & largest node in a html tree

    Usage:

    >>> parser = Readability(html, url)
    >>> parser.title
    # title of the article
    >>> parser.article
    # main body
    """
    USELESS_TAGS = ['script', 'style', 'link', 'textarea']

    FACTORS = {
        'text': 100,
        'elimination': 8,
        'negative': 10,
        'positive': 10,
        'p_br': 1,
        'comma': 10,
        'priority_compare': 1.66,  # 60%
        'text_tag': 0.6,
        'children': 10,
        'offset': 5
    }

    CHINESE_CHARS = {
        'comma': u'\uff0c',
    }

    DEBUG = False

    def __init__(self, source, url=None):
        assert isinstance(source, unicode), 'source should be unicode'
        self.url = url

        self.raw_source = source

        # the incomplete <p> or </p> will be fixed when soup is constructed
        self.source = format_html(source)

        # Force BeautifulSoup to use lxml as parser (lxml is the best,
        # others may cause problems)
        self.soup = BeautifulSoup(self.source, 'lxml')

        # NOTE There is a stange thing in b4.__version__ 4.0.4
        # that after clean the USELESS_TAGS, <title> in <head> is missing,
        # still don't know where the problem is.
        self.title = u''
        try:
            self.title = self.soup.find('title').text.strip()
        except:
            pass
        logging.info(u'got html title: %s', self.title)

        remove_tags(self.soup, self.USELESS_TAGS)

        # Get most possible nodes
        unsort_tops = self.get_readable_nodes()
        if len(unsort_tops) == 1:
            tops = unsort_tops
        else:
            tops = sorted(
                unsort_tops, key=lambda x: x['priority'], reverse=True)

        self.tops = tops

        self.winner = self.tops[0]

        # use node_to_soup to prevent winner node from changed
        self.article = node_to_soup(
            clean_node(
                node_to_soup(self.winner['node']).body
            )
        ).body
        stringify_contents(self.winner['node'].contents)
        if self.url:
            self.article = fix_images_path(self.article, self.url)

    def get_article_content(self):
        # Remove the <body> tag
        # content = re.sub(r'^\<body\>|\</body\>$', '', unicode(self.article))
        content = u'\n'.join(map(unicode, self.article.contents))
        return content

    def get_readable_nodes(self):
        """
        Player::
            node
            depth
            children_num
            text_len
            priority
        """
        self.players = []

        # NOTE Traversal of the tree should be as less as possible
        for e in self.soup.body.find_all(TAGS['common_block']):
            # If no `__dict__`, its a already removed tag
            # (include children of the removed tag)
            if not e.__dict__:
                continue

            # Filter the impossible nodes semantically before go into play
            id_and_class_list = []
            if e.get('id'):
                id_and_class_list.append(e.get('id'))
            if e.get('class'):
                id_and_class_list += (e.get('class'))
            id_and_class = '_'.join(id_and_class_list)

            # Remove social plugins
            if REGEX_OBJS['socialPlugins'].search(id_and_class) or\
                    (REGEX_OBJS['unlikelyCandidates'].search(id_and_class) and
                     not REGEX_OBJS['positive'].search(id_and_class)):
                logger.debug(
                    'Reject a node and its children, class & id: %s',
                    id_and_class)
                # Use `decompose` instead of `extract` to avoid iteration
                # of the removed tags' children
                e.decompose()
                continue

            # Clean empty tags ?

        # NOTE If filtering and player initializing are in same loop,
        # player's information may not be properly calculated.
        # So seperate them in two loops, means, two traversal of the whole tree
        for e in self.soup.body.find_all(True):

            player = Player({
                'node': e,
                'depth': len(list(e.parents)) - 1,
                'children_num': len(e.contents),
                # When counting text length, ` ` and `\n` shouldn't be involved
                'text_len': len(e.get_text().strip().replace('\n', '').replace(' ', '')),
                'previous_priority': 0,
                'negative_score': 0,
                'positive_score': 0,
                'p_br_num': 0,
                'comma_num': 0,
            })

            # alternative algorithm
            #player['priority'] = math.sqrt(player['depth'] * player['text_len'])
            player['priority'] = player['depth'] * player['text_len'] / self.FACTORS['text']

            self.players.append(player)

        # round one, get the front players by basic priority
        # and affect their priority by tags & children tags
        self.priority_desc_players = sorted(self.players, key=lambda x: x['priority'], reverse=True)
        next_round = self.priority_desc_players[:self.FACTORS['elimination']]

        logger.debug('# round one processing: basic front players')
        self._log_players(next_round)
        self._debug_round('one', next_round)

        for p in next_round:
            # Text tags
            if p['node'].name in ('p', 'b', 'span', 'i', ):
                p['priority'] = p['priority'] * self.FACTORS['text_tag']

            p['priority'] += p['children_num'] * self.FACTORS['children']

        logger.debug('# round one over')
        self._log_players(next_round)
        self._debug_round('one', next_round)

        ## round two, players that smaller than the biggest
        ## after multiplys priority factor will be rejected
        #current_players = next_round
        #next_round = []
        #for loop, p in enumerate(current_players):
        #    go_next = True
        #    if loop != 0:
        #        if p['priority'] * self.FACTORS['priority_compare'] < current_players[0]['priority']:
        #            go_next = False
        #    if go_next:
        #        next_round.append(p)
        #logger.debug('# round two over')
        #self._log_players(next_round)
        #self._debug_round('two', next_round)

        if len(next_round) == 1:
            return next_round

        # round three, affect priority in several ways:
        # 1. try to math negative and positive words in node
        #    and descendants' id and classes
        # 2. count the <p> tag number in node
        # 3. count commas, include EN and CN characters
        current_players = next_round
        for loop, player in enumerate(current_players):
            player['previous_priority'] = player['priority']
            node = player['node']
            offset = 0

            # 1. by id and class
            id_and_classes = []
            cal_list = node.find_all(True)
            cal_list.insert(0, node)
            for e in cal_list:
                if e.get('id'):
                    id_and_classes.append(e.get('id'))
                id_and_classes.extend(e.get('class', []))

            negative_score = 0
            positive_score = 0
            for i in id_and_classes:
                if REGEX_OBJS['negative'].search(i) and\
                        not REGEX_OBJS['positive'].search(i):
                    logger.debug('top %s find negative %s' % (loop, i))
                    negative_score += 1

                if REGEX_OBJS['positive'].search(i) and\
                        not REGEX_OBJS['negative'].search(i):
                    positive_score += 1
            logger.debug('negative score %s' % negative_score)
            logger.debug('positive_score %s' % positive_score)
            offset -= negative_score * self.FACTORS['negative']
            offset += positive_score * self.FACTORS['positive']
            player['negative_score'] = negative_score
            player['positive_score'] = positive_score

            # 2. by <p> and <br> number
            p_br_num = len(node.find_all('p')) + len(node.find_all('br'))
            logger.debug('p br num %s' % p_br_num)
            offset += p_br_num * self.FACTORS['p_br']
            player['p_br_num'] = p_br_num

            # 3. by comma(symbo) number
            node_text = node.get_text()
            comma_num = node_text.count(',')
            comma_num += node_text.count(self.CHINESE_CHARS['comma'])
            logger.debug('comma_num %s' % comma_num)
            offset += comma_num / self.FACTORS['comma']
            player['comma_num'] = comma_num

            player['offset'] = offset
            player['priority'] += offset * self.FACTORS['offset']

        logger.debug('# round three over')
        self._log_players(current_players)

        # Final round, tune priority by depth

        min_depth = sorted([i['depth'] for i in current_players])[0]

        for player in current_players:
            player['relative_depth'] = player['depth'] - min_depth + 1

            player['priority'] = player['priority'] * math.sqrt(player['relative_depth'])

        return current_players

    def _log_player(self, player):
        pass

    def _log_players(self, players):
        if not self.DEBUG:
            return
        for i in players:
            logger.debug(
                'depth:%s text_len:%s priority:%s pre_priority:%s -score:%s +score:%s p_br_num:%s comma_num:%s' %
                (i['depth'], i['text_len'], i['priority'], i['previous_priority'], i['negative_score'], i['positive_score'], i['p_br_num'], i['comma_num']))
            logger.debug('    ' + i['node'].get_text().strip().replace('\n', '')[:100])

    def _debug_round(self, name, players):
        if not self.DEBUG:
            return
        for loop, i in enumerate(players):
            with open('round_%s_%s.html' % (name, loop), 'w') as f:
                f.write(str(i['node']))


class Player(dict):
    """A player is an abstraction layer of a node in html tree,
    it will have following attributes during its life circle:

    - node
    - depth
    - relative_depth
    - priority
    - previous_priority
    - text_len
    - negative_score
    - positive_score
    - children_num
    - p_br_num
    - comma_num

    Player extends from dict, but it can retrieve value in dot style
    like ``player.node``.
    """
    def __getattr__(self, key):
        try:
            return self[key]
        except KeyError:
            raise AttributeError('Has no attribute %s' % key)

    def __setattr__(self, key, value):
        self[key] = value

    def __delattr__(self, key):
        try:
            del self[key]
        except KeyError:
            raise AttributeError(key)

    def __str__(self):
        return '<Player %s>' % (self.position)

    @property
    def path(self):
        if not hasattr(self, '_path'):
            self._path = self.node.get_path()
        return self._path

    @property
    def path_with_attrs(self):
        if not hasattr(self, '_path_with_attrs'):
            self._path_with_attrs = self.node.get_path(True)
        return self._path_with_attrs

    _log_tpl = ('[{path}] priority:{priority} text_len:{text_len} '
                'p_br:{p_br_num} +score:{positive_score} -score:{negative_score} '
                'offset:{offset}')

    def _log(self, head=False):
        d = dict(self)
        d['path'] = self.path
        msg = self._log_tpl.format(**d)
        logger.debug(msg)


def get_element_readable_string(e):
    s = ''
    for i in e.descendants:
        if isinstance(i, unicode):
            buf = i.strip()
            for j in PURE_STRINGS_FILTER:
                buf = buf.replace(j, '')
            s += buf
    return s


def format_html(html):
    """
    Replace deprecated tags
    """
    cleaned = REGEX_OBJS['shouldNotExist'].sub("", html)
    cleaned = REGEX_OBJS['replaceFonts'].sub("<\g<1>span>", cleaned)
    return cleaned


def remove_tag(node, tag):
    for e in node.find_all(tag):
        e.extract()


def remove_tags(node, tags):
    for e in node.find_all(True):
        if e.name in tags:
            e.extract()


def stringify_contents(contents):
    return u''.join(map(unicode, contents))


def _get_node_flag(i):
    if isinstance(i, NavigableString):
        if unicode(i) == u'\n':
            i_flag = 'linebreak'
        else:
            i_flag = 'text'
    else:
        i_flag = 'tag'
    return i_flag


def node_to_soup(node):
    """
    Copy node to a new BeautifulSoup object, do some formatting & cleaning
    at the same time.
    """
    # Strip \n between contents
    contents = []
    for loop, i in enumerate(node.children):
        last_flag = 'tag'
        i_flag = _get_node_flag(i)

        if loop == 0:
            if i_flag == 'linebreak':
                continue
            last_flag = i_flag
        else:
            if last_flag == 'tag' and i_flag == 'linebreak':
                continue
            last_flag = i_flag
        contents.append(i)

    node_u = stringify_contents(contents)

    # Fix &nbsp; show as \xa0 problem
    # http://stackoverflow.com/questions/19508442/beautiful-soup-and-unicode-problems
    node_u = node_u.replace(u'\xa0', u' ')
    return BeautifulSoup(node_u)


def fix_images_path(node, url):
    for img in node.find_all('img'):
        src = img.get('src')
        if not src:
            img.extract()
            continue

        if 'http://' != src[:7] and 'https://' != src[:8]:
            new_src = urlparse.urljoin(url, src)

            new_src_obj = urlparse.urlparse(new_src)
            new_path = posixpath.normpath(new_src_obj[2])
            new_src = urlparse.urlunparse(
                (new_src_obj.scheme, new_src_obj.netloc, new_path,
                 new_src_obj.params, new_src_obj.query, new_src_obj.fragment))
            print 'new src', new_src
            img['src'] = new_src
    return node


EMPTY_TAG_LIST = [
    'a', 'b', 'strong', 'div', 'p', 'span',
    'article', 'section', 'ul', 'li',
    'h1', 'h2', 'h3', 'h4', 'h5', 'h6']


def clean_node(node):
    # TODO replace brs

    # clean empty tags
    for e in node.find_all(EMPTY_TAG_LIST):
        # has image
        has_image = False
        for i in e.descendants:
            if hasattr(i, 'name') and i.name == 'img':
                has_image = True
                break
        if has_image:
            continue

        # has text
        if e.get_text().strip().replace('\n', ''):
            continue
        e.extract()

    # clean wrapper tags
    # Blocks
    for e in node.find_all(['div', 'article', 'section']):
        e.replace_with_children()
    # Inlines
    for e in node.find_all(['span']):
        e.replace_with_children()

    # clean attributes
    def clean_attrs(_e):
        for i in ['class', 'id', 'style', 'align']:
            if i in _e.attrs:
                del _e.attrs[i]

    clean_attrs(node)
    for e in node.find_all(True):
        clean_attrs(e)

    # print 'cleared node'
    # print node.prettify()

    return node

    # text = unicode(node)

    # # clean on text level
    # text = REGEX_OBJS['killBreaks'].sub("<br />", text)


def retrieve_http_body(url):
    import urllib2

    request = urllib2.Request(url)
    ua = ('Mozilla/5.0 (Macintosh; Intel Mac OS X 10_10_2) '
          'AppleWebKit/537.36 (KHTML, like Gecko) '
          'Chrome/41.0.2272.76 Safari/537.36')
    request.add_header('User-Agent', ua)
    r = urllib2.urlopen(request)
    return r.read()


if __name__ == '__main__':
    import sys

    url = ('http://www.smashingmagazine.com/2015/03/06/how-being-in-a-band'
           '-taught-me-to-be-a-better-web-designer/')
    if sys.argv[1:]:
        url = sys.argv[1]

    html = retrieve_http_body(url).decode('utf8')
    parser = Readability(html)

    print parser.get_article_content().encode('utf8')
