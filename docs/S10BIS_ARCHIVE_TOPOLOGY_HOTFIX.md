# S10bis archive-topology runtime hotfix

## Finding

A real bootstrap journal from the merged S10bis runtime reached `COMPONENT_ARTIFACT_VERIFIED` for the pinned Linux x86_64 llama.cpp OpenVINO archive and then failed at `ENGINE_COMPONENT` with `ComponentStoreError: archive links/devices are forbidden`. A second retry failed identically. The old remediation (`CLEAR_COMPONENT_CACHE_AND_RETRY`) was therefore non-causal for this class.

## Minimal reticular refactor

`verified archive -> topology preflight -> confined link resolution -> regular-file materialization -> symlink-free installed tree -> tree digest -> engine readiness`

The archive may contain symlink/hardlink metadata only when every link is relative, remains inside the archive namespace, has an existing acyclic bounded chain, and resolves to a regular file. The installed component never contains a symlink: safe aliases are copied from the final verified regular member. Traversal, absolute links, missing targets, cycles, link-to-directory/device, fifo/device nodes, duplicate paths, non-directory parents and host-filesystem resolution fail closed.

Materialized alias bytes count toward the existing 512 MiB extraction bound. Link depth is bounded to 32. Destination replacement remains atomic and failed extraction removes the temporary tree.

## Failure semantics

Unsafe topology is typed as `ArchiveTopologyError` and S10bis maps it to `ENGINE_ARCHIVE_UNSAFE_TOPOLOGY` / `VERIFY_ENGINE_ARTIFACT` / `manual`, instead of suggesting a cache retry that cannot change the artifact topology.

## Falsification

`python scripts/archive_topology_mutations.py --mutations 10000000 --tail 1000`

Observed locally on the candidate model: 10,000,000 mutation instances, 24/24 mutation families, 24 kill classes, 1,536 causal signatures, 0 survivors, +1,000 tail novelty 0. Representative executable TAR fixtures additionally cover OpenVINO-shaped internal aliases, parent-relative symlinks, hardlinks, link chains, expansion amplification and unsafe topology denial.

The mutation harness is a semantic/adversarial topology model; the executable TAR tests exercise the actual Python extraction boundary.
