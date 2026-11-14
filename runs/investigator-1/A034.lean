import ChainOfProof
open ChainOfProof

namespace Cert.A034

def cited : List Fact := [
  ⟨310, .webSearch, 1427134111817280, 1, 171, 160⟩,
  ⟨311, .webSearch, 1427134134101318, 1, 172, 160⟩,
  ⟨313, .webSearch, 1427134203820419, 1, 173, 160⟩,
  ⟨314, .webSearch, 1427134227643461, 1, 174, 160⟩,
  ⟨315, .webSearch, 1427134310582693, 1, 175, 160⟩,
  ⟨316, .webSearch, 1427134355567263, 1, 176, 160⟩,
  ⟨317, .webSearch, 1427134400892344, 1, 177, 160⟩,
  ⟨318, .webSearch, 1427134417494371, 1, 178, 160⟩,
  ⟨320, .webSearch, 1427134451977428, 1, 179, 160⟩ ]

def claim : Claim := .both (Sets.searched 310) (.both (Sets.searched 311) (.both (Sets.searched 313) (.both (Sets.searched 314) (.both (Sets.searched 315) (.both (Sets.searched 316) (.both (Sets.searched 317) (.both (Sets.searched 318) (Sets.searched 320))))))))

theorem verified : holds cited claim = true := by decide +kernel

end Cert.A034

#print axioms Cert.A034.verified
