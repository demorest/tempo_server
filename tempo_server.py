#! /usr/bin/env python

# A simple HTTP server that takes requests to generate polycos and
# replies using the VCI XML polyomial format.  Requires the 
# tempo_utils python package which can be found at:
#
#  http://github.com/demorest/tempo_utils
#
# as well as tempo which can be found at:
#
#  http://tempo.sourceforge.net/
#
# P. Demorest, 2017/06

import time
import os
import BaseHTTPServer
import urlparse
from lxml import etree
import tempo_utils

class TempoError(Exception):
    def __init__(self, result):
        self.result = result

class TempoHandler(BaseHTTPServer.BaseHTTPRequestHandler):

    def send_header_OK(self,ctype='text/plain'):
        self.send_response(200)
        self.send_header("Content-type", ctype)
        self.end_headers()

    def do_GET(self):

        # Split up path into components
        url = urlparse.urlparse(self.path)

        # Generate polycos according to the parameters
        if url.path == '/polyco':

            try:
                params = urlparse.parse_qs(url.query)

                parfile = params['parfile'][0]
                # Try opening file so that any IO exceptions get raised here
                open(parfile,'r')

                tstart = float(params['start'][0])

                # Generate one 1-hour polyco block with default params
                self.log_message("parfile='%s' tstart=%.8f" % (parfile,tstart))
                polys = tempo_utils.polycos.generate(parfile,'6',tstart,1.0)
                if len(polys)==0:
                    raise TempoError(polys)
                model_xml = self.polyco_to_xml(polys[0])

                self.send_header_OK(ctype='text/xml')
                self.log_message("sending result")
                self.wfile.write(model_xml)

            except TempoError as ex:
                self.log_error("Error calling tempo:")
                self.log_error("tempo_args = " + str(ex.result.tempo_args))
                self.log_error("tempo_output = " + ex.result.tempo_output)
                self.send_header_OK()
                self.wfile.write("Error calling tempo")

            except Exception as ex:
                self.log_error("Error processing request: " + repr(ex))
                self.send_header_OK() # should send an http error code?
                self.wfile.write("Error processing request")

        # Called with some other base path, could make up some info page
        else:
            self.send_header_OK()
            self.wfile.write("This is tempo_server!\n")

    @staticmethod
    def polyco_to_xml(p):
        tmid = ('%05d'%p.imjd) +  ('%.15f'%p.fmjd).lstrip('0')
        phaseBinModel = etree.Element('phaseBinModel',
                attrib = {
                    'numCff': '%d' % p.ncoeff,
                    'phaseRef': '%.10f' % p.rphase,
                    'freqRef': '%.15f' % p.rfreq,
                    'tMid': tmid
                    }
                )
        for i in range(p.ncoeff):
            ctmp = etree.SubElement(phaseBinModel, 'modelCff',
                    attrib = {
                        'index': '%d' % i,
                        'cff': '%+.15E' % p.coeffs[i]
                        }
                    )
        return etree.tostring(phaseBinModel, pretty_print=True, 
                xml_declaration=True, encoding='UTF-8')

if __name__ == "__main__":
    httpd = BaseHTTPServer.HTTPServer(('',8888), TempoHandler)
    print "Starting at ", time.asctime()
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        pass
    httpd.server_close()

