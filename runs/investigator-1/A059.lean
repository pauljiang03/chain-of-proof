import ChainOfProof
open ChainOfProof

namespace Cert.A059

def cited : List Fact := [
  ⟨66, .fileCreated, 1424037128960000, 10000, 22, 19⟩,
  ⟨202, .fileModified, 1417706690000000, 10000, 22, 19⟩,
  ⟨67, .fileCreated, 1424037129290000, 10000, 51, 19⟩,
  ⟨205, .fileModified, 1418746226000000, 10000, 51, 19⟩,
  ⟨68, .fileCreated, 1424037130630000, 10000, 52, 19⟩,
  ⟨250, .fileModified, 1422046030000000, 10000, 52, 19⟩,
  ⟨69, .fileCreated, 1424037132550000, 10000, 53, 19⟩,
  ⟨209, .fileModified, 1418939458000000, 10000, 53, 19⟩,
  ⟨70, .fileCreated, 1424037140430000, 10000, 18, 19⟩,
  ⟨213, .fileModified, 1419018826000000, 10000, 18, 19⟩ ]

def claim : Claim := .both (Sets.copiedHere 66 202) (.both (Sets.copiedHere 67 205) (.both (Sets.copiedHere 68 250) (.both (Sets.copiedHere 69 209) (Sets.copiedHere 70 213))))

theorem verified : holds cited claim = true := by decide +kernel

end Cert.A059

#print axioms Cert.A059.verified
