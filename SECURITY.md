# Security Policy

## Supported versions

| Version | Supported |
|---|:--:|
| 1.6.x | ✅ |
| < 1.6 | ❌ |

## Reporting a vulnerability

Please **do not** open a public issue for security problems.

Report privately through GitHub's
[private vulnerability reporting](https://github.com/aditbytes/PARC-Delta-Lab/security/advisories/new)
(**Security → Report a vulnerability**). Include:

- the affected file(s) and version or commit,
- steps to reproduce, and
- the impact you expect.

You can expect an acknowledgement within 7 days. Confirmed issues are fixed on `main` and noted in
the [changelog](CHANGELOG.md).

## Scope

This repository contains offline research and design code. Relevant reports include unsafe handling
of untrusted input files (for example, the JSON snapshot read by `parc_delta_v10.cli`), command
injection in pipeline scripts that call external tools, and vulnerable dependencies.

**Physical safety is out of scope for this policy.** PDX-1 is a concept study and must not be built
from these files. Its open questions (high-field magnets, stored energy, ¹¹B(α,n) neutrons) require
professional engineering and radiation-safety review.
