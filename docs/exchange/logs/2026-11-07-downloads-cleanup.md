# Downloads cleanup

Barry requested removal of disposable project downloads and an end to using
Downloads for project storage.

Cleared 31 project files and the generated `xraise` Python cache from Downloads
to recoverable system Trash, totalling 57,872,256 bytes. Eighteen files already
had byte-identical retained copies. The other 13 archives were first preserved
under ignored `private_archive/downloads_preserved_2026-11-07/` and verified
against their original SHA-256 hashes.

After cleanup, all retained copies and all trashed files were rehashed and
matched the inventory. Downloads contains only Finder metadata. No active
project scripts depended on Downloads; historical evidence paths remain intact.
The detailed inventory, retained-copy mapping, Trash receipt and verification
are under ignored `private_archive/downloads_cleanup_2026-11-07/`.

`AGENTS.md` now directs future transfers to ignored `private_archive/incoming/`
and requires any unavoidable browser-created Downloads copy to be cleared in
the same task.
