import xmlrpclib
s = xmlrpclib.Server('http://localhost:7080/')
print s.add(3, 4)