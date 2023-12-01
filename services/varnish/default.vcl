vcl 4.1;

import dynamic;
backend default none;

sub vcl_init {
    new d = dynamic.director(port = "80");
}

sub vcl_recv {
    set req.backend_hint = d.backend("nginx");
}

sub vcl_backend_response {
    # Provides Content-Lenght header, needed by GDAL vsicurl
    set beresp.do_stream = false;
}
