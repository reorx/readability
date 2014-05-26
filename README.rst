
Readability
===========


Another algorithm & implementation of widely known readability conception.


Usage:

.. code-block:: python

    import requests
    from readability import Readability

    html = requests.get('http://blog.hucheng.com/articles/482.html').content
    parser = Readability(html.decode('utf8'))

    parser.title
    parser.article
    parser.article.get_text()
