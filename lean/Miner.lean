import ChainOfProof
import Std.Data.HashMap

/-
  The brute-force miner: enumerate candidate bricks, keep the ones `holds` accepts.

  Generators are untrusted. A bug in one can miss bricks; it cannot emit a false one,
  because only the `holds` filter decides (`mine_sound`).

  Not built yet: `lake exe mine` (read facts.jsonl, write bricks.jsonl), generators
  for the remaining sets, and the chainer.
-/
open Std
namespace ChainOfProof

structure Brick where
  claim : Claim
  cited : List Fact    -- the few facts this brick talks about

/-- Small kinds: plain nested loops. -/
def candUsbMounted (fs : Array Fact) : Array Brick := Id.run do
  let us := fs.filter (·.kind == .usbInsert)
  let ms := fs.filter (·.kind == .volumeMount)
  let mut out := #[]
  for u in us do
    for m in ms do
      out := out.push ⟨Sets.usbMountedAs u.id m.id, [u, m]⟩
  return out

/-- Large kinds: hash-join on the shared stud instead of nested loops. -/
def candCopied (fs : Array Fact) : Array Brick := Id.run do
  let mut byPath : HashMap Nat (Array Fact) := {}
  for f in fs do
    if f.kind == .fileModified then
      byPath := byPath.insert f.obj ((byPath.getD f.obj #[]).push f)
  let mut out := #[]
  for c in fs do
    if c.kind == .fileCreated then
      for m in byPath.getD c.obj #[] do
        out := out.push ⟨Sets.copiedHere c.id m.id, [c, m]⟩
  return out

/-- Record observations keep their own types; no promotion into filesystem events. -/
def candRecordedObservations (fs : Array Fact) : Array Brick := Id.run do
  let mut out := #[]
  for f in fs do
    if f.kind == .fileRemoved then
      out := out.push ⟨Sets.fileRemovedAt f.id, [f]⟩
    if f.kind == .volumeRecorded then
      out := out.push ⟨Sets.volumeRecordedAt f.id, [f]⟩
    if f.kind == .fileCreationRecorded then
      out := out.push ⟨Sets.fileCreationRecordedAt f.id, [f]⟩
    if f.kind == .journalName then
      out := out.push ⟨Sets.journalNamed f.id, [f]⟩
    if f.kind == .journalParent then
      out := out.push ⟨Sets.journalParentRecorded f.id, [f]⟩
    if f.kind == .journalRemoval then
      out := out.push ⟨Sets.journalRemovalObserved f.id, [f]⟩
  return out

def candCreatedAfterVolume (fs : Array Fact) : Array Brick := Id.run do
  let vs := fs.filter (·.kind == .volumeRecorded)
  let mut out := #[]
  for c in fs do
    if c.kind == .fileCreated then
      for v in vs do
        out := out.push ⟨Sets.createdAfterVolumeRecord c.id v.id, [c, v]⟩
  return out

def candidates (fs : Array Fact) : Array Brick :=
  candUsbMounted fs ++ candCopied fs ++ candRecordedObservations fs ++ candCreatedAfterVolume fs

/-- Keep only candidates that hold on their own cited facts. -/
def mine (fs : Array Fact) : List Brick :=
  (candidates fs).toList.filter (fun b => holds b.cited b.claim)

/-- Soundness, for all inputs: anything the miner emits holds. -/
theorem mine_sound {fs : Array Fact} {b : Brick} (h : b ∈ mine fs) :
    holds b.cited b.claim = true :=
  (List.mem_filter.mp h).2

end ChainOfProof
