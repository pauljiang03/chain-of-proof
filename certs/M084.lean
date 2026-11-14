import ChainOfProof
open ChainOfProof

namespace Cert.M084

def cited : List Fact := [
  ⟨70, .fileCreated, 1424037140430000, 10000, 18, 19⟩,
  ⟨163, .fileModified, 1419018826000000, 10000, 18, 19⟩,
  ⟨331, .tag, 1794614400000000, 1, 18, 197⟩,
  ⟨332, .tag, 1794614400000000, 1, 18, 201⟩ ]

def claim : Claim := .both (Sets.copiedHere 70 163) (.both (Sets.tagged 70 .obj 331 197) (Sets.tagged 70 .obj 332 201))

theorem verified : holds cited claim = true := by decide +kernel

end Cert.M084

#print axioms Cert.M084.verified
