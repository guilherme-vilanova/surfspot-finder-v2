"""Application/orchestration layer: wires providers + ranking + caching
together into the operations the web layer needs (resolve a location, find
candidate beaches, rank them, build map links). Flask routes should only ever
call into this package, never into providers/ or ranking/ directly.
"""
