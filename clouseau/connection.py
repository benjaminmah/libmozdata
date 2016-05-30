# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this file,
# You can obtain one at http://mozilla.org/MPL/2.0/.

import multiprocessing
from requests.adapters import HTTPAdapter
from requests_futures.sessions import FuturesSession
from requests.packages.urllib3.util.retry import Retry


class Query(object):
    """To use with a Connection

    A query contains the params and the handler to use for these params.
    """

    def __init__(self, url, params=None, handler=None, handlerdata=None):
        """Constructor

        Args:
            url (str): the url
            params (Optional[dict]): the params
            handler (Optional[function]): the handler to apply to the json
            handlerdata (Optional): the data passed as second argument of handler
        """
        self.url = url
        self.params = params
        self.handler = handler
        self.handlerdata = handlerdata

    def __repr__(self):
        return 'url: %s' % self.url


class Connection(object):
    """Represents a connection to a server
    """

    TIMEOUT = 60
    MAX_RETRIES = 256
    MAX_WORKERS = multiprocessing.cpu_count()
    CHUNK_SIZE = 32
    TOKEN = ''

    # Error 429 is for 'Too many requests' => we retry
    STATUS_FORCELIST = [429]

    def __init__(self, base_url, queries=None):
        """Constructor

        Args:
            base_url (str): the server's url
            queries (Optional[Query]): the queries
        """

        self.session = FuturesSession(max_workers=self.MAX_WORKERS)
        retries = Retry(total=Connection.MAX_RETRIES, backoff_factor=1, status_forcelist=Connection.STATUS_FORCELIST)
        self.session.mount(base_url, HTTPAdapter(max_retries=retries))
        self.results = []
        self.queries = queries
        self.exec_queries()

    def __get_cb(self, query):
        """Get the callback to use when data have been retrieved

        Args:
            query (Query): the query

        Returns:
            function: the callback for the query
        """
        def cb(sess, res):
            if res.status_code == 200:
                query.handler(res.json(), query.handlerdata)
            else:
                print('Connection error:')
                print('   url: ', res.url)
                print('   json: ', res.json())

        return cb

    def wait(self):
        """Just wait that all the queries have been treated
        """
        for r in self.results:
            r.result()

    def get_apikey(self):
        """Get the api key

        Returns:
            str: the api key
        """
        return self.TOKEN

    def get_header(self):
        """Get the header to use each query

        Returns:
            dict: the header
        """
        return {'User-Agent': 'clouseau', 'Connection': 'close'}

    def get_auth(self):
        """Get the auth to use each query

        Returns:
            dict: the auth
        """
        return None

    def exec_queries(self, queries=None):
        """Set and exec some queries

        Args:
            queries (Optional[Query]): the queries to exec
        """
        if queries:
            self.queries = queries

        if self.queries:
            if isinstance(self.queries, Query):
                self.queries = [self.queries]

            header = self.get_header()
            auth = self.get_auth()

            for query in self.queries:
                cb = self.__get_cb(query)
                if query.params:
                    if isinstance(query.params, dict):
                        self.results.append(self.session.get(query.url,
                                                             params=query.params,
                                                             headers=header,
                                                             auth=auth,
                                                             verify=True,
                                                             timeout=self.TIMEOUT,
                                                             background_callback=cb))
                    else:
                        for p in query.params:
                            self.results.append(self.session.get(query.url,
                                                                 params=p,
                                                                 headers=header,
                                                                 auth=auth,
                                                                 verify=True,
                                                                 timeout=self.TIMEOUT,
                                                                 background_callback=cb))
                else:
                    self.results.append(self.session.get(query.url,
                                                         headers=header,
                                                         auth=auth,
                                                         verify=True,
                                                         timeout=self.TIMEOUT,
                                                         background_callback=cb))

    @staticmethod
    def chunks(l, chunk_size=CHUNK_SIZE):
        """Get chunk from a list

        Args:
            l (List): data to chunkify
            chunk_size (Optional[int]): the size of each chunk

        Yields:
            a chunk from the data
        """
        for i in range(0, len(l), chunk_size):
            yield l[i:(i + chunk_size)]
