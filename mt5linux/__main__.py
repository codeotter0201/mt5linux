def __generate_server_classic(fname):
    code = r'''#!/usr/bin/env python

# Code from: https://github.com/tomerfiliba-org/rpyc

"""
classic rpyc server (threaded, forking or std) running a SlaveService
usage:
    rpyc_classic.py                         # default settings
    rpyc_classic.py -m forking -p 12345     # custom settings

    # ssl-authenticated server (keyfile and certfile are required)
    rpyc_classic.py --ssl-keyfile keyfile.pem --ssl-certfile certfile.pem --ssl-cafile cafile.pem
"""
import sys
import os
import rpyc
from plumbum import cli
from rpyc.utils.server import ThreadedServer, ForkingServer, OneShotServer
from rpyc.utils.classic import DEFAULT_SERVER_PORT, DEFAULT_SERVER_SSL_PORT
from rpyc.utils.registry import REGISTRY_PORT
from rpyc.utils.registry import UDPRegistryClient, TCPRegistryClient
from rpyc.utils.authenticators import SSLAuthenticator
from rpyc.lib import setup_logger
from rpyc.core import SlaveService


class ClassicServer(cli.Application):
    mode = cli.SwitchAttr(["-m", "--mode"], cli.Set("threaded", "forking", "stdio", "oneshot"),
                          default="threaded", help="The serving mode (threaded, forking, or 'stdio' for "
                          "inetd, etc.)")

    port = cli.SwitchAttr(["-p", "--port"], cli.Range(0, 65535), default=None,
                          help="The TCP listener port ("
                               "default = {DEFAULT_SERVER_PORT!r}, "
                               "default for SSL = {DEFAULT_SERVER_SSL_PORT!r})",
                          group="Socket Options")
    host = cli.SwitchAttr(["--host"], str, default="", help="The host to bind to. "
                          "The default is localhost", group="Socket Options")
    ipv6 = cli.Flag(["--ipv6"], help="Enable IPv6", group="Socket Options")

    logfile = cli.SwitchAttr("--logfile", str, default=None, help="Specify the log file to use; "
                             "the default is stderr", group="Logging")
    quiet = cli.Flag(["-q", "--quiet"], help="Quiet mode (only errors will be logged)",
                     group="Logging")

    ssl_keyfile = cli.SwitchAttr("--ssl-keyfile", cli.ExistingFile,
                                 help="The keyfile to use for SSL. Required for SSL", group="SSL",
                                 requires=["--ssl-certfile"])
    ssl_certfile = cli.SwitchAttr("--ssl-certfile", cli.ExistingFile,
                                  help="The certificate file to use for SSL. Required for SSL", group="SSL",
                                  requires=["--ssl-keyfile"])
    ssl_cafile = cli.SwitchAttr("--ssl-cafile", cli.ExistingFile,
                                help="The certificate authority chain file to use for SSL. "
                                "Optional; enables client-side authentication",
                                group="SSL", requires=["--ssl-keyfile"])

    auto_register = cli.Flag("--register", help="Asks the server to attempt registering with "
                             "a registry server. By default, the server will not attempt to register",
                             group="Registry")
    registry_type = cli.SwitchAttr("--registry-type", cli.Set("UDP", "TCP"),
                                   default="UDP", help="Specify a UDP or TCP registry", group="Registry")
    registry_port = cli.SwitchAttr("--registry-port", cli.Range(0, 65535), default=REGISTRY_PORT,
                                   help="The registry's UDP/TCP port", group="Registry")
    registry_host = cli.SwitchAttr("--registry-host", str, default=None,
                                   help="The registry host machine. For UDP, the default is 255.255.255.255; "
                                   "for TCP, a value is required", group="Registry")

    def main(self):
        if not self.host:
            self.host = "::1" if self.ipv6 else "127.0.0.1"

        if self.registry_type == "UDP":
            if self.registry_host is None:
                self.registry_host = "255.255.255.255"
            self.registrar = UDPRegistryClient(ip=self.registry_host, port=self.registry_port)
        else:
            if self.registry_host is None:
                raise ValueError("With TCP registry, you must specify --registry-host")
            self.registrar = TCPRegistryClient(ip=self.registry_host, port=self.registry_port)

        if self.ssl_keyfile:
            self.authenticator = SSLAuthenticator(self.ssl_keyfile, self.ssl_certfile,
                                                  self.ssl_cafile)
            default_port = DEFAULT_SERVER_SSL_PORT
        else:
            self.authenticator = None
            default_port = DEFAULT_SERVER_PORT
        if self.port is None:
            self.port = default_port

        setup_logger(self.quiet, self.logfile)

        if self.mode == "threaded":
            self._serve_mode(ThreadedServer)
        elif self.mode == "forking":
            self._serve_mode(ForkingServer)
        elif self.mode == "oneshot":
            self._serve_oneshot()
        elif self.mode == "stdio":
            self._serve_stdio()

    def _serve_mode(self, factory):
        t = factory(SlaveService, hostname=self.host, port=self.port,
                    reuse_addr=True, ipv6=self.ipv6, authenticator=self.authenticator,
                    registrar=self.registrar, auto_register=self.auto_register)
        t.start()

    def _serve_oneshot(self):
        t = OneShotServer(SlaveService, hostname=self.host, port=self.port,
                          reuse_addr=True, ipv6=self.ipv6, authenticator=self.authenticator,
                          registrar=self.registrar, auto_register=self.auto_register)
        t._listen()
        sys.stdout.write("rpyc-oneshot\n")
        sys.stdout.write(f"{t.host}\t{t.port}\n")
        sys.stdout.flush()
        t.start()

    def _serve_stdio(self):
        origstdin = sys.stdin
        origstdout = sys.stdout
        sys.stdin = open(os.devnull, "r")
        sys.stdout = open(os.devnull, "w")
        sys.stderr = open(os.devnull, "w")
        conn = rpyc.classic.connect_pipes(origstdin, origstdout)
        try:
            try:
                conn.serve_all()
            except KeyboardInterrupt:
                print("User interrupt!")
        finally:
            conn.close()


if __name__ == "__main__":
    ClassicServer.run()
'''
    with open(fname, "w") as fp:
        fp.write(code)


