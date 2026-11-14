import ChainOfProof
open ChainOfProof

namespace Cert.A051

def cited : List Fact := [
  ⟨8865, .fileRenamed, 1427142662909250, 1, 12528, 12529⟩,
  ⟨2286, .cloudFile, 1427142755072000, 1000, 1424, 1426⟩ ]

def claim : Claim := .before 8865 2286

theorem verified : holds cited claim = true := by decide +kernel

end Cert.A051

#print axioms Cert.A051.verified
