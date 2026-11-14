/-
  Facts: the evidence vocabulary. Rows are produced by the extractor, never by an LLM.

  This file is the contract between the Data and Lean roles. Changing `Kind` or `Fact`
  means changing `extractor/schema.sql` and `checker/facts.py` in the same commit.

  Meaning of `obj` / `aux` per kind (both are interned entity ids):

    kind          obj                      aux
    usbInsert     device serial            0
    volumeMount   device serial            volume serial
    lnkTarget     target path              volume serial the target lives on
    fileCreated   file path                volume serial
    fileModified  file path                volume serial
    fileDeleted   original path            volume serial
    webSearch     query string             browser / profile
    emailSent     subject                  "from A to B", as the mailbox records them
    cdBurn        the trace found          where it was found
    tag           tagged entity            tag id
    volumeSeen    volume label             volume serial   (the PC's registry or a shortcut recorded it)
    volumeOnDevice device serial           volume serial   (read from the seized device's image)
    unallocatedOnDevice device serial      area id         (the seized device's image has directory
                                                            entries left outside any current file;
                                                            recovered fileCreated / fileModified rows
                                                            carry the same area id in `aux`)
-/
namespace ChainOfProof

inductive Kind where
  | usbInsert | volumeMount | lnkTarget
  | fileCreated | fileModified | fileDeleted
  | webSearch | emailSent | cdBurn
  | tag
  | volumeSeen | volumeOnDevice
  | unallocatedOnDevice
  deriving DecidableEq, Repr

structure Fact where
  id   : Nat    -- row id in the evidence DB
  kind : Kind
  t    : Nat    -- UTC microseconds since the Unix epoch
  res  : Nat    -- timestamp uncertainty in µs: the true time lies within (t - res, t + res)
  obj  : Nat    -- interned primary entity
  aux  : Nat    -- interned secondary entity
  deriving Repr

/-- A stud: one of a fact's two entity slots. -/
inductive Slot where
  | obj | aux
  deriving DecidableEq, Repr

def Fact.get (f : Fact) : Slot → Nat
  | .obj => f.obj
  | .aux => f.aux

end ChainOfProof
