"""Small kunanyi compatibility shim for plutokore import-time gadget support.

The particle/XRAiSE smoke path does not use plutokore.gadget, but plutokore's
top-level import imports that module. This shim keeps the unused import from
blocking the runtime when the site Anaconda module lacks yt.
"""
