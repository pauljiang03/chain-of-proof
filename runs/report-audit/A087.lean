import ChainOfProof
open ChainOfProof

namespace Cert.A087

def cited : List Fact := [
  ⟨217, .webSearch, 1427133729303892, 1, 130, 125⟩,
  ⟨218, .webSearch, 1427133764343210, 1, 131, 125⟩,
  ⟨221, .webSearch, 1427133820424839, 1, 132, 125⟩,
  ⟨227, .webSearch, 1427133948655159, 1, 133, 125⟩,
  ⟨228, .webSearch, 1427133987545120, 1, 134, 125⟩ ]

def claim : Claim := .both (Sets.searched 217) (.both (Sets.searched 218) (.both (Sets.searched 221) (.both (Sets.searched 227) (Sets.searched 228))))

theorem verified : holds cited claim = true := by decide +kernel

end Cert.A087

#print axioms Cert.A087.verified
