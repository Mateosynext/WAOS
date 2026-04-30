# WAOS request body limits

WAOS enforces request body limits in application middleware and must also enforce equivalent limits at the edge proxy/load balancer.

Required defaults:

- General API requests: `MAX_REQUEST_BODY_BYTES=2097152` (2 MiB)
- Webhook requests: `MAX_WEBHOOK_BODY_BYTES=1048576` (1 MiB)

The app-level middleware rejects oversized requests before route handlers run. For requests that omit `Content-Length` or use chunked transfer, the middleware reads `request.stream()` incrementally and returns `413 request_body_too_large` as soon as the accumulated bytes exceed the configured limit.

Proxy/load balancer examples:

```nginx
# nginx server/location handling WAOS API traffic
client_max_body_size 2m;

# Optional stricter webhook location
location /webhooks/ {
    client_max_body_size 1m;
    proxy_pass http://waos_backend;
}
```

```haproxy
# Reject payloads larger than 2 MiB before they reach the app tier.
http-request deny status 413 if { req.body_size gt 2097152 }
```

Cloud/load-balancer configurations must use limits equal to or lower than the application values above. Any intentional increase must update the environment variables, this document, and the release validation evidence in the same change.
