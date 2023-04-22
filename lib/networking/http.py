import http
import trio
import io
from contextvars import ContextVar

req_remote = ContextVar("req_remote")
req_headers = ContextVar("req_headers")
req_body = ContextVar("req_body")

res_headers = ContextVar("res_headers")
res_status = ContextVar("res_status")

def to_bytes(value):
    if isinstance(value, str):
        return value.encode("utf-8")
    elif isinstance(value, bytes):
        return value
    else:
        raise ValueError("Return value must be bytes")
    
class HTTPError(Exception):
    def __init__(self, code: int, msg=None):
        self.code = code
        self.msg = msg if msg else http.HTTPStatus(code).name.replace("_", " ").title()


class Headers(dict):
    def __getitem__(self, item):
        return super().__getitem__(item.lower())

    def __setitem__(self, item, value):
        super().__setitem__(item.lower(), value)


class Request():
    def __init__(self, conn: trio.SocketStream):
        self.connection = conn
        self.assocResponse = Response(self, conn)

    async def receive(self):
        bytestream = io.BytesIO()
        received_data = b""

        while b"\r\n\r\n" not in received_data:
            received_data = await self.connection.receive_some(1024)
            bytestream.write(received_data)
        
        headers, _, content = bytestream.getvalue().partition(b"\r\n\r\n")
        self.method, self.path, self.headers = self.parseHeaders(headers)
        
        content_length = int(self.headers.get("content-length", 0))
        with trio.move_on_after(2):
            if content_length:
                size = len(content)
                bytestream = io.BytesIO()
                bytestream.write(content)
                while size < content_length:
                    new = await self.connection.receive_some(content_length - size)
                    bytestream.write(new)
                    size += len(new)
                content = bytestream.getvalue()
            elif content:
                raise HTTPError(411)

            self.content = content
            return
        raise HTTPError(408)

    def parseHeaders(self, value: str):
        headers = value.decode("utf-8").split("\r\n")
        metaheader = headers.pop(0)
        method, path, *_ = metaheader.split()
        headers = Headers({key.lower(): value for key, value in (line.split(": ", maxsplit=1) for line in headers)})
        return method, path, headers

    def getParams(self):
        return(self.method, self.path, self.headers, self.content)


class Response():
    for key in ["status", "headers"]:

        def getter(self, key=key):
            return globals()["res_" + key].get(None)

        def setter(self, value, key=key):
            return globals()["res_" + key].set(value)

        vars()[key] = property(fget=getter, fset=setter)

    def __init__(self, req: Request, conn: trio.SocketStream):
        self.assocRequest = req
        self.connection = conn
        self.header = ''

    def buildHeaders(self):
        bytestream = io.BytesIO()
        status = self.status
        bytestream.write(b"HTTP/1.1 ")
        if status is None:
            bytestream.write(b"200 OK\r\n")
        else:
            bytestream.write(str(status.code).encode("utf-8"))
            bytestream.write(b" ")
            bytestream.write(status.msg.encode("utf-8"))
            bytestream.write(b"\r\n")
        headers = self.headers or {}
        for key, value in headers.items():
            bytestream.write(key.encode("utf-8"))
            bytestream.write(b": ")
            bytestream.write(str(value).encode("utf-8"))
            bytestream.write(b"\r\n")
        bytestream.write(b"\r\n")

        self.header = bytestream.getvalue()

    async def send(self):
        await self.connection.send_all(to_bytes(self.header))
