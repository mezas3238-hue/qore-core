# SHARED B PROVENANCE POINTER SUPPORT 001

Adds two B-native governance provenance pointers without changing any B workstream status:

- B-01 -> run 36765392663 / artifact 11120068080
- B-23 -> run 36757894898 / artifact 11117192542

Both artifacts belong to the Architect-B branch and are distinct, preserving the manifest's one-artifact-per-pointer invariant.

The pointers conservatively set source_hash_verified_inside_artifact=false because this support patch does not claim internal source-hash verification beyond the existing sealed artifact lineage.

B-14 is intentionally NOT added here. Its authoritative agricultural absence evidence predates the B branch, while the current B provenance contract rejects branch escape. B-14 therefore requires an explicit inherited-evidence provenance policy or a B-native sealed re-binding; it must not be forced into the manifest by falsifying head_branch.
