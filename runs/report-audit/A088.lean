import ChainOfProof
open ChainOfProof

namespace Cert.A088

def cited : List Fact := [
  ⟨236, .webSearch, 1427134111817280, 1, 137, 126⟩,
  ⟨237, .webSearch, 1427134134101318, 1, 138, 126⟩,
  ⟨239, .webSearch, 1427134203820419, 1, 139, 126⟩,
  ⟨241, .webSearch, 1427134310582693, 1, 141, 126⟩,
  ⟨242, .webSearch, 1427134355567263, 1, 142, 126⟩,
  ⟨246, .webSearch, 1427134451977428, 1, 145, 126⟩ ]

def claim : Claim := .both (Sets.searched 236) (.both (Sets.searched 237) (.both (Sets.searched 239) (.both (Sets.searched 241) (.both (Sets.searched 242) (Sets.searched 246)))))

theorem verified : holds cited claim = true := by decide +kernel

end Cert.A088

#print axioms Cert.A088.verified
