import ChainOfProof
open ChainOfProof

namespace Cert.M084

def cited : List Fact := [
  ⟨70, .fileCreated, 1424037140430000, 10000, 18, 19⟩,
  ⟨95, .fileModified, 1419018826000000, 10000, 18, 19⟩,
  ⟨208, .tag, 1794614400000000, 1, 18, 118⟩ ]

def claim : Claim := .both (Sets.copiedHere 70 95) (Sets.tagged 70 .obj 208 118)

theorem verified : holds cited claim = true := by decide +kernel

end Cert.M084

#print axioms Cert.M084.verified
