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
    emailSent     message id               recipient
    cdBurn        burn session / path      0
    tag           tagged entity            tag id
-/
namespace ChainOfProof

inductive Kind where
  | usbInsert | volumeMount | lnkTarget
  | fileCreated | fileModified | fileDeleted
  | webSearch | emailSent | cdBurn
  | tag
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
