# This work was supported by the Oak Ridge Leadership Computing Facility at
# the Oak Ridge National Laboratory, which is managed by UT Battelle, LLC for
# the U.S. DOE (under the contract No. DE-AC05-00OR22725).
#
#
# This file is part of OddMon.
#
# OddMon is free software: you can redistribute it and/or modify it under the
# terms of the GNU General Public License as published by the Free Software
# Foundation, either version 2 of the License, or (at your option) any later
# version.
#
# OddMon is distributed in the hope that it will be useful, but WITHOUT ANY
# WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS
# FOR A PARTICULAR PURPOSE.  See the GNU General Public License for more
# details.
#
# You should have received a copy of the GNU General Public License along
# with OddMon.  If not, see <http://www.gnu.org/licenses/>.

from SimpleXMLRPCServer import SimpleXMLRPCServer
from SimpleXMLRPCServer import SimpleXMLRPCRequestHandler


def ost_list(fsname=None):
    pass

def ost_ranks(top=None):
    pass



class RequestHandler(SimpleXMLRPCRequestHandler):
    rpc_paths = ('/RPC2', )

# Create server

def main(host='localhost', port=8889)
    server = SimpleXMLRPCServer(
        (host, port), requestHandler=RequestHandler)

    server.register_introspection_functions()

    # register functions

    server.register_function(ost_list)
    server.register_function(ost_ranks)

    # run the server

    server.serve_forever()






