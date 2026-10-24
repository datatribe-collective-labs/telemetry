import inspect

from backend.api import app


def test_openapi_and_synthetic_routes():
    schema=app.openapi()
    assert schema['openapi'].startswith('3.')
    # Check OpenAPI paths instead of app.routes (which has internal _IncludedRouter objects)
    synthetic_paths=[p for p in schema['paths'] if p.startswith('/telemetry/synthetic')]
    assert len(synthetic_paths)==12
    # Verify all synthetic endpoints are sync (not coroutine) when they have db dependency
    for path in synthetic_paths:
        methods = schema['paths'][path]
        for spec in methods.values():
            if 'operationId' in spec:
                op_id = spec['operationId']
                # Find the actual route endpoint
                for route in app.routes:
                    if hasattr(route, 'path') and route.path == path and hasattr(route, 'endpoint'):
                        endpoint = route.endpoint
                        sig = inspect.signature(endpoint)
                        if 'db' in sig.parameters:
                            assert not inspect.iscoroutinefunction(endpoint), f"{op_id} should be sync"
