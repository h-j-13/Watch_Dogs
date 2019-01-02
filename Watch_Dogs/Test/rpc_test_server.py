from twisted.web import xmlrpc, server


class Test(xmlrpc.XMLRPC):

    def xmlrpc_add(self, a, b):
        return a + b

    def xmlrpc_fault(self):
        raise xmlrpc.Fault(123, "The fault procedure is faulty.")


if __name__ == '__main__':
    from twisted.internet import reactor

    r = Test()
    reactor.listenTCP(7080, server.Site(r))
    reactor.run()
