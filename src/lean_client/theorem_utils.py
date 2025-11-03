from lean_client.client import Diagnostic, Range


def get_diagnostics_in_range(r: Range, ds: list[Diagnostic]) -> list[Diagnostic]:
    return [d for d in ds if r.intersect(d.range) or r.immediately_before(d.range)]


def get_errors_in_range(r: Range, ds: list[Diagnostic]) -> list[Diagnostic]:
    diagnostics_in_range = get_diagnostics_in_range(r, ds)
    return [d for d in diagnostics_in_range if d.severity == 1]
