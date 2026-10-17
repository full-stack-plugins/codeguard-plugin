# Portable vendor byte verification

Managed skills remain owned by their locked source repositories. The verifier
fix does not update a source ref, lock digest or skill blob. Plugin versioning
and publication are separate release steps.

The directory digest sorts case-sensitive POSIX **relative path strings** and
hashes each relative path plus the SHA256 of the file's original bytes. It does
not sort native Path objects, case-fold paths, normalize Unicode, or rewrite
CRLF during validation. Binary data is hashed unchanged. Mixed case and file /
directory prefixes have explicit regression coverage.

The private upstream checkout uses command-local `core.autocrlf=false` and
`core.eol=lf`; it does not change global / repository Git configuration or
replace inherited `GIT_CONFIG_COUNT` options. Tests use a real temporary Git
source and prove LF text, exact binary bytes and unchanged caller configuration
even when inherited settings request CRLF.

`.gitattributes` declares `skills/** text=auto eol=lf`. Git detects binary files
and preserves their bytes; text snapshots use LF on future checkouts. Adding
this policy does **not** repair bytes already present in a Windows working tree.
A current CRLF snapshot must continue to fail raw-byte vendor validation. Do
not regenerate the lock, silently normalize during hashing, overwrite local
changes, or reset the whole skills directory to make that failure disappear.
Use a separately verified clean LF checkout when local bytes differ. Any repair
of an existing checkout requires per-file verification and preservation of all
real modifications and untracked files.

Validation commands (temporary files must be on the approved development drive):

```text
python -B -m unittest discover -s tests -p test_skill_vendor_portability.py -v
python -B scripts/vendor/skill_vendor.py check --offline
python -B scripts/vendor/skill_vendor.py check
```

Offline checks prove local byte equality. Online checks additionally verify the
pinned upstream ref / commit and byte content; they do not prove installed-agent
loading, actual model invocation, or release publication.

## Existing Windows checkout verification

On 2026-10-17 the existing checkout initially failed its raw-byte checks. Each
tracked skill file was compared with its Git blob before any repair; only exact
CRLF equivalents were restored to the already locked source bytes. All 484
restored text files were backed up with before/source SHA256 records on the
approved development drive. Real modifications and untracked files were not
included. Skill blobs and the source lock remain unchanged in Git.

After restoration, both offline and online checks in this actual checkout
passed; the earlier failures and isolated LF results remain separate evidence.
The five portability tests also passed independently on Windows. These checks
do not claim a plugin release or installed-host acceptance.