def main():
    from rpyc.utils.classic import DEFAULT_SERVER_PORT, DEFAULT_SERVER_SSL_PORT
    import os
    from subprocess import Popen
    import argparse

    parser = argparse.ArgumentParser(description="Create Server.")
    parser.add_argument(
        "python",
        type=str,
        help="Python that will run the server (have to be a Windows version!)",
    )
    parser.add_argument(
        "--host",
        type=str,
        default="localhost",
        help="The host to connect to. The default is localhost",
    )
    parser.add_argument(
        "-p",
        "--port",
        type=int,
        default=DEFAULT_SERVER_PORT,
        help=f"The TCP listener port (default = {DEFAULT_SERVER_PORT!r}, default for SSL = {DEFAULT_SERVER_SSL_PORT!r})",
    )
    parser.add_argument(
        "-w",
        "--wine",
        type=str,
        default="wine",
        help="Command line to call wine program (default = wine)",
    )
    parser.add_argument(
        "-s",
        "--server",
        type=str,
        default="/tmp/mt5linux",
        help="Path where the server will be build and run (defaul = /tmp/mt5linux)",
    )
    args = parser.parse_args()
    #
    wine_cmd = args.wine
    win_python_path = args.python
    server_dir = args.server
    server_code = "server.py"
    port = args.port
    host = args.host
    #
    Popen(["mkdir", "-p", server_dir], shell=True).wait()
    __generate_server_classic(os.path.join(server_dir, server_code))
    Popen(
        [
            wine_cmd,
            os.path.join(win_python_path),
            os.path.join(server_dir, server_code),
            "--host",
            host,
            "-p",
            str(port),
        ],
        shell=True,
    ).wait()


if __name__ == "__main__":
    main()
