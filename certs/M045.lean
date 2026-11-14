import ChainOfProof
open ChainOfProof

namespace Cert.M045

def cited : List Fact := [
  ⟨299, .webSearch, 1427133919638342, 1, 166, 159⟩,
  ⟨480, .tag, 1794614400000000, 1, 166, 229⟩ ]

def claim : Claim := .both (Sets.searched 299) (Sets.tagged 299 .obj 480 229)

theorem verified : holds cited claim = true := by decide +kernel

end Cert.M045

#print axioms Cert.M045.verified
