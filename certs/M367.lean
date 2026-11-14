import ChainOfProof
open ChainOfProof

namespace Cert.M367

def cited : List Fact := [
  ⟨2262, .fileDownloaded, 1427140547290982, 1, 891, 1414⟩,
  ⟨2263, .fileDownloaded, 1427140547290982, 1, 891, 1415⟩,
  ⟨2264, .fileDownloaded, 1427140547290982, 1, 891, 1416⟩,
  ⟨2265, .fileDownloaded, 1427140590660454, 1, 889, 1417⟩,
  ⟨2266, .fileDownloaded, 1427140590660454, 1, 889, 1418⟩,
  ⟨2267, .fileDownloaded, 1427294853852505, 1, 963, 1396⟩,
  ⟨2268, .fileDownloaded, 1427294864103305, 1, 963, 1396⟩,
  ⟨2269, .fileDownloaded, 1427294902173805, 1, 965, 1419⟩,
  ⟨2270, .fileDownloaded, 1427294910739805, 1, 965, 1419⟩ ]

def census : Census := .total .fileDownloaded 9

theorem verified : counts cited census = true := by decide +kernel

end Cert.M367

#print axioms Cert.M367.verified
