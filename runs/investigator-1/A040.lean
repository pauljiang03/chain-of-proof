import ChainOfProof
open ChainOfProof

namespace Cert.A040

def cited : List Fact := [
  ⟨2264, .fileDownloaded, 1427140547290982, 1, 891, 1416⟩,
  ⟨2266, .fileDownloaded, 1427140590660454, 1, 889, 1418⟩,
  ⟨2267, .fileDownloaded, 1427294853852505, 1, 963, 1396⟩,
  ⟨2269, .fileDownloaded, 1427294902173805, 1, 965, 1419⟩ ]

def claim : Claim := .both (Sets.downloaded 2264) (.both (Sets.downloaded 2266) (.both (Sets.downloaded 2267) (Sets.downloaded 2269)))

theorem verified : holds cited claim = true := by decide +kernel

end Cert.A040

#print axioms Cert.A040.verified
